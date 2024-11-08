import sqlite3


def update_fenix_games():
    # Connect to the SQLite database
    conn = sqlite3.connect('mahjong.db')
    cursor = conn.cursor()

    # List of game IDs to update
    game_ids = [130, 122, 100, 79]

    # Update `is_fenix` to TRUE for the specified games
    cursor.executemany("UPDATE games SET is_fenix = TRUE WHERE game_id = ?", [(game_id,) for game_id in game_ids])

    # Commit the changes and close the connection
    conn.commit()
    print(f"Updated is_fenix to TRUE for game IDs: {game_ids}")
    conn.close()


if __name__ == "__main__":
    update_fenix_games()

