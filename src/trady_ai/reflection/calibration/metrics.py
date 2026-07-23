"""Pure deterministic metric functions for the Calibration Framework.

All functions are pure and deterministic — same inputs always produce the
same outputs. No random seeds, no state, no I/O.

Functions:
    aic: Akaike Information Criterion for a Markov chain.
    bic: Bayesian Information Criterion for a Markov chain.
    markov_chi2: Billingsley χ² test for first-order Markov property.
    state_persistence: Per-state mean residence times.
    conditional_entropy: Conditional entropy H(X_{n+1}|X_n).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import chi2  # type: ignore[import-untyped]


def aic(transition_counts: np.ndarray, state_sequence: list[int]) -> float:
    """Compute Akaike Information Criterion for a Markov chain.

    AIC = -2*ln(L) + 2*k, where k = |S|*(|S|-1) is the number of free
    transition parameters and L is the Markov chain likelihood using MLE.

    Args:
        transition_counts: |S|×|S| matrix of observed transition counts.
        state_sequence: Sequence of state indices (not used directly, but
            kept for API consistency with other metrics).

    Returns:
        AIC value as float. Returns 0.0 for degenerate cases (0 or 1 states).
    """
    num_states = transition_counts.shape[0]
    if num_states < 2:
        return 0.0

    k = num_states * (num_states - 1)

    # Compute MLE transition probabilities row-wise
    row_sums = transition_counts.sum(axis=1, dtype=np.float64)

    # Log-likelihood: Σᵢⱼ n_ij * ln(p_ij) where p_ij = n_ij / Σⱼ n_ij
    log_likelihood = 0.0
    for i in range(num_states):
        if row_sums[i] == 0:
            continue
        p_i = transition_counts[i, :] / row_sums[i]
        # Only count non-zero transitions (ln(0) is undefined)
        for j in range(num_states):
            count = transition_counts[i, j]
            if count > 0 and p_i[j] > 0:
                log_likelihood += float(count) * math.log(float(p_i[j]))

    return float(-2.0 * log_likelihood + 2.0 * k)


def bic(
    transition_counts: np.ndarray,
    state_sequence: list[int],
    n_observations: int,
) -> float:
    """Compute Bayesian Information Criterion for a Markov chain.

    BIC = -2*ln(L) + k*ln(n), where k = |S|*(|S|-1) and n = total
    observations.

    Args:
        transition_counts: |S|×|S| matrix of observed transition counts.
        state_sequence: Sequence of state indices (not used directly).
        n_observations: Total number of state transitions observed.

    Returns:
        BIC value as float. Returns 0.0 for degenerate cases.
    """
    if n_observations < 2:
        return 0.0

    num_states = transition_counts.shape[0]
    if num_states < 2:
        return 0.0

    k = num_states * (num_states - 1)

    # Reuse the same log-likelihood computation
    row_sums = transition_counts.sum(axis=1, dtype=np.float64)
    log_likelihood = 0.0
    for i in range(num_states):
        if row_sums[i] == 0:
            continue
        p_i = transition_counts[i, :] / row_sums[i]
        for j in range(num_states):
            count = transition_counts[i, j]
            if count > 0 and p_i[j] > 0:
                log_likelihood += float(count) * math.log(float(p_i[j]))

    return float(-2.0 * log_likelihood + k * math.log(n_observations))


def markov_chi2(
    state_sequence: list[int],
    num_states: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Billingsley χ² test for first-order Markov property.

    Tests H0: The sequence is first-order Markov.
    H1: Higher-order dependencies exist.

    The test statistic follows a χ² distribution with |S|*(|S|-1) degrees of
    freedom under H0.

    Args:
        state_sequence: Sequence of state indices (length N).
        num_states: Size of the state space (|S|).
        alpha: Significance level (default 0.05).

    Returns:
        dict with keys: statistic, p_value, df, reject_null,
            significance_level.
    """
    if len(state_sequence) < 2 or num_states < 2:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "df": 0,
            "reject_null": False,
            "significance_level": alpha,
        }

    df = num_states * (num_states - 1)

    # Build transition count matrix
    counts = np.zeros((num_states, num_states), dtype=np.int64)
    for t in range(len(state_sequence) - 1):
        i = state_sequence[t]
        j = state_sequence[t + 1]
        if 0 <= i < num_states and 0 <= j < num_states:
            counts[i, j] += 1

    # Row sums (n_i₊) and column sums (n_₊ⱼ)
    row_sums = counts.sum(axis=1, dtype=np.float64)
    col_sums = counts.sum(axis=0, dtype=np.float64)
    total = float(row_sums.sum())

    if total == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "df": df,
            "reject_null": False,
            "significance_level": alpha,
        }

    # Chi-squared statistic: Σ (n_ij - e_ij)² / e_ij
    # where e_ij = n_i₊ * n_₊ⱼ / n under independence
    chi2_stat = 0.0
    for i in range(num_states):
        if row_sums[i] == 0:
            continue
        for j in range(num_states):
            if col_sums[j] == 0:
                continue
            observed = float(counts[i, j])
            expected = row_sums[i] * col_sums[j] / total
            if expected > 0:
                chi2_stat += (observed - expected) ** 2 / expected

    # p-value using scipy chi2.sf (survival function = 1 - CDF)
    p_value = float(chi2.sf(chi2_stat, df))
    reject_null = p_value < alpha

    return {
        "statistic": round(chi2_stat, 10),
        "p_value": round(p_value, 10),
        "df": df,
        "reject_null": reject_null,
        "significance_level": alpha,
    }


def state_persistence(transition_matrix: np.ndarray) -> dict[int, float]:
    """Compute per-state mean residence times.

    Mean residence time for state i: 1 / (1 - p_ii), where p_ii is the
    probability of staying in the same state.

    A p_ii of 1.0 (absorbing state) yields infinite residence time.
    A p_ii of 0.0 yields residence time of 1.0 (immediate exit).

    Args:
        transition_matrix: |S|×|S| MLE transition probability matrix.

    Returns:
        Dict mapping state index → mean residence time in ticks.
    """
    num_states = transition_matrix.shape[0]
    result: dict[int, float] = {}
    for i in range(num_states):
        p_ii = float(transition_matrix[i, i])
        if p_ii >= 1.0:
            result[i] = float("inf")
        else:
            result[i] = float(round(1.0 / (1.0 - p_ii), 10))
    return result


def conditional_entropy(
    transition_matrix: np.ndarray,
    stationary_dist: np.ndarray | None = None,
) -> float:
    """Compute conditional entropy H(X_{n+1}|X_n) for a Markov chain.

    H(X_{n+1}|X_n) = -Σᵢ πᵢ Σⱼ p_ij * log₂(p_ij)

    If stationary_dist is None, the uniform distribution is used.

    Args:
        transition_matrix: |S|×|S| MLE transition probability matrix.
        stationary_dist: Optional stationary distribution (length |S|).
            If None, defaults to uniform.

    Returns:
        Conditional entropy in bits (log₂).
    """
    num_states = transition_matrix.shape[0]
    if num_states < 2:
        return 0.0

    if stationary_dist is None:
        pi = np.ones(num_states, dtype=np.float64) / num_states
    else:
        pi = np.asarray(stationary_dist, dtype=np.float64)
        pi = pi / pi.sum()  # normalize

    entropy = 0.0
    for i in range(num_states):
        if pi[i] <= 0:
            continue
        row_entropy = 0.0
        for j in range(num_states):
            p_ij = float(transition_matrix[i, j])
            if p_ij > 0:
                row_entropy += p_ij * math.log2(p_ij)
        entropy += pi[i] * row_entropy

    return float(round(-entropy, 10))
