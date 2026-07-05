#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试脚本：分析最近爬取的评论无法显示的问题
"""

import os
import sys
import logging
import pymysql
from datetime import datetime
import json

# 数据库配置类
class DatabaseConfig:
    @staticmethod
    def get_config():
        """返回数据库连接配置"""
        return {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'ml_douyin_comments_sentimentanalysis',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('debug_cleaned_table.log'),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)


def test_task_ids():
    """测试不同任务ID的表结构和数据"""
    conn = None
    cursor = None
    
    try:
        # 直接定义数据库配置
        db_config = {
            'host': 'localhost',  # 或其他主机地址
            'port': 3306,
            'database': 'ml_douyin_comments_sentimentanalysis',  # 假设数据库名是douyin_comments
            'user': 'root',  # 假设用户是root
            'password': '123456',  # 假设密码是123456
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        logger.info(f"数据库配置: 主机={db_config['host']}, 端口={db_config['port']}, 数据库={db_config['database']}")
        
        # 连接数据库
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 查询数据库中的所有表
        logger.info("\n===== 查询数据库中的所有表 =====")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        # 提取表名列表
        table_names = [table[f'Tables_in_{db_config["database"]}'] for table in tables]
        
        logger.info(f"在数据库 '{db_config['database']}' 中找到 {len(table_names)} 个表:")
        for table_name in table_names:
            logger.info(f"  - {table_name}")
        
        # 专门查找douyin_comments_task_*_mysql格式的表
        logger.info("\n===== 查找清洗后的评论表 =====")
        cleaned_tables = [t for t in table_names if t.startswith('douyin_comments_task_') and t.endswith('_mysql')]
        
        if cleaned_tables:
            logger.info(f"找到 {len(cleaned_tables)} 个清洗后的评论表:")
            for table in cleaned_tables:
                logger.info(f"  - {table}")
                
                # 提取任务ID
                parts = table.split('_')
                if len(parts) >= 5:
                    task_id = parts[-2]  # '_mysql'前面的部分是task_id
                    logger.info(f"    对应的任务ID: {task_id}")
                
                # 检查数据量
                try:
                    cursor.execute(f"SELECT COUNT(*) AS count FROM {table}")
                    count_result = cursor.fetchone()
                    count = count_result.get('count', 0) if count_result else 0
                    logger.info(f"    记录数: {count}")
                except Exception as e:
                    logger.error(f"    查询记录数失败: {e}")
        else:
            logger.info("没有找到清洗后的评论表 (douyin_comments_task_*_mysql)")
        
        # 检查comments表是否存在及其结构
        if 'comments' in table_names:
            logger.info("\n===== 分析comments表 =====")
            try:
                # 检查表结构
                cursor.execute("SHOW COLUMNS FROM comments")
                columns = cursor.fetchall()
                logger.info(f"表 comments 的列结构 ({len(columns)}列):")
                for column in columns:
                    logger.info(f"  - {column['Field']}: {column['Type']}")
                
                # 检查数据量
                cursor.execute("SELECT COUNT(*) AS count FROM comments")
                count = cursor.fetchone()['count']
                logger.info(f"表 comments 中的记录数: {count}")
                
                # 检查是否有task_id列
                has_task_id = any(col['Field'] == 'task_id' for col in columns)
                logger.info(f"表 comments 是否包含task_id列: {has_task_id}")
                
                # 如果有task_id列，查看任务分布
                if has_task_id and count > 0:
                    cursor.execute("SELECT task_id, COUNT(*) AS count FROM comments GROUP BY task_id ORDER BY task_id DESC LIMIT 10")
                    task_counts = cursor.fetchall()
                    logger.info(f"comments表中的任务分布:")
                    for row in task_counts:
                        logger.info(f"  任务ID {row['task_id']}: {row['count']} 条评论")
            except Exception as e:
                logger.error(f"分析comments表时出错: {e}")
        else:
            logger.info("\ncomments表不存在")
        
        # 检查scrape_tasks表中的最新任务
        logger.info("\n===== 检查最近的爬取任务 =====")
        try:
            cursor.execute("SELECT id, keyword, status, created_at, updated_at FROM scrape_tasks ORDER BY created_at DESC LIMIT 5")
            recent_tasks = cursor.fetchall()
            if recent_tasks:
                logger.info(f"找到 {len(recent_tasks)} 个最近的爬取任务:")
                for task in recent_tasks:
                    task_id = task['id']
                    status = task['status']
                    created_at = task['created_at']
                    # 检查是否有对应的清洗后表
                    cleaned_table_name = f"douyin_comments_task_{task_id}_mysql"
                    cursor.execute(f"SHOW TABLES LIKE '{cleaned_table_name}'")
                    has_cleaned_table = cursor.fetchone() is not None
                    
                    # 统计该任务在comments表中的评论数量
                    cursor.execute(f"SELECT COUNT(*) as count FROM comments WHERE task_id = {task_id}")
                    comments_count = cursor.fetchone()['count']
                    
                    logger.info(f"  - 任务ID: {task_id}, 关键词: {task['keyword']}, 状态: {status}")
                    logger.info(f"    创建时间: {created_at}, 评论数: {comments_count}, 清洗表存在: {has_cleaned_table}")
            else:
                logger.info("没有找到爬取任务")
        except Exception as e:
            logger.error(f"查询爬取任务时发生错误: {e}")
        
        # 检查analysis_histories表
        logger.info("\n===== 检查分析历史 =====")
        try:
            cursor.execute("SELECT task_id, analysis_type, status, created_at FROM analysis_histories ORDER BY created_at DESC LIMIT 5")
            histories = cursor.fetchall()
            if histories:
                logger.info(f"找到 {len(histories)} 条分析历史:")
                for history in histories:
                    task_id = history['task_id']
                    # 检查该任务是否有清洗后的表
                    cleaned_table_name = f"douyin_comments_task_{task_id}_mysql"
                    cursor.execute(f"SHOW TABLES LIKE '{cleaned_table_name}'")
                    has_cleaned_table = cursor.fetchone() is not None
                    
                    # 如果有清洗后表，检查其结构
                    if has_cleaned_table:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {cleaned_table_name}")
                        cleaned_count = cursor.fetchone()['count']
                        logger.info(f"  - 任务ID: {task_id}, 分析类型: {history['analysis_type']}, 状态: {history['status']}")
                        logger.info(f"    清洗表存在: 是, 清洗表记录数: {cleaned_count}")
                    else:
                        logger.info(f"  - 任务ID: {task_id}, 分析类型: {history['analysis_type']}, 状态: {history['status']}")
                        logger.info(f"    清洗表存在: 否")
            else:
                logger.info("没有找到分析历史")
        except Exception as e:
            logger.error(f"查询分析历史时发生错误: {e}")
        
        # 模拟get_comments_from_cleaned_table函数的逻辑测试
        logger.info("\n===== 模拟get_comments_from_cleaned_table函数逻辑测试 =====")
        try:
            # 选择最新的几个任务ID进行测试
            cursor.execute("SELECT id FROM scrape_tasks ORDER BY created_at DESC LIMIT 3")
            test_task_ids = [row['id'] for row in cursor.fetchall()]
            
            for task_id in test_task_ids:
                cleaned_table_name = f"douyin_comments_task_{task_id}_mysql"
                logger.info(f"\n测试任务ID: {task_id}, 清洗表名: {cleaned_table_name}")
                
                # 检查表是否存在
                cursor.execute(f"SHOW TABLES LIKE '{cleaned_table_name}'")
                if cursor.fetchone():
                    # 检查表结构
                    cursor.execute(f"DESCRIBE {cleaned_table_name}")
                    columns = cursor.fetchall()
                    column_names = [col['Field'] for col in columns]
                    logger.info(f"清洗表列结构: {', '.join(column_names)}")
                    
                    # 检查post_id列是否存在（用于关联查询）
                    if 'post_id' in column_names:
                        # 尝试模拟原始函数的查询逻辑
                        try:
                            # 这里模拟app_blueprint/analysis/routes.py中的get_comments_from_cleaned_table函数逻辑
                            query = f"""
                            SELECT c.*, ch.sentiment_label, ch.sentiment_score, ch.analyzed_at 
                            FROM {cleaned_table_name} c
                            LEFT JOIN comments ch ON c.post_id = ch.post_id AND ch.task_id = {task_id}
                            LIMIT 5
                            """
                            cursor.execute(query)
                            sample_data = cursor.fetchall()
                            if sample_data:
                                logger.info(f"成功执行关联查询，获取了 {len(sample_data)} 条样本数据")
                                # 显示第一条数据的部分字段
                                first_row = sample_data[0]
                                logger.info(f"样本数据示例 (部分字段):")
                                logger.info(f"  post_id: {first_row.get('post_id')}")
                                logger.info(f"  content: {str(first_row.get('content'))[:50]}...")
                                logger.info(f"  sentiment_label: {first_row.get('sentiment_label')}")
                                logger.info(f"  sentiment_score: {first_row.get('sentiment_score')}")
                            else:
                                logger.warning("关联查询没有返回数据")
                        except Exception as e:
                            logger.error(f"执行关联查询时发生错误: {e}")
                    else:
                        logger.warning("清洗表中不存在post_id列，无法执行关联查询")
                else:
                    logger.warning(f"清洗表 {cleaned_table_name} 不存在")
        except Exception as e:
            logger.error(f"模拟函数测试时发生错误: {e}")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        # 确保连接关闭
        try:
            if cursor and not cursor.closed:
                cursor.close()
                logger.info("游标已关闭")
        except:
            pass
        try:
            if conn and hasattr(conn, '_closed') and not conn._closed:
                conn.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接时发生错误: {e}")


def check_column_consistency():
    """检查不同表之间的列一致性问题"""
    conn = None
    cursor = None
    
    try:
        # 使用与test_task_ids相同的数据库配置
        db_config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'ml_douyin_comments_sentimentanalysis',
            'user': 'root',
            'password': '123456',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        # 连接数据库
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 获取所有douyin_comments_task_*_mysql表
        cursor.execute("SHOW TABLES LIKE 'douyin_comments_task_%_mysql'")
        tables = cursor.fetchall()
        
        if not tables:
            logger.info("没有找到清洗后的评论表，无法进行列一致性检查")
            return
        
        column_maps = {}
        
        # 获取每个表的列名（修复表名提取方式）
        for table in tables:
            # 尝试不同的方式获取表名
            if isinstance(table, dict):
                # 尝试直接获取第一个键的值
                table_name = list(table.values())[0]
            else:
                # 如果是元组或其他类型，取第一个元素
                table_name = table[0]
            
            logger.info(f"处理表: {table_name}")
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]
            column_maps[table_name] = column_names
        
        # 比较列结构差异
        if len(column_maps) >= 2:
            logger.info("\n===== 表列结构比较 =====")
            table_list = list(column_maps.keys())
            
            # 比较最新的表和之前的表
            latest_table = table_list[0]
            for old_table in table_list[1:]:
                logger.info(f"\n比较 {latest_table} vs {old_table}:")
                
                latest_cols = set(column_maps[latest_table])
                old_cols = set(column_maps[old_table])
                
                only_in_latest = latest_cols - old_cols
                only_in_old = old_cols - latest_cols
                
                if only_in_latest:
                    logger.info(f"  只在最新表中存在的列: {sorted(only_in_latest)}")
                if only_in_old:
                    logger.info(f"  只在旧表中存在的列: {sorted(only_in_old)}")
                if not only_in_latest and not only_in_old:
                    logger.info(f"  两表列结构完全相同")
    
    except Exception as e:
        logger.error(f"检查列一致性时发生错误: {e}")
    finally:
        # 确保连接关闭
        try:
            if cursor and not cursor.closed:
                cursor.close()
        except:
            pass
        try:
            if conn and hasattr(conn, '_closed') and not conn._closed:
                conn.close()
        except:
            pass


def simulate_get_comments_from_cleaned_table(task_id):
    """模拟get_comments_from_cleaned_table函数的执行逻辑，专注于测试comments表与清洗表的关联问题"""
    conn = None
    cursor = None
    
    try:
        # 使用与test_task_ids相同的数据库配置
        db_config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'ml_douyin_comments_sentimentanalysis',
            'user': 'root',
            'password': '123456',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        # 连接数据库
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        logger.info(f"\n===== 模拟获取任务ID {task_id} 的评论数据 =====")
        
        # 构建清洗后表名
        cleaned_table_name = f"douyin_comments_task_{task_id}_mysql"
        logger.info(f"构建的清洗后表名: {cleaned_table_name}")
        
        # 检查表是否存在
        cursor.execute(f"SHOW TABLES LIKE '{cleaned_table_name}'")
        table_exists = cursor.fetchone() is not None
        logger.info(f"清洗后表是否存在: {table_exists}")
        
        if not table_exists:
            logger.warning(f"清洗后表 {cleaned_table_name} 不存在")
            return
        
        # 获取表的列信息
        cursor.execute(f"SHOW COLUMNS FROM {cleaned_table_name}")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        logger.info(f"清洗后表的列名: {', '.join(column_names)}")
        
        # 检查主键列名
        primary_key_name = None
        cursor.execute(f"SHOW KEYS FROM {cleaned_table_name} WHERE Key_name = 'PRIMARY'")
        primary_keys = cursor.fetchall()
        if primary_keys:
            primary_key_name = primary_keys[0]['Column_name']
        logger.info(f"主键列名: {primary_key_name}")
        
        # 1. 统计两个表的记录数
        logger.info("\n===== 记录数统计 =====")
        
        # 清洗表记录数
        cursor.execute(f"SELECT COUNT(*) as count FROM {cleaned_table_name}")
        cleaned_count = cursor.fetchone()['count']
        logger.info(f"清洗表 {cleaned_table_name} 记录数: {cleaned_count}")
        
        # comments表记录数
        cursor.execute("SELECT COUNT(*) as count FROM comments WHERE task_id = %s", (task_id,))
        comments_count = cursor.fetchone()['count']
        logger.info(f"comments表中任务ID {task_id} 的记录数: {comments_count}")
        
        # 2. 检查情感分析字段填充情况
        logger.info("\n===== 情感分析字段填充情况 =====")
        
        # 统计有情感标签的记录
        cursor.execute("""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN sentiment_label IS NOT NULL THEN 1 ELSE 0 END) as labeled,
                SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as scored
            FROM comments 
            WHERE task_id = %s
        """, (task_id,))
        sentiment_stats = cursor.fetchone()
        logger.info(f"comments表中任务ID {task_id} 情感标签统计:")
        logger.info(f"  总记录数: {sentiment_stats['total']}")
        logger.info(f"  有sentiment_label的记录: {sentiment_stats['labeled']} ({sentiment_stats['labeled']/sentiment_stats['total']*100:.1f}%)")
        logger.info(f"  有sentiment_score的记录: {sentiment_stats['scored']} ({sentiment_stats['scored']/sentiment_stats['total']*100:.1f}%)")
        
        # 3. 验证post_id匹配情况
        logger.info("\n===== post_id匹配验证 =====")
        
        # 查看清洗表中的post_id样本
        cursor.execute(f"SELECT post_id FROM {cleaned_table_name} LIMIT 5")
        cleaned_post_ids = cursor.fetchall()
        logger.info(f"清洗表中的post_id样本: {[row['post_id'] for row in cleaned_post_ids]}")
        
        # 查看comments表中对应task_id的post_id样本
        cursor.execute("SELECT post_id FROM comments WHERE task_id = %s LIMIT 5", (task_id,))
        comments_post_ids = cursor.fetchall()
        logger.info(f"comments表中的post_id样本: {[row['post_id'] for row in comments_post_ids]}")
        
        # 4. 详细的JOIN查询测试
        logger.info("\n===== JOIN查询详细测试 =====")
        
        # 测试1: 检查两表post_id的匹配率
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_in_cleaned,
                SUM(CASE WHEN c.post_id IS NOT NULL THEN 1 ELSE 0 END) as matched
            FROM {cleaned_table_name} t
            LEFT JOIN comments c ON t.post_id = c.post_id AND c.task_id = %s
        """, (task_id,))
        match_stats = cursor.fetchone()
        if match_stats['total_in_cleaned'] > 0:
            match_rate = match_stats['matched'] / match_stats['total_in_cleaned'] * 100
            logger.info(f"清洗表与comments表post_id匹配统计:")
            logger.info(f"  清洗表总记录: {match_stats['total_in_cleaned']}")
            logger.info(f"  匹配成功记录: {match_stats['matched']} ({match_rate:.1f}%)")
        
        # 测试2: 获取匹配的样本数据，包含情感分析结果
        cursor.execute(f"""
            SELECT t.post_id, t.content, c.sentiment_label, c.sentiment_score
            FROM {cleaned_table_name} t
            LEFT JOIN comments c ON t.post_id = c.post_id AND c.task_id = %s
            LIMIT 10
        """, (task_id,))
        join_samples = cursor.fetchall()
        logger.info(f"\nJOIN查询样本结果 (10条):")
        for i, row in enumerate(join_samples):
            logger.info(f"  记录{i+1}:")
            logger.info(f"    post_id: {row.get('post_id')}")
            logger.info(f"    content: {str(row.get('content'))[:30]}...")
            logger.info(f"    sentiment_label: {row.get('sentiment_label')}")
            logger.info(f"    sentiment_score: {row.get('sentiment_score')}")
        
        # 测试3: 检查最近爬取的评论（假设按时间排序）
        logger.info("\n===== 最近爬取评论检查 =====")
        
        # 查看清洗表中最新的评论
        if 'create_time' in column_names:
            time_column = 'create_time'
        elif 'crawl_time' in column_names:
            time_column = 'crawl_time'
        else:
            time_column = None
            
        if time_column:
            cursor.execute(f"""
                SELECT post_id, {time_column}, content 
                FROM {cleaned_table_name} 
                ORDER BY {time_column} DESC 
                LIMIT 5
            """)
            latest_comments = cursor.fetchall()
            logger.info(f"清洗表中最新的5条评论 (按{time_column}排序):")
            for comment in latest_comments:
                logger.info(f"  post_id: {comment['post_id']}, {time_column}: {comment[time_column]}")
                
                # 检查这些最新评论在comments表中是否有情感分析结果
                cursor.execute("""
                    SELECT sentiment_label, sentiment_score 
                    FROM comments 
                    WHERE task_id = %s AND post_id = %s
                """, (task_id, comment['post_id']))
                sentiment = cursor.fetchone()
                if sentiment:
                    logger.info(f"    情感分析: label={sentiment['sentiment_label']}, score={sentiment['sentiment_score']}")
                else:
                    logger.info(f"    未找到对应的情感分析结果")
        else:
            logger.warning("清洗表中没有找到时间相关列，无法检查最新评论")
            
        # 5. 诊断为什么最近爬取的评论无法显示
        logger.info("\n===== 问题诊断 =====")
        
        # 检查是否存在post_id匹配但情感字段为NULL的情况
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM {cleaned_table_name} t
            LEFT JOIN comments c ON t.post_id = c.post_id AND c.task_id = %s
            WHERE c.post_id IS NOT NULL AND (c.sentiment_label IS NULL OR c.sentiment_score IS NULL)
        """, (task_id,))
        null_sentiment_count = cursor.fetchone()['count']
        logger.info(f"post_id匹配但情感字段为NULL的记录数: {null_sentiment_count}")
        
        if null_sentiment_count > 0:
            logger.warning("发现部分评论虽然在comments表中有记录，但缺少情感分析结果，这可能是导致评论无法显示的原因")
        
        # 检查是否有评论只存在于一个表中
        cursor.execute(f"""
            SELECT 'only_in_cleaned' as source, COUNT(*) as count
            FROM {cleaned_table_name} t
            LEFT JOIN comments c ON t.post_id = c.post_id AND c.task_id = %s
            WHERE c.post_id IS NULL
            UNION ALL
            SELECT 'only_in_comments' as source, COUNT(*) as count
            FROM comments c
            LEFT JOIN {cleaned_table_name} t ON c.post_id = t.post_id
            WHERE c.task_id = %s AND t.post_id IS NULL
        """, (task_id, task_id))
        one_side_counts = cursor.fetchall()
        logger.info("\n单边存在的评论统计:")
        for row in one_side_counts:
            logger.info(f"  只存在于{row['source']}的记录数: {row['count']}")
            
    except Exception as e:
        logger.error(f"模拟函数执行时发生错误: {e}")
    finally:
        # 确保连接关闭
        try:
            if cursor and not cursor.closed:
                cursor.close()
        except:
            pass
        try:
            if conn and hasattr(conn, '_closed') and not conn._closed:
                conn.close()
        except:
            pass


if __name__ == "__main__":
    logger.info("===== 开始调试最近爬取评论无法显示的问题 =====")
    
    # 1. 测试所有任务ID的表结构和数据
    test_task_ids()
    
    # 2. 检查不同表之间的列一致性
    check_column_consistency()
    
    # 3. 模拟特定任务ID的评论数据获取（需要用户输入）
    try:
        # 默认测试任务ID 17，也允许用户输入其他任务ID
        task_id_input = input("\n请输入要测试的任务ID (默认17，直接回车使用默认值): ").strip()
        if not task_id_input:
            task_id = 17
            logger.info(f"使用默认任务ID: {task_id}")
        elif task_id_input.isdigit():
            task_id = int(task_id_input)
        else:
            logger.warning("输入无效，使用默认任务ID 17")
            task_id = 17
        
        simulate_get_comments_from_cleaned_table(task_id)
    except Exception as e:
        logger.error(f"测试执行错误: {e}")
    
    logger.info("\n===== 调试完成 =====")