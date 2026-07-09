"""Phase 4 — Segmenter 测试

覆盖: 分割一致性、质量评估、Bhattacharyya 距离、边界情况
"""

import numpy as np
import cv2
import pytest
from vision2model.vision_modules.region.segmenter import (
    segment_image,
    _bhattacharyya_distance,
    _assess_quality,
)


class TestSegmenterCore:
    """核心功能测试"""

    def test_returns_labelmap_and_props(self, grid_image):
        """分割应返回 label_map, quality, props"""
        lm, q, props = segment_image(grid_image)
        assert lm is not None
        assert lm.shape == grid_image.shape[:2]
        assert q in ('good', 'acceptable', 'poor')
        assert len(props) > 0
        assert lm.max() >= 1

    def test_reproducible(self, grid_image):
        """同一图两次分割应输出相同形状"""
        lm1 = segment_image(grid_image)[0]
        lm2 = segment_image(grid_image)[0]
        assert lm1.shape == lm2.shape

    def test_solid_image_produces_output(self, solid_image):
        """纯色图不应崩溃，应返回有效输出"""
        lm, q, props = segment_image(solid_image)
        assert lm is not None
        assert lm.shape == solid_image.shape[:2]

    def test_tiny_image(self, tiny_image):
        """极小图像 (10x10) 不应崩溃"""
        lm, q, props = segment_image(tiny_image)
        assert lm is not None

    def test_noise_image(self, noise_image):
        """纯噪声图像不应崩溃"""
        lm, q, props = segment_image(noise_image)
        assert lm is not None

    def test_gradient_image(self, gradient_image):
        """渐变图像不应崩溃"""
        lm, q, props = segment_image(gradient_image)
        assert lm is not None


class TestBhattacharyya:
    """Bhattacharyya 距离单元测试"""

    def test_identical_histograms(self):
        """相同直方图的距离应为 0"""
        h = np.ones(96)
        d = _bhattacharyya_distance(h, h)
        assert d < 1e-6

    def test_different_histograms(self):
        """不同直方图的距离应 > 0"""
        a, b = np.zeros(96), np.zeros(96)
        a[0], b[-1] = 1, 1
        d = _bhattacharyya_distance(a, b)
        assert d > 1e-6

    def test_symmetry(self):
        """距离应对称: d(a,b) == d(b,a)"""
        a, b = np.zeros(96), np.zeros(96)
        a[:10], b[-10:] = 1, 1
        assert abs(_bhattacharyya_distance(a, b) - _bhattacharyya_distance(b, a)) < 1e-10


class TestQualityAssessment:
    """质量评估逻辑测试"""

    def test_quality_classification(self, grid_image):
        """质量应返回已知分类之一"""
        lm = segment_image(grid_image)[0]
        q = _assess_quality(lm, grid_image.shape)
        assert q in ('good', 'acceptable', 'poor')
