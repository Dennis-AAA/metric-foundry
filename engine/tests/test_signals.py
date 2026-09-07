import numpy as np
import pandas as pd

from macrovol import signals
from macrovol.config import ASSET_BY_KEY
from macrovol.options import GexResult, SkewResult
from macrovol.util import clip_score, round_half_away, score_from_z


def _series(values):
    idx = pd.bdate_range("2023-01-02", periods=len(values))
    return pd.Series(values, index=idx)


def test_round_half_away_is_symmetric():
    assert round_half_away(0.5) == 1
    assert round_half_away(-0.5) == -1
    assert round_half_away(0.49) == 0
    assert clip_score(3.2) == 2
    assert clip_score(-7) == -2


def test_score_from_z_thresholds():
    assert score_from_z(0.2, 0.75, 1.5) == 0
    assert score_from_z(0.8, 0.75, 1.5) == 1
    assert score_from_z(-1.6, 0.75, 1.5) == -2
    assert score_from_z(None, 0.75, 1.5) == 0


def test_long_delta_confirmed_uptrend():
    rng = np.random.default_rng(0)
    close = _series(100 * np.exp(np.cumsum(rng.normal(0.0008, 0.005, 600))))
    res = signals.long_delta(ASSET_BY_KEY["ES"], close, cot=None)
    conf = res["components"]["confirmed"]
    assert conf["votes"] == 3
    assert conf["score"] == 2
    assert res["score"] >= 0


def test_short_delta_pinned_by_positive_gamma_in_calm_regime():
    rng = np.random.default_rng(1)
    close = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))))
    close.iloc[-10:] = close.iloc[-11] * np.linspace(1.0, 1.06, 10)  # sharp 10-day rally
    gex = GexResult(net_gex=5e9, call_gex=8e9, put_gex=3e9, ratio=0.45, flip=90.0, spot=100.0,
                    spot_vs_flip_pct=11.0, total_oi=1e6, n_expiries=5, max_dte=40, profile=[], largest_strikes=[])
    res = signals.short_delta(ASSET_BY_KEY["ES"], close, cot=None, gex=gex, regime_code="calm")
    assert res["components"]["flash"]["score"] > 0
    assert res["score"] == 0
    assert any("钉住" in o or "维持中性" in o for o in res["overlays"])


def test_short_delta_not_pinned_when_storm():
    rng = np.random.default_rng(1)
    close = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))))
    close.iloc[-10:] = close.iloc[-11] * np.linspace(1.0, 1.08, 10)
    gex = GexResult(net_gex=-5e9, call_gex=3e9, put_gex=8e9, ratio=-0.45, flip=110.0, spot=100.0,
                    spot_vs_flip_pct=-9.0, total_oi=1e6, n_expiries=5, max_dte=40, profile=[], largest_strikes=[])
    res = signals.short_delta(ASSET_BY_KEY["ES"], close, cot=None, gex=gex, regime_code="choppy")
    assert res["score"] > 0
    assert res["components"]["gamma"]["score"] > 0


def test_skew_labels():
    es = ASSET_BY_KEY["ES"]
    bearish = SkewResult("2026-10-16", 39, 15.0, 13.0, 18.0, -5.0, -5.0 / 15.0, 50, 60, False)
    assert signals.skew(es, bearish, None)["label"] == "偏空 RR"
    flat = SkewResult("2026-10-16", 39, 15.0, 15.2, 15.0, 0.2, 0.2 / 15.0, 50, 60, False)
    out = signals.skew(es, flat, None)
    assert out["label"] == "中性" and out["warn"]  # far from the equity norm -> flagged
    assert signals.skew(es, None, None)["label"] == "无数据"


def test_gamma_regime_transitions():
    es = ASSET_BY_KEY["ES"]
    calm = GexResult(3e9, 6e9, 3e9, 0.33, 700.0, 770.0, 10.0, 5e6, 10, 50, [], [])
    assert signals.gamma_regime(es, calm, 0)["code"] == "calm"
    storm = GexResult(-3e9, 3e9, 6e9, -0.33, 800.0, 770.0, -3.75, 5e6, 10, 50, [], [])
    assert signals.gamma_regime(es, storm, -1)["label"] == "风暴·偏空"
    balanced = GexResult(-0.1e9, 5e9, 5.1e9, -0.01, 771.0, 770.0, -0.13, 5e6, 10, 50, [], [])
    assert signals.gamma_regime(es, balanced, 1)["code"] == "transition"


def test_vega_uses_level_and_carry():
    es = ASSET_BY_KEY["ES"]
    rng = np.random.default_rng(2)
    close = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.012, 400))))  # ~19% realised vol
    iv = _series(np.linspace(30, 12, 400))  # implied vol collapsing to a 1y low, below realised
    out = signals.vega(es, close, iv, None, None)
    assert out["score"] == 2 and out["label"] == "强买波"
    rich = _series(np.concatenate([np.full(300, 15.0), np.linspace(15, 40, 100)]))
    out = signals.vega(es, close, rich, None, None)
    assert out["score"] <= -1
