"""
MySQL 8.0 Database Manager for Posts table operations.
Provides CRUD operations for the posts table with proper error handling and connection management.
"""

import mysql.connector
from mysql.connector import Error
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """MySQL 8.0 Database Manager for Posts table operations."""
    
    def __init__(self, host: str = 'localhost', port: int = 3306, 
                 database: str = 'douyin_analysis', user: str = 'root', 
                 password: str = '', charset: str = 'utf8mb4'):
        """
        Initialize database connection parameters.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            charset: Character set
        """
        self.config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            'charset': charset,
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
            'raise_on_warnings': True
        }
        self.connection = None
    
    def connect(self) -> bool:
        """
        Establish database connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                logger.info("Successfully connected to MySQL database")
                return True
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def create_table(self) -> bool:
        """
        Create the posts table if it doesn't exist.
        
        Returns:
            bool: True if table created successfully, False otherwise
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS posts (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            post_id BIGINT DEFAULT NULL COMMENT '帖子ID',
            content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '帖子内容',
            user_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '用户昵称',
            user_id VARCHAR(100) COMMENT '用户ID',
            user_signature VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户签名',
            publish_time DATETIME COMMENT '发布时间',
            like_count INT DEFAULT 0 COMMENT '点赞数',
            comment_count INT DEFAULT 0 COMMENT '评论数',
            forward_count INT DEFAULT 0 COMMENT '转发数',
            ip_location VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'IP归属地',
            image_urls TEXT DEFAULT NULL COMMENT '图片URLs',
            user_homepage VARCHAR(500) DEFAULT NULL COMMENT '用户主页链接',
            reply_to_id BIGINT DEFAULT NULL COMMENT '回复的帖子ID',
            reply_to_user VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '回复的用户',
            pred_1 FLOAT DEFAULT NULL COMMENT '预测字段1',
            pred_2 FLOAT DEFAULT NULL COMMENT '预测字段2',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_post_id (post_id),
            INDEX idx_user_id (user_id),
            INDEX idx_publish_time (publish_time),
            INDEX idx_reply_to_id (reply_to_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帖子数据表';
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_query)
            logger.info("Posts table created successfully")
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error creating table: {e}")
            return False
    
    def insert_post(self, post_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a new post into the database.
        
        Args:
            post_data: Dictionary containing post data
            
        Returns:
            int: ID of inserted post, None if failed
        """
        insert_query = """
        INSERT INTO posts (
            post_id, content, user_name, user_id, user_signature, publish_time,
            like_count, comment_count, forward_count, ip_location, image_urls,
            user_homepage, reply_to_id, reply_to_user, pred_1, pred_2
        ) VALUES (
            %(post_id)s, %(content)s, %(user_name)s, %(user_id)s, %(user_signature)s,
            %(publish_time)s, %(like_count)s, %(comment_count)s, %(forward_count)s,
            %(ip_location)s, %(image_urls)s, %(user_homepage)s, %(reply_to_id)s,
            %(reply_to_user)s, %(pred_1)s, %(pred_2)s
        )
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_query, post_data)
            post_id = cursor.lastrowid
            logger.info(f"Post inserted successfully with ID: {post_id}")
            cursor.close()
            return post_id
        except Error as e:
            logger.error(f"Error inserting post: {e}")
            return None
    
    def insert_posts_batch(self, posts_data: List[Dict[str, Any]]) -> bool:
        """
        Insert multiple posts in batch.
        
        Args:
            posts_data: List of dictionaries containing post data
            
        Returns:
            bool: True if all posts inserted successfully, False otherwise
        """
        insert_query = """
        INSERT INTO posts (
            post_id, content, user_name, user_id, user_signature, publish_time,
            like_count, comment_count, forward_count, ip_location, image_urls,
            user_homepage, reply_to_id, reply_to_user, pred_1, pred_2
        ) VALUES (
            %(post_id)s, %(content)s, %(user_name)s, %(user_id)s, %(user_signature)s,
            %(publish_time)s, %(like_count)s, %(comment_count)s, %(forward_count)s,
            %(ip_location)s, %(image_urls)s, %(user_homepage)s, %(reply_to_id)s,
            %(reply_to_user)s, %(pred_1)s, %(pred_2)s
        )
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.executemany(insert_query, posts_data)
            logger.info(f"Batch inserted {len(posts_data)} posts successfully")
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error batch inserting posts: {e}")
            return False
    
    def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a post by its ID.
        
        Args:
            post_id: Post ID to retrieve
            
        Returns:
            Dict containing post data, None if not found
        """
        select_query = "SELECT * FROM posts WHERE id = %s"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(select_query, (post_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error retrieving post by ID: {e}")
            return None
    
    def get_posts_by_user_id(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve posts by user ID.
        
        Args:
            user_id: User ID to search for
            limit: Maximum number of posts to return
            
        Returns:
            List of dictionaries containing post data
        """
        select_query = "SELECT * FROM posts WHERE user_id = %s ORDER BY publish_time DESC LIMIT %s"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(select_query, (user_id, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error retrieving posts by user ID: {e}")
            return []
    
    def get_posts_by_date_range(self, start_date: datetime, end_date: datetime, 
                               limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve posts within a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            limit: Maximum number of posts to return
            
        Returns:
            List of dictionaries containing post data
        """
        select_query = """
        SELECT * FROM posts 
        WHERE publish_time BETWEEN %s AND %s 
        ORDER BY publish_time DESC 
        LIMIT %s
        """
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(select_query, (start_date, end_date, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error retrieving posts by date range: {e}")
            return []
    
    def update_post(self, post_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update a post by its ID.
        
        Args:
            post_id: Post ID to update
            update_data: Dictionary containing fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not update_data:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for field, value in update_data.items():
            set_clauses.append(f"{field} = %s")
            values.append(value)
        
        values.append(post_id)
        update_query = f"UPDATE posts SET {', '.join(set_clauses)} WHERE id = %s"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(update_query, values)
            affected_rows = cursor.rowcount
            cursor.close()
            
            if affected_rows > 0:
                logger.info(f"Post {post_id} updated successfully")
                return True
            else:
                logger.warning(f"No post found with ID {post_id}")
                return False
        except Error as e:
            logger.error(f"Error updating post: {e}")
            return False
    
    def update_predictions(self, post_id: int, pred_1: float, pred_2: float) -> bool:
        """
        Update prediction fields for a post.
        
        Args:
            post_id: Post ID to update
            pred_1: Prediction value 1
            pred_2: Prediction value 2
            
        Returns:
            bool: True if update successful, False otherwise
        """
        return self.update_post(post_id, {'pred_1': pred_1, 'pred_2': pred_2})
    
    def delete_post(self, post_id: int) -> bool:
        """
        Delete a post by its ID.
        
        Args:
            post_id: Post ID to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        delete_query = "DELETE FROM posts WHERE id = %s"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(delete_query, (post_id,))
            affected_rows = cursor.rowcount
            cursor.close()
            
            if affected_rows > 0:
                logger.info(f"Post {post_id} deleted successfully")
                return True
            else:
                logger.warning(f"No post found with ID {post_id}")
                return False
        except Error as e:
            logger.error(f"Error deleting post: {e}")
            return False
    
    def search_posts(self, keyword: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search posts by keyword in content.
        
        Args:
            keyword: Keyword to search for
            limit: Maximum number of posts to return
            
        Returns:
            List of dictionaries containing post data
        """
        search_query = """
        SELECT * FROM posts 
        WHERE content LIKE %s 
        ORDER BY publish_time DESC 
        LIMIT %s
        """
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(search_query, (f"%{keyword}%", limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error searching posts: {e}")
            return []
    
    def get_post_statistics(self) -> Dict[str, Any]:
        """
        Get basic statistics about posts in the database.
        
        Returns:
            Dictionary containing statistics
        """
        stats_query = """
        SELECT 
            COUNT(*) as total_posts,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(like_count) as avg_likes,
            AVG(comment_count) as avg_comments,
            MAX(publish_time) as latest_post,
            MIN(publish_time) as earliest_post
        FROM posts
        """
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(stats_query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def execute_custom_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of dictionaries containing query results
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"Error executing custom query: {e}")
            return []
