"""Hough 线检测 (HoughLinesP)

注册为 line_houghp:
  function=line_detect, size=all, accuracy=3, robustness=3, speed=medium
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'line_houghp',
    function='line_detect',
    size='all',
    accuracy=3,
    robustness=3,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def line_houghp(image, *, threshold: int = 80, min_length_ratio: float = 0.15,
                max_gap: int = 10):
    """Detect line segments using probabilistic Hough transform.

    Args:
        image: Binary edge image (Canny output recommended).
        threshold: Accumulator threshold.
        min_length_ratio: Minimum line length as fraction of image diagonal.
        max_gap: Maximum gap between segments to connect.

    Returns:
        dict with keys:
          'lines': Nx4 array of (x1, y1, x2, y2) or empty (0,4)
          'n_lines': int count
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    h, w = gray.shape
    diag = np.sqrt(h**2 + w**2)
    min_length = int(diag * min_length_ratio)

    lines = cv2.HoughLinesP(gray, rho=1, theta=np.pi/180,
                            threshold=threshold,
                            minLineLength=min_length,
                            maxLineGap=max_gap)
    if lines is None:
        return {'lines': np.empty((0, 4), dtype=np.int32), 'n_lines': 0}

    lines_arr = np.asarray(lines, dtype=np.int32)
    if lines_arr.ndim == 3:
        lines_arr = lines_arr[:, 0, :]
    lines_arr = lines_arr.reshape(-1, 4)
    return {'lines': lines_arr.astype(np.int32), 'n_lines': len(lines_arr)}


_validation_errors = validate_tags({'function': 'line_detect', 'size': 'all', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'line_houghp tag validation failed: {_validation_errors}')
