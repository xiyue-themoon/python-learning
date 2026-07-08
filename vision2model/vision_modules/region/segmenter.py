"""Vision→3D 测量管线 — 区域分割 (Node 2)

Felzenszwalb 自适应分割 + HSV 巴氏距离合并 + 质量评估 + 重试机制。
"""

import numpy as np
import cv2
from skimage import segmentation, measure, color


# ═══════════════════════════════════════════════════════════
# 可调参数表
# ═══════════════════════════════════════════════════════════

# 三组 Felzenszwalb 参数 (scale, sigma, min_size)
# 第一组保守、第二组激进、第三组更激进（降级路径）
FELZ_PARAMS = [
    (100.0, 0.8, 200),
    (200.0, 0.6, 100),
    (300.0, 0.5, 50),
]

# HSV 合并阈值 (Bhattacharyya distance)
BHATTA_THRESHOLD = 0.3

# 小特征保护：面积比超过此阈值不合并相邻 region
AREA_RATIO_LIMIT = 10.0

# 质量评估阈值
QUALITY_GOOD_REGION_RANGE = (3, 50)       # 合理的 region 数量
QUALITY_BODY_RATIO_MIN = 0.15             # dominant region 应占 >= 15%
QUALITY_SMALL_REGION_MAX_RATIO = 0.30     # 小 region 占比上限


# ═══════════════════════════════════════════════════════════
# HSV 巴氏距离合并
# ═══════════════════════════════════════════════════════════

def _bhattacharyya_distance(h1: np.ndarray, h2: np.ndarray) -> float:
    """Compute Bhattacharyya distance between two HSV histograms.
    
    Returns value in [0, inf), where 0 = identical distributions.
    """
    # Normalize histograms to probability distributions
    h1 = h1.astype(np.float64) / max(h1.sum(), 1e-10)
    h2 = h2.astype(np.float64) / max(h2.sum(), 1e-10)
    # Bhattacharyya coefficient
    bc = np.sqrt(np.clip(h1 * h2, 0, None)).sum()
    return -np.log(max(bc, 1e-10))


def _compute_hsv_hist(image: np.ndarray, mask: np.ndarray, bins: int = 32) -> np.ndarray:
    """Compute HSV histogram for a masked region."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Flatten masked pixels
    pixels = hsv[mask > 0]
    if len(pixels) == 0:
        return np.zeros(bins * 3)
    # Compute 1D histogram per channel (stacked)
    hist = np.concatenate([
        np.histogram(pixels[:, c], bins=bins, range=(0, 255))[0].astype(np.float64)
        for c in range(3)
    ])
    return hist


def _merge_similar_regions(
    label_map: np.ndarray,
    image: np.ndarray,
    props: list,
) -> np.ndarray:
    """Merge adjacent regions with similar HSV profiles using Bhattacharyya distance.
    
    Small feature protection: regions with area ratio > 10x are NOT merged
    to preserve fine details.
    """
    n_labels = label_map.max()
    if n_labels < 2:
        return label_map

    # Compute HSV histogram for each region
    histograms = {}
    for label_id, prop in props.items():
        if label_id == 0:
            continue
        mask = (label_map == label_id).astype(np.uint8)
        histograms[label_id] = _compute_hsv_hist(image, mask)

    # Compute adjacency graph manually (region_adjacency removed in recent skimage)
    # Use 4-connectivity: check rightward and downward pixel pairs
    adjacency = {i: set() for i in range(1, n_labels + 1)}
    # Check rightward neighbors
    for y in range(label_map.shape[0]):
        for x in range(label_map.shape[1] - 1):
            a, b = int(label_map[y, x]), int(label_map[y, x+1])
            if a != b and a != 0 and b != 0:
                adjacency[a].add(b)
                adjacency[b].add(a)
    # Check downward neighbors
    for y in range(label_map.shape[0] - 1):
        for x in range(label_map.shape[1]):
            a, b = int(label_map[y, x]), int(label_map[y+1, x])
            if a != b and a != 0 and b != 0:
                adjacency[a].add(b)
                adjacency[b].add(a)
    merged_map = label_map.copy()
    # Track which labels have been merged
    merged_into = {}  # child_label -> parent_label

    for i in range(1, n_labels + 1):
        if i in merged_into:
            continue
        neighbors = list(adjacency[i])  # copy to avoid set-changed-during-iteration
        for j in neighbors:
            if j in merged_into or j == i:
                continue
            if i not in props or j not in props:
                continue
            # Small feature protection
            area_i = props[i].area if i in props else 0
            area_j = props[j].area if j in props else 0
            if max(area_i, area_j) / max(min(area_i, area_j), 1) > AREA_RATIO_LIMIT:
                continue

            # Bhattacharyya distance check
            hi = histograms.get(i)
            hj = histograms.get(j)
            if hi is None or hj is None:
                continue
            dist = _bhattacharyya_distance(hi, hj)
            if dist < BHATTA_THRESHOLD:
                # Merge j into i (relabel j -> i)
                merged_map[merged_map == j] = i
                merged_into[j] = i
                # Update adjacency for the merged region
                if i in adjacency and j in adjacency:
                    adjacency[i].update(adjacency[j])

    return merged_map


def _assess_quality(label_map: np.ndarray, image_shape: tuple) -> str:
    """Evaluate segmentation quality.
    
    Returns:
        'good' | 'acceptable' | 'poor'
    """
    n_regions = label_map.max()
    h, w = image_shape[:2]
    total_px = h * w

    # Region count check
    if n_regions < QUALITY_GOOD_REGION_RANGE[0] or n_regions > QUALITY_GOOD_REGION_RANGE[1]:
        return 'acceptable' if n_regions < 100 else 'poor'

    # Body ratio: largest region as fraction of image
    region_sizes = [np.sum(label_map == i) for i in range(1, n_regions + 1)]
    if not region_sizes:
        return 'poor'
    body_ratio = max(region_sizes) / total_px
    if body_ratio < QUALITY_BODY_RATIO_MIN:
        return 'acceptable' if body_ratio > 0.05 else 'poor'

    # Small region ratio
    small_threshold = total_px * 0.005
    small_count = sum(1 for s in region_sizes if s < small_threshold)
    small_ratio = small_count / max(n_regions, 1)
    if small_ratio > QUALITY_SMALL_REGION_MAX_RATIO:
        return 'acceptable'

    return 'good'


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def segment_image(image: np.ndarray) -> tuple[np.ndarray, str, list]:
    """Felzenszwalb 自适应分割 + HSV 合并 + 质量评估 + 重试
    
    Args:
        image: BGR 图像 numpy 数组
    
    Returns:
        (label_map, quality, region_props)
        label_map: 整数标签阵列 (0 = background, 1..N = regions)
        quality: 'good' | 'acceptable' | 'poor'
        region_props: skimage.measure.regionprops 列表
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    best_map = None
    best_quality = None
    best_props = []

    for scale, sigma, min_size in FELZ_PARAMS:
        # Felzenszwalb segmentation
        felz_map = segmentation.felzenszwalb(
            image, scale=scale, sigma=sigma, min_size=min_size
        )
        # Normalize to consecutive integers
        felz_map = measure.label(felz_map, connectivity=1)

        # Compute region properties
        props = measure.regionprops(felz_map, intensity_image=gray)
        props_by_label = {p.label: p for p in props}

        # HSV-based merging
        merged_map = _merge_similar_regions(felz_map, image, props_by_label)
        merged_map = measure.label(merged_map, connectivity=1)

        # Assess quality
        quality = _assess_quality(merged_map, image.shape)
        merged_props = measure.regionprops(merged_map, intensity_image=gray)

        # Keep the best segmentation
        quality_order = {'good': 3, 'acceptable': 2, 'poor': 1, None: 0}
        if quality_order.get(quality, 0) > quality_order.get(best_quality, 0):
            best_map = merged_map
            best_quality = quality
            best_props = merged_props

        if best_quality == 'good':
            break  # Early exit on good quality

    return best_map, best_quality, best_props
