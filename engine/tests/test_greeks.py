import numpy as np

from macrovol import greeks


def test_call_put_delta_parity():
    S, K, T, sigma, r = 100.0, 100.0, 0.25, 0.2, 0.04
    dc = greeks.delta(S, K, T, sigma, r, True)
    dp = greeks.delta(S, K, T, sigma, r, False)
    assert np.isclose(dc - dp, 1.0)
    assert 0.5 < float(dc) < 0.6  # ATM call delta slightly above 0.5 with positive drift


def test_gamma_peaks_at_the_money():
    S, T, sigma, r = 100.0, 0.25, 0.2, 0.04
    strikes = np.array([80.0, 100.0, 120.0])
    g = greeks.gamma(S, strikes, T, sigma, r)
    assert g[1] > g[0] and g[1] > g[2]


def test_dollar_gamma_scales_with_open_interest():
    S, K, T, sigma, r = 100.0, 100.0, 0.1, 0.3, 0.04
    one = greeks.dollar_gamma_per_1pct(S, K, T, sigma, r, oi=1)
    ten = greeks.dollar_gamma_per_1pct(S, K, T, sigma, r, oi=10)
    assert np.isclose(ten, 10 * one)
