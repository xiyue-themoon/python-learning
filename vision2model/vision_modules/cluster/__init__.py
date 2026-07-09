"""聚类模块

自动导入子模块触发 @register 装饰器。
"""
from . import diff, dbscan

__all__ = ['diff', 'dbscan']
