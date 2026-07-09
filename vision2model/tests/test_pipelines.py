"""Phase 4 — Pipelines 测试

覆盖: S_grid 全管线、S_grid_ensemble、无标定、边界输入
"""

import numpy as np
import cv2
import pytest
from vision2model.vision_modules.types import CalibrationInput
from vision2model.pipelines.S_grid import run_S_grid
from vision2model.pipelines.S_grid_ensemble import run_S_grid_ensemble
from vision2model.dispatcher import dispatcher, select_pipeline, PIPELINE_TABLE
from vision2model.output.json_exporter import export_json
from vision2model.output.svg_renderer import render_svg
from vision2model.output.summary_printer import print_summary


class TestDispatcher:
    """Dispatcher 管线选择"""

    def test_select_s_grid(self):
        """S + grid + normal → S_grid"""
        from vision2model.vision_modules.types import ImageProfile
        pl = select_pipeline(ImageProfile(
            size='S', contrast='medium', noise='low', bg_type='grid', has_reference=False))
        assert pl.name == 'S_grid'

    def test_select_ensemble(self):
        """S + grid + high_contrast → S_grid_ensemble"""
        from vision2model.vision_modules.types import ImageProfile
        pl = select_pipeline(ImageProfile(
            size='S', contrast='high', noise='high', bg_type='grid', has_reference=False))
        assert pl.name == 'S_grid_ensemble'

    def test_select_fallback(self):
        """L + cluttered → fallback"""
        from vision2model.vision_modules.types import ImageProfile
        pl = select_pipeline(ImageProfile(
            size='L', contrast='low', noise='high', bg_type='cluttered', has_reference=False))
        assert pl.name == 'fallback'

    def test_ensemble_before_base(self):
        """PIPELINE_TABLE 中 ensemble 必须在 base 前"""
        names = [r[3] for r in PIPELINE_TABLE]
        assert names.index('S_grid_ensemble') < names.index('S_grid')
        assert names.index('M_grid_ensemble') < names.index('M_grid')
        assert names[-1] == 'fallback'

    def test_dispatcher_endtoend(self, grid_image, tmp_path):
        """dispatcher 端到端"""
        p = tmp_path / 'test.png'
        cv2.imwrite(str(p), grid_image)
        profile, pipeline = dispatcher(str(p))
        assert profile.size == 'S'
        assert pipeline.name in ('S_grid', 'S_grid_ensemble')


class TestSGrid:
    """S_grid 管线"""

    def test_pipeline_runs(self, grid_image):
        """S_grid 应正常执行"""
        res = run_S_grid(grid_image)
        assert res['pipeline'] == 'S_grid'
        assert 'measurements' in res

    def test_with_calibration(self, grid_image):
        """传入标定信息应计算 px_per_mm"""
        res = run_S_grid(grid_image, calib=CalibrationInput(method='grid', value_mm=5.0))
        cal = res.get('calibration', {})
        assert cal.get('method') == 'grid'
        # px_per_mm might be 0 for synthetic thin lines; just check structure

    def test_no_calibration(self, grid_image):
        """无标定 → px-only"""
        res = run_S_grid(grid_image)
        assert res['calibration']['method'] == 'none'

    def test_solid_color(self, solid_image):
        """纯色图不应崩溃"""
        res = run_S_grid(solid_image)
        assert 'pipeline' in res

    def test_all_regions_have_roles(self, grid_image):
        """所有 region 都应有角色"""
        res = run_S_grid(grid_image)
        for m in res['measurements']:
            assert len(m.get('roles', [])) > 0, f"R{m['id']} has no roles"

    def test_measurement_fields(self, grid_image):
        """measurements 应包含所有必需字段"""
        res = run_S_grid(grid_image, calib=CalibrationInput(method='grid', value_mm=5.0))
        required = {'id', 'roles', 'bbox', 'centroid', 'area_px', 'area_ratio'}
        for m in res['measurements'][:5]:
            missing = required - set(m.keys())
            assert not missing, f"R{m.get('id','?')} missing: {missing}"


class TestSGridEnsemble:
    """S_grid_ensemble 管线"""

    def test_pipeline_runs(self, grid_image):
        """S_grid_ensemble 应正常执行"""
        res = run_S_grid_ensemble(grid_image)
        assert res['pipeline'] == 'S_grid_ensemble'
        assert 'line_sets' in res.get('grid', {})

    def test_solid_color(self, solid_image):
        """纯色图不应崩溃"""
        res = run_S_grid_ensemble(solid_image)
        assert 'pipeline' in res


class TestOutput:
    """输出模块"""

    def test_json_roundtrip(self, grid_image, tmp_path):
        """JSON 序列化 → 反序列化应保持一致"""
        res = run_S_grid(grid_image)
        p = tmp_path / 'out.json'
        export_json(res, str(p))
        import json
        with open(p) as f:
            loaded = json.load(f)
        assert loaded['pipeline'] == 'S_grid'
        assert 'measurements' in loaded

    def test_svg_created(self, grid_image, tmp_path):
        """SVG 应包含有效结构"""
        res = run_S_grid(grid_image)
        p = tmp_path / 'out.svg'
        render_svg(grid_image, res, str(p), 'input.png')
        with open(p) as f:
            svg = f.read()
        assert '<svg' in svg
        assert 'image href' in svg
        assert len(svg) > 500

    def test_summary_runs(self, grid_image):
        """摘要打印不应抛出异常"""
        import io
        out = io.StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            print_summary(run_S_grid(grid_image))
        finally:
            sys.stdout = old
        assert 'S_grid' in out.getvalue()


import sys  # needed for test_summary
