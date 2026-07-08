"""Otsu 自适应二值化

注册为 preproc_otsu:
  function=preprocess, size=all, accuracy=3, robustness=3, speed=fast
"""

import cv2
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'preproc_otsu',
    function='preprocess',
    size='all',
    accuracy=3,
    robustness=3,
    speed='fast',
    gpu='none',
    deps=['opencv'],
)
def preproc_otsu(image, *, invert: bool = False, blur_first: bool = True):
    """Apply Otsu's binarization threshold.

    Args:
        image: BGR image or grayscale.
        invert: If True, use THRESH_BINARY_INV.
        blur_first: Apply light Gaussian blur before thresholding.

    Returns:
        Binary image (uint8, 0 or 255).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    if blur_first:
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

    thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, 0, 255, thresh_type + cv2.THRESH_OTSU)
    return binary


_validation_errors = validate_tags({'function': 'preprocess', 'size': 'all', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'preproc_otsu tag validation failed: {_validation_errors}')
