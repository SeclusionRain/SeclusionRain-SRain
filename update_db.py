"""
数据库表结构更新脚本
用于更新用户表，添加avatar字段
"""
from app import create_app
from extensions import db

def update_database():
    """更新数据库表结构"""
    # 创建Flask应用实例
    app = create_app('development')
    
    # 进入应用上下文
    with app.app_context():
        # 更新数据库表结构 - 这会添加新定义的字段但不会修改现有字段
        print("正在更新数据库表结构...")
        db.create_all()
        print("数据库表结构更新成功！")

if __name__ == '__main__':
    update_database()