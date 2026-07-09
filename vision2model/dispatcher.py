"""Vision→3D 测量管线 — 图像分诊 + 管线选择

Node 0 + Node 1 的完整实现。
analyze_image() 提取图像特征画像，select_pipeline() 按 profile 查管线表。
"""

import cv2
import numpy as np
from .vision_modules.types import ImageProfile, PipelineSelection

# ═══════════════════════════════════════════════════════════
# 管线表
# ═══════════════════════════════════════════════════════════

PIPELINE_TABLE = [
    # NOTE: ensemble-triggered entries must come BEFORE base entries of same size+bg
    # so high-contrast/noisy images hit S_grid_ensemble before falling through to S_grid.
    ('S', 'grid',      'high_contrast',  'S_grid_ensemble', ['gaussian', 'clahe', 'otsu', 'morphological', 'houghp', 'fld', 'fusion', 'calibrate'], True),
    ('S', 'grid',      None,             'S_grid',          ['gaussian', 'clahe', 'otsu', 'houghp', 'diff', 'calibrate'], False),
    ('S', 'solid',     None,             'S_solid',         ['gaussian', 'otsu', 'contour', 'shape'], False),
    ('S', 'cluttered', None,             'S_cluttered',     ['gaussian', 'clahe', 'felzenszwalb', 'contour', 'shape'], False),
    ('M', 'grid',      'high_contrast',  'M_grid_ensemble', ['gaussian', 'clahe', 'lsd', 'fld', 'fusion', 'calibrate'], True),
    ('M', 'grid',      None,             'M_grid',          ['gaussian', 'clahe', 'lsd', 'dbscan', 'calibrate'], False),
    # fallback catches everything else
    (None, None,       None,             'fallback',        ['gaussian', 'otsu', 'houghp', 'diff', 'calibrate'], False),
]

FALLBACK_PIPELINE = PipelineSelection(
    name='fallback',
    steps=['gaussian', 'otsu', 'houghp', 'diff', 'calibrate'],
    use_ensemble=False,
    params={},
)


# ═══════════════════════════════════════════════════════════
# 前置：pip install 完整性检查
# ═══════════════════════════════════════════════════════════

_MISSING_DEPS = []

try:
    from skimage import segmentation, measure
except ImportError:
    _MISSING_DEPS.append('scikit-image')

try:
    from scipy import ndimage as sp_ndimage
    from scipy.spatial import distance as sp_distance
except ImportError:
    _MISSING_DEPS.append('scipy')


# ═══════════════════════════════════════════════════════════
# 图像分析
# ═══════════════════════════════════════════════════════════

def _grade_size(w: int, h: int) -> str:
    """S: both dims <= 600, M: both <= 1920, L: any > 1920"""
    max_dim = max(w, h)
    if max_dim <= 600:
        return 'S'
    elif max_dim <= 1920:
        return 'M'
    return 'L'


def _estimate_contrast(gray: np.ndarray) -> str:
    """RMS contrast thresholds: low < 30, medium < 60, high >= 60"""
    rms = gray.std()
    if rms < 30:
        return 'low'
    elif rms < 60:
        return 'medium'
    return 'high'


def _estimate_noise(gray: np.ndarray) -> str:
    """Laplacian variance: low noise < 50, medium < 200, high >= 200"""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    var = lap.var()
    if var < 50:
        return 'low'
    elif var < 200:
        return 'medium'
    return 'high'


def _guess_bg_type(gray: np.ndarray) -> str:
    """Simple heuristic for background type classification.
    Uses edge density and histogram profile.
    """
    h, w = gray.shape
    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.sum() / 255.0 / (h * w)

    # Grid backgrounds have moderate, regular edge density + periodic structure
    if 0.05 < edge_density < 0.20:
        # Check for grid-like periodic structure via Hough lines
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                                minLineLength=max(w, h) * 0.15,
                                maxLineGap=10)
        if lines is not None and len(lines) >= 8:
            angles = [np.abs(np.arctan2(y2 - y1, x2 - x1)) for (x1, y1, x2, y2) in lines.reshape(-1, 4)]
            horz = sum(1 for a in angles if a < 0.2 or a > np.pi - 0.2)
            vert = sum(1 for a in angles if a > np.pi / 2 - 0.2 and a < np.pi / 2 + 0.2)
            if horz >= 3 and vert >= 3:
                return 'grid'

    if edge_density < 0.03:
        return 'solid'
    elif edge_density > 0.25:
        return 'cluttered'
    return 'unknown'


def _detect_reference(gray: np.ndarray) -> bool:
    """Simple reference object detection: look for a high-contrast
    rectangular or circular region with known-proportion area.
    Returns True if anything reference-like is found.
    """
    # Look for well-defined rectangular/circular high-contrast blobs
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    img_area = h * w
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < img_area * 0.005 or area > img_area * 0.5:
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = cw / max(ch, 1)
        # Reference object is typically compact (aspect ~1 for coin/grid)
        if 0.7 < aspect < 1.5:
            return True
    return False


def analyze_image(image_path: str) -> ImageProfile:
    """提取图像特征画像

    Args:
        image_path: 输入图像路径

    Returns:
        ImageProfile 包含尺寸/对比度/噪声/背景/参照物信息
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return ImageProfile(
        size=_grade_size(w, h),
        contrast=_estimate_contrast(gray),
        noise=_estimate_noise(gray),
        bg_type=_guess_bg_type(gray),
        has_reference=_detect_reference(gray),
    )


# ═══════════════════════════════════════════════════════════
# 管线选择
# ═══════════════════════════════════════════════════════════

def _check_ensemble_trigger(profile: ImageProfile, trigger: str) -> bool:
    """Check if ensemble trigger condition is met."""
    if trigger == 'high_contrast':
        return profile.contrast == 'high' or profile.noise == 'high'
    return False


def select_pipeline(profile: ImageProfile) -> PipelineSelection:
    """按 profile 查管线表，fallback 兜底

    Args:
        profile: 图像画像

    Returns:
        PipelineSelection 管线选择结果
    """
    for size, bg, trigger, name, steps, use_ensemble in PIPELINE_TABLE:
        if size is not None and profile.size != size:
            continue
        if bg is not None and profile.bg_type != bg:
            continue
        if trigger is not None and not _check_ensemble_trigger(profile, trigger):
            continue

        params = {}
        if use_ensemble:
            params = {'ensemble_method': 'vote', 'min_confidence': 0.4}
        return PipelineSelection(
            name=name,
            steps=steps,
            use_ensemble=use_ensemble,
            params=params,
        )

    return FALLBACK_PIPELINE


def dispatcher(image_path: str) -> tuple[ImageProfile, PipelineSelection]:
    """一站式图像分诊：分析 + 选管线

    Args:
        image_path: 输入图像路径

    Returns:
        (ImageProfile, PipelineSelection)
    """
    profile = analyze_image(image_path)
    pipeline = select_pipeline(profile)
    return profile, pipeline
