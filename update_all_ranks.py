import sqlite3


# Helper function to calculate the player's highest possible rank based on their game history
def calculate_best_rank_for_player(games, player_name):
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
        (10, 2.5),  # Rank 6 (2-dan)
        (10, 2.6),  # Rank 5 (1-dan)
        (10, 2.7),  # Rank 4 (1-que)
        (5, 2.8),  # Rank 3 (2-que)
        (5, 2.9),  # Rank 2 (3-que)
        (5, 3.0),  # Rank 1 (4-que)
    ]

    print(f"\nDEBUG: Calculating best rank for {player_name}...")

    # Initialize a list to store the ranks of the player for each game
    player_ranks = []

    # Calculate the ranks for each game
    for idx, game in enumerate(games):
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
        print(
            f"DEBUG: Game {idx + 1}: Player '{player_name}' had final score {player_final_score} and rank {player_rank}")

    # Initialize the best possible rank
    best_rank = 0
    total_games = len(player_ranks)

    print(f"DEBUG: Total games for {player_name}: {total_games}")
    print(f"DEBUG: Player ranks per game: {player_ranks}")

    # Iterate over the rank thresholds from highest (10-dan) to lowest (4-que)
    for rank_index, (required_games, max_avg) in enumerate(rank_thresholds):
        if total_games >= required_games:
            # Check all possible windows of 'required_games'
            for start_idx in range(total_games - required_games + 1):
                recent_ranks = player_ranks[start_idx:start_idx + required_games]
                avg_position = sum(recent_ranks) / required_games

                print(
                    f"DEBUG: Checking window for {required_games} games, avg rank: {avg_position:.2f}, required avg ≤ {max_avg}")
                print(f"DEBUG: Window ranks: {recent_ranks}")

                # If the player's average position meets the rank criteria, update their best rank
                if avg_position <= max_avg:
                    potential_best_rank = 14 - rank_index  # Rank 14 is 10-dan
                    print(f"DEBUG: Player '{player_name}' can achieve rank {potential_best_rank} based on this window.")

                    # Update best_rank only if it's higher than the current best_rank
                    if potential_best_rank > best_rank:
                        best_rank = potential_best_rank
                        # Since we are checking from highest to lowest, we can break once a higher rank is found
                        break

            # If a rank has been found, no need to check lower ranks
            if best_rank > 0:
                print(f"DEBUG: Best rank found for '{player_name}' is {best_rank}. No need to check lower ranks.")
                break

    print(f"DEBUG: Best possible rank for {player_name}: {best_rank}")
    return best_rank  # Return the best possible rank


# Main function to recalculate ranks for all players
def recalculate_all_players_ranks():
    # Connect to the database
    conn = sqlite3.connect('mahjong.db')
    conn.row_factory = sqlite3.Row  # This line ensures rows are returned as dictionaries
    cursor = conn.cursor()

    # Fetch all players
    cursor.execute("SELECT name FROM players")
    players = cursor.fetchall()

    # Iterate through all players and recalculate their highest rank
    for player in players:
        player_name = player['name']
        print(f"\nDEBUG: Starting recalculation for player '{player_name}'...")

        # Fetch the player's games sorted by game_date in descending order
        cursor.execute("""
            SELECT final_score1, final_score2, final_score3, final_score4, 
                   player1, player2, player3, player4
            FROM games
            WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
            ORDER BY game_date DESC
        """, (player_name, player_name, player_name, player_name))

        games = cursor.fetchall()

        # Calculate the best rank based on the player's game history
        best_rank = calculate_best_rank_for_player(games, player_name)

        # Fetch the player's current highest rank
        cursor.execute("SELECT highest_rank FROM players WHERE name = ?", (player_name,))
        highest_rank_row = cursor.fetchone()
        highest_rank = highest_rank_row['highest_rank'] if highest_rank_row else 0

        print(f"DEBUG: Current highest rank for '{player_name}': {highest_rank}")

        # Update the player's highest rank in the database if the new best_rank is higher
        if best_rank > highest_rank:
            cursor.execute("UPDATE players SET highest_rank = ? WHERE name = ?", (best_rank, player_name))
            print(f"DEBUG: Updated '{player_name}'s rank to {best_rank}")
        else:
            print(f"DEBUG: No update needed for '{player_name}'s rank.")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("\nRanks recalculated for all players.")


# Run the script
if __name__ == "__main__":
    recalculate_all_players_ranks()
