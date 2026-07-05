"""
爬虫功能路由
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from models.db_models import ScrapeTask, Comment
from extensions import db
from sqlalchemy import or_
from datetime import datetime
from . import scraper
import asyncio
import csv
import io
from datasets.DouyinDataset.scraper_service import DouyinScraperService
from services.data_processing_service import process_scraped_data

@scraper.route('/')
@login_required
def index():
    """爬虫主页"""
    # 获取用户的爬取任务
    tasks = ScrapeTask.query.filter_by(user_id=current_user.id).order_by(ScrapeTask.created_at.desc()).all()
    return render_template('scraper/index.html', tasks=tasks)

@scraper.route('/new_task', methods=['GET', 'POST'])
@login_required
def new_task():
    """创建新的爬取任务"""
    if request.method == 'POST':
        aweme_id = request.form.get('aweme_id')
        
        if not aweme_id:
            flash('请输入抖音视频ID')
            return render_template('scraper/new_task.html')
        
        # 创建新任务
        task = ScrapeTask(
            user_id=current_user.id,
            aweme_id=aweme_id,
            status='pending'
        )
        db.session.add(task)
        db.session.commit()
        
        # 启动爬取任务（同步执行，学习演示用）
        try:
            scraper_service = DouyinScraperService()
            comments_data = asyncio.run(scraper_service.scrape_comments(aweme_id))
            
            print(f"\n🎯 爬取完成，开始数据处理流程...")
            print(f"   任务ID: {task.id}")
            print(f"   抖音ID: {aweme_id}")
            print(f"   评论数量: {len(comments_data)}")
            
            # 使用新的数据处理服务
            # 生成任务名称
            task_name = f"douyin_{aweme_id}"
            
            # 处理数据：CSV -> 清洗 -> HDFS -> Hive -> MySQL
            pipeline_success = process_scraped_data(
                comments_data=comments_data,
                task_name=task_name,
                task_id=task.id,
                use_pipeline=True  # 使用数据管道
            )
            
            # 获取清洗后的实际评论数量
            try:
                # 尝试从清洗后的MySQL表中获取实际评论数量
                cleaned_table_name = f"douyin_comments_task_{task.id}_mysql"
                cursor = db.session.connection().connection.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {cleaned_table_name}")
                cleaned_count = cursor.fetchone()[0]
                cursor.close()
            except:
                # 如果获取失败，使用原始评论数量
                cleaned_count = len(comments_data)
            
            # 更新任务状态
            task.status = 'completed'
            task.total_comments = cleaned_count  # 使用清洗后的实际评论数量
            
            # 如果数据管道成功，添加额外信息
            if pipeline_success:
                task.error_message = f"数据管道处理成功 - Hive表: douyin_comments_task_{task.id} "
                print(f"✅ 完整数据流程处理成功! 清洗后评论数: {cleaned_count}")
            else:
                task.error_message = f"数据管道处理失败，但数据已保存到MySQL (清洗后评论数: {cleaned_count})"
                print(f"⚠️  数据管道处理失败，但数据已保存到MySQL. 清洗后评论数: {cleaned_count}")
            
            db.session.commit()
            
            flash(f'爬取完成！共获取 {len(comments_data)} 条评论。数据管道状态: {"成功" if pipeline_success else "失败（已保存到MySQL）"}')
            return redirect(url_for('scraper.view_task', task_id=task.id))
            
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            flash(f'爬取失败：{str(e)}')
    
    return render_template('scraper/new_task.html')

@scraper.route('/task/<int:task_id>')
@login_required
def view_task(task_id):
    """查看任务详情和评论数据"""
    # 确保用户只能查看自己的任务
    task = ScrapeTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    from extensions import db
    
    # 从清洗后的MySQL表获取数据（避免重复评论）
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 计算偏移量
    offset = (page - 1) * per_page
    
    # 动态构建清洗后的表名
    cleaned_table_name = f"douyin_comments_task_{task_id}_mysql"
    
    # 应用过滤器
    content_filter = request.args.get('content', '')
    user_filter = request.args.get('user', '')
    search_keyword = request.args.get('search_keyword', '')
    
    # 构建SQL查询
    query = f"SELECT * FROM {cleaned_table_name}"
    conditions = []
    params = []
    
    # 优先使用统一搜索关键词
    if search_keyword:
        # 同时搜索内容和用户名
        conditions.append("(content LIKE %s OR user_name LIKE %s)")
        params.append(f"%{search_keyword}%")
        params.append(f"%{search_keyword}%")
    else:
        # 否则使用原来的单独过滤器
        if content_filter:
            conditions.append("content LIKE %s")
            params.append(f"%{content_filter}%")
        
        if user_filter:
            conditions.append("user_name LIKE %s")
            params.append(f"%{user_filter}%")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # 添加排序和分页
    query += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    # 执行查询获取评论数据
    cursor = db.session.connection().connection.cursor()
    try:
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        comments = []
        
        # 收集所有post_id，用于批量查询情感分析数据
        post_ids = []
        for row in cursor.fetchall():
            comment_dict = dict(zip(columns, row))
            # 添加id字段（如果没有）
            if 'id' not in comment_dict and 'post_id' in comment_dict:
                comment_dict['id'] = hash(comment_dict['post_id']) % 1000000
            # 将publish_time字符串转换为datetime对象
            if 'publish_time' in comment_dict and comment_dict['publish_time']:
                from datetime import datetime
                if isinstance(comment_dict['publish_time'], str):
                    try:
                        # 尝试不同的日期格式
                        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
                        for fmt in formats:
                            try:
                                comment_dict['publish_time'] = datetime.strptime(comment_dict['publish_time'], fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        # 如果转换失败，保持原始字符串
                        pass
            comments.append(comment_dict)
            if 'post_id' in comment_dict:
                post_ids.append(comment_dict['post_id'])
        
        # 批量查询情感分析数据
        if post_ids:
            from models.db_models import Comment
            # 查询comments表中的情感分析字段
            sentiment_results = Comment.query.filter(
                Comment.task_id == task_id, 
                Comment.post_id.in_(post_ids)
            ).with_entities(
                Comment.post_id, 
                Comment.sentiment_label, 
                Comment.sentiment_score, 
                Comment.analyzed_at
            ).all()
            
            # 创建字典便于快速查找
            sentiment_dict = {}
            for post_id, label, score, analyzed_at in sentiment_results:
                sentiment_dict[post_id] = {
                    'sentiment_label': label,
                    'sentiment_score': score,
                    'analyzed_at': analyzed_at
                }
            
            # 将情感分析数据合并到评论数据中
            for comment in comments:
                if 'post_id' in comment and comment['post_id'] in sentiment_dict:
                    comment.update(sentiment_dict[comment['post_id']])
        
        # 获取总记录数
        count_query = f"SELECT COUNT(*) FROM {cleaned_table_name}"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        cursor.execute(count_query, params[:-2])  # 移除LIMIT和OFFSET参数
        total_count = cursor.fetchone()[0]
    except Exception as e:
        # 如果查询失败，回退到原始的Comment表查询
        comments_query = Comment.query.filter_by(task_id=task_id)
        
        # 优先使用统一搜索关键词
        if search_keyword:
            # 同时搜索内容和用户名
            comments_query = comments_query.filter(
                (Comment.content.contains(search_keyword)) | 
                (Comment.user_name.contains(search_keyword))
            )
        else:
            # 否则使用原来的单独过滤器
            if content_filter:
                comments_query = comments_query.filter(Comment.content.contains(content_filter))
            if user_filter:
                comments_query = comments_query.filter(Comment.user_name.contains(user_filter))
        
        comments = comments_query.order_by(Comment.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return render_template('scraper/view_task.html', task=task, comments=comments, 
                              content_filter=content_filter, user_filter=user_filter)
    finally:
        cursor.close()
    
    # 模拟分页对象
    class Pagination:
        def __init__(self, page, per_page, total, items):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = items
            
        @property
        def pages(self):
            return (self.total + self.per_page - 1) // self.per_page
            
        def prev_num(self):
            return self.page - 1 if self.page > 1 else None
            
        def next_num(self):
            return self.page + 1 if self.page < self.pages else None
            
        def has_prev(self):
            return self.page > 1
            
        def has_next(self):
            return self.page < self.pages
            
        # 新增iter_pages方法，兼容模板中的分页逻辑
        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and \
                    num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
        
        # 添加start_index和end_index属性以兼容模板
        @property
        def start_index(self):
            if self.total == 0:
                return 0
            return (self.page - 1) * self.per_page + 1
            
        @property
        def end_index(self):
            if self.total == 0:
                return 0
            end = self.page * self.per_page
            return min(end, self.total)
    
    pagination = Pagination(page, per_page, total_count, comments)
    
    return render_template('scraper/view_task.html', task=task, comments=pagination, 
                          content_filter=content_filter, user_filter=user_filter)

@scraper.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    """删除爬取任务"""
    from models.db_models import AnalysisHistory
    
    task = ScrapeTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    try:
        # 首先删除相关的分析历史记录
        analysis_histories = AnalysisHistory.query.filter_by(task_id=task_id).all()
        for history in analysis_histories:
            db.session.delete(history)
        
        # 然后删除任务（评论会通过级联删除自动删除）
        db.session.delete(task)
        db.session.commit()
        flash('任务已删除')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}')
    
    return redirect(url_for('scraper.index'))

@scraper.route('/edit_comment/<string:post_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(post_id):
    """编辑评论"""
    comment = Comment.query.join(ScrapeTask).filter(
        Comment.post_id == post_id,
        ScrapeTask.user_id == current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        # 更新评论内容和其他字段
        comment.content = request.form.get('content', '').strip()
        comment.like_count = int(request.form.get('like_count', 0) or 0)
        comment.ip_location = request.form.get('ip_location', '').strip() or None
        comment.user_signature = request.form.get('user_signature', '').strip() or None
        comment.sentiment_label = request.form.get('sentiment_label', '').strip() or None
        
        # 处理情感得分
        sentiment_score = request.form.get('sentiment_score', '').strip()
        if sentiment_score:
            try:
                comment.sentiment_score = float(sentiment_score)
            except ValueError:
                comment.sentiment_score = None
        
        if not comment.content:
            flash('评论内容不能为空', 'error')
            return render_template('scraper/edit_comment.html', comment=comment)
        
        try:
            db.session.commit()
            flash('评论已更新', 'success')
            return redirect(url_for('scraper.view_task', task_id=comment.task_id))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('scraper/edit_comment.html', comment=comment)

@scraper.route('/delete_comment/<string:post_id>', methods=['POST'])
@login_required
def delete_comment(post_id):
    """删除评论"""
    comment = Comment.query.join(ScrapeTask).filter(
        Comment.post_id == post_id,
        ScrapeTask.user_id == current_user.id
    ).first_or_404()
    
    task_id = comment.task_id
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除')
    return redirect(url_for('scraper.view_task', task_id=task_id))

@scraper.route('/export_comments/<int:task_id>')
@login_required
def export_comments(task_id):
    """导出评论为CSV格式"""
    # 验证用户权限
    task = ScrapeTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    # 获取搜索关键词
    search_keyword = request.args.get('search_keyword', '').strip()
    
    # 构建查询
    query = Comment.query.filter_by(task_id=task_id)
    
    # 应用搜索过滤
    if search_keyword:
        # 同时搜索评论内容和用户名
        query = query.filter(
            or_(
                Comment.content.ilike(f'%{search_keyword}%'),
                Comment.user_name.ilike(f'%{search_keyword}%')
            )
        )
    
    # 按发布时间排序
    query = query.order_by(Comment.publish_time.desc())
    
    # 获取所有评论
    comments = query.all()
    
    # 创建内存文件对象
    output = io.StringIO()
    
    # 添加UTF-8 BOM以支持中文显示
    output.write('\ufeff')
    
    # 创建CSV写入器
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(['用户名', '评论内容', '发布时间', '点赞数', 'IP位置', '情感标签', '情感得分'])
    
    # 写入数据
    for comment in comments:
        publish_time = comment.publish_time.strftime('%Y-%m-%d %H:%M:%S') if comment.publish_time else '未知'
        writer.writerow([
            comment.user_name or '',
            comment.content or '',
            publish_time,
            comment.like_count or 0,
            comment.ip_location or '',
            comment.sentiment_label or '',
            comment.sentiment_score if comment.sentiment_score is not None else ''
        ])
    
    # 生成响应
    output.seek(0)
    response = Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=comments_{task_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'}
    )
    
    return response
