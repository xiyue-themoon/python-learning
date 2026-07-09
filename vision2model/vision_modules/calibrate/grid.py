"""Vision→3D 测量管线 — 方格纸校准 (Phase 3.1)

从检测到的格线 → 格距 px → 比例尺 mm/px → MeasurementSet
"""

import numpy as np
from ..registry import register
from ..types import Measurement, MeasurementSet
from ..tag_schema import validate_tags


@register(
    'calibrate_grid',
    function='calibrate',
    size='all',
    accuracy=4,
    robustness=4,
    speed='fast',
    gpu='none',
    deps=[],
)
def calibrate_grid(lines, known_grid_mm: float = 5.0) -> MeasurementSet:
    """从检测到的格线计算像素到毫米的比例尺。

    Args:
        lines: dict with keys 'horizontal_positions' and 'vertical_positions'
               (lists of int/float positions), or a dict from _extract_grid_lines().
        known_grid_mm: 方格纸格距 (mm), 默认 5mm.

    Returns:
        MeasurementSet 包含比例尺测量值 (单位: mm/px 或 px/mm).
        如果无法检测到规律格线，返回空 MeasurementSet.
    """
    measurements = []

    # Extract positions from lines dict
    if isinstance(lines, dict):
        h_pos = lines.get('horizontal_positions', [])
        v_pos = lines.get('vertical_positions', [])
    else:
        return MeasurementSet(source='calibrate_grid', measurements=[])

    # Compute gaps for horizontal and vertical lines
    gaps = []
    if len(h_pos) >= 3:
        h_gaps = np.diff(sorted(h_pos))
        gaps.extend(h_gaps.tolist())
    if len(v_pos) >= 3:
        v_gaps = np.diff(sorted(v_pos))
        gaps.extend(v_gaps.tolist())

    if len(gaps) < 2:
        return MeasurementSet(source='calibrate_grid', measurements=[])

    gaps = np.array(gaps, dtype=np.float64)

    # Remove outliers (IQR)
    q1, q3 = np.percentile(gaps, [25, 75])
    iqr = q3 - q1
    clean = gaps[(gaps >= q1 - 1.5 * iqr) & (gaps <= q3 + 1.5 * iqr)]

    if len(clean) < 2:
        clean = gaps

    grid_px = float(clean.mean())
    px_per_mm = grid_px / known_grid_mm
    mm_per_px = known_grid_mm / grid_px if grid_px > 0 else 0
    error = float(clean.std() / np.sqrt(len(clean))) if len(clean) > 1 else grid_px * 0.1
    cv = float(clean.std() / clean.mean()) if clean.mean() > 0 else 1.0
    confidence = max(0.3, min(0.95, 1.0 - cv))

    measurements.append(
        Measurement(value=round(px_per_mm, 4), error=round(error / known_grid_mm, 4),
                    confidence=round(confidence, 3), unit='px_per_mm')
    )
    measurements.append(
        Measurement(value=round(mm_per_px, 4), error=round(error / grid_px * mm_per_px, 4),
                    confidence=round(confidence, 3), unit='mm_per_px')
    )
    measurements.append(
        Measurement(value=round(grid_px, 2), error=round(error, 2),
                    confidence=round(confidence, 3), unit='px')
    )

    return MeasurementSet(source='calibrate_grid', measurements=measurements,
                          raw_data={'n_gaps': len(clean), 'grid_cv': round(cv, 4)})
