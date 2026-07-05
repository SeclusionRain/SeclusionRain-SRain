"""
爬虫功能蓝图
"""
from flask import Blueprint

scraper = Blueprint('scraper', __name__)

from . import routes
