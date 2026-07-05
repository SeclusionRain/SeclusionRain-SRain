#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除comments表中指定task_id的数据
"""

import pymysql
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_config import DatabaseConfig

def delete_comments_by_task_id(task_ids):
    """
    删除指定task_id的数据
    
    Args:
        task_ids (list): 要删除的task_id列表
    """
    try:
        # 获取数据库配置
        config = DatabaseConfig.get_config()
        
        # 连接数据库
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset']
        )
        
        cursor = connection.cursor()
        
        # 构建删除SQL语句
        task_ids_str = ','.join(map(str, task_ids))
        sql = f"DELETE FROM comments WHERE task_id IN ({task_ids_str})"
        
        print(f"执行SQL: {sql}")
        
        # 执行删除操作
        cursor.execute(sql)
        affected_rows = cursor.rowcount
        
        # 提交事务
        connection.commit()
        
        print(f"成功删除 {affected_rows} 条记录")
        
    except Exception as e:
        print(f"删除数据时出错: {str(e)}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    # 指定要删除的task_id列表
    task_ids_to_delete = [ ]
    
    print(f"开始删除comments表中task_id为 {task_ids_to_delete} 的数据...")
    delete_comments_by_task_id(task_ids_to_delete)
    print("删除操作完成")