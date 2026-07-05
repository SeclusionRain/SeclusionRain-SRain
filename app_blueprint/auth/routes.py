"""
用户认证路由
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models.db_models import User
from extensions import db
from . import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('用户名或密码错误')
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 简单验证（学习演示用，不考虑复杂验证）
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已存在')
            return render_template('auth/register.html')
        
        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    """用户个人信息页面"""
    from models.db_models import ScrapeTask, AnalysisHistory
    
    # 获取最近的任务和分析记录
    recent_tasks = ScrapeTask.query.filter_by(user_id=current_user.id).order_by(ScrapeTask.created_at.desc()).limit(5).all()
    recent_analyses = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(AnalysisHistory.analysis_time.desc()).limit(5).all()
    
    return render_template('auth/profile_simple.html', 
                         recent_tasks=recent_tasks, 
                         recent_analyses=recent_analyses)

@auth.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """更新用户个人信息"""
    from flask import jsonify
    try:
        # 只更新邮箱（现有字段）
        current_user.email = request.form.get('email', '').strip()
        
        # 保存到数据库
        db.session.commit()
        
        return jsonify({'success': True, 'message': '个人信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@auth.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    from flask import jsonify
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证当前密码
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': '当前密码错误'})
        
        # 验证新密码
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '新密码和确认密码不匹配'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'})
        
        # 更新密码
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'修改失败：{str(e)}'})

@auth.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """上传用户头像"""
    from flask import jsonify
    import os
    import uuid
    
    try:
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return jsonify({'success': False, 'message': '只支持PNG、JPG、JPEG、GIF格式的图片'})
        
        # 生成唯一文件名
        filename = f"{uuid.uuid4()}_{file.filename}"
        upload_dir = os.path.join(os.path.dirname(__file__), '../../static/avatars')
        file_path = os.path.join(upload_dir, filename)
        
        # 保存文件
        file.save(file_path)
        
        # 更新用户头像路径
        avatar_url = f"/static/avatars/{filename}"
        
        # 删除旧头像文件（如果有）
        if current_user.avatar and current_user.avatar.startswith('/static/avatars/'):
            old_avatar_path = os.path.join(os.path.dirname(__file__), '../..', current_user.avatar[1:])
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        
        current_user.avatar = avatar_url
        db.session.commit()
        
        return jsonify({'success': True, 'message': '头像上传成功', 'avatar_url': avatar_url})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'})
