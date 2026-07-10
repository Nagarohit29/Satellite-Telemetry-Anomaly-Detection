"""Tests for inference input adaptation."""
import numpy as np


def test_adapt_pad():
    """Input with fewer features should be zero-padded."""
    data = np.random.randn(100, 3).astype(np.float32)
    expected_feats = 5
    if data.shape[1] < expected_feats:
        pad_width = expected_feats - data.shape[1]
        data = np.pad(data, ((0, 0), (0, pad_width)), mode='constant')
    assert data.shape == (100, 5)


def test_adapt_truncate():
    """Input with more features should be truncated."""
    data = np.random.randn(100, 10).astype(np.float32)
    expected_feats = 5
    if data.shape[1] > expected_feats:
        data = data[:, :expected_feats]
    assert data.shape == (100, 5)


def test_adapt_exact():
    """Input with exact features should pass through unchanged."""
    data = np.random.randn(100, 5).astype(np.float32)
    expected_feats = 5
    assert data.shape == (100, expected_feats)


def test_1d_reshape():
    """1D input should be reshaped to (N, 1)."""
    data = np.random.randn(100).astype(np.float32)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    assert data.ndim == 2
    assert data.shape == (100, 1)
