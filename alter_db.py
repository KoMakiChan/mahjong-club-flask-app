import sqlite3


# Function to add the 'highest_rank' column to the 'players' table
def add_column():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('mahjong.db')  # Update this path if needed
        cursor = conn.cursor()

        # Check if the 'highest_rank' column already exists
        cursor.execute("PRAGMA table_info(players);")
        columns = [column[1] for column in cursor.fetchall()]

        if 'highest_rank' not in columns:
            # Execute the ALTER TABLE command to add the new column
            cursor.execute("ALTER TABLE players ADD COLUMN highest_rank INTEGER DEFAULT 0;")
            print("Column 'highest_rank' added successfully.")
        else:
            print("Column 'highest_rank' already exists.")

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")


# Execute the function
if __name__ == "__main__":
    add_column()

