"""Vision→3D 测量管线 — 区域语义化 (Node 3)

给每个 region 分配通用数学角色 + 宽松对称检测。
不假设物体类型，只用几何和颜色统计量做判定。
"""

import numpy as np
import cv2
from skimage import measure
from ..types import GenericRegion


# ═══════════════════════════════════════════════════════════
# 角色判定阈值
# ═══════════════════════════════════════════════════════════

DOMINANT_AREA_RATIO = 0.10         # dominant 最少占图 10% (分割后碎片化容忍)
DOMINANT_CENTER_MARGIN = 0.20      # 质心距图像中心偏差容限 (归一化)

BACKGROUND_AREA_RATIO = 0.10       # background 最少占图 10%
BACKGROUND_BORDER_MARGIN = 0.10    # 距图像边界的最大容限

ACCENT_AREA_RATIO = 0.05           # accent 最多占图 5%
ACCENT_CONTRAST_MIN = 40           # 颜色强度标准差阈值

UNIFORM_STD_THRESHOLD = 20         # HSV 标准差低于此值视为 uniform

FRAGMENT_AREA_RATIO = 0.02         # fragment 最多占图 2%


# ═══════════════════════════════════════════════════════════
# 角色判定
# ═══════════════════════════════════════════════════════════

def _is_near_center(centroid_yx: tuple, img_shape: tuple, margin: float = DOMINANT_CENTER_MARGIN) -> bool:
    """Check if centroid falls within the central region of the image."""
    h, w = img_shape[:2]
    cy, cx = centroid_yx
    cx_norm = cx / max(w, 1)
    cy_norm = cy / max(h, 1)
    return (0.5 - margin < cx_norm < 0.5 + margin and
            0.5 - margin < cy_norm < 0.5 + margin)


def _is_near_border(bbox: tuple, img_shape: tuple, margin: float = BACKGROUND_BORDER_MARGIN) -> bool:
    """Check if bbox touches or is near the image border."""
    h, w = img_shape[:2]
    minr, minc, maxr, maxc = bbox
    return (minr < h * margin or maxr > h * (1 - margin) or
            minc < w * margin or maxc > w * (1 - margin))


def _get_centroid_yx(region_prop) -> tuple:
    """Get centroid as (y, x) from regionprops."""
    return (region_prop.centroid[0], region_prop.centroid[1])


def assign_roles(
    label_map: np.ndarray,
    image: np.ndarray,
    props: list,
) -> list[GenericRegion]:
    """给每个 region 分配通用数学角色

    Args:
        label_map: 整数标签阵列 (0=background, 1..N=regions)
        image: BGR 输入图像
        props: measure.regionprops 列表

    Returns:
        list[GenericRegion] 带角色的通用区域列表
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    img_area = h * w

    regions: list[GenericRegion] = []
    rid = 0

    # First pass: build GenericRegions with basic properties
    for prop in props:
        if prop.label == 0:
            continue
        rid += 1
        mask = (label_map == prop.label).astype(np.uint8)
        contour = _extract_contour(mask)

        # Color statistics
        masked_hsv = hsv[mask > 0]
        color_mean = masked_hsv.mean(axis=0) if len(masked_hsv) > 0 else np.zeros(3)
        color_std = masked_hsv.std(axis=0) if len(masked_hsv) > 0 else np.zeros(3)

        # Convexity
        if len(contour) >= 5:
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            convexity = cv2.contourArea(contour) / max(hull_area, 1)
        else:
            convexity = 1.0

        minr, minc, maxr, maxc = prop.bbox
        region = GenericRegion(
            id=rid,
            mask=mask,
            bbox=(minc, minr, maxc - minc, maxr - minr),  # (x, y, w, h)
            centroid=(prop.centroid[1], prop.centroid[0]),  # (cx, cy)
            area=int(prop.area),
            area_ratio=prop.area / max(img_area, 1),
            roles=set(),
            properties={},
            contour=contour,
            convexity=convexity,
            aspect_ratio=prop.area / max((maxc - minc) * (maxr - minr), 1),  # solidity proxy
            color_mean=color_mean,
            color_std=color_std,
        )
        regions.append(region)

    if not regions:
        return regions

    # Second pass: assign roles
    # Sort by area descending so we process dominant first
    regions.sort(key=lambda r: r.area, reverse=True)

    for region in regions:
        roles = set()

        # Dominant: largest regions near center
        cy, cx = region.centroid[1], region.centroid[0]  # y, x from GenericRegion
        if region.area_ratio >= DOMINANT_AREA_RATIO and _is_near_center((cy, cx), image.shape):
            roles.add('dominant')

        # Background: large, near border
        if region.area_ratio >= BACKGROUND_AREA_RATIO:
            bbox = (region.bbox[1], region.bbox[0],
                    region.bbox[1] + region.bbox[3], region.bbox[0] + region.bbox[2])
            if _is_near_border(bbox, image.shape):
                roles.add('background')

        # Accent: small + high contrast
        if region.area_ratio <= ACCENT_AREA_RATIO:
            std_val = max(region.color_std) if region.color_std.size > 0 else 0
            if std_val >= ACCENT_CONTRAST_MIN:
                roles.add('accent')

        # Uniform: low color variation
        if region.color_std.size > 0 and max(region.color_std) <= UNIFORM_STD_THRESHOLD:
            roles.add('uniform')

        # Patterned: high edge density within region
        edge_density = _edge_density_in_mask(gray, region.mask)
        if edge_density > 0.15:
            roles.add('patterned')

        # Fragment: very small, isolated
        if region.area_ratio <= FRAGMENT_AREA_RATIO:
            roles.add('fragment')

        # If no roles assigned, default to adjunct
        if not roles:
            roles.add('adjunct')

        region.roles = roles

    # Third pass: inclusion detection (needs full region list)
    _detect_inclusions(regions)

    return regions


def _extract_contour(mask: np.ndarray) -> np.ndarray:
    """Extract outer contour from a binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        cnt = contours[0]
        return cnt.reshape(-1, 2).astype(np.int32)
    return np.zeros((0, 2), dtype=np.int32)


def _edge_density_in_mask(gray: np.ndarray, mask: np.ndarray) -> float:
    """Compute edge density (Canny) within a mask region."""
    edges = cv2.Canny(gray, 50, 150)
    masked_edges = edges[mask > 0]
    masked_area = mask.sum()
    if masked_area == 0:
        return 0.0
    return masked_edges.sum() / 255.0 / masked_area


def _detect_inclusions(regions: list[GenericRegion]) -> None:
    """Detect inclusion roles: regions completely surrounded by another.
    Mutates regions in-place by adding 'inclusion' role.
    """
    for r in regions:
        if 'fragment' in r.roles:
            continue
        # Check if this region is fully inside another's bounding box
        rx, ry, rw, rh = r.bbox
        r_center = (rx + rw / 2, ry + rh / 2)
        for parent in regions:
            if parent.id == r.id:
                continue
            if abs(r.area - parent.area) < 0.01 * max(r.area, parent.area, 1):
                continue
            px, py, pw, ph = parent.bbox
            if (px < r_center[0] < px + pw and py < r_center[1] < py + ph and
                    r.area < parent.area * 0.5):
                r.roles.add('inclusion')
                # Remove dominant from inclusion (contradiction)
                r.roles.discard('dominant')
                break


# ═══════════════════════════════════════════════════════════
# 对称检测
# ═══════════════════════════════════════════════════════════

TOLERANCE_Y = 0.08   # 允许的垂直偏差 (占 dominant 高度比)
TOLERANCE_X = 0.12   # 允许的水平偏差 (占 dominant 宽度比)


def find_symmetric_pairs(
    candidates: list[GenericRegion],
    dominant_centroid: tuple,
    dominant_bbox: tuple,
) -> list[tuple[GenericRegion, GenericRegion]]:
    """宽松对称配对 — 用于成对特征识别

    Args:
        candidates: 候选 region 列表
        dominant_centroid: dominant region 的 (cx, cy)
        dominant_bbox: dominant region 的 (x, y, w, h)

    Returns:
        list[(r1, r2)] 对称对列表，每个 pair 按左→右排序
    """
    pairs = []
    used = set()
    dom_cx, dom_cy = dominant_centroid
    dom_w = dominant_bbox[2]
    dom_h = dominant_bbox[3]

    for i, a in enumerate(candidates):
        if i in used:
            continue
        for j, b in enumerate(candidates):
            if j <= i or j in used:
                continue

            # Vertical alignment: y-coordinates should be close
            dy = abs(a.centroid[1] - b.centroid[1])
            if dy > dom_h * TOLERANCE_Y:
                continue

            # Horizontal symmetry: distances from dominant center should match
            dx_a = abs(a.centroid[0] - dom_cx)
            dx_b = abs(b.centroid[0] - dom_cx)
            if abs(dx_a - dx_b) > dom_w * TOLERANCE_X:
                continue

            # Sort pair left-to-right
            if a.centroid[0] < b.centroid[0]:
                pairs.append((a, b))
            else:
                pairs.append((b, a))
            used.add(i)
            used.add(j)

    return pairs
