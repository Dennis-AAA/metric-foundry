"""Option-book analytics: ATM IV, 25-delta risk reversal and dealer gamma exposure (GEX)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import greeks
from .config import GEX_MAX_DTE, SKEW_DTE_RANGE, SKEW_TARGET_DTE
from .sources.yahoo import ChainSlice, OptionBook

IV_MIN, IV_MAX = 0.02, 3.0


def _valid_quotes(df: pd.DataFrame) -> pd.DataFrame:
    iv = df["impliedVolatility"].astype(float)
    ok = (iv > IV_MIN) & (iv < IV_MAX) & (df["bid"].astype(float) > 0)
    return df[ok].copy()


def _slice_oi(s: ChainSlice) -> float:
    return float(s.calls["openInterest"].sum() + s.puts["openInterest"].sum())


def pick_skew_slice(book: OptionBook) -> ChainSlice | None:
    """Expiry nearest the target DTE among the liquid ones (freshly listed weeklies have no OI)."""
    lo, hi = SKEW_DTE_RANGE
    cands = [s for s in book.slices if lo <= s.dte <= hi]
    if not cands:
        cands = [s for s in book.slices if s.dte >= 7]
    if not cands:
        return None
    max_oi = max(_slice_oi(s) for s in cands)
    liquid = [s for s in cands if _slice_oi(s) >= 0.2 * max_oi] or cands
    return min(liquid, key=lambda s: abs(s.dte - SKEW_TARGET_DTE))


@dataclass
class SkewResult:
    expiry: str
    dte: int
    atm_iv: float  # in %
    call25_iv: float | None
    put25_iv: float | None
    rr25: float | None  # call25 - put25, vol points
    rr25_norm: float | None  # rr25 / atm_iv
    n_calls: int
    n_puts: int
    thin: bool


def _interp_iv_at_delta(strikes, ivs, deltas, target: float) -> float | None:
    """Interpolate IV at a target |delta| along the OTM wing (delta monotone in strike)."""
    if len(strikes) < 3:
        return None
    order = np.argsort(deltas)
    d, v = np.asarray(deltas)[order], np.asarray(ivs)[order]
    if target < d.min() or target > d.max():
        return None
    return float(np.interp(target, d, v))


def compute_skew(book: OptionBook, r: float) -> SkewResult | None:
    sl = pick_skew_slice(book)
    if sl is None or math.isnan(book.spot):
        return None
    S, T = book.spot, sl.dte / 365.0
    calls, puts = _valid_quotes(sl.calls), _valid_quotes(sl.puts)
    otm_c = calls[calls["strike"] >= S * 0.98]
    otm_p = puts[puts["strike"] <= S * 1.02]
    if len(otm_c) < 3 or len(otm_p) < 3:
        return None

    dc = greeks.delta(S, otm_c["strike"].values, T, otm_c["impliedVolatility"].values, r, True)
    dp = greeks.delta(S, otm_p["strike"].values, T, otm_p["impliedVolatility"].values, r, False)
    c25 = _interp_iv_at_delta(otm_c["strike"].values, otm_c["impliedVolatility"].values, dc, 0.25)
    p25 = _interp_iv_at_delta(otm_p["strike"].values, otm_p["impliedVolatility"].values, -dp, 0.25)

    # ATM IV: interpolate call & put smiles at K = S and average
    def _atm(df: pd.DataFrame) -> float | None:
        if len(df) < 2:
            return None
        k, v = df["strike"].values.astype(float), df["impliedVolatility"].values.astype(float)
        o = np.argsort(k)
        if S < k[o].min() or S > k[o].max():
            return None
        return float(np.interp(S, k[o], v[o]))

    atm_vals = [x for x in (_atm(calls), _atm(puts)) if x is not None]
    if not atm_vals:
        return None
    atm = float(np.mean(atm_vals)) * 100
    rr = None if (c25 is None or p25 is None) else (c25 - p25) * 100
    thin = len(otm_c) < 6 or len(otm_p) < 6 or (sl.calls["openInterest"].sum() + sl.puts["openInterest"].sum()) < 5000
    return SkewResult(
        expiry=sl.expiry,
        dte=sl.dte,
        atm_iv=atm,
        call25_iv=None if c25 is None else c25 * 100,
        put25_iv=None if p25 is None else p25 * 100,
        rr25=rr,
        rr25_norm=None if rr is None else rr / atm,
        n_calls=int(len(otm_c)),
        n_puts=int(len(otm_p)),
        thin=bool(thin),
    )


@dataclass
class GexResult:
    net_gex: float  # $ per 1% move, dealer sign convention (long calls / short puts)
    call_gex: float
    put_gex: float
    ratio: float  # net / (|calls| + |puts|), in [-1, 1]
    flip: float | None  # spot level where dealer gamma crosses zero
    spot: float
    spot_vs_flip_pct: float | None
    total_oi: float
    n_expiries: int
    max_dte: int
    profile: list[list[float]]  # [[spot_level, net_gex_$bn], ...] for the drill-down chart
    largest_strikes: list[list[float]]  # [[strike, net_gex_$bn], ...] top absolute contributors


def _book_arrays(book: OptionBook):
    ks, ts, ivs, ois, signs = [], [], [], [], []
    for sl in book.slices:
        if sl.dte > GEX_MAX_DTE:
            continue
        T = sl.dte / 365.0
        for df, sgn in ((sl.calls, 1.0), (sl.puts, -1.0)):
            d = df[df["openInterest"] > 0]
            if d.empty:
                continue
            iv = d["impliedVolatility"].astype(float).values
            # Yahoo IVs for illiquid strikes are unreliable; clamp instead of discarding OI
            iv = np.clip(iv, 0.05, 2.0)
            ks.append(d["strike"].values.astype(float))
            ts.append(np.full(len(d), T))
            ivs.append(iv)
            ois.append(d["openInterest"].values.astype(float))
            signs.append(np.full(len(d), sgn))
    if not ks:
        return None
    return tuple(np.concatenate(x) for x in (ks, ts, ivs, ois, signs))


def compute_gex(book: OptionBook, r: float) -> GexResult | None:
    if math.isnan(book.spot) or not book.slices:
        return None
    arrays = _book_arrays(book)
    if arrays is None:
        return None
    K, T, IV, OI, SGN = arrays
    S = book.spot

    dg = greeks.dollar_gamma_per_1pct(S, K, T, IV, r, OI)
    signed = dg * SGN
    call_gex = float(dg[SGN > 0].sum())
    put_gex = float(dg[SGN < 0].sum())
    net = float(signed.sum())
    denom = call_gex + put_gex
    ratio = net / denom if denom > 0 else 0.0

    # Gamma profile: re-price the whole book across a spot grid and locate the zero crossing.
    grid = S * np.linspace(0.85, 1.15, 121)
    prof = np.array([(greeks.dollar_gamma_per_1pct(g, K, T, IV, r, OI) * SGN).sum() for g in grid])
    flip = None
    sign_changes = np.where(np.sign(prof[:-1]) != np.sign(prof[1:]))[0]
    if len(sign_changes):
        # pick the crossing closest to spot
        idx = min(sign_changes, key=lambda i: abs(grid[i] - S))
        x0, x1, y0, y1 = grid[idx], grid[idx + 1], prof[idx], prof[idx + 1]
        flip = float(x0 - y0 * (x1 - x0) / (y1 - y0)) if y1 != y0 else float(x0)

    by_strike = pd.Series(signed).groupby(K).sum()
    top = by_strike.reindex(by_strike.abs().sort_values(ascending=False).index[:8])
    used = [sl for sl in book.slices if sl.dte <= GEX_MAX_DTE]
    return GexResult(
        net_gex=net,
        call_gex=call_gex,
        put_gex=put_gex,
        ratio=float(ratio),
        flip=flip,
        spot=S,
        spot_vs_flip_pct=None if flip is None else float((S / flip - 1) * 100),
        total_oi=float(OI.sum()),
        n_expiries=len(used),
        max_dte=max((sl.dte for sl in used), default=0),
        profile=[[float(g), float(v) / 1e9] for g, v in zip(grid[::4], prof[::4])],
        largest_strikes=[[float(k), float(v) / 1e9] for k, v in top.items()],
    )


def atm_iv_from_book(book: OptionBook, target_dte: int = 30) -> float | None:
    """ATM IV (%) from the expiry nearest to `target_dte`; used when no vol index exists."""
    cands = [s for s in book.slices if 10 <= s.dte <= 75]
    if not cands or math.isnan(book.spot):
        return None
    sl = min(cands, key=lambda s: abs(s.dte - target_dte))
    S = book.spot
    vals = []
    for df in (sl.calls, sl.puts):
        d = _valid_quotes(df)
        if len(d) < 2:
            continue
        k, v = d["strike"].values.astype(float), d["impliedVolatility"].values.astype(float)
        o = np.argsort(k)
        if k[o].min() <= S <= k[o].max():
            vals.append(float(np.interp(S, k[o], v[o])))
    return None if not vals else float(np.mean(vals)) * 100
