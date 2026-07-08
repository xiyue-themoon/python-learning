"""Vision→3D 测量管线 — 核心数据结构"""

from dataclasses import dataclass, field
from typing import Optional, Union, Tuple
import numpy as np


# ══════════════════════════════════════════════
# 0. 图像画像
# ══════════════════════════════════════════════

@dataclass
class ImageProfile:
    """图像分诊结果"""
    size: str               # 'S' | 'M' | 'L'
    contrast: str           # 'high' | 'medium' | 'low'
    noise: str              # 'high' | 'medium' | 'low'
    bg_type: str            # 'grid' | 'solid' | 'cluttered' | 'unknown'
    has_reference: bool     # 是否检测到参照物


# ══════════════════════════════════════════════
# 1. 管线选择
# ══════════════════════════════════════════════

@dataclass
class PipelineSelection:
    """管线选择结果"""
    name: str
    steps: list[str]                # 模块名序列
    use_ensemble: bool = False      # 是否启用投票融合
    params: dict = field(default_factory=dict)  # 管线级参数覆盖


# ══════════════════════════════════════════════
# 2. 通用区域
# ══════════════════════════════════════════════

@dataclass(eq=False)
class GenericRegion:
    """数学分割后的通用区域。基于 id 的身份比较和哈希，不看字段值。"""
    id: int
    mask: np.ndarray = field(repr=False, hash=False)  # 布尔矩阵
    bbox: tuple                 # (x, y, w, h)
    centroid: tuple             # (cx, cy)
    area: int                   # 像素数
    area_ratio: float           # 占图像总面积比
    roles: set = field(hash=False)   # {'dominant', 'uniform', ...}
    properties: dict = field(hash=False)  # 扩展统计量
    contour: np.ndarray = field(repr=False, hash=False)  # N×2 边界点集
    convexity: float            # 凸包面积 / 实际面积
    aspect_ratio: float         # 宽高比
    color_mean: np.ndarray = field(repr=False, hash=False)  # HSV 均值
    color_std: np.ndarray = field(repr=False, hash=False)   # HSV 标准差

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, GenericRegion) and self.id == other.id


# ══════════════════════════════════════════════
# 3. 测量结果
# ══════════════════════════════════════════════

@dataclass
class Measurement:
    """单次测量的结果"""
    value: Union[float, Tuple[float, float], Tuple[float, float, float]]  # 单值 / (x,y) / (x,y,z)
    error: float                # 标准误差
    unit: str                   # 'px' | 'mm'
    confidence: float           # 0.0 ~ 1.0


@dataclass
class MeasurementSet:
    """一个算法产出的测量集合"""
    source: str                 # 算法名
    measurements: list[Measurement]
    raw_data: dict = field(default_factory=dict)  # debug 中间结果


# ══════════════════════════════════════════════
# 4. 融合结果
# ══════════════════════════════════════════════

@dataclass
class FusionResult:
    """多算法融合后结果"""
    value: float | tuple
    error: float
    unit: str
    confidence: float
    n_sources: int
    consistency: str            # 'high' | 'medium' | 'low'
    details: list[dict] = field(default_factory=list)
    annotated: bool = False     # True = 已人工复核


# ══════════════════════════════════════════════
# 5. 算法分配
# ══════════════════════════════════════════════

@dataclass
class AlgorithmTask:
    """一个 region 的检测任务"""
    target_region_id: int
    algorithms: list[str]       # ['blob_detect', 'subpixel_fit']
    ensemble: bool = False      # 是否多算法投票
    priority: int = 0           # 执行优先级


# ══════════════════════════════════════════════
# 6. 标定输入
# ══════════════════════════════════════════════

@dataclass
class CalibrationInput:
    """用户输入的标定信息"""
    method: str                 # 'grid' | 'body_height' | 'reference_object' | 'none'
    value_mm: float             # 真实尺寸 (mm)
    description: str = ''       # 描述
    object_bbox: Optional[tuple] = None  # 参照物图像框 (x1, y1, x2, y2) 浮点像素坐标, y向下
