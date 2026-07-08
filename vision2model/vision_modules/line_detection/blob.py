"""Blob / 斑点检测 (LoG)

注册为 blob_detect:
  function=blob_detect, size=S|M, accuracy=3, robustness=2, speed=slow
"""

import numpy as np
import cv2
from skimage import feature
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'blob_detect',
    function='blob_detect',
    size='S|M',
    accuracy=3,
    robustness=2,
    speed='slow',
    gpu='none',
    deps=['scikit-image'],
)
def blob_detect(image, *, max_sigma: float = 30, num_sigma: int = 10,
                threshold: float = 0.1, overlap: float = 0.5):
    """Detect blobs using Laplacian of Gaussian (LoG).

    Args:
        image: Grayscale or BGR image.
        max_sigma: Maximum blob radius.
        num_sigma: Number of scales.
        threshold: Detection threshold (lower = more blobs).
        overlap: Max allowed overlap (0-1).

    Returns:
        dict with keys:
          'blobs': Nx3 array of (y, x, radius) or empty (0,3)
          'n_blobs': int
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    blobs = feature.blob_log(gray, max_sigma=max_sigma, num_sigma=num_sigma,
                             threshold=threshold, overlap=overlap)
    if len(blobs) == 0:
        return {'blobs': np.empty((0, 3), dtype=np.float64), 'n_blobs': 0}

    return {'blobs': blobs, 'n_blobs': len(blobs)}


_validation_errors = validate_tags({'function': 'blob_detect', 'size': 'S|M', 'accuracy': 3})
if _validation_errors:
    raise RuntimeError(f'blob_detect tag validation failed: {_validation_errors}')
