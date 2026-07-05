"""
可视化路由
"""
from flask import render_template, request, jsonify, Response
from flask_login import login_required, current_user
from models.db_models import AnalysisHistory, Comment, ScrapeTask
from sqlalchemy import func
from . import visualization
import json
import jieba
from collections import Counter
import re
import base64
import io

@visualization.route('/')
@login_required
def index():
    """可视化主页"""
    # 获取用户的分析历史
    histories = AnalysisHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(AnalysisHistory.analysis_time.desc()).all()
    
    return render_template('visualization/index.html', histories=histories)

@visualization.route('/charts/<int:history_id>')
@login_required
def view_charts(history_id):
    """查看可视化图表 - 新的四模块仪表板"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('visualization/charts.html', history=history)

@visualization.route('/wordcloud/<int:history_id>')
@login_required
def wordcloud_module(history_id):
    """关键词词云展示模块"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('visualization/wordcloud.html', history=history)

@visualization.route('/likes_charts/<int:history_id>')
@login_required
def likes_charts(history_id):
    """点赞量情感倾向可视化模块"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('visualization/likes_charts.html', history=history)

@visualization.route('/time_charts/<int:history_id>')
@login_required
def time_charts(history_id):
    """时间情感倾向可视化模块"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('visualization/time_charts.html', history=history)

@visualization.route('/location_charts/<int:history_id>')
@login_required
def location_charts(history_id):
    """地域情感倾向可视化模块"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('visualization/location_charts.html', history=history)

@visualization.route('/api/sentiment_distribution/<int:history_id>')
@login_required
def api_sentiment_distribution(history_id):
    """API: 获取情感分布数据"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    data = {
        'positive': history.positive_count,
        'negative': history.negative_count
    }
    
    return jsonify(data)

@visualization.route('/api/sentiment_timeline/<int:history_id>')
@login_required
def api_sentiment_timeline(history_id):
    """API: 获取情感时间线数据"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    # 按日期分组统计情感分布
    comments = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_label.isnot(None)
    ).all()
    
    # 按发布日期分组
    timeline_data = {}
    for comment in comments:
        date_str = comment.publish_time.strftime('%Y-%m-%d') if comment.publish_time else '未知'
        if date_str not in timeline_data:
            timeline_data[date_str] = {'positive': 0, 'negative': 0}
        timeline_data[date_str][comment.sentiment_label] += 1
    
    # 转换为图表数据格式
    dates = sorted(timeline_data.keys())
    positive_data = [timeline_data[date]['positive'] for date in dates]
    negative_data = [timeline_data[date]['negative'] for date in dates]
    
    result = {
        'dates': dates,
        'positive': positive_data,
        'negative': negative_data
    }
    
    return jsonify(result)

@visualization.route('/api/word_frequency/<int:history_id>')
@login_required
def api_word_frequency(history_id):
    """API: 获取词频数据 - 支持情感分类"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    sentiment_filter = request.args.get('sentiment', 'all')  # all, positive, negative
    
    # 获取评论数据
    query = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_label.isnot(None)
    )
    
    if sentiment_filter != 'all':
        query = query.filter(Comment.sentiment_label == sentiment_filter)
    
    comments = query.all()
    
    # 停用词列表
    stopwords = {'的', '了', '是', '我', '你', '他', '她', '它', '们', '这', '那', '在', '有', '和', '与', '或', '但', '而', '就', '都', '也', '还', '不', '没', '很', '太', '非常', '真', '好', '啊', '呀', '吧', '呢', '哦', '嗯', '额', '哈', '嘿'}
    
    # 使用jieba分词统计
    word_count = Counter()
    for comment in comments:
        if comment.content:
            # 清理文本
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', comment.content)
            words = jieba.lcut(text)
            for word in words:
                word = word.strip()
                if len(word) > 1 and word not in stopwords:
                    word_count[word] += 1
    
    # 取前50个高频词用于词云
    top_words = word_count.most_common(50)
    
    result = {
        'words': [{'name': word, 'value': count} for word, count in top_words],
        'total_comments': len(comments)
    }
    
    return jsonify(result)

@visualization.route('/api/sentiment_scores/<int:history_id>')
@login_required
def api_sentiment_scores(history_id):
    """API: 获取情感得分分布"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    comments = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_score.isnot(None)
    ).all()
    
    # 按情感标签分组得分
    scores_by_label = {'positive': [], 'negative': []}
    for comment in comments:
        if comment.sentiment_label in scores_by_label:
            scores_by_label[comment.sentiment_label].append(comment.sentiment_score)
    
    return jsonify(scores_by_label)

# 新增API端点用于增强的可视化模块

@visualization.route('/api/likes_sentiment/<int:history_id>')
@login_required
def api_likes_sentiment(history_id):
    """API: 获取点赞量与情感分布数据"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    comments = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_label.isnot(None),
        Comment.like_count.isnot(None)
    ).all()
    
    # 按点赞量分层
    likes_tiers = {'low': [], 'medium': [], 'high': []}
    likes_values = [c.like_count for c in comments if c.like_count is not None]
    
    if likes_values:
        likes_values.sort()
        low_threshold = likes_values[len(likes_values)//3] if len(likes_values) > 3 else 0
        high_threshold = likes_values[len(likes_values)*2//3] if len(likes_values) > 3 else 1
        
        # 统计各层级的情感分布
        tier_stats = {
            'low': {'positive': 0, 'negative': 0, 'total': 0},
            'medium': {'positive': 0, 'negative': 0, 'total': 0},
            'high': {'positive': 0, 'negative': 0, 'total': 0}
        }
        
        scatter_data = {'positive': [], 'negative': []}
        
        for comment in comments:
            if comment.like_count is not None:
                # 确定层级
                if comment.like_count <= low_threshold:
                    tier = 'low'
                elif comment.like_count <= high_threshold:
                    tier = 'medium'
                else:
                    tier = 'high'
                
                tier_stats[tier]['total'] += 1
                tier_stats[tier][comment.sentiment_label] += 1
                
                # 散点图数据
                scatter_data[comment.sentiment_label].append([comment.like_count, comment.sentiment_score or 0.5])
    
    return jsonify({
        'tier_stats': tier_stats,
        'scatter_data': scatter_data,
        'thresholds': {'low': low_threshold, 'high': high_threshold} if likes_values else {'low': 0, 'high': 1}
    })

@visualization.route('/api/time_sentiment/<int:history_id>')
@login_required
def api_time_sentiment(history_id):
    """API: 获取时间与情感分布数据"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    comments = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_label.isnot(None),
        Comment.publish_time.isnot(None)
    ).all()
    
    # 按小时统计
    hourly_stats = {}
    daily_stats = {}
    
    for comment in comments:
        if comment.publish_time:
            hour = comment.publish_time.hour
            date = comment.publish_time.strftime('%Y-%m-%d')
            
            # 小时统计
            if hour not in hourly_stats:
                hourly_stats[hour] = {'positive': 0, 'negative': 0}
            hourly_stats[hour][comment.sentiment_label] += 1
            
            # 日期统计
            if date not in daily_stats:
                daily_stats[date] = {'positive': 0, 'negative': 0}
            daily_stats[date][comment.sentiment_label] += 1
    
    # 时间段统计
    period_stats = {
        'morning': {'positive': 0, 'negative': 0},
        'afternoon': {'positive': 0, 'negative': 0},
        'evening': {'positive': 0, 'negative': 0},
        'night': {'positive': 0, 'negative': 0}
    }
    
    for comment in comments:
        if comment.publish_time:
            hour = comment.publish_time.hour
            if 6 <= hour < 12:
                period = 'morning'
            elif 12 <= hour < 18:
                period = 'afternoon'
            elif 18 <= hour < 22:
                period = 'evening'
            else:
                period = 'night'
            
            period_stats[period][comment.sentiment_label] += 1
    
    return jsonify({
        'hourly_stats': hourly_stats,
        'daily_stats': daily_stats,
        'period_stats': period_stats
    })

@visualization.route('/api/location_sentiment/<int:history_id>')
@login_required
def api_location_sentiment(history_id):
    """API: 获取地域与情感分布数据"""
    history = AnalysisHistory.query.filter_by(
        id=history_id,
        user_id=current_user.id
    ).first_or_404()
    
    comments = Comment.query.filter_by(task_id=history.task_id).filter(
        Comment.sentiment_label.isnot(None),
        Comment.ip_location.isnot(None)
    ).all()
    
    # 地域统计
    location_stats = {}
    for comment in comments:
        if comment.ip_location:
            location = comment.ip_location
            if location not in location_stats:
                location_stats[location] = {'positive': 0, 'negative': 0, 'total': 0}
            
            location_stats[location][comment.sentiment_label] += 1
            location_stats[location]['total'] += 1
    
    # 转换为图表数据格式
    locations = list(location_stats.keys())
    positive_data = [location_stats[loc]['positive'] for loc in locations]
    negative_data = [location_stats[loc]['negative'] for loc in locations]
    
    # 计算正面率用于热力图
    heatmap_data = []
    for loc in locations:
        stats = location_stats[loc]
        positive_rate = stats['positive'] / stats['total'] * 100 if stats['total'] > 0 else 0
        heatmap_data.append([loc, positive_rate, stats['total']])
    
    return jsonify({
        'location_stats': location_stats,
        'chart_data': {
            'locations': locations,
            'positive': positive_data,
            'negative': negative_data
        },
        'heatmap_data': heatmap_data
    })

@visualization.route('/export_chart', methods=['POST'])
@login_required
def export_chart():
    """导出图表为图片"""
    try:
        # 获取前端发送的图表数据
        data = request.json
        if not data or 'image_data' not in data:
            return jsonify({'success': False, 'message': '缺少图表数据'})
        
        # 处理Base64编码的图片数据
        image_data = data['image_data']
        # 移除Base64前缀
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # 解码Base64数据
        image_bytes = base64.b64decode(image_data)
        
        # 获取图表类型
        chart_type = data.get('chart_type', 'chart')
        file_ext = data.get('file_ext', 'png')
        
        # 创建响应
        response = Response(
            image_bytes,
            mimetype=f'image/{file_ext}',
            headers={
                'Content-Disposition': f'attachment; filename={chart_type}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{file_ext}'
            }
        )
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@visualization.route('/export_wordcloud', methods=['POST'])
@login_required
def export_wordcloud():
    """导出词云为图片"""
    try:
        # 获取前端发送的词云数据
        data = request.json
        if not data or 'image_data' not in data:
            return jsonify({'success': False, 'message': '缺少词云数据'})
        
        # 处理Base64编码的图片数据
        image_data = data['image_data']
        # 移除Base64前缀
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # 解码Base64数据
        image_bytes = base64.b64decode(image_data)
        
        # 获取词云类型
        wordcloud_type = data.get('wordcloud_type', 'wordcloud')
        file_ext = data.get('file_ext', 'png')
        
        # 创建响应
        response = Response(
            image_bytes,
            mimetype=f'image/{file_ext}',
            headers={
                'Content-Disposition': f'attachment; filename={wordcloud_type}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{file_ext}'
            }
        )
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 导入datetime模块用于日期时间处理
from datetime import datetime
