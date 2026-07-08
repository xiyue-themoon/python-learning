"""预处理模块

自动导入子模块触发 @register 装饰器。
"""
from . import gaussian, clahe, otsu, morphological

__all__ = ['gaussian', 'clahe', 'otsu', 'morphological']
