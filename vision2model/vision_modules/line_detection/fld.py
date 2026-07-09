"""FLD 线检测 (Fast Line Detector)

注册为 line_fld:
  function=line_detect, size=S|M, accuracy=4, robustness=3, speed=medium
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'line_fld',
    function='line_detect',
    size='S|M',
    accuracy=4,
    robustness=3,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def line_fld(image, *, length_threshold: int = 20, distance_threshold: float = 1.414,
             canny_th1: float = 50.0, canny_th2: float = 50.0, canny_aperture: int = 3,
             do_merge: bool = False):
    """Detect line segments using OpenCV's Fast Line Detector.

    NOTE: Requires opencv-contrib-python for ximgproc.createFastLineDetector.
    If not available, falls back to HoughLinesP.

    Args:
        image: Grayscale or BGR image.
        length_threshold: Minimum line length (pixels).
        distance_threshold: Max gap for merging.
        canny_th1, canny_th2: Canny thresholds.
        canny_aperture: Canny aperture size.
        do_merge: If True, merge nearby segments.

    Returns:
        dict with keys:
          'lines': Nx4 array of (x1, y1, x2, y2)
          'n_lines': int
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Try FLD; fall back to HoughLinesP if ximgproc unavailable
    if hasattr(cv2, 'ximgproc') and hasattr(cv2.ximgproc, 'createFastLineDetector'):
        fld = cv2.ximgproc.createFastLineDetector(
            length_threshold=length_threshold,
            distance_threshold=distance_threshold,
            canny_th1=canny_th1,
            canny_th2=canny_th2,
            canny_aperture_size=canny_aperture,
            do_merge=do_merge,
        )
        lines = fld.detect(gray)
    else:
        # Fallback: Canny + HoughLinesP
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80,
                                minLineLength=length_threshold, maxLineGap=10)
        if lines is not None:
            lines_arr = np.asarray(lines, dtype=np.float32)
            if lines_arr.ndim == 3:
                lines_arr = lines_arr[:, 0, :]
            lines = lines_arr

    if lines is None:
        return {'lines': np.empty((0, 4), dtype=np.float32), 'n_lines': 0}

    return {'lines': lines.reshape(-1, 4), 'n_lines': len(lines)}


_validation_errors = validate_tags({'function': 'line_detect', 'size': 'S|M', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'line_fld validation: {_validation_errors}')
