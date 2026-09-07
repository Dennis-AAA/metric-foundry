"""Build one dashboard snapshot: fetch -> score -> JSON."""
from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

import pandas as pd

from . import config as C
from . import signals
from .cache import Cache
from .config import ASSETS, AssetSpec
from .options import atm_iv_from_book, compute_gex, compute_skew
from .sources.cboe import fetch_cboe_index
from .sources.cftc import fetch_cot
from .sources.yahoo import OptionBook, SourceError, fetch_closes, fetch_option_book
from .util import last_valid, r, series_tail, sign

log = logging.getLogger(__name__)
NY = zoneinfo.ZoneInfo("America/New_York")


class SourceLog:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.items.append({"name": name, "status": "ok", "detail": detail})

    def warn(self, name: str, detail: str) -> None:
        self.items.append({"name": name, "status": "warn", "detail": detail})

    def fail(self, name: str, detail: str) -> None:
        self.items.append({"name": name, "status": "error", "detail": detail})


def _drop_partial_session(close: pd.DataFrame, intraday: bool) -> pd.DataFrame:
    if intraday or close.empty:
        return close
    now_ny = dt.datetime.now(NY)
    today = pd.Timestamp(now_ny.date())
    # futures print a row for the running session; treat it as final only after the 17:00 ET close
    if close.index[-1] >= today and now_ny.hour < 17:
        return close.iloc[:-1]
    return close


def build_snapshot(cache: Cache, mode: str = "daily", assets: list[AssetSpec] | None = None,
                   skip_options: bool = False, intraday: bool = False) -> dict:
    assets = assets or ASSETS
    src = SourceLog()

    # ---- prices -------------------------------------------------------------------
    # always pull the full universe so the cache key is stable across --assets subsets
    tickers = [a.futures_ticker for a in ASSETS] + list(C.AUX_TICKERS.values())
    try:
        closes = fetch_closes(tickers, cache)
        closes = _drop_partial_session(closes, intraday)
        src.ok("Yahoo Finance 期货/指数日线", f"{len(closes)} 行, 至 {closes.index[-1]:%Y-%m-%d}")
    except SourceError as exc:
        src.fail("Yahoo Finance 期货/指数日线", str(exc))
        raise

    # ---- CBOE vol indices ---------------------------------------------------------
    cboe: dict[str, pd.Series] = {}
    for name in C.CBOE_INDICES:
        try:
            cboe[name] = fetch_cboe_index(name, cache)
        except Exception as exc:
            src.warn(f"CBOE {name}", str(exc))
    if cboe:
        latest = max(s.dropna().index[-1] for s in cboe.values())
        src.ok("CBOE 波动率指数", f"{', '.join(cboe)} 至 {latest:%Y-%m-%d}")

    move = closes.get(C.AUX_TICKERS["MOVE"])
    if move is not None and move.dropna().empty:
        move = None
    if move is None:
        src.warn("ICE BofA MOVE (^MOVE)", "不可用，美债 Vega/体制退化为 RV 代理")

    irx = last_valid(closes[C.AUX_TICKERS["IRX"]]) if C.AUX_TICKERS["IRX"] in closes else None
    rf = (irx / 100) if irx is not None else 0.04

    out_assets = []
    cot_dates: list[pd.Timestamp] = []
    chain_dates: list[str] = []
    for a in assets:
        close = closes[a.futures_ticker].dropna()
        # ---- COT -----------------------------------------------------------------
        cot = None
        try:
            cot = fetch_cot(a.cot.dataset, a.cot.code, a.cot.fast_money, a.cot.real_money, cache)
            cot_dates.append(cot.index[-1])
        except Exception as exc:
            src.warn(f"CFTC COT {a.key}", str(exc))

        # ---- option book -----------------------------------------------------------
        book: OptionBook | None = None
        skew_res = gex_res = None
        chain_atm = None
        if not skip_options:
            try:
                book = fetch_option_book(a.option_proxy, cache, max_dte=max(C.GEX_MAX_DTE, C.SKEW_DTE_RANGE[1]))
                if book.error and not book.slices:
                    src.warn(f"{a.option_proxy} 期权链", book.error)
                else:
                    chain_dates.append(book.as_of)
                    skew_res = compute_skew(book, rf)
                    gex_res = compute_gex(book, rf)
                    chain_atm = atm_iv_from_book(book)
                    src.ok(f"{a.option_proxy} 期权链", f"{len(book.slices)} 个到期, OI {int(book.total_oi):,}")
            except Exception as exc:  # never let one ETF kill the run
                log.exception("option book %s", a.option_proxy)
                src.warn(f"{a.option_proxy} 期权链", str(exc))

        # ---- implied-vol series ----------------------------------------------------
        iv_series = None
        if a.iv_index == "MOVE":
            iv_series = None if move is None else move.dropna() * a.iv_index_scale
        elif a.iv_index and a.iv_index in cboe:
            iv_series = cboe[a.iv_index].dropna() * a.iv_index_scale

        term = None
        if a.key == "ES" and all(k in cboe for k in ("VIX", "VIX9D", "VIX3M")):
            v, v9, v3 = (last_valid(cboe[k]) for k in ("VIX", "VIX9D", "VIX3M"))
            term = {
                "vix9d_vix": r(v9 / v, 3) if v else None,
                "vix_vix3m": r(v / v3, 3) if v3 else None,
                "vvix": r(last_valid(cboe["VVIX"])) if "VVIX" in cboe else None,
                "shape": "倒挂(backwardation)" if v3 and v / v3 > 1 else "正常(contango)",
            }

        # ---- scores --------------------------------------------------------------
        reg = signals.vol_regime(a, close, iv_series)
        iv_hist = None if iv_series is not None else load_iv_history(C.HISTORY_DIR, a.key)
        veg = signals.vega(a, close, iv_series, chain_atm, term, iv_hist)
        short = signals.short_delta(a, close, cot, gex_res, reg["code"])
        long_ = signals.long_delta(a, close, cot)
        skew_index = last_valid(cboe["SKEW"]) if (a.key == "ES" and "SKEW" in cboe) else None
        sk = signals.skew(a, skew_res, skew_index)
        flash_dir = sign(short["components"]["flash"]["z"] or 0)
        gam = signals.gamma_regime(a, gex_res, flash_dir)
        ht = signals.heat(short, long_, veg, sk, gam, reg)

        out_assets.append({
            "key": a.key,
            "name": a.name_zh,
            "code_label": a.code_label,
            "instrument": a.instrument,
            "futures_ticker": a.futures_ticker,
            "option_proxy": a.option_proxy,
            "diverge": sign(short["score"]) != sign(long_["score"]),
            "price": r(last_valid(close), 4),
            "price_date": close.index[-1].strftime("%Y-%m-%d"),
            "chg_1d_pct": r((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else None,
            "cot_date": None if cot is None else cot.index[-1].strftime("%Y-%m-%d"),
            "heat": ht,
            "short": short,
            "long": long_,
            "vega": veg,
            "skew": sk,
            "gamma": gam,
            "regime": reg,
            "series": {
                "close": series_tail(close, 90),
                "iv": None if iv_series is None else series_tail(iv_series, 90, 2),
                "fm_net_pct": None if cot is None else series_tail(cot["fm_net_pct"], 52, 2),
                "rm_net_pct": None if cot is None else series_tail(cot["rm_net_pct"], 52, 2),
            },
        })

    as_of_prices = closes.index[-1].strftime("%Y-%m-%d")
    snapshot = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "as_of": {
            "prices": as_of_prices,
            "vol_indices": max((s.dropna().index[-1] for s in cboe.values()), default=closes.index[-1]).strftime("%Y-%m-%d"),
            "cot": max(cot_dates).strftime("%Y-%m-%d") if cot_dates else None,
            "options": max(chain_dates) if chain_dates else None,
        },
        "risk_free": r(rf * 100, 2),
        "sources": src.items,
        "notes": _footer_notes(out_assets),
        "assets": out_assets,
    }
    return snapshot


def _footer_notes(assets: list[dict]) -> dict:
    ups = [a["name"] for a in assets if a["short"]["dot"] == "green"]
    downs = [a["name"] for a in assets if a["short"]["dot"] == "red"]
    neutral_short = sum(1 for a in assets if a["short"]["score"] == 0)
    pinned = sum(1 for a in assets if any("钉住" in o or "维持中性" in o for o in a["short"]["overlays"]))
    structural = [f"{a['name']}{'偏多' if a['long']['score'] > 0 else '偏空'}" for a in assets if a["long"]["structural"]]
    confirmed = [f"{a['name']}{'多' if a['long']['score'] > 0 else '空'}" for a in assets if a["long"]["confirmed"]]
    short_txt = f"Flash 方向：多 {'/'.join(ups) or '—'}；空 {'/'.join(downs) or '—'}。经高频叠加（正Gamma·平静体制钉住 {pinned} 个）后 {neutral_short}/{len(assets)} 为中性"
    long_parts = []
    if confirmed:
        long_parts.append("趋势确认：" + "、".join(confirmed))
    if structural:
        long_parts.append("暂定结构偏向（半档·雷达）：" + "、".join(structural))
    if not long_parts:
        long_parts.append("无方向性长线信号")
    return {"short": short_txt, "long": "；".join(long_parts) + "，非正式配置"}


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------
def write_outputs(snapshot: dict, data_dir: Path) -> dict[str, Path]:
    data_dir = Path(data_dir)
    hist_dir = data_dir / "history"
    hist_dir.mkdir(parents=True, exist_ok=True)
    latest = data_dir / "latest.json"
    latest.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1))
    day = snapshot["as_of"]["prices"]
    hist_file = hist_dir / f"{day}.json"
    hist_file.write_text(json.dumps(snapshot, ensure_ascii=False))
    timeline = build_timeline(hist_dir)
    tl_file = data_dir / "timeline.json"
    tl_file.write_text(json.dumps(timeline, ensure_ascii=False))
    return {"latest": latest, "history": hist_file, "timeline": tl_file}


def load_iv_history(hist_dir: Path, key: str) -> list[float]:
    """Chain-implied ATM IV recorded by previous snapshots (for assets without a vol index)."""
    out: list[float] = []
    for f in sorted(Path(hist_dir).glob("*.json")):
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        for a in snap.get("assets", []):
            if a["key"] == key:
                iv = a.get("vega", {}).get("metrics", {}).get("iv")
                if iv is not None:
                    out.append(float(iv))
    return out


def build_timeline(hist_dir: Path) -> dict:
    """Compact per-day score history used for the sparklines."""
    dates: list[str] = []
    per_asset: dict[str, dict[str, list]] = {}
    for f in sorted(Path(hist_dir).glob("*.json")):
        try:
            snap = json.loads(f.read_text())
        except Exception:
            continue
        dates.append(snap["as_of"]["prices"])
        for a in snap["assets"]:
            slot = per_asset.setdefault(a["key"], {"short": [], "long": [], "vega": [], "skew": [], "gamma": [], "heat": [], "regime": []})
            slot["short"].append(a["short"]["score"])
            slot["long"].append(a["long"]["score"])
            slot["vega"].append(a["vega"]["score"])
            slot["skew"].append(a["skew"]["score"])
            slot["gamma"].append(a["gamma"].get("code"))
            slot["heat"].append(a["heat"]["value"])
            slot["regime"].append(a["regime"]["code"])
    return {"dates": dates, "assets": per_asset}
