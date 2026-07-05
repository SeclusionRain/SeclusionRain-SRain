"""
Flask应用配置文件
"""
import os
from utils.db_config import DatabaseConfig
from utils.vm_config import VMConfig

class Config:
    """基础配置类"""
    SECRET_KEY = 'dev-secret-key-for-learning'  
    
    # 数据库配置 - 复用现有的数据库配置
    db_config = DatabaseConfig.get_config()
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset={db_config['charset']}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Celery配置（如果需要异步任务）
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    
    # VM虚拟机环境配置
    VM_CONFIG = VMConfig.get_vm_config()
    HDFS_CONFIG = VMConfig.get_hdfs_config()
    YARN_CONFIG = VMConfig.get_yarn_config()
    HIVE_CONFIG = VMConfig.get_hive_config()
    SSH_CONFIG = VMConfig.get_ssh_config()
    
    # 数据管道模式：'docker' 或 'vm'
    PIPELINE_MODE = os.environ.get('PIPELINE_MODE', 'vm')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
