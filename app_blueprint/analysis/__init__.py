"""
情感分析蓝图
"""
from flask import Blueprint

analysis = Blueprint('analysis', __name__)

from . import routes
