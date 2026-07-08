"""形态学预处理（开/闭运算）

注册为 preproc_morphological:
  function=preprocess, size=all, accuracy=2, robustness=5, speed=fast
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'preproc_morphological',
    function='preprocess',
    size='all',
    accuracy=2,
    robustness=5,
    speed='fast',
    gpu='none',
    deps=['opencv'],
)
def preproc_morphological(
    image,
    *,
    operation: str = 'open',
    kernel_size: int = 3,
    iterations: int = 1,
):
    """Apply morphological operation (open/close/dilate/erode).

    Args:
        image: Binary or grayscale image.
        operation: 'open' | 'close' | 'dilate' | 'erode'.
        kernel_size: Structuring element size (odd int).
        iterations: Number of iterations.

    Returns:
        Morphologically processed image.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    op_map = {
        'open': cv2.MORPH_OPEN,
        'close': cv2.MORPH_CLOSE,
        'dilate': cv2.MORPH_DILATE,
        'erode': cv2.MORPH_ERODE,
    }
    op = op_map.get(operation, cv2.MORPH_OPEN)
    return cv2.morphologyEx(image, op, kernel, iterations=iterations)


_validation_errors = validate_tags({'function': 'preprocess', 'size': 'all', 'accuracy': 2})
if _validation_errors:
    raise RuntimeError(f'preproc_morphological tag validation failed: {_validation_errors}')
