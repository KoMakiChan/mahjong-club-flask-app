import sqlite3

def inspect_db():
    conn = sqlite3.connect('mahjong.db')
    cursor = conn.cursor()

    # Check the contents of the players table
    print("Players Table:")
    cursor.execute("SELECT * FROM players;")
    players = cursor.fetchall()
    for player in players:
        print(player)

    # Check the contents of the games table
    print("\nGames Table:")
    cursor.execute("SELECT * FROM games;")
    games = cursor.fetchall()
    for game in games:
        print(game)

    conn.close()

if __name__ == "__main__":
    inspect_db()
