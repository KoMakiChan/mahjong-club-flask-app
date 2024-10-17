import sqlite3

# Connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('mahjong.db')
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

# Insert a pseudo game into the database
def insert_pseudo_game():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the pseudo game directly into the database
    cursor.execute("""
    INSERT INTO games (player1, player2, player3, player4, raw_score1, raw_score2, raw_score3, raw_score4, final_score1, final_score2, final_score3, final_score4)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('A', 'B', 'C', 'D', 10000, 10000, 10000, 10000, 400.0, -2000.0, -5.0, -5.0))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    insert_pseudo_game()
    print("Pseudo game inserted into the database.")