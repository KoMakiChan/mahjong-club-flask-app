from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3
import random
import os
from datetime import datetime
from urllib.parse import unquote

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

    # SQL query to calculate player stats dynamically from the games table
    cursor.execute("""
    SELECT 
        p.name,
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
    conn.close()
  # Modify the total_points to round it before sending to the template
    rounded_players = []
    for player in players:
        rounded_player = dict(player)
        rounded_player['total_points'] = round(player['total_points'], 1)
        rounded_players.append(rounded_player)

    return render_template("home.html", players=rounded_players)

# Route for the admin login page
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == os.getenv('FLASK_ADMIN_PASSWORD') :
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
        # Add a new player
        if "add_player" in request.form:
            player_name = request.form["player_name"]
            try:
                cursor.execute("INSERT INTO players (name) VALUES (?)", (player_name,))
                flash(f"Player '{player_name}' added successfully.", "success")
            except sqlite3.IntegrityError:
                flash(f"Player '{player_name}' already exists.", "danger")

        # Add a new game
        # Add a new game
        elif "add_game" in request.form:
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
                # Calculate final scores and determine ranks
                final_scores = [(score / 1000) - 30 for score in scores]

                # Sort indices by final scores in descending order
                sorted_indices = sorted(range(4), key=lambda i: final_scores[i], reverse=True)

                # Ranking bonuses: 50, 10, -10, -30
                bonuses = [50, 10, -10, -30]

                # Apply ranking bonuses
                for i, idx in enumerate(sorted_indices):
                    final_scores[idx] += bonuses[i]

                # Round final scores to one decimal place
                final_scores = [round(score, 1) for score in final_scores]

                # Insert the new game into the database
                cursor.execute("""
                    INSERT INTO games (player1, player2, player3, player4, 
                                       raw_score1, raw_score2, raw_score3, raw_score4,
                                       final_score1, final_score2, final_score3, final_score4)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, players + scores + final_scores)

                # Update each player's statistics in the database
                for i, player in enumerate(players):
                    rank = sorted_indices.index(i) + 1
                    rank_column = f"rank{rank}_count"
                    cursor.execute(f"""
                        UPDATE players
                        SET games_played = games_played + 1,
                            {rank_column} = {rank_column} + 1
                        WHERE name = ?
                    """, (player,))

                flash("Game added successfully!", "success")

        # Delete a game
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

    # Fetch the players and games for the admin page
    cursor.execute("SELECT * FROM players ORDER BY name")
    players = cursor.fetchall()

    cursor.execute("SELECT game_id, game_date, player1, player2, player3, player4, raw_score1, raw_score2, raw_score3, raw_score4 FROM games ORDER BY game_date DESC")
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
    player_name = unquote(player_name) 
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


def update_player_stats(cursor, players, scores):
    # Sort players by their scores (descending)
    sorted_indices = sorted(range(4), key=lambda i: scores[i], reverse=True)
    print(f"Sorted indices for stats: {sorted_indices}")  # Debugging output

    # Determine ranks based on the sorted scores
    ranks = [0] * 4
    for i in range(4):
        if i > 0 and scores[sorted_indices[i]] == scores[sorted_indices[i - 1]]:
            ranks[sorted_indices[i]] = ranks[sorted_indices[i - 1]]
        else:
            ranks[sorted_indices[i]] = i + 1

    print(f"Ranks: {ranks}")  # Debugging output

    # Map ranks to rank counts: 1 -> Rank1, 2 -> Rank2, etc.
    rank_counts = [0, 0, 0, 0]
    for rank in ranks:
        rank_counts[rank - 1] += 1

    print(f"Rank counts: {rank_counts}")  # Debugging output

    # Update each player's statistics in the database
    for i, player in enumerate(players):
        cursor.execute("""
            UPDATE players
            SET games_played = games_played + 1,
                rank1_count = rank1_count + ?,
                rank2_count = rank2_count + ?,
                rank3_count = rank3_count + ?,
                rank4_count = rank4_count + ?
            WHERE name = ?
        """, (rank_counts[0], rank_counts[1], rank_counts[2], rank_counts[3], player))

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
