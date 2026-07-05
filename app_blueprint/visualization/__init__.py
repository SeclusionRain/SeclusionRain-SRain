"""
可视化蓝图
"""
from flask import Blueprint

visualization = Blueprint('visualization', __name__)

from . import routes
