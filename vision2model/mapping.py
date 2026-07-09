"""Vision→3D 测量管线 — 2D→3D 映射 + FreeCAD 脚本生成 (Phase 3.3)

从 2D 图像测量值自动检测 3D 基元类型并生成 FreeCAD Python 脚本。
"""

import numpy as np
from vision2model.vision_modules.registry import register, find_modules
from vision2model.vision_modules.tag_schema import validate_tags


# ═══════════════════════════════════════════════════════════
# 基元检测
# ═══════════════════════════════════════════════════════════

PRIMITIVE_ELLIPSE_FIT_THRESHOLD = 0.85   # 轮廓与椭圆拟合的匹配度阈值
PRIMITIVE_ASPECT_CYLINDER = 2.5          # 宽高比 > 此值 → cylinder
PRIMITIVE_ASPECT_BOX_LOW = 0.6           # 宽高比在此区间 → box
PRIMITIVE_ASPECT_BOX_HIGH = 1.8


def detect_primitive(
    aspect_ratio: float,
    convexity: float,
    contour: np.ndarray = None,
    mode: str = 'auto',
) -> str:
    """检测最佳 3D 基元类型。

    Args:
        aspect_ratio: 宽高比 (w/h).
        convexity: 凸度 (凸包面积/实际面积).
        contour: N×2 轮廓点集 (可选，用于椭圆拟合).
        mode: 'auto' | 'revolve' | 'box' | 'cylinder'.

    Returns:
        'revolve' | 'box' | 'cylinder'.

    Raises:
        ValueError: 如果 mode 参数不合法.
    """
    valid_modes = {'auto', 'revolve', 'box', 'cylinder'}
    if mode not in valid_modes:
        raise ValueError(f"mapping_mode 应为 {valid_modes}, 实际为 {mode}")

    if mode != 'auto':
        return mode

    # Auto detection from shape
    if aspect_ratio > PRIMITIVE_ASPECT_CYLINDER:
        return 'cylinder'

    if contour is not None and len(contour) >= 10:
        ellipse_fit = _check_ellipse_fit(contour)
        if ellipse_fit > PRIMITIVE_ELLIPSE_FIT_THRESHOLD:
            return 'revolve'

    if PRIMITIVE_ASPECT_BOX_LOW <= aspect_ratio <= PRIMITIVE_ASPECT_BOX_HIGH:
        return 'box'

    # Default: if convex and near-square, box; otherwise revolve
    if convexity > 0.85:
        return 'box'
    return 'revolve'


def _check_ellipse_fit(contour: np.ndarray) -> float:
    """检查轮廓与椭圆的匹配度。返回 0~1 的分数。"""
    try:
        import cv2
    except ImportError:
        return 0.0

    if len(contour) < 5:
        return 0.0

    contour_f32 = contour.astype(np.float32).reshape(-1, 1, 2)
    ellipse = cv2.fitEllipse(contour_f32)
    ellipse_contour = cv2.ellipse2Poly(
        (int(ellipse[0][0]), int(ellipse[0][1])),
        (int(ellipse[1][0] / 2), int(ellipse[1][1] / 2)),
        int(ellipse[2]), 0, 360, 5,
    )

    # IoU-like score: fraction of contour points near ellipse
    if len(ellipse_contour) == 0:
        return 0.0

    from scipy.spatial import KDTree
    tree = KDTree(ellipse_contour)
    distances, _ = tree.query(contour)
    max_dim = max(ellipse[1]) / 2 if max(ellipse[1]) > 0 else 1
    near = (distances < max_dim * 0.1).mean()
    return float(near)


# ═══════════════════════════════════════════════════════════
# FreeCAD 脚本生成
# ═══════════════════════════════════════════════════════════

def generate_freecad_script(
    primitive: str,
    dimensions: dict,
    output_path: str = None,
) -> str:
    """生成 FreeCAD Python 脚本，创建指定基元并导出 STL。

    Args:
        primitive: 'revolve' | 'box' | 'cylinder'.
        dimensions: 尺寸字典，基元相关:
            - revolve: {'width_mm': float, 'height_mm': float}
            - box:     {'width_mm': float, 'depth_mm': float, 'height_mm': float}
            - cylinder: {'radius_mm': float, 'height_mm': float}
        output_path: 可选 STL 输出路径.

    Returns:
        FreeCAD Python 脚本字符串.
    """
    if primitive == 'revolve':
        script = _script_revolve(dimensions, output_path)
    elif primitive == 'box':
        script = _script_box(dimensions, output_path)
    elif primitive == 'cylinder':
        script = _script_cylinder(dimensions, output_path)
    else:
        raise ValueError(f"未知基元: {primitive}")

    return script


def _script_revolve(dim: dict, out: str = None) -> str:
    w = dim.get('width_mm', 10)
    h = dim.get('height_mm', 20)
    out = out or 'output.stl'
    return f'''import FreeCAD, Part, Mesh
import MeshGui

DOC = FreeCAD.newDocument("RevolvedPart")

# Profile: half of the width as radius
r = {w} / 2
h = {h}
pts = [
    FreeCAD.Vector(0, 0, 0),
    FreeCAD.Vector(r, 0, 0),
    FreeCAD.Vector(r, h, 0),
    FreeCAD.Vector(0, h, 0),
]
wire = Part.makePolygon(pts)
face = Part.Face(wire)
solid = face.revolve(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 360)
Part.show(solid)
Mesh.export([solid], r"{out}")
print("STL exported: {out}")
'''


def _script_box(dim: dict, out: str = None) -> str:
    w = dim.get('width_mm', 20)
    d = dim.get('depth_mm', 20)
    h = dim.get('height_mm', 30)
    out = out or 'output.stl'
    return f'''import FreeCAD, Part, Mesh

DOC = FreeCAD.newDocument("BoxPart")
solid = Part.makeBox({w}, {d}, {h})
Part.show(solid)
Mesh.export([solid], r"{out}")
print("STL exported: {out}")
'''


def _script_cylinder(dim: dict, out: str = None) -> str:
    r = dim.get('radius_mm', 10)
    h = dim.get('height_mm', 30)
    out = out or 'output.stl'
    return f'''import FreeCAD, Part, Mesh

DOC = FreeCAD.newDocument("CylinderPart")
solid = Part.makeCylinder({r}, {h})
Part.show(solid)
Mesh.export([solid], r"{out}")
print("STL exported: {out}")
'''


def map_to_3d(
    measurements: list,
    dominant_region: dict = None,
    px_per_mm: float = None,
    mapping_mode: str = 'auto',
) -> dict:
    """2D 图像测量 → 3D 模型 + FreeCAD 脚本。

    从 dominant region 的 bounding box/轮廓/宽高比推断 3D 基元，
    结合像素比例尺换算为真实尺寸，生成 FreeCAD 脚本。

    Args:
        measurements: S_grid 管线输出的 measurements 列表.
        dominant_region: dominant region 的测量字典 (含 bbox, area_ratio, etc).
        px_per_mm: 像素/毫米比例尺 (None = 仅 px).
        mapping_mode: 'auto' | 'revolve' | 'box' | 'cylinder'.

    Returns:
        dict:
          primitive: str
          dimensions_mm: dict
          freecad_script: str
          px_per_mm: float or None
    """
    if dominant_region is None and measurements:
        for m in measurements:
            if 'dominant' in m.get('roles', []):
                dominant_region = m
                break

    if dominant_region is None:
        return {
            'primitive': 'unknown',
            'dimensions_mm': {},
            'freecad_script': '',
            'px_per_mm': px_per_mm,
            'warning': 'No dominant region found',
        }

    bbox = dominant_region.get('bbox', (0, 0, 1, 1))
    bw, bh = bbox[2], bbox[3]
    aspect = bw / max(bh, 1)
    convexity = dominant_region.get('convexity', 1.0)

    primitive = detect_primitive(aspect, convexity, mode=mapping_mode)

    dim_px = {'width_px': bw, 'height_px': bh}

    if px_per_mm and px_per_mm > 0:
        dim_mm = {
            'width_mm': round(bw / px_per_mm, 2),
            'height_mm': round(bh / px_per_mm, 2),
        }
        if primitive == 'box':
            # Assume equal depth for 2D-derived box
            dim_mm['depth_mm'] = round(min(dim_mm['width_mm'], dim_mm['height_mm']) * 0.6, 2)
        elif primitive == 'cylinder':
            dim_mm['radius_mm'] = round(min(dim_mm['width_mm'], dim_mm['height_mm']) / 2, 2)
            dim_mm['height_mm'] = round(max(dim_mm['width_mm'], dim_mm['height_mm']), 2)
        elif primitive == 'revolve':
            dim_mm['radius_mm'] = round(dim_mm['width_mm'] / 2, 2)
    else:
        dim_mm = {k.replace('_px', '_px_only'): v for k, v in dim_px.items()}
        dim_mm['unit'] = 'px'

    script = generate_freecad_script(primitive, dim_mm) if px_per_mm else ''

    return {
        'primitive': primitive,
        'dimensions_px': dim_px,
        'dimensions_mm': dim_mm if px_per_mm else {},
        'px_per_mm': px_per_mm,
        'freecad_script': script if px_per_mm else 'Calibrate first (provide --grid-mm or --body-height)',
    }
