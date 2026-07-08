"""SVG renderer — 验证图生成

在原图上叠加 region 边界 + 特征标注。
"""

import numpy as np
import cv2
import os


def render_svg(
    image: np.ndarray,
    result: dict,
    output_path: str,
    base_image_path: str = None,
) -> str:
    """Render SVG validation image with region overlays.

    The SVG reference the original image as a base and draw
    region boundaries, centroids, and grid lines on top.

    Args:
        image: Original BGR image.
        result: Pipeline result dict.
        output_path: Path to write SVG file.
        base_image_path: Path to the original image (for embedding in SVG).

    Returns:
        The output path.
    """
    h, w = image.shape[:2]
    image_rel = os.path.basename(base_image_path) if base_image_path else 'input.png'

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        f'  <image href="{image_rel}" width="{w}" height="{h}"/>',
    ]

    # Draw region boundaries
    measurements = result.get('measurements', [])
    for m in measurements:
        bbox = m.get('bbox', (0, 0, 0, 0))
        cx, cy = m.get('centroid', (0, 0))
        roles = ', '.join(m.get('roles', []))
        rid = m.get('id', 0)
        color = _role_color(m.get('roles', []))

        # Bounding box
        svg_lines.append(
            f'  <rect x="{bbox[0]}" y="{bbox[1]}" '
            f'width="{bbox[2]}" height="{bbox[3]}" '
            f'fill="none" stroke="{color}" stroke-width="1.5" stroke-dasharray="4,2"/>'
        )
        # Centroid
        svg_lines.append(
            f'  <circle cx="{cx}" cy="{cy}" r="3" fill="{color}" '
            f'stroke="white" stroke-width="0.5"/>'
        )
        # Label
        svg_lines.append(
            f'  <text x="{cx + 5}" y="{cy - 5}" font-size="9" fill="{color}">'
            f'R{rid}: {roles}</text>'
        )

    # Draw grid lines if available
    grid = result.get('grid', {})
    grid_est = grid.get('grid_cell_estimate_px', 0)
    if grid_est > 0:
        svg_lines.append(
            f'  <text x="10" y="20" font-size="12" fill="#333">'
            f'Grid cell: {grid_est:.1f} px</text>'
        )

    # Draw calibration info
    calib = result.get('calibration', {})
    if calib.get('method') == 'grid':
        svg_lines.append(
            f'  <text x="10" y="35" font-size="12" fill="#333">'
            f'px/mm: {calib["px_per_mm"]:.2f} (grid={calib["grid_mm"]}mm)'
            f'</text>'
        )

    svg_lines.append('</svg>')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_lines))

    return output_path


def _role_color(roles: list[str]) -> str:
    """Map region roles to SVG colors."""
    role_colors = {
        'dominant': '#e74c3c',
        'background': '#95a5a6',
        'inclusion': '#2ecc71',
        'accent': '#f39c12',
        'protrusion': '#9b59b6',
        'uniform': '#3498db',
        'patterned': '#1abc9c',
        'fragment': '#bdc3c7',
        'adjunct': '#e67e22',
    }
    for role in roles:
        if role in role_colors:
            return role_colors[role]
    return '#7f8c8d'
