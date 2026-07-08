"""CLAHE 对比度受限自适应直方图均衡化

注册为 preproc_clahe:
  function=preprocess, size=all, accuracy=3, robustness=4, speed=fast
"""

import cv2
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'preproc_clahe',
    function='preprocess',
    size='all',
    accuracy=3,
    robustness=4,
    speed='fast',
    gpu='none',
    deps=['opencv'],
)
def preproc_clahe(image, *, clip_limit: float = 2.0, grid_size: int = 8):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Args:
        image: BGR image (converted to LAB internally).
        clip_limit: Contrast limit (default 2.0).
        grid_size: Tile grid size (default 8).

    Returns:
        CLAHE-enhanced BGR image.
    """
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
        l_eq = clahe.apply(l_channel)
        merged = cv2.merge((l_eq, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
        return clahe.apply(image)


_validation_errors = validate_tags({'function': 'preprocess', 'size': 'all', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'preproc_clahe tag validation failed: {_validation_errors}')
