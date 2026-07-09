"""LSD 线段检测 (Line Segment Detector)

注册为 line_lsd:
  function=line_detect, size=S|M, accuracy=4, robustness=4, speed=medium
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'line_lsd',
    function='line_detect',
    size='S|M',
    accuracy=4,
    robustness=4,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def line_lsd(image, *, min_length: int = 20):
    """Detect line segments using LSD (Line Segment Detector).

    Args:
        image: Grayscale or BGR image.
        min_length: Minimum line segment length (shorter ones filtered out).

    Returns:
        dict with keys:
          'lines': Nx4 array of (x1, y1, x2, y2)
          'n_lines': int
          'widths': line width estimates
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    lsd = cv2.createLineSegmentDetector(0, _refine=cv2.LSD_REFINE_STD)
    lines, widths, _, _ = lsd.detect(gray)

    if lines is None:
        return {'lines': np.empty((0, 4), dtype=np.float32), 'n_lines': 0,
                'widths': np.empty((0, 1), dtype=np.float32)}

    lines = lines.reshape(-1, 4)
    widths = widths.reshape(-1, 1) if widths is not None else np.ones((len(lines), 1))

    # Filter by length
    lengths = np.sqrt((lines[:, 2] - lines[:, 0])**2 + (lines[:, 3] - lines[:, 1])**2)
    mask = lengths >= min_length
    return {
        'lines': lines[mask],
        'n_lines': int(mask.sum()),
        'widths': widths[mask],
    }


_validation_errors = validate_tags({'function': 'line_detect', 'size': 'S|M', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'line_lsd validation: {_validation_errors}')
