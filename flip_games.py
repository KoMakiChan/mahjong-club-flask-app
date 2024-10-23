import sqlite3
from datetime import datetime, timedelta


# Connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('mahjong.db')
    conn.row_factory = sqlite3.Row  # To retrieve rows as dictionaries
    return conn


# Get all games played on a specific date
def get_games_by_date(date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE DATE(game_date) = ?", (date_str,))
    games = cursor.fetchall()
    conn.close()
    return games


# Update the game_date for a specific game
def update_game_time(game_id, new_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE games SET game_date = ? WHERE game_id = ?", (new_time, game_id))
    conn.commit()
    conn.close()


# Flip the order of games by modifying their timestamps
def flip_game_times(games, base_date):
    # Sort the games by their original timestamps (just to ensure correct order before flipping)
    games_sorted = sorted(games, key=lambda x: x['game_date'])

    # Create new timestamps in reverse order
    base_time = datetime.strptime(f"{base_date} 00:00:00", "%Y-%m-%d %H:%M:%S")
    time_increment = timedelta(minutes=5)  # 5-minute increments between games (you can adjust this)

    for i, game in enumerate(reversed(games_sorted)):
        new_time = base_time + i * time_increment
        update_game_time(game['game_id'], new_time.strftime("%Y-%m-%d %H:%M:%S"))
        print(f"Updated game ID {game['game_id']} with new time: {new_time}")


if __name__ == "__main__":
    # Date of games you want to flip (October 17th in this case)
    target_date = "2024-10-17"

    # Get the games played on the target date
    games_on_target_date = get_games_by_date(target_date)

    # Flip the game times
    if games_on_target_date:
        flip_game_times(games_on_target_date, target_date)
        print("Game times flipped successfully!")
    else:
        print(f"No games found on {target_date}")

