"""S_grid_ensemble 管线 — 多算法融合版 (Phase 2)

Steps: gaussian → clahe → otsu → [morphological + houghp + fld] → fusion → calibrate

与 S_grid 的区别：线检测阶段用 3 种算法并行检测，结果送入 fusion engine 投票融合。
"""

import numpy as np
from ..vision_modules.registry import MODULE_REGISTRY
from ..vision_modules.types import Measurement, MeasurementSet, CalibrationInput
from ..vision_modules.fusion.engine import fuse_measurements
from ..vision_modules.region.segmenter import segment_image
from ..vision_modules.region.semantifier import assign_roles
from ..vision_modules.region.allocator import allocate_algorithms
from .S_grid import _extract_grid_lines


def _call_algo(name: str, image: np.ndarray) -> dict:
    """Call a registered algorithm by name."""
    entry = MODULE_REGISTRY.get(name)
    if entry is None:
        # Search by suffix
        for n, e in MODULE_REGISTRY.items():
            if n.endswith(name):
                entry = e
                break
    if entry is None:
        return {'n_lines': 0, 'lines': np.empty((0, 4), dtype=np.int32)}
    result = entry['fn'](image)
    # Normalize to dict if not already
    if not isinstance(result, dict):
        return {'raw': result}
    return result


def _extract_ensemble_lines(
    image: np.ndarray,
    line_algos: list[str],
    preproc_steps: list[str],
) -> dict:
    """Run multiple line detection algorithms and fuse their results."""
    # Preprocess
    current = image.copy()
    for step in preproc_steps:
        for name, entry in MODULE_REGISTRY.items():
            if name == step or name.endswith(step):
                step_result = entry['fn'](current)
                if isinstance(step_result, np.ndarray):
                    current = step_result
                break

    # Run each line detection algorithm
    all_measurements = []
    line_sets = {}
    for algo in line_algos:
        result = _call_algo(algo, current)
        lines = result.get('lines', np.empty((0, 4), dtype=np.int32))
        n = result.get('n_lines', len(lines))
        line_sets[algo] = {
            'n_lines': n,
            'lines': lines,
        }
        if n > 0:
            all_measurements.append(MeasurementSet(
                source=algo,
                measurements=[
                    Measurement(value=float(n), error=float(np.sqrt(n)),
                                confidence=min(0.9, n / 100.0), unit='count'),
                ],
            ))

    # Fuse line counts
    fusion_results = fuse_measurements(all_measurements) if len(all_measurements) >= 2 else []

    # Combine lines from all algorithms (dedup)
    combined = []
    for algo_info in line_sets.values():
        lines = algo_info['lines']
        for i in range(len(lines)):
            combined.append(lines[i].tolist() if hasattr(lines[i], 'tolist') else list(lines[i]))

    return {
        'line_sets': {k: {'n_lines': v['n_lines']} for k, v in line_sets.items()},
        'combined_lines': combined,
        'total_lines': len(combined),
        'fusion': [
            {'value': r.value, 'consistency': r.consistency, 'n_sources': r.n_sources}
            for r in fusion_results
        ],
    }


def run_S_grid_ensemble(
    image: np.ndarray,
    calib: CalibrationInput = None,
) -> dict:
    """S_grid_ensemble 管线完整执行

    与 S_grid 的差异：
    - 线检测使用 morphological + houghp + fld 三算法并行
    - 线计数经 fusion engine 投票融合
    - 输出含融合置信度

    Args:
        image: BGR 图像
        calib: 标定信息 (可选)

    Returns:
        dict 融合分析结果
    """
    h, w = image.shape[:2]
    result = {
        'image_shape': (w, h),
        'pipeline': 'S_grid_ensemble',
        'outputs': {},
    }

    # --- Segmentation ---
    label_map, quality, props = segment_image(image)
    result['segmentation'] = {'n_regions': label_map.max(), 'quality': quality}

    # --- Semantification ---
    regions = assign_roles(label_map, image, props)
    result['semantics'] = {
        'n_regions': len(regions),
        'dominant_ids': [r.id for r in regions if 'dominant' in r.roles],
    }

    # --- Algorithm allocation ---
    tasks = allocate_algorithms(regions)
    result['tasks'] = [
        {'region_id': t.target_region_id, 'algorithms': t.algorithms, 'ensemble': t.ensemble}
        for t in tasks
    ]

    # --- Ensemble line detection ---
    ensemble_info = _extract_ensemble_lines(
        image,
        line_algos=['line_morphological', 'line_houghp', 'line_fld'],
        preproc_steps=['gaussian', 'clahe', 'otsu'],
    )
    result['grid'] = ensemble_info

    # --- Region measurements ---
    measurements = []
    for region in regions:
        entry = {
            'id': region.id,
            'roles': list(region.roles),
            'bbox': region.bbox,
            'centroid': region.centroid,
            'area_px': region.area,
            'area_ratio': region.area_ratio,
            'convexity': region.convexity,
        }
        measurements.append(entry)
    result['measurements'] = measurements

    # --- Calibration ---
    if calib and calib.method == 'grid' and calib.value_mm > 0:
        # Use Hough lines for grid cell estimation
        hough = ensemble_info.get('line_sets', {}).get('line_houghp', {})
        result['calibration'] = {
            'method': 'grid',
            'grid_mm': calib.value_mm,
            'n_algorithms': len(ensemble_info.get('line_sets', {})),
        }
    else:
        result['calibration'] = {'method': 'none', 'unit': 'px'}

    return result
