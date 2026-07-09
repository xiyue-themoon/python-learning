"""Vision→3D 测量管线 — 融合引擎 (Phase 2)

多算法测量融合管线:
  低置信过滤 (<0.3) → IQR 去异常值 → 加权平均 → 误差传播 → 一致性检验
"""

import numpy as np
from ..types import MeasurementSet, FusionResult


# ═══════════════════════════════════════════════════════════
# 阈值
# ═══════════════════════════════════════════════════════════

MIN_CONFIDENCE = 0.3        # 低于此值的测量直接丢弃
CV_HIGH = 0.05              # 变异系数 < 5% → high consistency
CV_MEDIUM = 0.15            # 变异系数 < 15% → medium consistency


def fuse_measurements(sets: list[MeasurementSet]) -> list[FusionResult]:
    """融合多算法测量结果

    策略:
      1. 低置信过滤: confidence < MIN_CONFIDENCE 的测量丢弃
      2. IQR 去异常值: 对每个测量维度独立去噪
      3. 加权平均: 以 confidence 为权重
      4. 误差传播: σ² = Σ(w² · σ²ᵢ) / (Σw)²
      5. 一致性检验: CV < 5% high, < 15% medium, else low

    Args:
        sets: 多算法测量集合列表

    Returns:
        list[FusionResult] 融合后的结果列表
    """
    if not sets:
        return []

    # Flatten all measurements across all sets
    all_measurements = []
    for ms in sets:
        for m in ms.measurements:
            all_measurements.append({
                'source': ms.source,
                'value': m.value,
                'error': m.error,
                'confidence': m.confidence,
                'unit': m.unit,
            })

    if not all_measurements:
        return []

    # Pre-filter low confidence
    filtered = [m for m in all_measurements if m['confidence'] >= MIN_CONFIDENCE]
    if len(filtered) < 2:
        # Not enough data for fusion; return raw best
        return _single_best(all_measurements)

    # Group by value type (single float vs tuple)
    scalar = [m for m in filtered if isinstance(m['value'], (int, float))]
    vec2 = [m for m in filtered if isinstance(m['value'], (tuple, list)) and len(m['value']) == 2]
    vec3 = [m for m in filtered if isinstance(m['value'], (tuple, list)) and len(m['value']) == 3]

    results = []

    if scalar:
        result = _fuse_scalar(scalar)
        if result:
            results.append(result)

    if vec2:
        result = _fuse_vector(vec2, 2)
        if result:
            results.append(result)

    if vec3:
        result = _fuse_vector(vec3, 3)
        if result:
            results.append(result)

    return results


def _single_best(measurements: list[dict]) -> list[FusionResult]:
    """Not enough measurements for fusion — return highest-confidence single."""
    if not measurements:
        return []
    best = max(measurements, key=lambda m: m['confidence'])
    return [FusionResult(
        value=best['value'],
        error=best['error'],
        unit=best['unit'],
        confidence=best['confidence'],
        n_sources=1,
        consistency='low',
        details=[{'source': best['source'], 'value': best['value']}],
    )]


def _fuse_scalar(measurements: list[dict]) -> FusionResult | None:
    """Fuse scalar measurements into a single FusionResult."""
    if len(measurements) < 2:
        return None

    values = np.array([m['value'] for m in measurements], dtype=np.float64)
    errors = np.array([m['error'] for m in measurements], dtype=np.float64)
    weights = np.array([m['confidence'] for m in measurements], dtype=np.float64)
    unit = measurements[0]['unit']

    # IQR outlier removal
    clean_mask = _iqr_filter(values)
    if clean_mask.sum() < 1:
        return None

    cv = _compute_cv(values[clean_mask])
    fused_value, fused_error = _weighted_avg(
        values[clean_mask], errors[clean_mask], weights[clean_mask]
    )

    return FusionResult(
        value=float(fused_value),
        error=float(fused_error),
        unit=unit,
        confidence=float(weights[clean_mask].mean()),
        n_sources=int(clean_mask.sum()),
        consistency=_classify_consistency(cv),
        details=[
            {'source': m['source'], 'value': float(m['value']), 'confidence': float(m['confidence'])}
            for m in measurements
        ],
    )


def _fuse_vector(measurements: list[dict], dim: int) -> FusionResult | None:
    """Fuse vector (2D or 3D) measurements into a single FusionResult."""
    if len(measurements) < 2:
        return None

    values = np.array([list(m['value']) for m in measurements], dtype=np.float64)
    errors = np.array([m['error'] for m in measurements], dtype=np.float64)
    weights = np.array([m['confidence'] for m in measurements], dtype=np.float64)

    # Per-dimension IQR filtering
    clean_mask = np.ones(len(measurements), dtype=bool)
    for d in range(dim):
        dim_clean = _iqr_filter(values[:, d])
        clean_mask &= dim_clean
    if clean_mask.sum() < 1:
        return None

    fused_values = []
    fused_errors = []
    for d in range(dim):
        fv, fe = _weighted_avg(values[clean_mask, d], errors[clean_mask], weights[clean_mask])
        fused_values.append(float(fv))
        fused_errors.append(float(fe))

    # Overall CV across all dimensions
    cvs = [_compute_cv(values[clean_mask, d]) for d in range(dim)]
    overall_cv = np.mean(cvs)

    return FusionResult(
        value=tuple(fused_values),
        error=float(np.mean(fused_errors)),
        unit=measurements[0]['unit'],
        confidence=float(weights[clean_mask].mean()),
        n_sources=int(clean_mask.sum()),
        consistency=_classify_consistency(overall_cv),
        details=[
            {'source': m['source'], 'value': m['value'], 'confidence': m['confidence']}
            for m in measurements
        ],
    )


def _iqr_filter(values: np.ndarray) -> np.ndarray:
    """IQR-based outlier removal. Returns boolean mask."""
    if len(values) < 4:
        # Too few samples for meaningful IQR
        return np.ones(len(values), dtype=bool)
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return (values >= lower) & (values <= upper)


def _weighted_avg(
    values: np.ndarray, errors: np.ndarray, weights: np.ndarray
) -> tuple[float, float]:
    """Weighted average with error propagation.

    value = Σ(w · v) / Σ(w)
    σ² = Σ(w² · σ²ᵢ) / (Σw)²
    """
    w_sum = weights.sum()
    if w_sum == 0:
        return float(values.mean()), float(errors.mean())

    fused = (weights * values).sum() / w_sum
    # Error propagation
    var = (weights**2 * errors**2).sum() / (w_sum**2)
    return float(fused), float(np.sqrt(var))


def _compute_cv(values: np.ndarray) -> float:
    """Coefficient of variation = std / mean (for positive values)."""
    mean = values.mean()
    if abs(mean) < 1e-10:
        return float('inf')
    return float(values.std() / abs(mean))


def _classify_consistency(cv: float) -> str:
    """Classify consistency from coefficient of variation."""
    if cv < CV_HIGH:
        return 'high'
    elif cv < CV_MEDIUM:
        return 'medium'
    return 'low'
