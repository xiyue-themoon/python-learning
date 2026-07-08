"""轮廓提取 (cv2.findContours)

注册为 contour_extract:
  function=contour, size=all, accuracy=4, robustness=4, speed=medium
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'contour_extract',
    function='contour',
    size='all',
    accuracy=4,
    robustness=4,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def contour_extract(image, *, mode: str = 'external', approx: bool = True):
    """Extract contours from a binary image.

    Args:
        image: Binary image (0 or 255).
        mode: 'external' (RETR_EXTERNAL) or 'tree' (RETR_TREE).
        approx: If True, use CHAIN_APPROX_SIMPLE; otherwise CHAIN_APPROX_NONE.

    Returns:
        dict with keys:
          'contours': list of Nx2 arrays
          'n_contours': int count
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

    retrieval = cv2.RETR_EXTERNAL if mode == 'external' else cv2.RETR_TREE
    approx_method = cv2.CHAIN_APPROX_SIMPLE if approx else cv2.CHAIN_APPROX_NONE

    contours, hierarchy = cv2.findContours(binary, retrieval, approx_method)

    contour_list = [cnt.reshape(-1, 2).astype(np.int32) for cnt in contours]
    return {'contours': contour_list, 'n_contours': len(contour_list)}


_validation_errors = validate_tags({'function': 'contour', 'size': 'all', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'contour_extract tag validation failed: {_validation_errors}')
