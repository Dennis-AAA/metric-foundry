"""Small numeric helpers shared by the signal modules."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def round_half_away(x: float) -> int:
    """Round to nearest integer with .5 going away from zero (Python's round() is banker's)."""
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def clip_score(x: float, lo: int = -2, hi: int = 2) -> int:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0
    return int(max(lo, min(hi, round_half_away(x))))


def sign(x: float) -> int:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0
    return (x > 0) - (x < 0)


def score_from_z(z: float | None, t1: float, t2: float) -> int:
    """Map a z-score to the discrete -2..+2 scale using two thresholds."""
    if z is None or math.isnan(z):
        return 0
    a = abs(z)
    if a >= t2:
        return 2 * sign(z)
    if a >= t1:
        return 1 * sign(z)
    return 0


def last_valid(s: pd.Series) -> float | None:
    s = s.dropna()
    return None if s.empty else float(s.iloc[-1])


def rolling_z(s: pd.Series, window: int) -> float | None:
    """z-score of the last observation versus the trailing window (excluding nothing)."""
    s = s.dropna()
    if len(s) < max(30, window // 4):
        return None
    w = s.iloc[-window:]
    sd = float(w.std(ddof=0))
    if sd == 0 or math.isnan(sd):
        return None
    return float((s.iloc[-1] - w.mean()) / sd)


def pct_rank(s: pd.Series, window: int) -> float | None:
    """Percentile (0-100) of the last observation within the trailing window."""
    s = s.dropna()
    if len(s) < max(30, window // 4):
        return None
    w = s.iloc[-window:]
    return float((w < w.iloc[-1]).mean() * 100)


def pct_rank_value(value: float, ref: pd.Series) -> float | None:
    ref = ref.dropna()
    if ref.empty or value is None or math.isnan(value):
        return None
    return float((ref < value).mean() * 100)


def r(x: Any, nd: int = 2) -> Any:
    """Round for JSON output; keeps None / non-numeric values untouched."""
    if x is None:
        return None
    if isinstance(x, (bool, str)):
        return x
    if isinstance(x, (int, np.integer)):
        return int(x)
    try:
        f = float(x)
    except (TypeError, ValueError):
        return x
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def series_tail(s: pd.Series, n: int = 60, nd: int = 4) -> list[list[Any]]:
    s = s.dropna().iloc[-n:]
    return [[idx.strftime("%Y-%m-%d"), r(v, nd)] for idx, v in s.items()]


def realized_vol(close: pd.Series, window: int) -> pd.Series:
    lr = np.log(close / close.shift(1))
    return lr.rolling(window).std(ddof=0) * math.sqrt(252) * 100
