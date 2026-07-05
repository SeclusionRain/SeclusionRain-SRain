"""
情感分析路由
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.db_models import ScrapeTask, Comment, AnalysisHistory
from extensions import db
from services.model_service import SentimentModelService
from . import analysis
from datetime import datetime
import logging
from utils.db_manager import DatabaseManager
from utils.db_config import DatabaseConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局数据库管理器实例
def get_db_manager():
    """获取数据库管理器实例"""
    config = DatabaseConfig.get_config()
    return DatabaseManager(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password']
    )

# 从清洗后的表获取评论数据
class CommentDict:
    """将字典转换为可通过点号访问属性的对象"""
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
    
    # 提供字典风格的访问方式作为备选
    def __getitem__(self, key):
        return getattr(self, key, None)
    
    # 支持字典风格的项赋值操作
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def get(self, key, default=None):
        return getattr(self, key, default)
    

def get_comments_from_cleaned_table(task_id):
    """从清洗后的表获取评论数据并结合comments表中的情感分析结果"""
    table_name = f"douyin_comments_task_{task_id}_mysql"
    comments = []
    
    try:
        # 记录尝试获取数据的日志
        logger.info(f"尝试从表 {table_name} 获取评论数据并结合comments表的情感分析结果")
        
        with get_db_manager() as db_manager:
            # 检查数据库连接
            if not db_manager.connection:
                logger.error(f"无法连接到数据库")
                return []
                
            # 检查表是否存在
            cursor = db_manager.connection.cursor(dictionary=True)
            cursor.execute(f"SHOW TABLES LIKE %s", (table_name,))
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                logger.warning(f"清洗后的表 {table_name} 不存在")
                return []
            
            # 检查表的列结构
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            logger.info(f"表 {table_name} 的列结构: {[col['Field'] for col in columns]}")
            
            # 查询所有评论数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")  # 仅查询前5条用于调试
            sample_rows = cursor.fetchall()
            logger.info(f"表 {table_name} 的前5行样本数据: {sample_rows}")
            
            # 重置游标并获取所有数据
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # 如果有评论数据，尝试从comments表获取情感分析结果
            sentiment_data = {}
            if rows:
                try:
                    # 从comments表获取情感分析相关字段
                    cursor.execute("""
                        SELECT post_id, sentiment_label, sentiment_score, analyzed_at 
                        FROM comments 
                        WHERE task_id = %s
                    """, (task_id,))
                    sentiment_rows = cursor.fetchall()
                    # 创建post_id到情感数据的映射
                    for s_row in sentiment_rows:
                        post_id = s_row['post_id']
                        sentiment_data[post_id] = {
                            'sentiment_label': s_row['sentiment_label'],
                            'sentiment_score': s_row['sentiment_score'],
                            'analyzed_at': s_row['analyzed_at']
                        }
                    logger.info(f"从comments表获取到 {len(sentiment_data)} 条评论的情感分析结果")
                except Exception as e:
                    logger.error(f"从comments表获取情感分析结果失败: {e}")
            
            cursor.close()
            
            logger.info(f"从表 {table_name} 获取到 {len(rows)} 条评论数据")
            
            # 转换为可通过点号访问属性的对象
            for row in rows:
                # 处理时间字段，确保是datetime对象
                if 'publish_time' in row and row['publish_time']:
                    try:
                        if isinstance(row['publish_time'], str):
                            # 尝试不同的时间格式
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                                try:
                                    row['publish_time'] = datetime.strptime(row['publish_time'], fmt)
                                    break
                                except ValueError:
                                    continue
                    except Exception as e:
                        logger.error(f"解析发布时间失败: {e}")
                        row['publish_time'] = None
                
                # 处理点赞数字段，确保是整数
                if 'like_count' in row:
                    try:
                        row['like_count'] = int(row['like_count'])
                    except (ValueError, TypeError):
                        row['like_count'] = 0
                    
                # 添加task_id字段
                row['task_id'] = task_id
                
                # 获取并添加情感分析相关字段
                post_id = row.get('post_id')
                if post_id and post_id in sentiment_data:
                    sentiment_info = sentiment_data[post_id]
                    row['sentiment_label'] = sentiment_info['sentiment_label']
                    row['sentiment_score'] = sentiment_info['sentiment_score']
                    row['analyzed_at'] = sentiment_info['analyzed_at']
                
                # 将字典转换为可通过点号访问属性的对象
                comment_obj = CommentDict(row)
                comments.append(comment_obj)
    except Exception as e:
        logger.error(f"从清洗后的表获取评论数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info(f"最终返回 {len(comments)} 条评论数据")
    return comments

# 初始化模型服务实例
model_service = SentimentModelService()
# 打印模型服务状态，用于调试
print(f"分析路由模型服务初始化完成，可用模型: {model_service.get_available_models()}")

@analysis.route('/')
@login_required
def index():
    """分析主页"""
    # 获取用户的爬取任务
    tasks = ScrapeTask.query.filter_by(
        user_id=current_user.id, 
        status='completed'
    ).order_by(ScrapeTask.created_at.desc()).all()
    
    # 获取可用模型和模型信息
    models = model_service.get_available_models()
    model_info = model_service.get_all_model_info()
    
    # 获取最近的分析历史（最多5条）
    recent_histories = AnalysisHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(AnalysisHistory.analysis_time.desc()).limit(5).all()
    
    return render_template('analysis/index.html', 
                         tasks=tasks, 
                         models=models, 
                         model_info=model_info,
                         recent_histories=recent_histories)

@analysis.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """执行情感分析"""
    task_id = request.form.get('task_id')
    model_name = request.form.get('model_name')
    
    if not task_id or not model_name:
        flash('请选择任务和模型')
        return redirect(url_for('analysis.index'))
    
    # 验证任务属于当前用户
    task = ScrapeTask.query.filter_by(
        id=task_id, 
        user_id=current_user.id,
        status='completed'
    ).first()
    
    if not task:
        flash('任务不存在或未完成')
        return redirect(url_for('analysis.index'))
    
    # 从清洗后的表获取评论数据
    comments = get_comments_from_cleaned_table(task_id)
    
    if not comments:
        flash(f'没有找到清洗后的评论数据（表名：douyin_comments_task_{task_id}_mysql）')
        return redirect(url_for('analysis.index'))
    
    logger.info(f"从清洗后的表获取到 {len(comments)} 条评论数据")
    
    try:
        # 准备文本数据
        texts = [comment.content if hasattr(comment, 'content') else comment.get('content', '') for comment in comments]
        
        # 执行情感分析
        results = model_service.predict_sentiment(model_name, texts)
        
        # 更新评论的情感分析结果
        positive_count = 0
        negative_count = 0
            
        with get_db_manager() as db_manager:
                if db_manager.connection:
                    cursor = db_manager.connection.cursor()
                    
                    for i, comment in enumerate(comments):
                        result = results[i]
                        # 获取情感标签和置信度
                        sentiment_label = result['label']  # 'positive', 'negative', 'unknown'
                        confidence_score = result['score']
                        
                        # 调试日志
                        if i % 50 == 0:  # 每50条评论打印一次状态
                            print(f"处理评论 {i+1}/{len(comments)}: 标签={sentiment_label}, 置信度={confidence_score:.4f}")
                        
                        # 更新到主comments表
                        update_query = """
                        UPDATE comments
                        SET sentiment_label = %s, sentiment_score = %s, analyzed_at = %s
                        WHERE post_id = %s AND task_id = %s
                        """
                        try:
                            cursor.execute(update_query, (
                                sentiment_label, 
                                confidence_score, 
                                datetime.now(),
                                comment.get('post_id'),
                                task_id
                            ))
                        except Exception as e:
                            logger.error(f"更新评论情感分析结果时出错: {str(e)}")
                        
                        # 更新内存中的评论对象
                        comment['sentiment_label'] = sentiment_label
                        comment['sentiment_score'] = confidence_score
                        comment['analyzed_at'] = datetime.now()
                        
                        # 处理不同类型的标签
                        if sentiment_label == 'positive':
                            positive_count += 1
                        elif sentiment_label == 'unknown':
                            # 对于未知结果，不计入正负面统计
                            continue
                        else:  # negative或其他
                            negative_count += 1
                    
                    cursor.close()
                    db_manager.connection.commit()
        
        # 保存分析历史
        analysis_history = AnalysisHistory(
            user_id=current_user.id,
            task_id=task_id,
            model_name=model_name,
            total_comments=len(comments),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=0
        )
        
        # 设置结果摘要
        summary = {
            'total': len(comments),
            'positive': positive_count,
            'negative': negative_count,
            'positive_rate': round(positive_count / len(comments) * 100, 2),
            'negative_rate': round(negative_count / len(comments) * 100, 2)
        }
        analysis_history.set_result_summary(summary)
        
        db.session.add(analysis_history)
        db.session.commit()
        
        flash(f'分析完成！正面：{positive_count}，负面：{negative_count}')
        return redirect(url_for('analysis.analysis_dashboard', history_id=analysis_history.id))
        
    except Exception as e:
        flash(f'分析失败：{str(e)}')
        return redirect(url_for('analysis.index'))

@analysis.route('/dashboard/<int:history_id>')
@login_required
def analysis_dashboard(history_id):
    """分析仪表板 - 显示四个分析板块"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('analysis/dashboard.html', history=history)

@analysis.route('/sentiment_overview/<int:history_id>')
@login_required
def sentiment_overview(history_id):
    """模型情感正负向分析"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 50  # 每页显示50条评论
    
    # 获取筛选参数 - 同时支持多种参数名以保持兼容性
    sentiment = request.args.get('sentiment', 'all')
    
    # 从清洗后的表获取分析的评论数据
    all_comments = get_comments_from_cleaned_table(history.task_id)
    
    if not all_comments:
        flash('没有找到评论数据')
        return redirect(url_for('analysis.index'))
    
    # 过滤已分析的评论
    all_comments = [c for c in all_comments if c.get('sentiment_label') is not None]
    
    # 根据情感筛选参数过滤评论
    if sentiment != 'all':
        all_comments = [c for c in all_comments if c.get('sentiment_label') == sentiment]
    
    # 计算总体情感统计 - 只使用前N条数据进行统计，提高性能
    sample_size = 200  # 最多使用200条评论进行统计
    sample_comments = all_comments[:sample_size]
    
    total_comments = len(sample_comments)
    positive_count = sum(1 for c in sample_comments if c.get('sentiment_label') == 'positive')
    negative_count = sum(1 for c in sample_comments if c.get('sentiment_label') == 'negative')
    
    # 计算百分比
    positive_rate = (positive_count / total_comments * 100) if total_comments > 0 else 0
    negative_rate = (negative_count / total_comments * 100) if total_comments > 0 else 0
    
    # 计算分页（基于筛选后的数据）
    total = len(all_comments)
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'sentiment': sentiment  # 将筛选条件添加到分页信息中
    }
    
    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    comments = all_comments[start:end]
    
    return render_template('analysis/sentiment_overview.html',
                         history=history,
                         comments=comments,
                         total_comments=total,
                         positive_count=positive_count,
                         negative_count=negative_count,
                         positive_rate=positive_rate,
                         negative_rate=negative_rate,
                         pagination=pagination,
                         sentiment=sentiment)

@analysis.route('/time_analysis/<int:history_id>')
@login_required
def time_analysis(history_id):
    """时间情感倾向分析"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 50  # 每页显示50条评论
    
    # 获取筛选参数 - 同时支持time_filter和time参数
    time_filter = request.args.get('time_filter', request.args.get('time', 'all'))
    
    # 从清洗后的表获取评论数据
    all_comments = get_comments_from_cleaned_table(history.task_id)
    
    if not all_comments:
        flash('没有找到评论数据')
        return redirect(url_for('analysis.index'))
    
    # 过滤已分析的评论
    all_comments = [c for c in all_comments if c.get('sentiment_label') is not None]
    
    # 按时间排序，处理混合类型问题
    def get_sortable_time(comment):
        time_val = comment.get('publish_time')
        # 如果是字符串类型，返回一个较小的值确保排序稳定性
        if isinstance(time_val, str):
            # 尝试将字符串转换为datetime，如果失败则返回一个极小值
            try:
                from datetime import datetime as dt
                # 这里假设字符串可能有多种格式，尝试基本转换
                return dt.strptime(time_val, '%Y-%m-%d %H:%M:%S')
            except:
                return datetime.min.replace(year=1900)
        return time_val or datetime.min
    
    # 根据时间段筛选评论
    if time_filter != 'all':
        filtered_comments = []
        for comment in all_comments:
            publish_time = get_sortable_time(comment)
            if publish_time and publish_time != datetime.min:
                hour = publish_time.hour
                # 根据时间段进行筛选
                if time_filter == 'morning' and 6 <= hour < 12:
                    filtered_comments.append(comment)
                elif time_filter == 'afternoon' and 12 <= hour < 18:
                    filtered_comments.append(comment)
                elif time_filter == 'evening' and (hour < 6 or hour >= 18):
                    filtered_comments.append(comment)
        all_comments = filtered_comments
    
    all_comments.sort(key=get_sortable_time, reverse=True)
    
    # 处理时间段统计 - 只针对第一页数据，提高性能
    time_stats = {
        'morning': {'positive': 0, 'negative': 0, 'total': 0},
        'afternoon': {'positive': 0, 'negative': 0, 'total': 0},
        'evening': {'positive': 0, 'negative': 0, 'total': 0}
    }
    
    # 使用第一页的数据进行统计，而不是全部数据
    sample_comments = all_comments[:100]  # 最多使用100条评论进行统计
    for comment in sample_comments:
        # 使用get_sortable_time获取标准化的时间对象
        publish_time = get_sortable_time(comment)
        if publish_time and publish_time != datetime.min:
            # 获取小时并进行时间段分类
            hour = publish_time.hour
            if 6 <= hour < 12:
                period = 'morning'
            elif 12 <= hour < 18:
                period = 'afternoon'
            else:
                period = 'evening'
            
            time_stats[period]['total'] += 1
            if comment.get('sentiment_label') == 'positive':
                time_stats[period]['positive'] += 1
            else:
                time_stats[period]['negative'] += 1
    
    # 计算分页（基于筛选后的数据）
    total = len(all_comments)
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'time_filter': time_filter  # 将筛选条件添加到分页信息中
    }
    
    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    comments = all_comments[start:end]
    
    return render_template('analysis/time_analysis.html', 
                         history=history, 
                         comments=comments,
                         pagination=pagination,
                         time_stats=time_stats,
                         time_filter=time_filter)

@analysis.route('/likes_analysis/<int:history_id>')
@login_required
def likes_analysis(history_id):
    """点赞量情感倾向分析"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 50  # 每页显示50条评论
    
    # 获取筛选参数 - 同时支持likes_level和level参数
    likes_level = request.args.get('likes_level', request.args.get('level', 'all'))
    
    # 从清洗后的表获取评论数据
    all_comments = get_comments_from_cleaned_table(history.task_id)
    
    if not all_comments:
        flash('没有找到评论数据')
        return redirect(url_for('analysis.index'))
    
    # 过滤已分析的评论
    all_comments = [c for c in all_comments if c.get('sentiment_label') is not None]
    
    # 确保所有评论的like_count都是整数
    for comment in all_comments:
        try:
            # 尝试两种访问方式确保转换成功
            like_count_val = comment.get('like_count', 0)
            # 首先尝试直接转换
            like_count_int = int(like_count_val)
            # 同时设置字典样式和属性样式访问
            comment['like_count'] = like_count_int
            if hasattr(comment, '__setattr__'):
                setattr(comment, 'like_count', like_count_int)
        except (ValueError, TypeError):
            # 转换失败时设置默认值0
            comment['like_count'] = 0
            if hasattr(comment, '__setattr__'):
                setattr(comment, 'like_count', 0)
    
    # 根据点赞等级筛选评论
    if likes_level != 'all':
        filtered_comments = []
        for comment in all_comments:
            like_count = comment.get('like_count', 0)
            # 匹配点赞等级
            if likes_level == 'high' and like_count > 100:
                filtered_comments.append(comment)
            elif likes_level == 'medium' and 10 < like_count <= 100:
                filtered_comments.append(comment)
            elif likes_level == 'low' and like_count <= 10:
                filtered_comments.append(comment)
        all_comments = filtered_comments
    
    # 按点赞量排序
    all_comments.sort(key=lambda x: x.get('like_count') or 0, reverse=True)
    
    # 统计各点赞区间的评论数 - 只针对前N条数据进行统计
    like_ranges = {
        '0-9': {'count': 0},
        '10-99': {'count': 0},
        '100-999': {'count': 0},
        '1000+': {'count': 0}
    }
    
    # 只对前100条数据进行区间统计
    sample_comments = all_comments[:100]
    for comment in sample_comments:
        likes = comment.get('like_count', 0)
        if likes < 10:
            like_ranges['0-9']['count'] += 1
        elif likes < 100:
            like_ranges['10-99']['count'] += 1
        elif likes < 1000:
            like_ranges['100-999']['count'] += 1
        else:
            like_ranges['1000+']['count'] += 1
    
    # 计算分页（基于筛选后的数据）
    total = len(all_comments)
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'likes_level': likes_level  # 将筛选条件添加到分页信息中
    }
    
    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    comments = all_comments[start:end]
    
    return render_template('analysis/likes_analysis.html', 
                         history=history, 
                         comments=comments,
                         all_comments=all_comments,
                         like_ranges=like_ranges,
                         pagination=pagination,
                         likes_level=likes_level)

@analysis.route('/location_analysis/<int:history_id>')
@login_required
def location_analysis(history_id):
    """地域情感倾向分析"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 50  # 每页显示50条评论
    
    # 获取筛选参数 - 同时支持location和location_filter参数，优先使用location
    location_filter = request.args.get('location', request.args.get('location_filter', 'all'))
    
    # 从清洗后的表获取评论数据
    all_comments = get_comments_from_cleaned_table(history.task_id)
    
    if not all_comments:
        flash('没有找到评论数据')
        return redirect(url_for('analysis.index'))
    
    # 过滤已分析的评论
    all_comments = [c for c in all_comments if c.get('sentiment_label') is not None]
    
    # 保存原始评论的副本用于生成统计数据（包含所有地区）
    original_comments = all_comments.copy()
    
    # 根据地区筛选评论用于显示
    if location_filter != 'all':
        all_comments = [c for c in all_comments if c.get('ip_location') == location_filter]
    
    # 处理地域统计 - 使用所有评论数据进行统计，确保数据准确性
    sample_comments = original_comments  # 使用全部原始评论数据
    
    location_stats = {}
    for comment in sample_comments:
        if comment.get('ip_location'):
            location = comment['ip_location']
            if location not in location_stats:
                location_stats[location] = {'total': 0, 'positive': 0, 'negative': 0}
            
            location_stats[location]['total'] += 1
            if comment.get('sentiment_label') == 'positive':
                location_stats[location]['positive'] += 1
            else:
                location_stats[location]['negative'] += 1
    
    # 找出最活跃和最正面的地区
    most_active_location = None
    most_positive_location = None
    highest_count = 0
    highest_positive_rate = 0
    
    for location, stats in location_stats.items():
        if stats['total'] > highest_count:
            highest_count = stats['total']
            most_active_location = location
        
        if stats['total'] >= 3:  # 至少3条评论才考虑
            positive_rate = stats['positive'] / stats['total'] * 100
            if positive_rate > highest_positive_rate:
                highest_positive_rate = positive_rate
                most_positive_location = location
    
    # 按地域排序评论
    all_comments.sort(key=lambda x: x.get('ip_location') or '')
    
    # 计算分页（基于筛选后的数据）
    total = len(all_comments)
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'location': location_filter  # 将筛选条件添加到分页信息中，使用location参数名保持一致性
    }
    
    # 获取当前页的数据
    start = (page - 1) * per_page
    end = start + per_page
    comments = all_comments[start:end]
    
    return render_template('analysis/location_analysis.html', 
                         history=history, 
                         comments=comments,
                         location_stats=location_stats,
                         most_active_location=most_active_location,
                         most_positive_location=most_positive_location,
                         highest_positive_rate=highest_positive_rate,
                         pagination=pagination,
                         location_filter=location_filter)

@analysis.route('/result/<int:history_id>')
@login_required
def view_result(history_id):
    """查看分析结果 - 保留兼容性"""
    return redirect(url_for('analysis.analysis_dashboard', history_id=history_id))

@analysis.route('/history')
@login_required
def history():
    """分析历史"""
    histories = AnalysisHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(AnalysisHistory.analysis_time.desc()).all()
    
    return render_template('analysis/history.html', histories=histories)

@analysis.route('/delete/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history(history_id):
    """删除分析历史"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    try:
        db.session.delete(history)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
