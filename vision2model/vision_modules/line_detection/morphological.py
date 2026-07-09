"""形态学线检测 — 骨架提取 + 交叉点检测

注册为 line_morphological:
  function=line_detect, size=all, accuracy=2, robustness=5, speed=fast
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'line_morphological',
    function='line_detect',
    size='all',
    accuracy=2,
    robustness=5,
    speed='fast',
    gpu='none',
    deps=['opencv'],
)
def line_morphological(image, *, min_angle: float = 15.0):
    """Skeleton-based line detection via morphological thinning.

    Uses Zhang-Suen thinning to extract skeleton, then detects
    junction points (crossings) and line segments.

    Args:
        image: Binary image (0 or 255).
        min_angle: Minimum angle to consider a valid corner (degrees).

    Returns:
        dict with keys:
          'skeleton': thinned binary image
          'junctions': Nx2 array of (x, y) junction coordinates
          'n_junctions': int
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    binary = (binary > 0).astype(np.uint8)

    # Zhang-Suen thinning (pure Python, no ximgproc dependency)
    skeleton = _zhang_suen(binary)

    # Detect junctions: pixels with >= 3 neighbors in 3x3
    kernel = np.ones((3, 3), np.uint8)
    neighbor_count = cv2.filter2D((skeleton > 0).astype(np.uint8), -1, kernel)
    neighbor_count = neighbor_count * (skeleton > 0)

    junctions = np.column_stack(np.where((neighbor_count >= 4) & (skeleton > 0)))
    # Swap to (x, y) format
    if junctions.shape[0] > 0:
        junctions = junctions[:, [1, 0]].astype(np.int32)
    else:
        junctions = np.empty((0, 2), dtype=np.int32)

    return {
        'skeleton': (skeleton * 255).astype(np.uint8),
        'junctions': junctions,
        'n_junctions': len(junctions),
    }


def _zhang_suen(binary: np.ndarray) -> np.ndarray:
    """Pure Python Zhang-Suen thinning algorithm (fallback when cv2.ximgproc unavailable)."""
    img = binary.copy()
    prev = np.zeros_like(img)
    while not np.array_equal(img, prev):
        prev = img.copy()
        img = _zhang_suen_pass(img, 1)
        img = _zhang_suen_pass(img, 2)
    return img


def _zhang_suen_pass(img: np.ndarray, iteration: int) -> np.ndarray:
    """Single pass of Zhang-Suen thinning."""
    result = img.copy()
    h, w = img.shape
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if img[y, x] == 0:
                continue
            p = [img[y-1, x], img[y-1, x+1], img[y, x+1], img[y+1, x+1],
                 img[y+1, x], img[y+1, x-1], img[y, x-1], img[y-1, x-1]]
            B = sum(p)
            A = sum((p[i] == 0 and p[(i+1) % 8] == 1) for i in range(8))
            cond1 = 2 <= B <= 6
            cond2 = A == 1
            if iteration == 1:
                cond3 = p[0] * p[2] * p[4] == 0
                cond4 = p[2] * p[4] * p[6] == 0
            else:
                cond3 = p[0] * p[2] * p[6] == 0
                cond4 = p[0] * p[4] * p[6] == 0
            if cond1 and cond2 and cond3 and cond4:
                result[y, x] = 0
    return result


_validation_errors = validate_tags({'function': 'line_detect', 'size': 'all', 'accuracy': 2})
if _validation_errors:
    raise RuntimeError(f'line_morphological validation: {_validation_errors}')
