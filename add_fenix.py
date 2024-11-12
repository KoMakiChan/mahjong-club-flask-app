import sqlite3


def add_is_fenix_column():
    # Connect to the SQLite database
    conn = sqlite3.connect('mahjong.db')
    cursor = conn.cursor()

    # Add the is_fenix column if it doesn't already exist
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN is_fenix BOOLEAN DEFAULT FALSE;")
        print("Column 'is_fenix' added successfully.")
    except sqlite3.OperationalError as e:
        # This will catch if the column already exists
        if "duplicate column name" in str(e):
            print("Column 'is_fenix' already exists.")
        else:
            print(f"An error occurred: {e}")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    add_is_fenix_column()
