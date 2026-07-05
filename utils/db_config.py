"""
Database configuration file for MySQL 8.0 connection settings.
Contains default configuration and environment variable support.
"""

import os
from typing import Dict, Any


class DatabaseConfig:
    """Database configuration class with environment variable support."""
    
    # Default configuration
    DEFAULT_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'database': 'ml_douyin_comments_sentimentanalysis',
        'user': 'root',
        'password': '123456',
        'charset': 'utf8mb4'
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Get database configuration from environment variables or defaults.
        
        Environment variables:
        - DB_HOST: Database host
        - DB_PORT: Database port
        - DB_NAME: Database name
        - DB_USER: Database user
        - DB_PASSWORD: Database password
        
        Returns:
            Dict containing database configuration
        """
        config = cls.DEFAULT_CONFIG.copy()
        
        # Override with environment variables if available
        config['host'] = os.getenv('DB_HOST', config['host'])
        config['port'] = int(os.getenv('DB_PORT', config['port']))
        config['database'] = os.getenv('DB_NAME', config['database'])
        config['user'] = os.getenv('DB_USER', config['user'])
        config['password'] = os.getenv('DB_PASSWORD', config['password'])
        
        return config
    
    @classmethod
    def create_connection_string(cls) -> str:
        """
        Create MySQL connection string.
        
        Returns:
            MySQL connection string
        """
        config = cls.get_config()
        return (f"mysql://{config['user']}:{config['password']}@"
                f"{config['host']}:{config['port']}/{config['database']}")


# Example usage configuration
EXAMPLE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'douyin_analysis',
    'user': 'root',
    'password': 'your_password_here'
}

# SQL commands for database setup
CREATE_DATABASE_SQL = """
CREATE DATABASE IF NOT EXISTS douyin_analysis 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
"""

USE_DATABASE_SQL = "USE douyin_analysis;"
