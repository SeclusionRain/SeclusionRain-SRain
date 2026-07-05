"""
Flask扩展初始化
避免循环导入问题
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
