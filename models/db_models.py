"""
数据库模型定义
使用Flask-SQLAlchemy定义所有数据表模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

# 导入扩展
from extensions import db

class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    avatar = db.Column(db.String(255))  # 头像路径
    
    # 关系
    scrape_tasks = db.relationship('ScrapeTask', backref='user', lazy='dynamic')
    analysis_histories = db.relationship('AnalysisHistory', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class ScrapeTask(db.Model):
    """爬取任务表"""
    __tablename__ = 'scrape_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    aweme_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    celery_task_id = db.Column(db.String(100))  # Celery任务ID
    total_comments = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    # 关系
    comments = db.relationship('Comment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    analysis_histories = db.relationship('AnalysisHistory', backref='task', lazy='dynamic')
    
    def __repr__(self):
        return f'<ScrapeTask {self.aweme_id}>'

class Comment(db.Model):
    """评论数据表"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('scrape_tasks.id'), nullable=False)
    post_id = db.Column(db.String(50), nullable=False)  # 抖音评论ID
    content = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(100))
    user_id = db.Column(db.String(100))
    user_signature = db.Column(db.String(200))
    publish_time = db.Column(db.DateTime)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    forward_count = db.Column(db.Integer, default=0)
    ip_location = db.Column(db.String(50))
    image_urls = db.Column(db.Text)  # JSON格式存储
    user_homepage = db.Column(db.String(200))
    reply_to_id = db.Column(db.String(50))  # 回复的评论ID
    reply_to_user = db.Column(db.String(100))  # 回复的用户
    
    # 情感分析结果
    sentiment_label = db.Column(db.String(20))  # positive, negative, neutral
    sentiment_score = db.Column(db.Float)  # 情感得分
    analyzed_at = db.Column(db.DateTime)  # 分析时间
    
    def get_image_urls(self):
        """获取图片URL列表"""
        if self.image_urls:
            try:
                return json.loads(self.image_urls)
            except:
                return []
        return []
    
    def __repr__(self):
        return f'<Comment {self.post_id}>'

class AnalysisHistory(db.Model):
    """分析历史表"""
    __tablename__ = 'analysis_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('scrape_tasks.id'), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)  # 使用的模型名称
    analysis_time = db.Column(db.DateTime, default=datetime.now)
    result_summary = db.Column(db.Text)  # JSON格式存储结果摘要
    total_comments = db.Column(db.Integer, default=0)
    positive_count = db.Column(db.Integer, default=0)
    negative_count = db.Column(db.Integer, default=0)
    neutral_count = db.Column(db.Integer, default=0)
    
    def get_result_summary(self):
        """获取结果摘要"""
        if self.result_summary:
            try:
                return json.loads(self.result_summary)
            except:
                return {}
        return {}
    
    def set_result_summary(self, summary_dict):
        """设置结果摘要"""
        self.result_summary = json.dumps(summary_dict, ensure_ascii=False)
    
    def __repr__(self):
        return f'<AnalysisHistory {self.model_name}>'
