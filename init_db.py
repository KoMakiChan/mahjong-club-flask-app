import sqlite3

# Connect to SQLite database (creates 'mahjong.db' if it doesn't exist)
conn = sqlite3.connect('mahjong.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Create 'players' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    games_played INTEGER DEFAULT 0,
    rank1_count INTEGER DEFAULT 0,
    rank2_count INTEGER DEFAULT 0,
    rank3_count INTEGER DEFAULT 0,
    rank4_count INTEGER DEFAULT 0
)
''')

# Create 'games' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1 TEXT NOT NULL,
    player2 TEXT NOT NULL,
    player3 TEXT NOT NULL,
    player4 TEXT NOT NULL,
    raw_score1 INTEGER NOT NULL,
    raw_score2 INTEGER NOT NULL,
    raw_score3 INTEGER NOT NULL,
    raw_score4 INTEGER NOT NULL,
    final_score1 INTEGER NOT NULL,
    final_score2 INTEGER NOT NULL,
    final_score3 INTEGER NOT NULL,
    final_score4 INTEGER NOT NULL,
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database initialized successfully!")
