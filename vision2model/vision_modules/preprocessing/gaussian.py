"""高斯滤波预处理

注册为 preproc_gaussian:
  function=preprocess, size=all, accuracy=3, robustness=4, speed=fast
"""

import cv2
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'preproc_gaussian',
    function='preprocess',
    size='all',
    accuracy=3,
    robustness=4,
    speed='fast',
    gpu='none',
    deps=['opencv'],
)
def preproc_gaussian(image, *, ksize: int = 5, sigma: float = 0):
    """Apply Gaussian blur.

    Args:
        image: BGR or grayscale image (numpy array).
        ksize: Kernel size (odd int, default 5).
        sigma: Standard deviation (0 = auto from ksize).

    Returns:
        Blurred image (same shape as input).
    """
    ksize = ksize if ksize % 2 == 1 else ksize + 1  # ensure odd
    return cv2.GaussianBlur(image, (ksize, ksize), sigma)


# Verify tags on import
_validation_errors = validate_tags({'function': 'preprocess', 'size': 'all', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'preproc_gaussian tag validation failed: {_validation_errors}')
