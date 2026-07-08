"""形状分析 (minAreaRect + fitEllipse)

注册为 shape_analysis:
  function=shape, size=all, accuracy=4, robustness=3, speed=medium
"""

import cv2
import numpy as np
from ..registry import register
from ..tag_schema import validate_tags


@register(
    'shape_analysis',
    function='shape',
    size='all',
    accuracy=4,
    robustness=3,
    speed='medium',
    gpu='none',
    deps=['opencv'],
)
def shape_analysis(image_or_contours, *, as_array: bool = True):
    """Analyze shape properties of contours.

    Args:
        image_or_contours: If as_array=True, a list of Nx2 contour arrays.
                           Otherwise a binary image from which contours are extracted.
        as_array: If True, input is a list of contour arrays directly.

    Returns:
        dict with keys:
          'shapes': list of dicts with area/perimeter/aspect_ratio/circularity
          'n_shapes': int
    """
    if as_array:
        contours = image_or_contours
    else:
        if len(image_or_contours.shape) == 3:
            gray = cv2.cvtColor(image_or_contours, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_or_contours
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        result, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [cnt.reshape(-1, 2).astype(np.int32) for cnt in result]

    shapes = []
    for cnt in contours:
        if len(cnt) < 5:
            continue
        area = cv2.contourArea(cnt)
        if area < 1:
            continue
        perimeter = cv2.arcLength(cnt, closed=True)
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box_area = cv2.contourArea(box)
        aspect_ratio = max(rect[1]) / max(min(rect[1]), 1) if rect[1][0] > 0 and rect[1][1] > 0 else 1.0
        circularity = 4 * np.pi * area / max(perimeter ** 2, 1e-6)

        shapes.append({
            'area': float(area),
            'perimeter': float(perimeter),
            'aspect_ratio': float(aspect_ratio),
            'circularity': float(circularity),
            'bbox_width': float(rect[1][0]),
            'bbox_height': float(rect[1][1]),
            'angle': float(rect[2]),
        })

    return {'shapes': shapes, 'n_shapes': len(shapes)}


_validation_errors = validate_tags({'function': 'shape', 'size': 'all', 'accuracy': 4})
if _validation_errors:
    raise RuntimeError(f'shape_analysis tag validation failed: {_validation_errors}')
