"""
Flask应用主入口文件
"""
from flask import Flask
from extensions import db, login_manager
from config import config

def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 添加数字格式化过滤器
    @app.template_filter('number_format')
    def number_format(value):
        if value is None:
            return '0'
        try:
            return '{:,}'.format(int(value)).replace(',', ',')
        except (ValueError, TypeError):
            return str(value)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    # 注册蓝图
    from app_blueprint.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app_blueprint.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from app_blueprint.scraper import scraper as scraper_blueprint
    app.register_blueprint(scraper_blueprint, url_prefix='/scraper')
    
    from app_blueprint.analysis import analysis as analysis_blueprint
    app.register_blueprint(analysis_blueprint, url_prefix='/analysis')
    
    from app_blueprint.visualization import visualization as visualization_blueprint
    app.register_blueprint(visualization_blueprint, url_prefix='/visualization')
    
    from app_blueprint.ai import ai as ai_blueprint
    app.register_blueprint(ai_blueprint, url_prefix='/ai')
    
    # 导入模型（在应用上下文中）
    from models.db_models import User
    
    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5001, debug=True)
