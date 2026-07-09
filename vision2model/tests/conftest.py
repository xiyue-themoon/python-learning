"""Vision→3D 测试共享 fixtures"""
import numpy as np
import cv2
import pytest


@pytest.fixture(scope='module')
def grid_image():
    """Synthetic grid image with a centered dark rectangle."""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 240
    for i in range(0, 400, 40):
        cv2.line(img, (i, 0), (i, 400), (0, 0, 0), 1)
        cv2.line(img, (0, i), (400, i), (0, 0, 0), 1)
    cv2.rectangle(img, (100, 120), (260, 280), (80, 80, 80), -1)
    return img


@pytest.fixture(scope='module')
def solid_image():
    """Uniform gray image."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 128


@pytest.fixture(scope='module')
def noise_image():
    """Random noise image."""
    return np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)


@pytest.fixture(scope='module')
def tiny_image():
    """Extremely low-resolution image."""
    return np.ones((10, 10, 3), dtype=np.uint8) * 128


@pytest.fixture(scope='module')
def gradient_image():
    """Gradient image."""
    grad = np.zeros((200, 200, 3), dtype=np.uint8)
    for y in range(200):
        grad[y, :, :] = int(y * 1.2)
    return grad
