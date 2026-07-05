"""
AI功能蓝图
"""
from flask import Blueprint

ai = Blueprint('ai', __name__)

from . import routes
