import sqlite3

def delete_player(player_name, db_path='mahjong.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find all games that the player participated in
    cursor.execute("""
        SELECT game_id, player1, player2, player3, player4,
               final_score1, final_score2, final_score3, final_score4
        FROM games
        WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
    """, (player_name, player_name, player_name, player_name))
    games = cursor.fetchall()

    # For each game the player was involved in, update the other players' statistics
    for game in games:
        game_id = game['game_id']
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
            for k, idx in enumerate(tied_indices):
                ranks[idx] = i + k + 1
            i = j + 1

        # Update the other players' statistics by decrementing the rank counts
        for i, player in enumerate(players):
            if player == player_name:
                continue  # Skip the player to be deleted

            rank = ranks[i]
            rank_column = f"rank{rank}_count"
            cursor.execute(f"""
                UPDATE players
                SET games_played = games_played - 1,
                    {rank_column} = {rank_column} - 1
                WHERE name = ?
            """, (player,))

        # Delete the game from the games table
        cursor.execute("DELETE FROM games WHERE game_id = ?", (game_id,))

    # Finally, delete the player from the players table
    cursor.execute("DELETE FROM players WHERE name = ?", (player_name,))
    print(f"Player '{player_name}' and all their games have been deleted.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    player_name_to_delete = input("Enter the name of the player to delete: ")
    delete_player(player_name_to_delete)
