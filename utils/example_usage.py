"""
Example usage of the DatabaseManager for MySQL 8.0 CRUD operations.
This file demonstrates how to use the database utilities for the posts table.
"""

from datetime import datetime
from utils.db_manager import DatabaseManager
from utils.db_config import DatabaseConfig


def example_usage():
    """Demonstrate basic CRUD operations with the DatabaseManager."""
    
    # Get database configuration
    config = DatabaseConfig.get_config()
    
    # Create database manager instance
    with DatabaseManager(**config) as db:
        # Create the posts table
        print("Creating posts table...")
        db.create_table()
        
        # Example post data
        sample_post = {
            'post_id': 7546597652197084442,
            'content': '这是一个测试帖子内容，包含中文字符 🎉',
            'user_name': '测试用户',
            'user_id': 'test_user_123',
            'user_signature': '这是用户签名',
            'publish_time': datetime.now(),
            'like_count': 100,
            'comment_count': 25,
            'forward_count': 10,
            'ip_location': '北京',
            'image_urls': '["http://example.com/image1.jpg", "http://example.com/image2.jpg"]',
            'user_homepage': 'http://example.com/user/test_user_123',
            'reply_to_id': None,
            'reply_to_user': None,
            'pred_1': 0.85,
            'pred_2': 0.92
        }
        
        # Insert a single post
        print("Inserting sample post...")
        post_id = db.insert_post(sample_post)
        if post_id:
            print(f"Post inserted with ID: {post_id}")
        
        # Retrieve the post
        print("Retrieving post...")
        retrieved_post = db.get_post_by_id(post_id)
        if retrieved_post:
            print(f"Retrieved post: {retrieved_post['content'][:50]}...")
        
        # Update the post
        print("Updating post predictions...")
        update_success = db.update_predictions(post_id, 0.90, 0.95)
        if update_success:
            print("Predictions updated successfully")
        
        # Search posts
        print("Searching posts...")
        search_results = db.search_posts('测试')
        print(f"Found {len(search_results)} posts matching '测试'")
        
        # Get statistics
        print("Getting database statistics...")
        stats = db.get_post_statistics()
        if stats:
            print(f"Total posts: {stats.get('total_posts', 0)}")
            print(f"Unique users: {stats.get('unique_users', 0)}")
        
        # Example batch insert
        batch_posts = []
        for i in range(3):
            post = sample_post.copy()
            post['post_id'] = 7546597652197084442 + i + 1
            post['content'] = f'批量插入测试帖子 {i+1}'
            post['user_name'] = f'批量用户{i+1}'
            batch_posts.append(post)
        
        print("Batch inserting posts...")
        batch_success = db.insert_posts_batch(batch_posts)
        if batch_success:
            print(f"Batch inserted {len(batch_posts)} posts successfully")


def csv_import_example():
    """Example of importing data from CSV file to database."""
    import pandas as pd
    
    # Read CSV file (adjust path as needed)
    csv_file = 'DouyinDataset/douyin_comments_7546597652197084442.csv'
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} rows from CSV")
        
        # Get database configuration
        config = DatabaseConfig.get_config()
        
        with DatabaseManager(**config) as db:
            # Create table
            db.create_table()
            
            # Convert DataFrame to list of dictionaries
            posts_data = []
            for _, row in df.iterrows():
                post_data = {
                    'post_id': row.get('post_id', 0),
                    'content': row.get('content', ''),
                    'user_name': row.get('user_name', ''),
                    'user_id': row.get('user_id', ''),
                    'user_signature': row.get('user_signature'),
                    'publish_time': pd.to_datetime(row.get('publish_time', datetime.now())),
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
            
            # Batch insert
            success = db.insert_posts_batch(posts_data)
            if success:
                print(f"Successfully imported {len(posts_data)} posts from CSV")
            else:
                print("Failed to import CSV data")
                
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file}")
    except Exception as e:
        print(f"Error importing CSV: {e}")


if __name__ == "__main__":
    print("=== Database Manager Example Usage ===")
    
    # Run basic example
    example_usage()
    
    print("\n=== CSV Import Example ===")
    # Run CSV import example
    csv_import_example()
