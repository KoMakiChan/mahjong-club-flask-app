import sqlite3

# Function to reset the rank for all players to 0
def reset_all_players_rank_to_zero():
    # Connect to the database
    conn = sqlite3.connect('mahjong.db')
    cursor = conn.cursor()

    # Update the rank of all players to 0 (reset)
    cursor.execute("UPDATE players SET highest_rank = 0")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    print("All players' ranks have been reset to 0.")

# Run the script
if __name__ == "__main__":
    reset_all_players_rank_to_zero()

