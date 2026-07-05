#!/usr/bin/env python3
"""
测试数据源API的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.db_models import User, ScrapeTask, Comment, AnalysisHistory

def test_data_sources():
    app = create_app('development')
    
    with app.app_context():
        print("=== 测试数据源API逻辑 ===")
        
        # 模拟用户ID为1
        user_id = 1
        print(f"测试用户ID: {user_id}")
        
        try:
            # 获取用户的分析历史记录
            histories = AnalysisHistory.query.filter_by(user_id=user_id).all()
            print(f"找到分析历史: {len(histories)}条")
            
            data_sources = []
            for history in histories:
                print(f"处理分析历史 ID: {history.id}, 任务ID: {history.task_id}")
                
                # 获取对应的爬取任务信息
                task = ScrapeTask.query.filter_by(id=history.task_id).first()
                print(f"找到任务: {task}")
                
                if task:
                    comment_count = Comment.query.filter_by(task_id=task.id).count()
                    print(f"评论数量: {comment_count}")
                    
                    data_source = {
                        'id': history.id,
                        'video_title': f'抖音视频{task.aweme_id}',
                        'comment_count': comment_count,
                        'created_at': history.analysis_time.strftime('%Y-%m-%d %H:%M')
                    }
                    data_sources.append(data_source)
                    print(f"添加数据源: {data_source}")
                else:
                    print(f"警告: 任务ID {history.task_id} 不存在")
            
            print(f"\n最终数据源列表: {data_sources}")
            return data_sources
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == '__main__':
    test_data_sources()
