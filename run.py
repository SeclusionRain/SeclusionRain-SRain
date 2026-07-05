"""
Flask应用启动脚本
"""
from app import create_app

# 创建应用实例
app = create_app('development')

if __name__ == '__main__':
    print("=" * 50)
    print("抖音美妆视频评论情感分析系统启动中...")
    print("访问地址: http://127.0.0.1:5001/")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5001, debug=True)
