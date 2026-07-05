"""
数据处理服务
处理爬取后的数据：CSV存储 -> 数据清洗 -> HDFS上传 -> Hive表 -> MySQL导出
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from utils.vm_data_pipeline import VMDataPipeline
from models.db_models import Comment

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessingService:
    """数据处理服务类"""
    
    def __init__(self):
        self.csv_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv_data')
        self.ensure_csv_directory()
    
    def ensure_csv_directory(self):
        """确保CSV数据目录存在"""
        if not os.path.exists(self.csv_data_dir):
            os.makedirs(self.csv_data_dir)
            logger.info(f"创建CSV数据目录: {self.csv_data_dir}")
    
    def generate_csv_filename(self, task_name: str, task_id: int) -> str:
        """生成CSV文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_name}_{task_id}_{timestamp}.csv"
        return os.path.join(self.csv_data_dir, filename)
    
    def save_comments_to_csv(self, comments_data: List[Dict[str, Any]], 
                           task_name: str, task_id: int) -> str:
        """
        将评论数据保存为CSV文件
        
        Args:
            comments_data: 评论数据列表
            task_name: 任务名称
            task_id: 任务ID
            
        Returns:
            CSV文件路径
        """
        print(f"📄 开始保存评论数据到CSV文件...")
        
        # 生成CSV文件路径
        csv_path = self.generate_csv_filename(task_name, task_id)
        
        # 转换数据格式
        processed_data = []
        for comment in comments_data:
            processed_data.append({
                'task_id': task_id,
                'post_id': comment.get('post_id', ''),
                'content': comment.get('content', ''),
                'user_name': comment.get('user_name', ''),
                'user_id': comment.get('user_id', ''),
                'user_signature': comment.get('user_signature', ''),
                'publish_time': comment.get('publish_time', ''),
                'like_count': comment.get('like_count', 0),
                'comment_count': comment.get('comment_count', 0),
                'forward_count': comment.get('forward_count', 0),
                'ip_location': comment.get('ip_location', ''),
                'image_urls': str(comment.get('image_urls', [])),
                'user_homepage': comment.get('user_homepage', ''),
                'reply_to_id': comment.get('reply_to_id', ''),
                'reply_to_user': comment.get('reply_to_user', '')
            })
        
        # 创建DataFrame并保存
        df = pd.DataFrame(processed_data)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ CSV文件已保存: {os.path.basename(csv_path)} ({len(processed_data)} 条记录)")
        logger.info(f"CSV文件保存成功: {csv_path}")
        
        return csv_path
    
    def clean_csv_data(self, csv_path: str) -> str:
        """
        清洗CSV数据
        
        Args:
            csv_path: 原始CSV文件路径
            
        Returns:
            清洗后的CSV文件路径
        """
        print(f"🧹 开始清洗CSV数据...")
        
        # 读取数据
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        original_count = len(df)
        
        # 数据清洗步骤
        # 1. 去除空评论
        df = df.dropna(subset=['content'])
        df = df[df['content'].str.strip() != '']
        
        # 2. 去除重复评论（基于post_id）
        df = df.drop_duplicates(subset=['post_id'], keep='first')
        
        # 3. 清理文本内容
        df['content'] = df['content'].str.strip()
        df['user_name'] = df['user_name'].fillna('').str.strip()
        df['user_signature'] = df['user_signature'].fillna('').str.strip()
        df['ip_location'] = df['ip_location'].fillna('').str.strip()
        
        # 4. 处理数值字段
        numeric_fields = ['like_count', 'comment_count', 'forward_count']
        for field in numeric_fields:
            df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
        
        # 5. 处理时间字段
        if 'publish_time' in df.columns:
            df['publish_time'] = pd.to_datetime(df['publish_time'], errors='coerce')
        
        cleaned_count = len(df)
        
        # 生成清洗后的文件路径
        base_name = os.path.basename(csv_path)
        name, ext = os.path.splitext(base_name)
        cleaned_path = os.path.join(self.csv_data_dir, f"{name}_cleaned{ext}")
        
        # 保存清洗后的数据（不包含标题，供Hive使用）
        df.to_csv(cleaned_path, index=False, header=False, encoding='utf-8')
        
        print(f"✅ 数据清洗完成: {original_count} -> {cleaned_count} 条记录")
        logger.info(f"数据清洗完成: {cleaned_path}")
        
        return cleaned_path
    
    def process_and_transfer_data(self, comments_data: List[Dict[str, Any]], 
                                task_name: str, task_id: int) -> bool:
        """
        处理并传输数据的完整流程
        
        Args:
            comments_data: 评论数据列表
            task_name: 任务名称
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        try:
            print(f"\n🚀 开始数据处理流程 (任务: {task_name}, ID: {task_id})")
            
            # 步骤1: 保存为CSV
            csv_path = self.save_comments_to_csv(comments_data, task_name, task_id)
            
            # 步骤2: 数据清洗
            cleaned_csv_path = self.clean_csv_data(csv_path)
            
            # 步骤3: 使用数据管道传输到HDFS -> Hive -> MySQL
            print(f"📊 开始数据管道传输...")
            
            # 定义Hive表结构
            hive_columns = {
                'task_id': 'INT',
                'post_id': 'STRING',
                'content': 'STRING',
                'user_name': 'STRING',
                'user_id': 'STRING',
                'user_signature': 'STRING',
                'publish_time': 'STRING',
                'like_count': 'INT',
                'comment_count': 'INT',
                'forward_count': 'INT',
                'ip_location': 'STRING',
                'image_urls': 'STRING',
                'user_homepage': 'STRING',
                'reply_to_id': 'STRING',
                'reply_to_user': 'STRING'
            }
            
            # MySQL列名（与Hive对应）
            mysql_columns = list(hive_columns.keys())
            
            # Hive表名
            hive_table_name = f"douyin_comments_task_{task_id}"
            
            # 使用VM数据管道
            with VMDataPipeline() as pipeline:
                success = pipeline.run_complete_pipeline(
                    csv_path=cleaned_csv_path,
                    table_name=hive_table_name,
                    hive_columns=hive_columns,
                    mysql_columns=mysql_columns
                )
                
                if success:
                    print(f"✅ VM数据管道处理成功!")
                    print(f"   - Hive表: {hive_table_name}")
                    print(f"   - MySQL表: {hive_table_name}_mysql")
                    logger.info(f"VM数据管道处理成功: 任务{task_id}")
                    return True
                else:
                    print(f"❌ VM数据管道处理失败!")
                    logger.error(f"VM数据管道处理失败: 任务{task_id}")
                    return False
                    
        except Exception as e:
            print(f"❌ 数据处理流程异常: {e}")
            logger.error(f"数据处理流程异常: {e}")
            return False
        finally:
            # 清理临时文件（可选，保留用于调试）
            # if os.path.exists(csv_path):
            #     os.remove(csv_path)
            # if os.path.exists(cleaned_csv_path):
            #     os.remove(cleaned_csv_path)
            pass
    
    def save_to_mysql_directly(self, comments_data: List[Dict[str, Any]], task_id: int):
        """
        直接保存到MySQL
        
        Args:
            comments_data: 评论数据列表
            task_id: 任务ID
        """
        from extensions import db
        
        print(f"💾 开始保存到MySQL数据库...")
        
        saved_count = 0
        for comment_data in comments_data:
            comment = Comment(
                task_id=task_id,
                post_id=comment_data['post_id'],
                content=comment_data['content'],
                user_name=comment_data['user_name'],
                user_id=comment_data['user_id'],
                user_signature=comment_data['user_signature'],
                publish_time=comment_data['publish_time'],
                like_count=comment_data['like_count'],
                comment_count=comment_data['comment_count'],
                forward_count=comment_data['forward_count'],
                ip_location=comment_data['ip_location'],
                image_urls=comment_data['image_urls'],
                user_homepage=comment_data['user_homepage'],
                reply_to_id=comment_data.get('reply_to_id'),
                reply_to_user=comment_data.get('reply_to_user')
            )
            db.session.add(comment)
            saved_count += 1
        
        db.session.commit()
        print(f"✅ MySQL保存完成: {saved_count} 条记录")
        logger.info(f"MySQL直接保存完成: {saved_count} 条记录")


# 便捷函数
def process_scraped_data(comments_data: List[Dict[str, Any]], 
                        task_name: str, task_id: int,
                        use_pipeline: bool = True) -> bool:
    """
    处理爬取的数据的便捷函数
    
    Args:
        comments_data: 评论数据列表
        task_name: 任务名称
        task_id: 任务ID
        use_pipeline: 是否使用数据管道（True）还是直接保存到MySQL（False）
        
    Returns:
        是否成功
    """
    service = DataProcessingService()
    
    if use_pipeline:
        # 使用新的数据管道流程
        pipeline_success = service.process_and_transfer_data(comments_data, task_name, task_id)
        
        # 无论管道是否成功，都保存到MySQL（确保数据不丢失）
        service.save_to_mysql_directly(comments_data, task_id)
        
        return pipeline_success
    else:
        # 仅使用原有的直接保存逻辑
        service.save_to_mysql_directly(comments_data, task_id)
        return True
