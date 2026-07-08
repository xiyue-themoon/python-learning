"""Vision→3D 视觉模块

自动导入子包触发 @register 装饰器。
"""
from . import (
    registry, tag_schema, types,
    preprocessing, line_detection, cluster,
    calibrate, fusion, region,
)
