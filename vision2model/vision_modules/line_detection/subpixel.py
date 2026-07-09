"""亚像素拟合 — 2D 高斯拟合获取精确特征点

注册为 subpixel_fit:
  function=blob_detect, size=S|M, accuracy=5, robustness=2, speed=slow
"""

import numpy as np
from scipy.optimize import curve_fit
from ..registry import register
from ..tag_schema import validate_tags


def _gaussian_2d(xy, amplitude, x0, y0, sigma_x, sigma_y, theta, offset):
    """2D Gaussian function for fitting."""
    x, y = xy
    xo = x - x0
    yo = y - y0
    a = np.cos(theta)**2 / (2 * sigma_x**2) + np.sin(theta)**2 / (2 * sigma_y**2)
    b = -np.sin(2 * theta) / (4 * sigma_x**2) + np.sin(2 * theta) / (4 * sigma_y**2)
    c = np.sin(theta)**2 / (2 * sigma_x**2) + np.cos(theta)**2 / (2 * sigma_y**2)
    return offset + amplitude * np.exp(-(a * xo**2 + 2 * b * xo * yo + c * yo**2))


@register(
    'subpixel_fit',
    function='blob_detect',
    size='S|M',
    accuracy=5,
    robustness=2,
    speed='slow',
    gpu='none',
    deps=['scipy'],
)
def subpixel_fit(image, *, rough_centers: list = None, window_size: int = 11):
    """Fit 2D Gaussians around rough feature centers for subpixel precision.

    Args:
        image: Grayscale image.
        rough_centers: List of (x, y) tuples for initial estimates.
                      If None, uses blob_log detection.
        window_size: Fitting window size (odd int).

    Returns:
        dict with keys:
          'fits': list of subpixel positions (x, y)
          'n_fits': int
          'errors': list of fitting error estimates
    """
    if len(image.shape) == 3:
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    if rough_centers is None:
        # Fall back to simple detection
        from skimage.feature import blob_log
        blobs = blob_log(gray, max_sigma=10, num_sigma=5, threshold=0.05)
        rough_centers = [(b[1], b[0]) for b in blobs] if len(blobs) > 0 else []

    hw = window_size // 2
    fits = []
    errors = []

    for cx, cy in rough_centers:
        x0, y0 = int(round(cx)), int(round(cy))
        x_start = max(0, x0 - hw)
        x_end = min(gray.shape[1], x0 + hw + 1)
        y_start = max(0, y0 - hw)
        y_end = min(gray.shape[0], y0 + hw + 1)

        patch = gray[y_start:y_end, x_start:x_end].astype(np.float64)
        if patch.size < 9:
            continue

        ys, xs = np.mgrid[y_start:y_end, x_start:x_end]
        try:
            p0 = [patch.max() - patch.min(), cx, cy, hw / 2, hw / 2, 0, patch.min()]
            popt, _ = curve_fit(
                _gaussian_2d, (xs, ys), patch.ravel(),
                p0=p0, maxfev=500,
            )
            fits.append((float(popt[1]), float(popt[2])))
            errors.append(float(np.sqrt(popt[3]**2 + popt[4]**2)))
        except (RuntimeError, ValueError):
            continue

    return {'fits': fits, 'n_fits': len(fits), 'errors': errors}


_validation_errors = validate_tags({'function': 'blob_detect', 'size': 'S|M', 'accuracy': 5})
if _validation_errors:
    raise RuntimeError(f'subpixel_fit validation: {_validation_errors}')
