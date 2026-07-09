"""Phase 4 — Calibration + Mapping 测试

覆盖: 网格校准、交叉校验、3D 基元检测、FreeCAD 脚本
"""

import numpy as np
import pytest
from vision2model.vision_modules.types import Measurement
from vision2model.vision_modules.calibrate.grid import calibrate_grid
from vision2model.vision_modules.calibrate.crosscheck import crosscheck_scales
from vision2model.mapping import detect_primitive, map_to_3d, generate_freecad_script


class TestGridCalibration:
    """方格纸校准"""

    def test_regular_grid(self):
        """规律格线应返回准确 px_per_mm"""
        ms = calibrate_grid(
            {'horizontal_positions': [0, 50, 100, 150],
             'vertical_positions': [0, 50, 100, 150]},
            known_grid_mm=5.0,
        )
        assert len(ms.measurements) >= 1
        # 50px / 5mm = 10 px_per_mm
        assert abs(ms.measurements[0].value - 10.0) < 1.0

    def test_different_spacing(self):
        """不同格距应正确计算"""
        ms = calibrate_grid(
            {'horizontal_positions': [0, 20, 40],
             'vertical_positions': [0, 20, 40]},
            known_grid_mm=2.0,
        )
        assert len(ms.measurements) >= 1
        # 20px / 2mm = 10 px_per_mm
        assert abs(ms.measurements[0].value - 10.0) < 1.0

    def test_insufficient_lines(self):
        """不足 3 条线时返回空"""
        ms = calibrate_grid(
            {'horizontal_positions': [0], 'vertical_positions': [0]},
            known_grid_mm=5.0,
        )
        assert len(ms.measurements) == 0

    def test_noisy_grid(self):
        """带噪声的格线应仍能计算"""
        positions = sorted([0, 51, 98, 152, 200, 250])
        ms = calibrate_grid(
            {'horizontal_positions': positions, 'vertical_positions': positions},
            known_grid_mm=5.0,
        )
        assert len(ms.measurements) >= 1
        # Spacing ~50px / 5mm = 10, but noise reduces accuracy
        assert ms.measurements[0].value > 0


class TestCrosscheck:
    """多参照交叉校验"""

    def test_consistent_sources(self):
        """相差 < 5% → ok"""
        r = crosscheck_scales({
            'a': Measurement(value=10.0, error=0.5, confidence=0.9, unit='px_per_mm'),
            'b': Measurement(value=10.5, error=0.5, confidence=0.85, unit='px_per_mm'),
        })
        assert r['status'] == 'ok'
        assert r['consistency'] == 'high'

    def test_single_source(self):
        """单来源 → single"""
        r = crosscheck_scales({
            'a': Measurement(value=10.0, error=0.5, confidence=0.9, unit='px_per_mm'),
        })
        assert r['status'] == 'single'

    def test_warning_sources(self):
        """相差 5-15% → warning"""
        r = crosscheck_scales({
            'a': Measurement(value=10.0, error=0.5, confidence=0.9, unit='x'),
            'b': Measurement(value=11.5, error=0.5, confidence=0.85, unit='x'),
        })
        assert r['status'] == 'warning'

    def test_failed_sources(self):
        """相差 > 15% → failed"""
        r = crosscheck_scales({
            'a': Measurement(value=10.0, error=0.5, confidence=0.9, unit='x'),
            'b': Measurement(value=50.0, error=0.5, confidence=0.9, unit='x'),
        })
        assert r['status'] == 'failed'

    def test_empty(self):
        """空输入 → failed"""
        r = crosscheck_scales({})
        assert r['status'] == 'failed'


class TestPrimitiveDetection:
    """3D 基元检测"""

    def test_cylinder(self):
        """宽高比 > 2.5 → cylinder"""
        assert detect_primitive(3.0, 0.9) == 'cylinder'

    def test_box(self):
        """宽高比 0.6-1.8 + 凸 → box"""
        assert detect_primitive(1.2, 0.9) == 'box'

    def test_manual_mode(self):
        """手动指定 mode 应直接返回"""
        assert detect_primitive(1.0, 0.9, mode='cylinder') == 'cylinder'
        assert detect_primitive(3.0, 0.9, mode='box') == 'box'

    def test_invalid_mode(self):
        """非法 mode 应抛出 ValueError"""
        with pytest.raises(ValueError):
            detect_primitive(1.0, 0.9, mode='invalid')


class TestFreeCADScript:
    """FreeCAD 脚本生成"""

    def test_box_script(self):
        script = generate_freecad_script('box', {'width_mm': 20, 'depth_mm': 20, 'height_mm': 30})
        assert 'Part.makeBox(20, 20, 30)' in script
        assert 'STL exported' in script

    def test_cylinder_script(self):
        script = generate_freecad_script('cylinder', {'radius_mm': 10, 'height_mm': 30})
        assert 'Part.makeCylinder(10, 30)' in script

    def test_revolve_script(self):
        script = generate_freecad_script('revolve', {'width_mm': 20, 'height_mm': 40})
        assert 'face.revolve' in script
        assert 'STL exported' in script

    def test_invalid_primitive(self):
        with pytest.raises(ValueError):
            generate_freecad_script('unknown', {})


class TestMapTo3D:
    """map_to_3d 集成"""

    def test_no_dominant(self):
        """无 dominant region 应返回 unknown"""
        r = map_to_3d([])
        assert r['primitive'] == 'unknown'
        assert 'warning' in r

    def test_with_dominant(self):
        """有 dominant region 应推断基元"""
        measurements = [{
            'id': 1, 'roles': ['dominant'],
            'bbox': (0, 0, 200, 100), 'centroid': (100, 50),
            'area_px': 20000, 'area_ratio': 0.5,
            'convexity': 0.9,
        }]
        r = map_to_3d(measurements, dominant_region=measurements[0], px_per_mm=10.0)
        assert r['primitive'] in ('box', 'cylinder')
        assert len(r.get('dimensions_mm', {})) > 0
        assert len(r.get('freecad_script', '')) > 100

    def test_no_calibration(self):
        """无比例尺时输出 px 值"""
        measurements = [{
            'id': 1, 'roles': ['dominant'],
            'bbox': (0, 0, 200, 100), 'centroid': (100, 50),
            'area_px': 20000, 'area_ratio': 0.5,
            'convexity': 0.9,
        }]
        r = map_to_3d(measurements, dominant_region=measurements[0], px_per_mm=None)
        assert 'unit' in r.get('dimensions_mm', {})
        assert r['freecad_script'] != ''
        assert 'Calibrate first' in r['freecad_script']
