"""
主页蓝图
"""
from flask import Blueprint

main = Blueprint('main', __name__)

from . import routes
