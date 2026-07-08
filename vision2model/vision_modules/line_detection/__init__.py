"""线检测模块

自动导入子模块触发 @register 装饰器。
"""
from . import houghp, contour, shape, blob

__all__ = ['houghp', 'contour', 'shape', 'blob']
