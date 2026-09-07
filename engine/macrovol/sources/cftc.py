"""CFTC Commitments of Traders via the public Socrata API (no key required).

Traders in Financial Futures (TFF) covers ES / ZN / 6E / 6J with Dealer, Asset Manager,
Leveraged Funds and Other Reportables; the Disaggregated report covers GC / CL with
Producer, Swap Dealer, Managed Money and Other Reportables.
"""
from __future__ import annotations

import logging

import pandas as pd
import requests

from ..cache import Cache
from ..config import CFTC_DATASETS

log = logging.getLogger(__name__)

BASE = "https://publicreporting.cftc.gov/resource/{dataset}.json"

# Socrata column names are inconsistent (`_all` suffix present on some families only),
# so every family lists the candidates in order of preference.
_COLUMN_CANDIDATES = {
    "lev_money": (["lev_money_positions_long_all", "lev_money_positions_long"],
                  ["lev_money_positions_short_all", "lev_money_positions_short"]),
    "asset_mgr": (["asset_mgr_positions_long_all", "asset_mgr_positions_long"],
                  ["asset_mgr_positions_short_all", "asset_mgr_positions_short"]),
    "dealer": (["dealer_positions_long_all", "dealer_positions_long"],
               ["dealer_positions_short_all", "dealer_positions_short"]),
    "m_money": (["m_money_positions_long_all", "m_money_positions_long"],
                ["m_money_positions_short_all", "m_money_positions_short"]),
    "swap": (["swap_positions_long_all", "swap_positions_long"],
             ["swap__positions_short_all", "swap_positions_short_all", "swap__positions_short", "swap_positions_short"]),
    "prod_merc": (["prod_merc_positions_long_all", "prod_merc_positions_long"],
                  ["prod_merc_positions_short_all", "prod_merc_positions_short"]),
    "other_rept": (["other_rept_positions_long_all", "other_rept_positions_long"],
                   ["other_rept_positions_short_all", "other_rept_positions_short"]),
}


def _pick(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for c in candidates:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce")
    raise KeyError(f"none of {candidates} in COT response")


def fetch_cot(dataset: str, code: str, fast_money: str, real_money: str, cache: Cache,
              weeks: int = 260, timeout: int = 30) -> pd.DataFrame:
    """Weekly positioning table indexed by report date.

    Columns: oi, fm_long, fm_short, fm_net, rm_long, rm_short, rm_net (contracts) and
    fm_net_pct / rm_net_pct (net as % of open interest).
    """
    key = f"cftc_{dataset}_{code}"
    cached = cache.get_df(key)
    if cached is None and not cache.offline:
        params = {
            "cftc_contract_market_code": code,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": str(weeks),
        }
        try:
            resp = requests.get(BASE.format(dataset=CFTC_DATASETS[dataset]), params=params, timeout=timeout)
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                raise RuntimeError("empty response")
            raw = pd.DataFrame(rows)
            fm_l, fm_s = _COLUMN_CANDIDATES[fast_money]
            rm_l, rm_s = _COLUMN_CANDIDATES[real_money]
            out = pd.DataFrame({
                "oi": pd.to_numeric(raw["open_interest_all"], errors="coerce"),
                "fm_long": _pick(raw, fm_l),
                "fm_short": _pick(raw, fm_s),
                "rm_long": _pick(raw, rm_l),
                "rm_short": _pick(raw, rm_s),
            })
            out.index = pd.to_datetime(raw["report_date_as_yyyy_mm_dd"]).dt.normalize()
            out.index.name = "report_date"
            out = out.sort_index()
            out = out[~out.index.duplicated(keep="last")]
            cache.put_df(key, out)
            cached = out
        except Exception as exc:
            log.warning("CFTC %s/%s failed (%s); trying stale cache", dataset, code, exc)
            cached = cache.stale_df(key)
    if cached is None:
        cached = cache.stale_df(key)
    if cached is None:
        raise RuntimeError(f"no COT data for {dataset}/{code}")
    df = cached.copy()
    df["fm_net"] = df["fm_long"] - df["fm_short"]
    df["rm_net"] = df["rm_long"] - df["rm_short"]
    df["fm_net_pct"] = 100 * df["fm_net"] / df["oi"]
    df["rm_net_pct"] = 100 * df["rm_net"] / df["oi"]
    return df
