"""
主页路由
"""
from flask import render_template
from flask_login import current_user
from . import main
from models.db_models import Comment, AnalysisHistory, ScrapeTask

@main.route('/')
def index():
    """主页"""
    # 根据当前登录用户ID查询统计数据
    if current_user.is_authenticated:
        # 查询当前用户的爬取任务数
        user_tasks = ScrapeTask.query.filter_by(user_id=current_user.id).all()
        total_tasks = len(user_tasks)
        
        # 查询当前用户任务下的评论总数
        if user_tasks:
            task_ids = [task.id for task in user_tasks]
            total_comments = Comment.query.filter(Comment.task_id.in_(task_ids)).count()
            total_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).count()
        else:
            total_comments = 0
            total_analyses = 0
    else:
        # 未登录用户显示0
        total_comments = 0
        total_analyses = 0
        total_tasks = 0
        
    return render_template('index.html', total_comments=total_comments, total_analyses=total_analyses, total_tasks=total_tasks)

@main.route('/about')
def about():
    """关于页面"""
    return render_template('pages/about.html')

@main.route('/help')
def help():
    """帮助中心页面"""
    return render_template('pages/help.html')
