import sqlite3

def cleanup_database(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete all records from the games table
    cursor.execute("DELETE FROM games")
    print("All records from 'games' table have been deleted.")

    # Reset the players' statistics
    cursor.execute("UPDATE players SET games_played = 0, rank1_count = 0, rank2_count = 0, rank3_count = 0, rank4_count = 0")
    print("All player statistics have been reset.")

    # Optionally, delete all players except for testing purposes
    # cursor.execute("DELETE FROM players")
    # print("All records from 'players' table have been deleted.")

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("Database cleanup completed successfully.")

if __name__ == "__main__":
    # Provide the path to your database
    db_path = 'mahjong.db'
    cleanup_database(db_path)