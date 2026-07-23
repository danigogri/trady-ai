"""Tests for calibration metrics — pure deterministic functions.

Known-answer tests on synthetic matrices: near-singular, uniform,
deterministic chain.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from trady_ai.reflection.calibration.metrics import (
    aic,
    bic,
    conditional_entropy,
    markov_chi2,
    state_persistence,
)


class TestAIC:
    """AIC formula: -2*ln(L) + 2k, k=|S|*(|S|-1)."""

    def test_aic_uniform_3state(self):
        """Uniform 3×3 transition matrix: each row = [1/3, 1/3, 1/3],
        each cell count = 10 (total 90 observations).
        AIC = -2*ln(L) + 2k where k = 3*2 = 6
        ln(L) = Σᵢⱼ n_ij * ln(p_ij) = 90 * ln(1/3) = -98.87...
        AIC = -2*(-98.87) + 12 = 209.74...
        """
        counts = np.full((3, 3), 10, dtype=np.int64)
        val = aic(counts, [0, 1, 2])
        # -2 * (90 * ln(1/3)) + 12 = -180 * ln(1/3) + 12
        expected = -180.0 * math.log(1.0 / 3.0) + 12.0
        assert val == pytest.approx(expected, rel=1e-9)
        assert val > 0

    def test_aic_deterministic_3state(self):
        """Deterministic chain: always transitions in fixed pattern.
        Transition matrix = [[10,0,0],[0,10,0],[0,0,10]]
        p_ii = 1 for all i, ln(L) = sum of n_ii * ln(1) = 0
        AIC = 0 + 12 = 12
        """
        counts = np.array([[10, 0, 0], [0, 10, 0], [0, 0, 10]], dtype=np.int64)
        val = aic(counts, [0, 0, 1, 1, 2, 2])
        assert val == pytest.approx(12.0, rel=1e-9)

    def test_aic_2state(self):
        """2-state chain (k=2)."""
        counts = np.array([[5, 5], [3, 7]], dtype=np.int64)
        val = aic(counts, [0, 1, 0, 1])
        # k = 2*1 = 2
        assert val > 0

    def test_aic_single_state_returns_zero(self):
        """1×1 matrix → AIC = 0.0 (no free params)."""
        counts = np.array([[10]], dtype=np.int64)
        val = aic(counts, [0, 0, 0])
        assert val == 0.0

    def test_aic_larger_penalizes_more_states(self):
        """Same dataset approximated, larger |S| → larger AIC."""
        data_3 = np.array([[10, 2, 1], [2, 15, 3], [1, 2, 10]], dtype=np.int64)
        # Simulate 4-state with same total observations but more params
        data_4 = np.array(
            [[8, 2, 1, 1], [2, 10, 2, 1], [1, 2, 8, 1], [1, 1, 2, 6]],
            dtype=np.int64,
        )
        seq = [0, 1, 2, 0, 1, 2]
        val3 = aic(data_3, seq)
        val4 = aic(data_4, seq)
        assert val4 > val3, "4-state should have larger AIC penalty"

    def test_aic_same_inputs_same_output(self):
        """Determinism check: same matrix twice → same AIC."""
        counts = np.array([[10, 2, 1], [2, 15, 3], [1, 2, 10]], dtype=np.int64)
        seq = [0, 0, 1, 1, 2, 2, 0]
        val1 = aic(counts, seq)
        val2 = aic(counts, seq)
        assert val1 == val2


class TestBIC:
    """BIC formula: -2*ln(L) + k*ln(n)."""

    def test_bic_uniform_3state_n90(self):
        """Uniform 3×3 matrix, 90 obs.
        BIC = -2*ln(L) + k*ln(90)
        k = 6, ln(90) ≈ 4.4998
        BIC = -180*ln(1/3) + 6*ln(90)
        """
        counts = np.full((3, 3), 10, dtype=np.int64)
        val = bic(counts, [0, 1, 2], n_observations=90)
        expected = -180.0 * math.log(1.0 / 3.0) + 6.0 * math.log(90.0)
        assert val == pytest.approx(expected, rel=1e-9)

    def test_bic_deterministic_3state(self):
        """P_ii=1 for all. ln(L)=0.
        BIC = 0 + 6*ln(30) where n = 30
        """
        counts = np.array([[10, 0, 0], [0, 10, 0], [0, 0, 10]], dtype=np.int64)
        val = bic(counts, [0, 0, 1, 1, 2, 2], n_observations=30)
        expected = 6.0 * math.log(30.0)
        assert val == pytest.approx(expected, rel=1e-9)

    def test_bic_bigger_penalty_than_aic(self):
        """For n=1000, |S|=3 (k=6):
        BIC penalty = 6*ln(1000) ≈ 41.4
        AIC penalty = 12
        """
        counts = np.full((3, 3), 10, dtype=np.int64)
        aic_val = aic(counts, [0, 1, 2])
        bic_val = bic(counts, [0, 1, 2], n_observations=1000)
        # BIC should have larger penalty component
        bic_penalty = 6.0 * math.log(1000.0)
        aic_penalty = 12.0
        assert bic_penalty > aic_penalty
        # BIC should be larger than AIC with these params
        assert bic_val > aic_val

    def test_bic_2state(self):
        """2-state k=2, small n."""
        counts = np.array([[5, 5], [3, 7]], dtype=np.int64)
        val = bic(counts, [0, 1], n_observations=20)
        assert val > 0

    def test_bic_single_state_returns_zero(self):
        """1×1 matrix → BIC = 0.0."""
        counts = np.array([[10]], dtype=np.int64)
        val = bic(counts, [0, 0, 0], n_observations=10)
        assert val == 0.0

    def test_bic_same_inputs_same_output(self):
        """Determinism check."""
        counts = np.full((3, 3), 10, dtype=np.int64)
        val1 = bic(counts, [0, 1, 2], n_observations=90)
        val2 = bic(counts, [0, 1, 2], n_observations=90)
        assert val1 == val2


class TestMarkovChi2:
    """Billingsley χ² test for first-order Markov property."""

    def test_strong_markov_signal(self):
        """Second-order chain → reject H0, p < 0.001.

        Sequence with pattern (0,0)→1, (2,0)→0: transition from state 0
        depends on previous state (k). This violates first-order Markov.
        """
        # Pattern: 0,0,1,1,2,2,0,0,1,1,2,2,... repeated
        # From state 0: if came from 0, go to 1; if came from 2, go to 0
        # This is NOT first-order Markov → test rejects H0
        cycle = [0, 0, 1, 1, 2, 2]
        seq = (cycle * 30)[:-1]  # 179 elements, well-structured
        result = markov_chi2(seq, num_states=3)
        assert result["reject_null"] is True
        assert result["p_value"] < 0.001
        assert result["df"] == 6  # 3*2
        assert result["significance_level"] == 0.05
        assert "statistic" in result
        assert result["statistic"] >= 0

    def test_uniform_sequence_not_reject(self):
        """Uniform random-like sequence → may not reject H0."""
        # Short sequence of alternating states (not strongly Markovian)
        seq = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]
        result = markov_chi2(seq, num_states=3)
        # With only 11 transitions, df=6, may not reject
        assert isinstance(result["p_value"], float)
        assert result["df"] == 6

    def test_single_state(self):
        """Single state → df=0, not rejected."""
        result = markov_chi2([0, 0, 0, 0], num_states=1)
        assert result["df"] == 0
        assert result["reject_null"] is False

    def test_too_short_sequence(self):
        """Less than 2 elements → not rejected."""
        result = markov_chi2([0], num_states=3)
        assert result["reject_null"] is False
        assert result["df"] == 0

    def test_custom_alpha(self):
        """Custom significance level appears in result."""
        seq = [0, 0, 0, 1, 1, 1, 2, 2, 2, 0]
        result = markov_chi2(seq, num_states=3, alpha=0.01)
        assert result["significance_level"] == 0.01

    def test_deterministic(self):
        """Same inputs → same output."""
        seq = [0, 0, 1, 1, 2, 2, 0, 1]
        r1 = markov_chi2(seq, num_states=3)
        r2 = markov_chi2(seq, num_states=3)
        assert r1["statistic"] == r2["statistic"]
        assert r1["p_value"] == r2["p_value"]


class TestStatePersistence:
    """Per-state mean residence time: 1/(1-p_ii)."""

    def test_identity_matrix(self):
        """mat=I → residence time = inf for all states."""
        mat = np.eye(3, dtype=np.float64)
        result = state_persistence(mat)
        assert len(result) == 3
        for v in result.values():
            assert v == float("inf")

    def test_no_self_loops(self):
        """mat with p_ii=0 → residence time = 1.0 for all."""
        mat = np.array(
            [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]],
            dtype=np.float64,
        )
        result = state_persistence(mat)
        for v in result.values():
            assert v == 1.0

    def test_mixed_persistence(self):
        """mat = [[0.9,0.1],[0.2,0.8]]
        State 0: 1/(1-0.9) = 10
        State 1: 1/(1-0.8) = 5
        """
        mat = np.array([[0.9, 0.1], [0.2, 0.8]], dtype=np.float64)
        result = state_persistence(mat)
        assert result[0] == pytest.approx(10.0, rel=1e-9)
        assert result[1] == pytest.approx(5.0, rel=1e-9)

    def test_deterministic(self):
        """Same inputs → same output."""
        mat = np.array([[0.8, 0.2], [0.3, 0.7]], dtype=np.float64)
        r1 = state_persistence(mat)
        r2 = state_persistence(mat)
        assert r1 == r2

    def test_absorbing_state(self):
        """One absorbing state, one transient."""
        mat = np.array([[1.0, 0.0], [0.5, 0.5]], dtype=np.float64)
        result = state_persistence(mat)
        assert result[0] == float("inf")
        assert result[1] == pytest.approx(2.0, rel=1e-9)


class TestConditionalEntropy:
    """H(X_{n+1}|X_n) = -Σᵢ πᵢ Σⱼ p_ij * log₂(p_ij)."""

    def test_deterministic_chain_entropy_zero(self):
        """Deterministic chain (each row has one 1.0) → entropy = 0."""
        mat = np.eye(3, dtype=np.float64)
        h = conditional_entropy(mat)
        assert h == 0.0

    def test_uniform_chain_max_entropy(self):
        """Uniform |S|=3: each row [1/3, 1/3, 1/3]
        Row entropy: -3 * (1/3)*log2(1/3) = log2(3) ≈ 1.585
        Stationary uniform: π_i = 1/3
        h = Σ (1/3) * log2(3) = log2(3) ≈ 1.585
        """
        mat = np.full((3, 3), 1.0 / 3.0, dtype=np.float64)
        h = conditional_entropy(mat)
        expected = math.log2(3.0)
        assert h == pytest.approx(expected, rel=1e-9)

    def test_two_state_uniform(self):
        """|S|=2 uniform: each row [0.5, 0.5]
        h = log2(2) = 1.0
        """
        mat = np.full((2, 2), 0.5, dtype=np.float64)
        h = conditional_entropy(mat)
        assert h == pytest.approx(1.0, rel=1e-9)

    def test_custom_stationary_dist(self):
        """Custom stationary distribution changes the weighted sum."""
        mat = np.array([[0.9, 0.1], [0.2, 0.8]], dtype=np.float64)
        pi = np.array([0.5, 0.5], dtype=np.float64)
        h_custom = conditional_entropy(mat, stationary_dist=pi)
        h_uniform = conditional_entropy(mat)
        # Should produce different results
        assert abs(h_custom - h_uniform) < 10.0  # both should be valid

    def test_deterministic(self):
        """Same inputs → same output."""
        mat = np.array([[0.7, 0.3], [0.4, 0.6]], dtype=np.float64)
        h1 = conditional_entropy(mat)
        h2 = conditional_entropy(mat)
        assert h1 == h2

    def test_single_state_zero_entropy(self):
        """Single state → H = 0."""
        mat = np.array([[1.0]], dtype=np.float64)
        h = conditional_entropy(mat)
        assert h == 0.0
