"""Phase 4 — Fusion Engine 测试

覆盖: 自洽虚拟数据、异常值剔除、低置信过滤、2D/3D 向量、空输入
"""

import numpy as np
import pytest
from vision2model.vision_modules.types import Measurement, MeasurementSet
from vision2model.vision_modules.fusion.engine import (
    fuse_measurements,
    _iqr_filter,
    _weighted_avg,
    _compute_cv,
    _classify_consistency,
    MIN_CONFIDENCE,
)


def _ms(name, values):
    return MeasurementSet(source=name, measurements=[
        Measurement(value=v, error=2.0, confidence=0.85, unit='mm') for v in values
    ])


class TestCoreFunctions:
    """内部函数单元测试"""

    def test_iqr_filter_no_outliers(self):
        """无明显异常值时不应剔除数据"""
        vals = np.array([10.0, 11.0, 10.5, 10.8, 11.2])
        mask = _iqr_filter(vals)
        assert mask.sum() == 5

    def test_iqr_filter_with_outlier(self):
        """明显异常值应被剔除"""
        vals = np.array([10.0, 10.5, 11.0, 100.0])
        mask = _iqr_filter(vals)
        # IQR with n >= 4 should work; 100 is far outside
        assert mask.sum() < 4

    def test_iqr_filter_too_few(self):
        """n < 4 时应保留所有数据"""
        vals = np.array([10.0, 100.0])
        mask = _iqr_filter(vals)
        assert mask.sum() == 2

    def test_weighted_avg(self):
        """加权平均应正确计算"""
        v = np.array([10.0, 12.0])
        e = np.array([1.0, 1.0])
        w = np.array([0.9, 0.1])
        fv, fe = _weighted_avg(v, e, w)
        # (10*0.9 + 12*0.1) / 1.0 = 10.2
        assert abs(fv - 10.2) < 0.01

    def test_compute_cv(self):
        """变异系数 CV = std / mean"""
        vals = np.array([10.0, 11.0])
        cv = _compute_cv(vals)
        expected = vals.std() / vals.mean()
        assert abs(cv - expected) < 0.01

    def test_compute_cv_zero_mean(self):
        """均值为 0 时返回 inf"""
        assert _compute_cv(np.array([0, 0, 0])) == float('inf')

    def test_classify_consistency(self):
        assert _classify_consistency(0.01) == 'high'
        assert _classify_consistency(0.10) == 'medium'
        assert _classify_consistency(0.50) == 'low'


class TestFuseMeasurements:
    """fuse_measurements 集成测试"""

    def test_empty(self):
        """空输入应返回 []"""
        assert fuse_measurements([]) == []

    def test_empty_measurementsets(self):
        """包含空 MeasurementSet 应返回 []"""
        assert fuse_measurements([MeasurementSet(source='x', measurements=[])]) == []

    def test_single_measurement(self):
        """单个测量应返回单源结果（fallback）"""
        ms = MeasurementSet(source='a', measurements=[
            Measurement(value=50.0, error=1.0, confidence=0.95, unit='mm'),
        ])
        results = fuse_measurements([ms])
        assert len(results) == 1
        assert results[0].n_sources == 1
        assert results[0].value == 50.0

    def test_consistent_fusion(self):
        """自洽数据应产生 high consistency 融合结果"""
        results = fuse_measurements([
            _ms('a', [100, 101, 102]),
        ])
        assert len(results) == 1
        assert results[0].n_sources >= 2  # IQR kept at least 2
        assert results[0].consistency in ('high', 'medium')
        assert results[0].unit == 'mm'

    def test_low_confidence_filtered(self):
        """低置信度测量应被过滤并回退到最高置信单源"""
        ms = MeasurementSet(source='low', measurements=[
            Measurement(value=99.0, error=2.0, confidence=0.1, unit='mm'),
        ])
        results = fuse_measurements([ms])
        assert len(results) == 1
        assert results[0].n_sources == 1  # single best pick

    def test_2d_vector_fusion(self):
        """2D 向量应正确融合"""
        ms = MeasurementSet(source='v', measurements=[
            Measurement(value=(10.0, 20.0), error=0.5, confidence=0.9, unit='px'),
            Measurement(value=(10.5, 19.5), error=0.5, confidence=0.85, unit='px'),
            Measurement(value=(9.8, 20.2), error=0.5, confidence=0.8, unit='px'),
        ])
        results = fuse_measurements([ms])
        assert len(results) == 1
        assert isinstance(results[0].value, tuple)
        assert len(results[0].value) == 2
