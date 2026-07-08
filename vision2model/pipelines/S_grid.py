"""S_grid 管线 — 小尺寸方格纸图像的完整处理管线

Steps: gaussian → clahe → otsu → houghp → diff → calibrate
"""

import cv2
import numpy as np
from ..dispatcher import dispatcher
from ..vision_modules.region.segmenter import segment_image
from ..vision_modules.region.semantifier import assign_roles
from ..vision_modules.region.allocator import allocate_algorithms
from ..vision_modules.registry import MODULE_REGISTRY, find_modules
from ..vision_modules.types import ImageProfile, PipelineSelection, MeasurementSet, CalibrationInput


def _execute_step(step_name: str, image: np.ndarray, params: dict = None) -> np.ndarray:
    """Execute a single pipeline step by looking up the registered module.
    
    Returns processed image (or dict for non-image steps).
    """
    fn = None
    for name, entry in MODULE_REGISTRY.items():
        if name == step_name or name.endswith(step_name):
            fn = entry['fn']
            break
        if 'function' in entry['tags'] and entry['tags']['function'] == step_name:
            fn = entry['fn']
            break
    if fn is None:
        raise ValueError(f"Step '{step_name}' not found in registry")
    
    step_params = (params or {}).get(step_name, {})
    return fn(image, **step_params)


def _extract_grid_lines(
    image: np.ndarray,
    preproc_steps: list[str],
    params: dict,
) -> dict:
    """Execute preprocessing steps and Hough line detection for grid lines."""
    current = image.copy()
    for step in preproc_steps:
        step_result = _execute_step(step, current, params)
        if isinstance(step_result, np.ndarray):
            current = step_result

    # Run Hough lines on the preprocessed image
    hough_result = _execute_step('houghp', current, params)
    lines_arr = hough_result.get('lines', np.empty((0, 4), dtype=np.int32))

    # Cluster lines into horizontal and vertical
    if len(lines_arr) > 0:
        angles = []
        positions = []
        for x1, y1, x2, y2 in lines_arr:
            dx = x2 - x1
            dy = y2 - y1
            angle = np.degrees(np.arctan2(abs(dy), max(abs(dx), 1)))
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            angles.append(angle)
            positions.append((mid_x, mid_y, angle))

        # Classify: horizontal (angle < 30 deg from horizontal) vs vertical (angle > 60 deg)
        h_lines = [(x, y, a) for x, y, a in positions if a < 30]
        v_lines = [(x, y, a) for x, y, a in positions if a > 60]
    else:
        h_lines = []
        v_lines = []

    return {
        'n_horizontal': len(h_lines),
        'n_vertical': len(v_lines),
        'total_lines': len(lines_arr),
        'horizontal_positions': sorted(set(round(y) for _, y, _ in h_lines)),
        'vertical_positions': sorted(set(round(x) for x, _, _ in v_lines)),
        'grid_cell_estimate_px': _estimate_grid_cell_px(h_lines, v_lines),
        'raw_lines': lines_arr,
    }


def _estimate_grid_cell_px(h_lines: list, v_lines: list) -> float:
    """Estimate grid cell size in pixels from line spacing."""
    if len(h_lines) < 3 and len(v_lines) < 3:
        return 0.0
    gaps = []
    h_ys = sorted(set(round(y) for _, y, _ in h_lines))
    for i in range(1, len(h_ys)):
        gaps.append(h_ys[i] - h_ys[i - 1])
    v_xs = sorted(set(round(x) for x, _, _ in v_lines))
    for i in range(1, len(v_xs)):
        gaps.append(v_xs[i] - v_xs[i - 1])
    if not gaps:
        return 0.0
    # Remove outliers (IQR)
    gaps = np.array(gaps, dtype=np.float64)
    q1, q3 = np.percentile(gaps, [25, 75])
    iqr = q3 - q1
    clean = gaps[(gaps >= q1 - 1.5 * iqr) & (gaps <= q3 + 1.5 * iqr)]
    return float(np.mean(clean)) if len(clean) > 0 else float(np.mean(gaps))


def run_S_grid(
    image: np.ndarray,
    calib: CalibrationInput = None,
) -> dict:
    """S_grid 管线完整执行

    Steps:
      1. dispatcher → profile (验证 pipeline match)
      2. segmenter → regions
      3. semantifier → labeled regions
      4. allocator → tasks
      5. 按 tasks 执行对应算法
      6. calibrate
      7. output JSON + SVG

    Args:
        image: BGR 图像
        calib: 标定信息 (可选)

    Returns:
        dict 包含所有分析结果
    """
    h, w = image.shape[:2]
    result = {
        'image_shape': (w, h),
        'pipeline': 'S_grid',
        'outputs': {},
        'measurements': [],
    }

    # --- Step 1: Segmentation ---
    label_map, quality, props = segment_image(image)
    result['segmentation'] = {
        'n_regions': label_map.max(),
        'quality': quality,
    }
    if label_map.max() < 1:
        result['outputs']['warning'] = 'Segmentation produced no regions'
        return result

    # --- Step 2: Semantification ---
    regions = assign_roles(label_map, image, props)
    result['semantics'] = {
        'n_regions': len(regions),
        'dominant_ids': [r.id for r in regions if 'dominant' in r.roles],
        'inclusion_ids': [r.id for r in regions if 'inclusion' in r.roles],
        'accent_ids': [r.id for r in regions if 'accent' in r.roles],
    }

    # --- Step 3: Algorithm allocation ---
    tasks = allocate_algorithms(regions)
    result['tasks'] = [
        {'region_id': t.target_region_id, 'algorithms': t.algorithms, 'ensemble': t.ensemble}
        for t in tasks
    ]

    # --- Step 4: Grid line detection (S_grid specific) ---
    grid_info = _extract_grid_lines(image, ['gaussian', 'clahe', 'otsu'], {})
    result['grid'] = grid_info

    # --- Step 5: Region measurements ---
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
            'aspect_ratio': region.aspect_ratio,
            'color_mean': region.color_mean.tolist() if hasattr(region.color_mean, 'tolist') else region.color_mean,
        }
        measurements.append(entry)
    result['measurements'] = measurements

    # --- Step 6: Calibration ---
    if calib and calib.method == 'grid' and calib.value_mm > 0 and grid_info['grid_cell_estimate_px'] > 0:
        px_per_mm = grid_info['grid_cell_estimate_px'] / calib.value_mm
        scale_info = {
            'method': 'grid',
            'px_per_mm': px_per_mm,
            'grid_mm': calib.value_mm,
            'grid_px': grid_info['grid_cell_estimate_px'],
        }
        result['calibration'] = scale_info

        # Convert key measurements to mm
        for m in result['measurements']:
            if 'area_px' in m:
                m['area_mm2'] = m['area_px'] / (px_per_mm ** 2)
    else:
        result['calibration'] = {'method': 'none', 'unit': 'px'}

    return result
