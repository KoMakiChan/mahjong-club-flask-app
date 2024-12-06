import sqlite3
import random

def get_db_connection():
    conn = sqlite3.connect('mahjong.db')
    conn.row_factory = sqlite3.Row
    return conn

def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Reset all players' rates to 1500.0 in the DB (initial state)
    cursor.execute("UPDATE players SET rate = 1500.0")
    conn.commit()

    # Fetch all games by ascending date
    cursor.execute("SELECT * FROM games ORDER BY game_date ASC")
    all_games = cursor.fetchall()

    # Create a dictionary to hold player stats in memory
    # Structure: player_stats[player_name] = {'rate': float, 'games_played': int}
    player_stats = {}

    # Rank result mapping
    rank_result_map = {
        1: 45.0,
        2: 5.0,
        3: -15.0,
        4: -35.0
    }

    # We will print detailed info for the first 10 games
    PRINT_LIMIT = 10

    for game_index, game in enumerate(all_games, start=1):
        # Extract players and final scores
        players = [game['player1'], game['player2'], game['player3'], game['player4']]
        final_scores = [game['final_score1'], game['final_score2'], game['final_score3'], game['final_score4']]

        # Initialize players in stats if not present
        for p in players:
            if p not in player_stats:
                player_stats[p] = {'rate': 1500.0, 'games_played': 0}

        # Determine ranks for each player
        sorted_indices = sorted(range(4), key=lambda i: final_scores[i], reverse=True)
        ranks = [0]*4
        i = 0
        while i < 4:
            j = i
            while j < 3 and final_scores[sorted_indices[j]] == final_scores[sorted_indices[j+1]]:
                j += 1
            tied_indices = sorted_indices[i:j+1]
            random.shuffle(tied_indices)
            for k, idx in enumerate(tied_indices):
                ranks[idx] = i + k + 1
            i = j + 1

        current_rates = [player_stats[p]['rate'] for p in players]
        total_rate = sum(current_rates)
        avg_rate = total_rate / 4.0
        if avg_rate < 1500.0:
            avg_rate = 1500.0

        if game_index <= PRINT_LIMIT:
            print(f"\n--- Game #{game_index} ---")
            print(f"Game ID: {game['game_id']} Date: {game['game_date']}")
            print("Players and Final Scores:")
            for p, s in zip(players, final_scores):
                print(f"  {p}: {s}")
            print("Current Player Stats before update:")
            

        # Calculate new rates
        for idx, player in enumerate(players):
            player_rate = player_stats[player]['rate']
            games_played = player_stats[player]['games_played']
            rate_coef = max(1 - games_played * 0.002, 0.2)
            match_result = rank_result_map[ranks[idx]]

            rate_change = rate_coef * (match_result + (avg_rate - player_rate) / 40.0)
            new_rate = player_rate + rate_change

            if game_index <= PRINT_LIMIT:
                print(f"\nUpdating {player}:")
                print(f"  Match Result: {match_result}")
                print(f"  Player Rate Before: {player_rate:.2f}")
                print(f"  Games Played: {games_played}")
                print(f"  Rate Coef: {rate_coef:.3f}")
        
                print(f"  Rate Change = {rate_change:.2f}")
                print(f"  New Rate = {new_rate:.2f}")

            player_stats[player]['rate'] = new_rate

        # Increment games_played for each player
        for p in players:
            player_stats[p]['games_played'] += 1

    # After all games processed, update DB
    for player, stats in player_stats.items():
        cursor.execute("UPDATE players SET rate = ? WHERE name = ?", (stats['rate'], player))
    conn.commit()

    conn.close()
    print("\nRates recalculated successfully from scratch using in-memory games_played counts.")

if __name__ == "__main__":
    main()

