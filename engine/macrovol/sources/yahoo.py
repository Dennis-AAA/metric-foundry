"""Yahoo Finance access through yfinance: daily futures history and ETF option chains."""
from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

from ..cache import Cache

log = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


def fetch_closes(tickers: list[str], cache: Cache, period: str = "3y") -> pd.DataFrame:
    """Daily closes for a list of Yahoo symbols (columns = tickers)."""
    key = "yahoo_closes_" + "_".join(sorted(tickers))
    cached = cache.get_df(key)
    if cached is not None:
        return cached
    if cache.offline:
        raise SourceError("offline and no cached Yahoo closes")
    try:
        raw = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="column",
        )
    except Exception as exc:  # network / provider failure -> fall back to stale cache
        stale = cache.stale_df(key)
        if stale is not None:
            log.warning("Yahoo download failed (%s); using stale cache", exc)
            return stale
        raise SourceError(f"Yahoo download failed: {exc}") from exc
    if raw is None or raw.empty:
        stale = cache.stale_df(key)
        if stale is not None:
            return stale
        raise SourceError("Yahoo returned no data")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": tickers[0]})
    close = close.copy()
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    close = close.sort_index()
    cache.put_df(key, close)
    return close


@dataclass
class ChainSlice:
    expiry: str
    dte: int
    calls: pd.DataFrame
    puts: pd.DataFrame


@dataclass
class OptionBook:
    symbol: str
    spot: float
    as_of: str
    slices: list[ChainSlice] = field(default_factory=list)
    error: str | None = None

    @property
    def total_oi(self) -> float:
        return float(sum(s.calls["openInterest"].sum() + s.puts["openInterest"].sum() for s in self.slices))


_KEEP = ["strike", "bid", "ask", "lastPrice", "impliedVolatility", "openInterest", "volume"]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df[[c for c in _KEEP if c in df.columns]].copy()
    for c in _KEEP:
        if c not in out.columns:
            out[c] = 0.0
    out = out.fillna({"bid": 0.0, "ask": 0.0, "lastPrice": 0.0, "openInterest": 0, "volume": 0})
    out["openInterest"] = out["openInterest"].astype(float)
    return out.reset_index(drop=True)


def fetch_option_book(symbol: str, cache: Cache, max_dte: int = 90, max_expiries: int = 40) -> OptionBook:
    """Pull every listed expiry up to `max_dte` days for an ETF and return a compact book.

    The result is cached for the day as JSON so that repeated runs (and the offline
    mode) do not hammer Yahoo; each expiry is a separate request on their side.
    """
    today = dt.date.today()
    key = f"yahoo_chain_{symbol}_{today:%Y%m%d}"
    cached = cache.get_json(key)
    if cached is None and cache.offline:
        cached = cache.stale_json(key)
        if cached is None:
            # any previous day is better than nothing when offline
            candidates = sorted(cache.root.glob(f"yahoo_chain_{symbol}_*.json"))
            if candidates:
                import json

                cached = json.loads(candidates[-1].read_text())
    if cached is not None:
        return _book_from_json(cached)

    tk = yf.Ticker(symbol)
    book = OptionBook(symbol=symbol, spot=float("nan"), as_of=today.isoformat())
    try:
        expiries = list(tk.options)
    except Exception as exc:
        book.error = f"expiries: {exc}"
        return book
    if not expiries:
        book.error = "no listed expiries"
        return book

    spot = None
    kept = 0
    for exp in expiries:
        exp_date = dt.date.fromisoformat(exp)
        dte = (exp_date - today).days
        if dte <= 0:
            continue
        if dte > max_dte or kept >= max_expiries:
            break
        try:
            ch = tk.option_chain(exp)
        except Exception as exc:
            log.warning("%s %s chain failed: %s", symbol, exp, exc)
            time.sleep(0.5)
            continue
        if spot is None:
            und = getattr(ch, "underlying", None) or {}
            spot = und.get("regularMarketPrice") or und.get("postMarketPrice")
        calls, puts = _clean(ch.calls), _clean(ch.puts)
        if calls.empty and puts.empty:
            continue
        book.slices.append(ChainSlice(expiry=exp, dte=dte, calls=calls, puts=puts))
        kept += 1
        time.sleep(0.15)

    if spot is None:
        try:
            spot = float(tk.fast_info["lastPrice"])
        except Exception:
            spot = float("nan")
    book.spot = float(spot)
    if not book.slices:
        book.error = "no usable expiries"
    cache.put_json(key, _book_to_json(book))
    return book


def _book_to_json(book: OptionBook) -> dict:
    return {
        "symbol": book.symbol,
        "spot": book.spot,
        "as_of": book.as_of,
        "error": book.error,
        "slices": [
            {
                "expiry": s.expiry,
                "dte": s.dte,
                "calls": s.calls.to_dict(orient="list"),
                "puts": s.puts.to_dict(orient="list"),
            }
            for s in book.slices
        ],
    }


def _book_from_json(obj: dict) -> OptionBook:
    book = OptionBook(symbol=obj["symbol"], spot=float(obj["spot"]), as_of=obj["as_of"], error=obj.get("error"))
    for s in obj.get("slices", []):
        book.slices.append(
            ChainSlice(expiry=s["expiry"], dte=int(s["dte"]), calls=pd.DataFrame(s["calls"]), puts=pd.DataFrame(s["puts"]))
        )
    return book
