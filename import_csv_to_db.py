"""
This script imports data from a CSV file into the 'posts' table in the MySQL database.

It uses the DatabaseManager and DatabaseConfig from the 'utils' package to handle
database operations and configuration.
"""

import pandas as pd
from datetime import datetime
import numpy as np

from utils.db_manager import DatabaseManager
from utils.db_config import DatabaseConfig

def import_csv_to_database(csv_file_path: str):
    """
    Imports data from a CSV file to the 'posts' table in the database.

    Args:
        csv_file_path (str): The path to the CSV file to import.
    """
    print(f"Starting import process for {csv_file_path}...")

    try:
        # Load data from CSV
        df = pd.read_csv(csv_file_path)
        # Replace NaN values with None for database compatibility
        df = df.replace({np.nan: None})
        print(f"Successfully loaded {len(df)} rows from CSV file.")

    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return

    # Get database configuration
    db_config = DatabaseConfig.get_config()

    with DatabaseManager(**db_config) as db:
        # Ensure the database connection is established
        if not db.connection or not db.connection.is_connected():
            print("Failed to connect to the database. Please check your configuration.")
            return

        # Create the 'posts' table if it doesn't exist
        print("Ensuring 'posts' table exists...")
        if db.create_table():
            print("'posts' table is ready.")
        else:
            print("Failed to create or verify 'posts' table. Aborting import.")
            return

        # Prepare data for batch insertion
        posts_data = []
        for _, row in df.iterrows():
            try:
                post_data = {
                    'post_id': row.get('post_id'),
                    'content': row.get('content'),
                    'user_name': row.get('user_name'),
                    'user_id': row.get('user_id'),
                    'user_signature': row.get('user_signature'),
                    'publish_time': pd.to_datetime(row.get('publish_time')) if pd.notna(row.get('publish_time')) else None,
                    'like_count': int(row.get('like_count', 0)),
                    'comment_count': int(row.get('comment_count', 0)),
                    'forward_count': int(row.get('forward_count', 0)),
                    'ip_location': row.get('ip_location'),
                    'image_urls': row.get('image_urls'),
                    'user_homepage': row.get('user_homepage'),
                    'reply_to_id': row.get('reply_to_id'),
                    'reply_to_user': row.get('reply_to_user'),
                    'pred_1': None,
                    'pred_2': None
                }
                posts_data.append(post_data)
            except (ValueError, TypeError) as e:
                print(f"Skipping row due to data conversion error: {e} - Row: {row.to_dict()}")

        if not posts_data:
            print("No valid data to import after processing.")
            return

        # Insert data in batches
        print(f"Starting batch insert of {len(posts_data)} records...")
        if db.insert_posts_batch(posts_data):
            print("Successfully imported all data into the 'posts' table.")
        else:
            print("An error occurred during batch insertion.")

if __name__ == "__main__":
    # Specify the path to your CSV file
    CSV_PATH = 'DouyinDataset/douyin_comments_7546597652197084442.csv'
    import_csv_to_database(CSV_PATH)
