"""Scoring rules for the seven dashboard columns.

Every function returns a plain dict that is serialised as-is into the snapshot JSON, so
the web layer can show both the headline label and the intermediate metrics that
produced it.  Direction scores live on a -2..+2 scale; the other columns carry a score
on the same scale plus a Chinese label matching the original board.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config as C
from .config import AssetSpec
from .options import GexResult, SkewResult
from .util import (
    clip_score,
    last_valid,
    pct_rank,
    pct_rank_value,
    r,
    realized_vol,
    rolling_z,
    score_from_z,
    sign,
)


def _dir_label(asset: AssetSpec, score: int) -> str:
    if score == 0:
        return "中性"
    base = asset.long_label if score > 0 else asset.short_label
    return f"偏{base}" if abs(score) == 1 else base


def _dot(z: float | None, band: float = 0.35) -> str:
    if z is None or math.isnan(z):
        return "yellow"
    return "green" if z > band else "red" if z < -band else "yellow"


# ---------------------------------------------------------------------------
# 短线 DELTA  (Flash · FM · Gamma) ~1-4 周
# ---------------------------------------------------------------------------
def short_delta(asset: AssetSpec, close: pd.Series, cot: pd.DataFrame | None, gex: GexResult | None,
                regime_code: str) -> dict:
    ret = close.pct_change(C.FLASH_RET_DAYS)
    flash_z = rolling_z(ret, C.LOOKBACK_1Y)
    flash_score = score_from_z(flash_z, C.FLASH_Z_T1, C.FLASH_Z_T2)
    hi20, lo20 = close.rolling(20).max(), close.rolling(20).min()
    px = last_valid(close)
    breakout = "上破20日高" if px is not None and px >= last_valid(hi20) else ("下破20日低" if px is not None and px <= last_valid(lo20) else None)

    fm_z = fm_score = fm_pct = fm_net_pct = fm_flow = None
    if cot is not None and len(cot) > 30:
        flow = cot["fm_net_pct"].diff(C.FM_FLOW_WEEKS)
        fm_z = rolling_z(flow, 104)
        fm_score = score_from_z(fm_z, C.FLASH_Z_T1, C.FLASH_Z_T2)
        fm_pct = pct_rank(cot["fm_net_pct"], 156)
        fm_net_pct = last_valid(cot["fm_net_pct"])
        fm_flow = last_valid(flow)
    fm_score = fm_score or 0

    # Dealer gamma: negative gamma amplifies the prevailing impulse, positive gamma dampens it.
    gamma_score = 0
    gamma_note = "无期权数据"
    if gex is not None:
        if gex.net_gex < 0:
            impulse = sign(flash_score) or sign(flash_z or 0)
            gamma_score = impulse * (2 if gex.ratio < -0.3 else 1)
            gamma_note = "负Gamma：做市商追涨杀跌，放大 Flash 方向"
        else:
            gamma_note = "正Gamma：做市商反向对冲，抑制趋势"

    raw = C.SHORT_WEIGHTS["flash"] * flash_score + C.SHORT_WEIGHTS["fm"] * fm_score + C.SHORT_WEIGHTS["gamma"] * gamma_score
    overlays: list[str] = []
    if fm_pct is not None:
        if fm_pct > 90 and raw > 0:
            raw -= 0.5
            overlays.append("快钱多头拥挤(>90%)，打折")
        elif fm_pct < 10 and raw < 0:
            raw += 0.5
            overlays.append("快钱空头拥挤(<10%)，打折")
    score = clip_score(raw)
    pinned = gex is not None and gex.net_gex > 0 and regime_code == "calm"
    if pinned and abs(raw) < C.SHORT_PIN_THRESHOLD and score != 0:
        overlays.append("高频叠加：正Gamma+平静体制 → 钉住，拉回中性")
        score = 0
    elif pinned and score == 0:
        overlays.append("高频叠加：正Gamma+平静体制，维持中性")

    return {
        "score": score,
        "label": _dir_label(asset, score),
        "dot": _dot(flash_z),
        "raw": r(raw, 2),
        "overlays": overlays,
        "components": {
            "flash": {
                "score": flash_score,
                "z": r(flash_z),
                "ret_pct": r((last_valid(ret) or 0) * 100),
                "days": C.FLASH_RET_DAYS,
                "breakout": breakout,
                "desc": f"{C.FLASH_RET_DAYS}日收益 z 值（对比1年分布）",
            },
            "fm": {
                "score": fm_score,
                "z": r(fm_z),
                "net_pct_oi": r(fm_net_pct),
                "flow_4w_pct_oi": r(fm_flow),
                "level_pct_3y": r(fm_pct, 0),
                "group": "Leveraged Funds" if asset.cot.fast_money == "lev_money" else "Managed Money",
                "desc": f"快钱净仓位(占OI%) {C.FM_FLOW_WEEKS}周变化 z 值；分位=3年水位",
            },
            "gamma": {
                "score": gamma_score,
                "note": gamma_note,
                "net_gex_bn": None if gex is None else r(gex.net_gex / 1e9, 3),
            },
        },
        "weights": C.SHORT_WEIGHTS,
    }


# ---------------------------------------------------------------------------
# 长线 DELTA  (Confirmed · RM · FV) ~1-3 月
# ---------------------------------------------------------------------------
def long_delta(asset: AssetSpec, close: pd.Series, cot: pd.DataFrame | None) -> dict:
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    ret63 = close.pct_change(C.CONFIRM_RET_DAYS)
    px = last_valid(close)
    t1 = sign(px - (last_valid(ma200) or px)) if px is not None else 0
    t2 = sign((last_valid(ma50) or 0) - (last_valid(ma200) or 0))
    t3 = sign(last_valid(ret63) or 0)
    votes = t1 + t2 + t3
    ret63_z = rolling_z(ret63, C.LOOKBACK_2Y)
    if abs(votes) == 3:
        confirmed = 2 * sign(votes)
    else:
        confirmed = sign(ret63_z or 0) if ret63_z is not None and abs(ret63_z) > 0.75 else 0

    rm_z = rm_score = rm_pct = rm_net_pct = rm_flow = None
    if cot is not None and len(cot) > 40:
        flow = cot["rm_net_pct"].diff(C.RM_FLOW_WEEKS)
        rm_z = rolling_z(flow, 156)
        rm_score = score_from_z(rm_z, C.FLASH_Z_T1, C.FLASH_Z_T2)
        rm_pct = pct_rank(cot["rm_net_pct"], 156)
        rm_net_pct = last_valid(cot["rm_net_pct"])
        rm_flow = last_valid(flow)
    rm_score = rm_score or 0

    logp = np.log(close)
    fv_z = rolling_z(logp, C.LOOKBACK_1Y)
    fv_score = -score_from_z(fv_z, C.FV_Z_T1, C.FV_Z_T2)  # stretched above the 1y mean -> negative

    raw = C.LONG_WEIGHTS["confirmed"] * confirmed + C.LONG_WEIGHTS["rm"] * rm_score + C.LONG_WEIGHTS["fv"] * fv_score
    score = clip_score(raw)
    structural = score != 0 and (confirmed == 0 or sign(confirmed) != sign(score))
    notes: list[str] = []
    if structural:
        score = sign(score)  # 半档: structural bias only, never a full-size position
        notes.append("暂定结构偏向：RM/FV 主导、趋势未确认 → 半档、雷达观察")
    confirmed_flag = score != 0 and sign(confirmed) == sign(score) and abs(confirmed) == 2
    label = _dir_label(asset, score)
    if structural:
        label += "·结构观察"
    elif confirmed_flag:
        label += "·确认"
        notes.append("价格 > MA200、MA50 > MA200、63日收益同向：趋势确认")

    return {
        "score": score,
        "label": label,
        "dot": "green" if votes == 3 else "red" if votes == -3 else "yellow",
        "structural": structural,
        "confirmed": confirmed_flag,
        "raw": r(raw, 2),
        "notes": notes,
        "components": {
            "confirmed": {
                "score": confirmed,
                "votes": votes,
                "above_ma200": t1 > 0,
                "ma50_gt_ma200": t2 > 0,
                "ret_63d_pct": r((last_valid(ret63) or 0) * 100),
                "ret_63d_z": r(ret63_z),
                "desc": "价格 vs MA200 · MA50 vs MA200 · 63日收益 三票制",
            },
            "rm": {
                "score": rm_score,
                "z": r(rm_z),
                "net_pct_oi": r(rm_net_pct),
                "flow_13w_pct_oi": r(rm_flow),
                "level_pct_3y": r(rm_pct, 0),
                "group": "Asset Manager / Institutional" if asset.cot.real_money == "asset_mgr" else "Swap Dealers (指数/机构代理)",
                "desc": f"慢钱净仓位(占OI%) {C.RM_FLOW_WEEKS}周变化 z 值；分位=3年水位",
            },
            "fv": {
                "score": fv_score,
                "stretch_z": r(fv_z),
                "desc": "对数价格相对1年均值的偏离 (σ)，>+1.5σ 视为偏贵",
            },
        },
        "weights": C.LONG_WEIGHTS,
    }


# ---------------------------------------------------------------------------
# VEGA
# ---------------------------------------------------------------------------
VEGA_LABELS = {2: "强买波", 1: "买波", 0: "中性", -1: "卖波", -2: "强卖波"}


def vega(asset: AssetSpec, close: pd.Series, iv_series: pd.Series | None, chain_atm_iv: float | None,
         term: dict | None, iv_history: list[float] | None = None) -> dict:
    rv20 = realized_vol(close, C.RV_WINDOW)
    rv60 = realized_vol(close, 60)
    rv20_now, rv60_now = last_valid(rv20), last_valid(rv60)

    proxy = None
    if iv_series is not None and last_valid(iv_series) is not None:
        iv_now = last_valid(iv_series)
        iv_pct = pct_rank(iv_series, C.LOOKBACK_1Y)
        iv_source = f"{asset.iv_index} 指数" + (f" ×{asset.iv_index_scale}" if asset.iv_index_scale != 1 else "")
    elif chain_atm_iv is not None:
        iv_now = chain_atm_iv
        iv_source = f"{asset.option_proxy} 期权链 ATM IV (~30D)"
        if iv_history and len(iv_history) >= 60:
            # enough of our own daily snapshots to rank the chain IV against itself
            iv_pct = pct_rank_value(iv_now, pd.Series(iv_history[-C.LOOKBACK_1Y:]))
            proxy = f"无公开IV指数：分位数基于本看板累计的 {len(iv_history)} 个日度 IV 快照"
        else:
            iv_pct = pct_rank(rv20, C.LOOKBACK_1Y)
            proxy = "无公开IV指数：水位用 20日已实现波动率的1年分位代理"
    else:
        return {"score": 0, "label": "无数据", "warn": True, "metrics": {"rv20": r(rv20_now)}, "why": ["缺少隐含波动率"]}

    carry = None if not rv20_now else (iv_now - rv20_now) / rv20_now
    level_pts = 0
    if iv_pct is not None:
        if iv_pct < C.IV_PCT_VERY_CHEAP:
            level_pts = 2
        elif iv_pct < C.IV_PCT_CHEAP:
            level_pts = 1
        elif iv_pct > C.IV_PCT_VERY_RICH:
            level_pts = -2
        elif iv_pct > C.IV_PCT_RICH:
            level_pts = -1
    carry_pts = 0
    if carry is not None:
        if carry < C.CARRY_CHEAP:
            carry_pts = 1
        elif carry > C.CARRY_RICH:
            carry_pts = -1
    score = max(-2, min(2, level_pts + carry_pts))
    conflict = level_pts * carry_pts < 0
    why = []
    if iv_pct is not None:
        why.append(f"IV 1年分位 {iv_pct:.0f}%")
    if carry is not None:
        why.append(f"IV/RV20 溢价 {carry*100:+.0f}%")
    if conflict:
        why.append("水位与 carry 信号冲突")
    if proxy:
        why.append(proxy)
    return {
        "score": score,
        "label": VEGA_LABELS[score],
        "warn": bool(conflict or proxy),
        "metrics": {
            "iv": r(iv_now),
            "iv_source": iv_source,
            "iv_pct_1y": r(iv_pct, 0),
            "rv20": r(rv20_now),
            "rv60": r(rv60_now),
            "iv_minus_rv": r(None if rv20_now is None else iv_now - rv20_now),
            "carry": r(None if carry is None else carry * 100, 0),
            "level_pts": level_pts,
            "carry_pts": carry_pts,
            "term": term,
        },
        "why": why,
    }


# ---------------------------------------------------------------------------
# SKEW
# ---------------------------------------------------------------------------
def skew(asset: AssetSpec, sk: SkewResult | None, skew_index: float | None) -> dict:
    if sk is None or sk.rr25_norm is None:
        return {
            "score": 0,
            "label": "无数据",
            "warn": True,
            "metrics": {"skew_index": r(skew_index)},
            "why": ["期权链不足以计算 25Δ 风险逆转"],
        }
    x = sk.rr25_norm
    if x < -C.RR_NEUTRAL_BAND:
        score = -2 if x < -C.RR_STRONG else -1
        label = "偏空 RR"
    elif x > C.RR_NEUTRAL_BAND:
        score = 2 if x > C.RR_STRONG else 1
        label = "偏多 RR"
    else:
        score, label = 0, "中性"
    dev = x - asset.rr_baseline
    warn = sk.thin or (score == 0 and abs(dev) > C.RR_BASELINE_WARN)
    why = [f"25Δ RR = {sk.rr25:+.2f} vol ({x*100:+.0f}% of ATM)", f"相对常态 ({asset.rr_baseline*100:+.0f}%) 偏离 {dev*100:+.0f}%"]
    if sk.thin:
        why.append("报价稀疏，可靠性低")
    if skew_index is not None:
        why.append(f"CBOE SKEW {skew_index:.1f}")
    return {
        "score": score,
        "label": label,
        "warn": bool(warn),
        "metrics": {
            "rr25_vol": r(sk.rr25),
            "rr25_norm": r(x, 3),
            "baseline": asset.rr_baseline,
            "dev_vs_baseline": r(dev, 3),
            "atm_iv": r(sk.atm_iv),
            "call25_iv": r(sk.call25_iv),
            "put25_iv": r(sk.put25_iv),
            "expiry": sk.expiry,
            "dte": sk.dte,
            "n_quotes": [sk.n_calls, sk.n_puts],
            "skew_index": r(skew_index),
            "proxy": asset.option_proxy,
        },
        "why": why,
    }


# ---------------------------------------------------------------------------
# GAMMA (dealer positioning regime)
# ---------------------------------------------------------------------------
GAMMA_HEAT = {"calm": 0, "transition": 1, "storm": 2, "na": 0}
WEAK_PROXIES = {"FXE", "FXY", "USO"}


def gamma_regime(asset: AssetSpec, gex: GexResult | None, flash_dir: int) -> dict:
    if gex is None:
        return {"score": 0, "code": "na", "label": "无数据", "warn": True, "metrics": {}, "why": ["无期权链"]}
    svf = gex.spot_vs_flip_pct
    why = [f"净 GEX {gex.net_gex/1e9:+.2f} bn$/1%", f"看涨/看跌 gamma 比 {gex.ratio:+.2f}"]
    if gex.flip is not None:
        why.append(f"Gamma 翻转位 {gex.flip:.1f}（现价偏离 {svf:+.1f}%）")
    near_flip = svf is not None and abs(svf) < C.GEX_FLIP_BAND_PCT
    balanced = abs(gex.ratio) < C.GEX_RATIO_BAND
    clearly_below_flip = svf is not None and svf < -C.GEX_FLIP_BAND_PCT
    if gex.net_gex > 0 and not balanced and not near_flip:
        code, label, score = "calm", "平静·收theta", 1
        why.append("做市商多Gamma → 波动被压制，适合收 theta")
    elif gex.net_gex < 0 and (not balanced or clearly_below_flip):
        code = "storm"
        score = -1
        if flash_dir > 0:
            label = "风暴·偏多"
        elif flash_dir < 0:
            label = "风暴·偏空"
        else:
            label = "风暴"
        why.append("做市商空Gamma → 追涨杀跌，波动放大")
    else:
        code, label, score = "transition", "初起·中性", 0
        why.append("多空Gamma接近平衡/贴近翻转位：体制切换初起")
    weak = asset.option_proxy in WEAK_PROXIES or gex.total_oi < C.GEX_MIN_OI
    if weak:
        why.append(f"{asset.option_proxy} ETF 期权仅是期货做市商仓位的弱代理")
    return {
        "score": score,
        "code": code,
        "label": label,
        "warn": bool(weak),
        "metrics": {
            "net_gex_bn": r(gex.net_gex / 1e9, 3),
            "call_gex_bn": r(gex.call_gex / 1e9, 3),
            "put_gex_bn": r(gex.put_gex / 1e9, 3),
            "ratio": r(gex.ratio, 3),
            "flip": r(gex.flip),
            "spot": r(gex.spot),
            "spot_vs_flip_pct": r(svf),
            "total_oi": int(gex.total_oi),
            "n_expiries": gex.n_expiries,
            "max_dte": gex.max_dte,
            "proxy": asset.option_proxy,
            "profile": [[r(a, 2), r(b, 3)] for a, b in gex.profile],
            "largest_strikes": [[r(a, 2), r(b, 3)] for a, b in gex.largest_strikes],
        },
        "why": why,
    }


# ---------------------------------------------------------------------------
# VOL 体制
# ---------------------------------------------------------------------------
REGIME_LABELS = {
    "calm": "平静",
    "choppy": "混乱",
    "high_easing": "高Vol缓和",
    "high_expanding": "高Vol扩张",
    "low_turning": "低Vol转折",
}
REGIME_HEAT = {"calm": 0, "low_turning": 1, "high_easing": 1, "choppy": 2, "high_expanding": 2}


def vol_regime(asset: AssetSpec, close: pd.Series, iv_series: pd.Series | None) -> dict:
    rv20 = realized_vol(close, C.RV_WINDOW)
    rv60 = realized_vol(close, 60)
    proxy = iv_series is None or last_valid(iv_series) is None
    vol = rv20 if proxy else iv_series.dropna()
    vol = vol.dropna()
    if len(vol) < 60:
        return {"code": "calm", "label": "平静", "warn": True, "metrics": {}, "why": ["历史不足"]}
    pct = pct_rank(vol, C.LOOKBACK_1Y)
    chg5 = float(vol.iloc[-1] / vol.iloc[-6] - 1) if len(vol) > 6 and vol.iloc[-6] else 0.0
    vov = vol.pct_change().rolling(20).std()
    vov_pct = pct_rank(vov, C.LOOKBACK_1Y)
    rv20_now, rv60_now = last_valid(rv20), last_valid(rv60)
    iv_now = float(vol.iloc[-1])
    rv_ratio = None if not rv60_now else (rv20_now or 0) / rv60_now
    rv_gt_iv = (not proxy) and rv20_now is not None and rv20_now > iv_now

    if pct is not None and pct > C.REGIME_HIGH_PCT:
        code = "high_easing" if chg5 < 0 else "high_expanding"
    elif vov_pct is not None and vov_pct > C.REGIME_VOV_PCT and (rv_gt_iv or (rv_ratio or 0) > 1.15):
        code = "choppy"
    elif pct is not None and pct < C.REGIME_LOW_PCT and chg5 > C.REGIME_TURN_CHANGE:
        code = "low_turning"
    else:
        code = "calm"
    why = [f"波动率1年分位 {pct:.0f}%" if pct is not None else "分位不可用", f"5日变化 {chg5*100:+.0f}%"]
    if vov_pct is not None:
        why.append(f"vol-of-vol 分位 {vov_pct:.0f}%")
    if rv_ratio is not None:
        why.append(f"RV20/RV60 = {rv_ratio:.2f}")
    if proxy:
        why.append("无IV指数：以20日已实现波动率代理")
    return {
        "code": code,
        "label": REGIME_LABELS[code],
        "heat": REGIME_HEAT[code],
        "warn": bool(proxy),
        "metrics": {
            "vol_now": r(iv_now),
            "vol_pct_1y": r(pct, 0),
            "chg_5d_pct": r(chg5 * 100, 0),
            "vov_pct_1y": r(vov_pct, 0),
            "rv20": r(rv20_now),
            "rv60": r(rv60_now),
            "rv_ratio": r(rv_ratio),
            "source": "RV20 代理" if proxy else f"{asset.iv_index} 指数",
        },
        "why": why,
    }


def heat(short: dict, long: dict, veg: dict, sk: dict, gam: dict, reg: dict) -> dict:
    parts = {
        "short": abs(short["score"]),
        "long": abs(long["score"]),
        "vega": abs(veg["score"]),
        "skew": abs(sk["score"]),
        "gamma": GAMMA_HEAT.get(gam.get("code", "na"), 0),
        "regime": reg.get("heat", 0),
    }
    return {"value": int(sum(parts.values())), "max": 12, "parts": parts}
