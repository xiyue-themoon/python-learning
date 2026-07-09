"""Vision→3D 测量管线 — 多参照交叉校验 (Phase 3.2)

比较多个校准来源的 scale 值，输出 ok/warning/failed + 加权平均。
"""

import numpy as np
from ..types import Measurement, MeasurementSet, FusionResult
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'crosscheck',
    function='calibrate',
    size='all',
    accuracy=5,
    robustness=4,
    speed='fast',
    gpu='none',
    deps=[],
)
def crosscheck_scales(scales: dict[str, Measurement]) -> dict:
    """交叉校验多个校准来源。

    Args:
        scales: {source_name: Measurement} 字典。
               每个 Measurement 应是 mm/px 或 px_per_mm 值。

    Returns:
        dict:
          status: 'single' | 'ok' | 'warning' | 'failed'
          scale: 最佳合并比例尺 (None if failed)
          px_per_mm: float
          error: 标准误差
          consistency: str
          detail: dict[str, float] 每个来源的偏差百分比
          recommendation: str (仅 failed 时)
    """
    if not scales:
        return {
            'status': 'failed', 'scale': None, 'px_per_mm': 0,
            'error': float('inf'), 'consistency': 'unknown',
            'recommendation': '无校准数据',
        }

    # Extract values
    values = []
    names = []
    for name, m in scales.items():
        val = m.value
        if isinstance(val, (list, tuple)):
            val = val[0]
        values.append(float(val))
        names.append(name)

    values = np.array(values)
    if len(values) < 2:
        return {
            'status': 'single',
            'scale': float(values[0]),
            'px_per_mm': float(values[0]),
            'error': 0,
            'consistency': 'unknown',
            'detail': {},
        }

    # Median-based deviation analysis
    median = float(np.median(values))
    deviations = {}
    for i, name in enumerate(names):
        dev_pct = abs(values[i] - median) / max(median, 1e-10) * 100
        deviations[name] = round(dev_pct, 2)

    max_dev = max(deviations.values())
    std_err = float(values.std() / np.sqrt(len(values)))

    if max_dev < 5:
        # All sources agree within 5%
        return {
            'status': 'ok',
            'scale': round(median, 6),
            'px_per_mm': round(median, 6),
            'error': round(std_err, 6),
            'consistency': 'high',
            'detail': deviations,
            'n_sources': len(values),
        }
    elif max_dev < 15:
        # Sources disagree moderately
        return {
            'status': 'warning',
            'scale': round(median, 6),
            'px_per_mm': round(median, 6),
            'error': round(std_err * 1.5, 6),
            'consistency': 'medium',
            'detail': deviations,
            'n_sources': len(values),
            'recommendation': '校准偏差中等，结果仅供参考',
        }
    else:
        # Sources disagree significantly
        return {
            'status': 'failed',
            'scale': None,
            'px_per_mm': None,
            'error': float('inf'),
            'consistency': 'low',
            'detail': deviations,
            'n_sources': len(values),
            'recommendation': '确认参照物真实尺寸或拍摄角度',
        }
