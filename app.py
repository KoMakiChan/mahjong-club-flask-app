from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3
import random
from urllib.parse import unquote
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session management

# Custom filter to safely round values
def safe_round(value, precision=2):
    try:
        if value is None:
            return 0  # Default to 0 if value is None
        return round(value, precision)
    except (TypeError, ValueError):
        return 0  # Return 0 if rounding fails for any reason

# Register the custom filter with Flask
app.jinja_env.filters['safe_round'] = safe_round


# Helper function to connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('mahjong.db')
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

# Route for the home page (default)
@app.route("/")
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    # SQL query to calculate player stats dynamically from the games table and players table
    cursor.execute("""
    SELECT 
        p.name,
        p.games_played,
        p.rank1_count,
        p.rank2_count,
        p.rank3_count,
        p.rank4_count,
        p.highest_rank,
        COUNT(g.game_id) AS games_played,
        SUM(CASE 
            WHEN g.player1 = p.name THEN g.final_score1
            WHEN g.player2 = p.name THEN g.final_score2
            WHEN g.player3 = p.name THEN g.final_score3
            WHEN g.player4 = p.name THEN g.final_score4
            ELSE 0
        END) AS total_points
    FROM players p
    LEFT JOIN games g
        ON p.name IN (g.player1, g.player2, g.player3, g.player4)
    GROUP BY p.name
    ORDER BY total_points DESC
    """)

    players = cursor.fetchall()

    # Step 1: Get the 4th highest rank to determine qualifying players for the Fenix game
    cursor.execute("SELECT highest_rank FROM players ORDER BY highest_rank DESC LIMIT 4")
    ranks = cursor.fetchall()

    if len(ranks) < 4:
        qualifying_rank = ranks[-1]['highest_rank'] if ranks else 0
    else:
        qualifying_rank = ranks[-1]['highest_rank'] - 1  # Qualify if rank >= (4th highest - 1)

    # Step 2: Fetch the current Fenix from the latest Fenix game
    cursor.execute("""
        SELECT * FROM games
        WHERE player1 IN (SELECT name FROM players WHERE highest_rank >= ?)
          AND player2 IN (SELECT name FROM players WHERE highest_rank >= ?)
          AND player3 IN (SELECT name FROM players WHERE highest_rank >= ?)
          AND player4 IN (SELECT name FROM players WHERE highest_rank >= ?)
        ORDER BY game_date DESC LIMIT 1
        """, (qualifying_rank, qualifying_rank, qualifying_rank, qualifying_rank))

    latest_fenix_game = cursor.fetchone()

    if latest_fenix_game:
        current_fenix = get_winner(latest_fenix_game)
    else:
        current_fenix = None  # Fallback if no Fenix game exists
    player_data = []
    for player in players:
        # Calculate the average rank directly from the player's rank counts
        total_games = player['games_played']
        if total_games > 0:
            # Weigh the ranks: 1*rank1_count + 2*rank2_count + 3*rank3_count + 4*rank4_count
            total_rank_score = (1 * player['rank1_count']) + (2 * player['rank2_count']) + (3 * player['rank3_count']) + (4 * player['rank4_count'])
            average_rank = round(total_rank_score / total_games, 2)
        else:
            average_rank = 'N/A'

        # Append the player's data along with the calculated average rank
        player_data.append({
            'name': player['name'],
            'total_points': round(player['total_points'], 1),
            'games_played': total_games,
            'highest_rank': player['highest_rank'],
            'average_rank': average_rank  # Use the calculated average rank
        })

    conn.close()

    return render_template("home.html", players=player_data, current_fenix=current_fenix)


# Route for the admin login page
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == "1":
            session["is_admin"] = True  # Set admin session
            flash("Logged in as admin.", "success")
            return redirect(url_for("admin_page"))
        else:
            flash("Invalid password.", "danger")
    return render_template("admin_login.html")

# Route for the admin page
@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if not session.get("is_admin"):
        flash("Admin access required.", "danger")
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        # Add a new game
        if "add_game" in request.form:
            players = [request.form[f"player{i}"] for i in range(1, 5)]
            scores = [int(request.form[f"score{i}"]) for i in range(1, 5)]

            # Check for unique players and score validity
            if len(set(players)) != 4:
                flash("All players must be unique.", "danger")
            elif sum(scores) != 100000:
                flash("Total raw points must add up to 100,000.", "danger")
            elif not all(score % 100 == 0 for score in scores):
                flash("All scores must be multiples of 100.", "danger")
            else:
                # Calculate final scores and assign ranks
                final_scores = [(score / 1000) - 30 for score in scores]
                sorted_indices = sorted(range(4), key=lambda i: final_scores[i], reverse=True)

                # Handle ranking bonuses
                bonuses = [50, 10, -10, -30]
                ranks = [0] * 4
                i = 0
                while i < 4:
                    j = i
                    while j < 3 and final_scores[sorted_indices[j]] == final_scores[sorted_indices[j + 1]]:
                        j += 1
                    tied_indices = sorted_indices[i:j + 1]
                    random.shuffle(tied_indices)
                    for k, idx in enumerate(tied_indices):
                        ranks[idx] = i + k + 1
                    i = j + 1

                for i, idx in enumerate(sorted_indices):
                    final_scores[idx] += bonuses[i]
                final_scores = [round(score, 1) for score in final_scores]

                # Insert the new game into the database
                cursor.execute("""
                    INSERT INTO games (player1, player2, player3, player4, 
                                       raw_score1, raw_score2, raw_score3, raw_score4,
                                       final_score1, final_score2, final_score3, final_score4)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, players + scores + final_scores)

                conn.commit()  # Commit the game insertion

                # Update the rank statistics for each player after the game is added
                for i, player in enumerate(players):
                    rank_column = f"rank{ranks[i]}_count"
                    cursor.execute(f"""
                        UPDATE players
                        SET games_played = games_played + 1,
                            {rank_column} = {rank_column} + 1
                        WHERE name = ?
                    """, (player,))

                    # Recalculate rank for each player inline
                    # Fetch the player's recent games (up to 30 or fewer, depending on rank threshold)
                    cursor.execute("""
                    SELECT final_score1, final_score2, final_score3, final_score4, 
                           player1, player2, player3, player4
                    FROM games
                    WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
                    ORDER BY game_date DESC
                    LIMIT 30
                    """, (player, player, player, player))

                    games = cursor.fetchall()

                    # Calculate the player's current rank based on their recent games
                    current_rank = calculate_player_rank(games, player)

                    # Fetch the highest rank the player ever achieved
                    cursor.execute("SELECT highest_rank FROM players WHERE name = ?", (player,))
                    highest_rank = cursor.fetchone()['highest_rank']

                    # Update only if the current rank is higher than the highest rank
                    if current_rank > highest_rank:
                        cursor.execute("UPDATE players SET highest_rank = ? WHERE name = ?", (current_rank, player))

                conn.commit()  # Commit the rank updates
                flash("Game and ranks updated successfully!", "success")

        elif "delete_game" in request.form:
            game_id = request.form["game_id"]

            # Retrieve the game data before deleting
            cursor.execute("""
                     SELECT player1, player2, player3, player4,
                            final_score1, final_score2, final_score3, final_score4
                     FROM games WHERE game_id = ?
                 """, (game_id,))
            game = cursor.fetchone()

            if game:
                players = [game['player1'], game['player2'], game['player3'], game['player4']]
                final_scores = [game['final_score1'], game['final_score2'], game['final_score3'], game['final_score4']]

                # Determine ranks based on final scores
                sorted_indices = sorted(range(4), key=lambda i: final_scores[i], reverse=True)
                ranks = [0] * 4

                # Assign ranks considering ties, randomly assigning tied ranks
                i = 0
                while i < 4:
                    j = i
                    while j < 3 and final_scores[sorted_indices[j]] == final_scores[sorted_indices[j + 1]]:
                        j += 1
                    tied_indices = sorted_indices[i:j + 1]
                    random.shuffle(tied_indices)  # Randomly assign ranks among tied players
                    for k, idx in enumerate(tied_indices):
                        ranks[idx] = i + k + 1
                    i = j + 1

                # Update each player's statistics by decrementing the rank counts
                for i, player in enumerate(players):
                    rank = ranks[i]
                    rank_column = f"rank{rank}_count"
                    cursor.execute(f"""
                             UPDATE players
                             SET games_played = games_played - 1,
                                 {rank_column} = {rank_column} - 1
                             WHERE name = ?
                         """, (player,))

                # Delete the game
                cursor.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
                flash("Game deleted successfully!", "success")

        conn.commit()
    conn.close()
    # Fetch the players and games for the admin page
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players ORDER BY name")
    players = cursor.fetchall()

    cursor.execute("""SELECT game_id, game_date, player1, player2, player3, player4, raw_score1, 
    raw_score2, raw_score3, raw_score4 FROM games ORDER BY game_date DESC""")
    games = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", players=players, games=games)


@app.route("/view-past-games", methods=["GET", "POST"])
def view_past_games():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Handle filters if they are provided
    player_filter = request.form.get("player_filter")
    date_filter = request.form.get("date_filter")

    query = """
    SELECT game_date, player1, player2, player3, player4, raw_score1, raw_score2, raw_score3, raw_score4
    FROM games WHERE 1=1
    """
    params = []

    if player_filter:
        query += " AND (? IN (player1, player2, player3, player4))"
        params.append(player_filter)

    if date_filter:
        query += " AND DATE(game_date) = ?"
        params.append(date_filter)

    query += " ORDER BY game_date DESC"
    cursor.execute(query, params)
    games = cursor.fetchall()

    # Fetch players for the dropdown
    cursor.execute("SELECT name FROM players")
    players = cursor.fetchall()

    conn.close()

    return render_template("view_past_games.html", games=games, players=players)

@app.route("/player/<player_name>")
def player_statistics(player_name):
    player_name = unquote(player_name)  # Decode the URL-encoded player name
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the player's game history
    cursor.execute("""
    SELECT game_date, player1, player2, player3, player4, 
           raw_score1, raw_score2, raw_score3, raw_score4,
           final_score1, final_score2, final_score3, final_score4
    FROM games 
    WHERE ? IN (player1, player2, player3, player4)
    ORDER BY game_date DESC
    """, (player_name,))
    games = cursor.fetchall()

    # Track cumulative total points for the player
    running_total = 0
    processed_games = []

    # Process each game in reverse order (oldest to newest) to calculate the running total
    for game in reversed(games):
        players_and_scores = [
            (game['player1'], game['raw_score1'], game['final_score1']),
            (game['player2'], game['raw_score2'], game['final_score2']),
            (game['player3'], game['raw_score3'], game['final_score3']),
            (game['player4'], game['raw_score4'], game['final_score4'])
        ]
        players_and_scores.sort(key=lambda x: x[2], reverse=True)  # Sort by final score

        # Find the current player's final score
        current_game_points = None
        for player, raw_score, final_score in players_and_scores:
            if player == player_name:
                current_game_points = final_score
                break

        # Calculate the point change and update the running total
        previous_total = running_total
        running_total += current_game_points  # Update cumulative points

        processed_games.append({
            'game_date': game['game_date'],
            'players_and_scores': players_and_scores,
            'point_change' : round(current_game_points,1),
            'previous_total': round(previous_total, 1),
            'total_points_after_game': round(running_total, 1)  # Round the running total
        })

    # Reverse processed games back to descending order (newest to oldest)
    processed_games.reverse()

    conn.close()

    return render_template("player_statistics.html", player_name=player_name, games=processed_games)

# Helper function to determine the winner of a Fenix game
def get_winner(game):
    scores = [
        (game['player1'], game['final_score1']),
        (game['player2'], game['final_score2']),
        (game['player3'], game['final_score3']),
        (game['player4'], game['final_score4'])
    ]
    return max(scores, key=lambda x: x[1])[0]  # Return the player with the highest final score
app.jinja_env.globals.update(get_winner=get_winner)

@app.route("/fenix")
def fenix_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Step 1: Get the 4th highest rank
    cursor.execute("SELECT highest_rank FROM players ORDER BY highest_rank DESC LIMIT 4")
    ranks = cursor.fetchall()
    if len(ranks) < 4:
        qualifying_rank = ranks[-1]['highest_rank'] if ranks else 0
    else:
        qualifying_rank = ranks[-1]['highest_rank'] - 1  # Qualify if rank >= (4th highest - 1)

    # Step 2: Get the list of qualifying players
    cursor.execute("SELECT name, highest_rank FROM players WHERE highest_rank >= ?", (qualifying_rank,))
    qualifying_players = cursor.fetchall()

    # Step 3: Get all past Fenix games
    players_in_clause = ', '.join(['?'] * len(qualifying_players))
    qualifying_names = [player['name'] for player in qualifying_players]
    cursor.execute(f"""
        SELECT * FROM games
        WHERE player1 IN ({players_in_clause})
          AND player2 IN ({players_in_clause})
          AND player3 IN ({players_in_clause})
          AND player4 IN ({players_in_clause})
        ORDER BY game_date DESC
    """, (*qualifying_names, *qualifying_names, *qualifying_names, *qualifying_names))
    fenix_games = cursor.fetchall()

    # Step 4: Determine the "current Fenix"
    current_fenix = None
    if fenix_games:
        latest_game = fenix_games[0]
        current_fenix = get_winner(latest_game)  # Get the winner using the helper function

    conn.close()

    return render_template("fenix.html", qualifying_players=qualifying_players, fenix_games=fenix_games, current_fenix=current_fenix, qualifying_rank=qualifying_rank)
# Function to calculate final scores
def calculate_final_scores(raw_scores):
    # Calculate base points: (raw_score // 1000) - 30
    base_points = [(score / 1000) - 30 for score in raw_scores]

    # Sort indices by raw scores in descending order
    sorted_indices = sorted(range(4), key=lambda i: raw_scores[i], reverse=True)

    # Ranking bonuses: 50, 10, -10, -30
    bonuses = [50, 10, -10, -30]
    final_scores = base_points[:]

    # Apply bonuses considering ties
    i = 0
    while i < 4:
        j = i
        while j < 3 and raw_scores[sorted_indices[j]] == raw_scores[sorted_indices[j + 1]]:
            j += 1
        # If there's a tie, split the bonuses equally
        split_bonus = sum(bonuses[i:j + 1]) / (j - i + 1)
        for k in range(i, j + 1):
            final_scores[sorted_indices[k]] += split_bonus
        i = j + 1

    # Round final scores to one decimal place
    final_scores = [round(score, 1) for score in final_scores]

    # Calculate ranks for each player
    ranks = [0] * 4
    rank_counts = [0, 0, 0, 0]
    rank_position = 1

    i = 0
    while i < 4:
        j = i
        while j < 3 and raw_scores[sorted_indices[j]] == raw_scores[sorted_indices[j + 1]]:
            j += 1
        for k in range(i, j + 1):
            ranks[sorted_indices[k]] = rank_position
            rank_counts[rank_position - 1] += 1
        rank_position += (j - i + 1)
        i = j + 1

    return final_scores, rank_counts



# New function to calculate the player's rank based on their last X games
def update_player_rank(player_name):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the player's recent games (up to 30 or fewer, depending on rank threshold)
    cursor.execute("""
    SELECT final_score1, final_score2, final_score3, final_score4, 
           player1, player2, player3, player4
    FROM games
    WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
    ORDER BY game_date DESC
    LIMIT 30
    """, (player_name, player_name, player_name, player_name))

    games = cursor.fetchall()

    # Calculate the player's current rank based on their recent games
    current_rank = calculate_player_rank(games, player_name)

    # Fetch the highest rank the player ever achieved
    cursor.execute("SELECT highest_rank FROM players WHERE name = ?", (player_name,))
    highest_rank = cursor.fetchone()['highest_rank']

    # Update only if the current rank is higher than the highest rank
    if current_rank > highest_rank:
        cursor.execute("UPDATE players SET highest_rank = ? WHERE name = ?", (current_rank, player_name))

    conn.commit()
    conn.close()
# New function to calculate the player's rank based on their last X games
def calculate_player_rank(games, player_name):
    # Rank thresholds: (required games, max average rank), starting from 10-dan (highest rank)
    rank_thresholds = [
        (30, 2.0),  # Rank 14 (10-dan)
        (25, 2.1),  # Rank 13 (9-dan)
        (25, 2.2),  # Rank 12 (8-dan)
        (25, 2.3),  # Rank 11 (7-dan)
        (20, 2.3),  # Rank 10 (6-dan)
        (20, 2.4),  # Rank 9 (5-dan)
        (15, 2.4),  # Rank 8 (4-dan)
        (15, 2.5),  # Rank 7 (3-dan)
        (10, 2.5),  # Rank 6 (2-dan) <-- Fixed!
        (10, 2.6),  # Rank 5 (1-dan)
        (10, 2.7),  # Rank 4 (1-que)
        (5, 2.8),  # Rank 3 (2-que)
        (5, 2.9),  # Rank 2 (3-que)
        (5, 3.0),  # Rank 1 (4-que)
    ]

    # Initialize a list to store the ranks of the player for each game
    player_ranks = []

    # Calculate the ranks for each game
    for game in games:
        final_scores = [
            game['final_score1'],
            game['final_score2'],
            game['final_score3'],
            game['final_score4']
        ]
        sorted_scores = sorted(final_scores, reverse=True)

        # Find the player's final score in this game
        if game['player1'] == player_name:
            player_final_score = game['final_score1']
        elif game['player2'] == player_name:
            player_final_score = game['final_score2']
        elif game['player3'] == player_name:
            player_final_score = game['final_score3']
        elif game['player4'] == player_name:
            player_final_score = game['final_score4']
        else:
            continue  # Skip if the player is not part of this game

        # Find the rank for the player in this game
        player_rank = sorted_scores.index(player_final_score) + 1
        player_ranks.append(player_rank)

    # Now we calculate the average rank for each threshold by sliding the window of recent games
    total_games = len(player_ranks)

    # Iterate over the rank thresholds from highest (10-dan) to lowest (4-que)
    for rank, (required_games, max_avg) in enumerate(rank_thresholds, start=1):
        if total_games >= required_games:
            # Calculate the average rank over the most recent 'required_games' number of games
            recent_ranks = player_ranks[-required_games:]  # Get the most recent 'required_games'
            avg_position = sum(recent_ranks) / required_games

            if avg_position <= max_avg:
                return 15 - rank  # Return the appropriate rank (Rank 14 in the database is 10-dan)

    return 0  # Default to rank 0 (5-que) in the system



# Helper function to map highest_rank to rank description
def rank_display(highest_rank):
    rank_mapping = {
        0: "5级",
        1: "4级",
        2: "3级",
        3: "2级",
        4: "1级",
        5: "初段",
        6: "二段",
        7: "三段",
        8: "四段",
        9: "五段",
        10: "六段",
        11: "七段",
        12: "八段",
        13: "九段",
        14: "十段"
    }
    return rank_mapping.get(highest_rank, "Unranked")
app.jinja_env.globals.update(rank_display=rank_display)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
