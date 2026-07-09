"""曲率分析 — contour 曲率突变点检测

注册为 curvature_analysis:
  function=shape, size=all, accuracy=4, robustness=3, speed=medium
"""

import numpy as np
import cv2
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'curvature_analysis',
    function='shape',
    size='all',
    accuracy=4,
    robustness=3,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def curvature_analysis(image_or_contour, *, sigma: float = 3.0, threshold: float = 0.3):
    """Detect curvature extrema along a contour (protrusion/corner detection).

    Args:
        image_or_contour: Either a binary image (contours extracted internally)
                         or an Nx2 contour array.
        sigma: Gaussian smoothing sigma for curvature computation.
        threshold: Normalized curvature threshold [0, 1] for detecting extrema.

    Returns:
        dict with keys:
          'curvature': list of curvature values along the contour
          'extrema_idx': list of indices where curvature exceeds threshold
          'extrema_points': list of (x, y) at extrema locations
          'mean_curvature': float
    """
    if isinstance(image_or_contour, list):
        # Use first (largest) contour
        contour = image_or_contour[0] if image_or_contour else np.empty((0, 2), dtype=np.int32)
    elif len(image_or_contour.shape) == 2:
        contour = image_or_contour
    else:
        gray = cv2.cvtColor(image_or_contour, cv2.COLOR_BGR2GRAY) if len(image_or_contour.shape) == 3 else image_or_contour
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contour = cnts[0][:, 0, :] if cnts else np.empty((0, 2), dtype=np.int32)

    if len(contour) < 10:
        return {'curvature': [], 'extrema_idx': [], 'extrema_points': [], 'mean_curvature': 0.0}

    # Convert to float and ensure shape
    contour = contour.astype(np.float64)
    if contour.ndim == 3:
        contour = contour[:, 0, :]
    contour = contour.reshape(-1, 2)

    # Compute curvature using central differences
    n = len(contour)
    curvature = np.zeros(n)

    # Gaussian filter contour
    from scipy.ndimage import gaussian_filter1d
    xs = gaussian_filter1d(contour[:, 0], sigma=sigma, mode='wrap')
    ys = gaussian_filter1d(contour[:, 1], sigma=sigma, mode='wrap')

    for i in range(n):
        prev = (i - 1) % n
        next_ = (i + 1) % n
        dx = xs[next_] - xs[prev]
        dy = ys[next_] - ys[prev]
        ddx = xs[next_] - 2 * xs[i] + xs[prev]
        ddy = ys[next_] - 2 * ys[i] + ys[prev]
        denom = (dx**2 + dy**2) ** 1.5
        if denom > 1e-10:
            curvature[i] = abs(dx * ddy - dy * ddx) / denom

    # Normalize curvature
    max_curv = curvature.max()
    if max_curv > 0:
        curvature_norm = curvature / max_curv
    else:
        curvature_norm = curvature

    # Find extrema (peaks above threshold)
    extrema = []
    for i in range(1, n - 1):
        if curvature_norm[i] > threshold and \
           curvature_norm[i] > curvature_norm[i-1] and \
           curvature_norm[i] > curvature_norm[i+1]:
            extrema.append(i)

    # Peak detection at wrap point
    if n > 2 and curvature_norm[0] > threshold and \
       curvature_norm[0] > curvature_norm[-1] and \
       curvature_norm[0] > curvature_norm[1]:
        extrema.append(0)

    return {
        'curvature': curvature.tolist(),
        'extrema_idx': extrema,
        'extrema_points': [contour[i].tolist() for i in extrema],
        'mean_curvature': float(curvature.mean()),
    }


_validation_errors = validate_tags({'function': 'shape', 'size': 'all', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'curvature_analysis validation: {_validation_errors}')
