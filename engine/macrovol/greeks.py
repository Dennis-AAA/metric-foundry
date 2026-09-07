"""Black-Scholes(-Merton) Greeks, vectorised over numpy arrays."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _d1(S, K, T, sigma, r, q=0.0):
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.maximum(np.asarray(T, dtype=float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-6)
    return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def delta(S, K, T, sigma, r, is_call, q=0.0):
    d1 = _d1(S, K, T, sigma, r, q)
    disc = np.exp(-q * np.asarray(T, dtype=float))
    call = disc * norm.cdf(d1)
    return np.where(np.asarray(is_call, dtype=bool), call, call - disc)


def gamma(S, K, T, sigma, r, q=0.0):
    d1 = _d1(S, K, T, sigma, r, q)
    T = np.maximum(np.asarray(T, dtype=float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-6)
    disc = np.exp(-q * T)
    return disc * norm.pdf(d1) / (np.asarray(S, dtype=float) * sigma * np.sqrt(T))


def dollar_gamma_per_1pct(S, K, T, sigma, r, oi, contract_size=100, q=0.0):
    """Dollar gamma for a 1% move in the underlying: gamma * OI * size * S^2 * 1%."""
    g = gamma(S, K, T, sigma, r, q)
    S = np.asarray(S, dtype=float)
    return g * np.asarray(oi, dtype=float) * contract_size * S * S * 0.01
