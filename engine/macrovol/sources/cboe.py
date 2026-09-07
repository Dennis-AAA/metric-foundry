"""CBOE daily index history (VIX, VIX9D, VIX3M, VVIX, SKEW, GVZ, OVX) as CSV."""
from __future__ import annotations

import io
import logging

import pandas as pd
import requests

from ..cache import Cache

log = logging.getLogger(__name__)

URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{name}_History.csv"


def fetch_cboe_index(name: str, cache: Cache, timeout: int = 30) -> pd.Series:
    key = f"cboe_{name}"
    cached = cache.get_df(key)
    if cached is None and not cache.offline:
        try:
            resp = requests.get(URL.format(name=name), timeout=timeout, headers={"User-Agent": "macrovol/0.1"})
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip().upper() for c in df.columns]
            date_col = df.columns[0]
            value_col = "CLOSE" if "CLOSE" in df.columns else df.columns[-1]
            out = pd.DataFrame({"close": pd.to_numeric(df[value_col], errors="coerce").values},
                               index=pd.to_datetime(df[date_col], format="%m/%d/%Y", errors="coerce"))
            out = out[~out.index.isna()].sort_index()
            out.index.name = "date"
            cache.put_df(key, out)
            cached = out
        except Exception as exc:
            log.warning("CBOE %s failed (%s); trying stale cache", name, exc)
            cached = cache.stale_df(key)
    if cached is None:
        cached = cache.stale_df(key)
    if cached is None:
        raise RuntimeError(f"no data for CBOE {name}")
    s = cached["close"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s
