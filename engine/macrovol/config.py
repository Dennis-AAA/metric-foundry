"""Asset universe, data-source mapping and scoring thresholds.

Everything the dashboard shows is derived from the parameters in this file, so
tuning the framework (thresholds, look-backs, proxies) only requires edits here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
HISTORY_DIR = DATA_DIR / "history"


@dataclass(frozen=True)
class CotSpec:
    """CFTC Commitments of Traders mapping for one contract."""

    dataset: str  # "tff" (Traders in Financial Futures) or "disagg" (Disaggregated)
    code: str  # CFTC contract market code
    fast_money: str  # column family used as "FM" (short-horizon speculators)
    real_money: str  # column family used as "RM" (slow institutional money)


@dataclass(frozen=True)
class AssetSpec:
    key: str
    name_zh: str  # 大类 label
    code_label: str  # small label next to the name (ES / ZN / 期货 ...)
    instrument: str  # description of the priced instrument
    futures_ticker: str  # Yahoo Finance futures symbol used for the DELTA columns
    option_proxy: str  # liquid ETF whose listed options approximate the dealer book
    iv_index: str | None  # CBOE / ICE implied-vol index (None -> use ATM IV from chain)
    iv_index_scale: float  # multiplier to convert the index into %-price-vol of the future
    cot: CotSpec
    rr_baseline: float  # "normal" 25-delta risk reversal / ATM IV for the asset
    long_label: str  # wording for a positive direction score
    short_label: str  # wording for a negative direction score
    tags: tuple[str, ...] = field(default_factory=tuple)


ASSETS: list[AssetSpec] = [
    AssetSpec(
        key="ES",
        name_zh="美股",
        code_label="ES",
        instrument="E-mini S&P 500 期货 (ES)",
        futures_ticker="ES=F",
        option_proxy="SPY",
        iv_index="VIX",
        iv_index_scale=1.0,
        cot=CotSpec("tff", "13874A", "lev_money", "asset_mgr"),
        rr_baseline=-0.30,
        long_label="多",
        short_label="空",
    ),
    AssetSpec(
        key="ZN",
        name_zh="美债",
        code_label="ZN",
        instrument="10年期美债期货 (ZN, 价格方向)",
        futures_ticker="ZN=F",
        option_proxy="TLT",
        iv_index="MOVE",
        # MOVE is annualised bp yield vol; ZN modified duration ~6.5 -> price vol% ~ MOVE * 0.065
        iv_index_scale=0.065,
        cot=CotSpec("tff", "043602", "lev_money", "asset_mgr"),
        rr_baseline=-0.08,
        long_label="多",
        short_label="空",
    ),
    AssetSpec(
        key="EUR",
        name_zh="EUR",
        code_label="期货",
        instrument="欧元期货 (6E, EURUSD 方向)",
        futures_ticker="6E=F",
        option_proxy="FXE",
        iv_index=None,  # CBOE EVZ was discontinued in Mar-2025
        iv_index_scale=1.0,
        cot=CotSpec("tff", "099741", "lev_money", "asset_mgr"),
        rr_baseline=-0.02,
        long_label="多EUR",
        short_label="空EUR",
    ),
    AssetSpec(
        key="JPY",
        name_zh="JPY",
        code_label="期货",
        instrument="日元期货 (6J, JPY 升值 = 多)",
        futures_ticker="6J=F",
        option_proxy="FXY",
        iv_index=None,
        iv_index_scale=1.0,
        cot=CotSpec("tff", "097741", "lev_money", "asset_mgr"),
        rr_baseline=0.05,  # JPY calls (USD puts) are usually bid: safe-haven skew
        long_label="多JPY",
        short_label="空JPY",
    ),
    AssetSpec(
        key="GC",
        name_zh="黄金",
        code_label="GC",
        instrument="COMEX 黄金期货 (GC)",
        futures_ticker="GC=F",
        option_proxy="GLD",
        iv_index="GVZ",
        iv_index_scale=1.0,
        cot=CotSpec("disagg", "088691", "m_money", "swap"),
        rr_baseline=0.05,
        long_label="多",
        short_label="空",
    ),
    AssetSpec(
        key="CL",
        name_zh="WTI",
        code_label="CL",
        instrument="NYMEX WTI 原油期货 (CL)",
        futures_ticker="CL=F",
        option_proxy="USO",
        iv_index="OVX",
        iv_index_scale=1.0,
        cot=CotSpec("disagg", "067651", "m_money", "swap"),
        rr_baseline=0.0,
        long_label="多",
        short_label="空",
    ),
]

ASSET_BY_KEY = {a.key: a for a in ASSETS}

# Yahoo symbols downloaded alongside the futures (auxiliary series).
AUX_TICKERS = {
    "MOVE": "^MOVE",  # ICE BofA MOVE (only public daily source is Yahoo)
    "IRX": "^IRX",  # 13-week T-bill yield -> risk-free rate for Greeks
}

# CBOE publishes full daily history as CSV; these are the primary IV/term-structure inputs.
CBOE_INDICES = ["VIX", "VIX9D", "VIX3M", "VVIX", "SKEW", "GVZ", "OVX"]

# Socrata datasets on publicreporting.cftc.gov (futures-only reports).
CFTC_DATASETS = {
    "tff": "gpe5-46if",
    "disagg": "72hh-3qpy",
}

# ---------------------------------------------------------------------------
# Scoring parameters
# ---------------------------------------------------------------------------
LOOKBACK_1Y = 252
LOOKBACK_2Y = 504

# 短线 DELTA (1-4 weeks)
FLASH_RET_DAYS = 10
FLASH_Z_T1, FLASH_Z_T2 = 0.75, 1.5
FM_FLOW_WEEKS = 4
SHORT_WEIGHTS = {"flash": 0.5, "fm": 0.3, "gamma": 0.2}
SHORT_PIN_THRESHOLD = 1.25  # |raw| below this is pulled to neutral when dealers are long gamma in a calm regime

# 长线 DELTA (1-3 months)
CONFIRM_RET_DAYS = 63
RM_FLOW_WEEKS = 13
FV_Z_T1, FV_Z_T2 = 1.5, 3.0
LONG_WEIGHTS = {"confirmed": 0.4, "rm": 0.3, "fv": 0.3}

# VEGA
RV_WINDOW = 20
IV_PCT_CHEAP, IV_PCT_VERY_CHEAP = 25, 10
IV_PCT_RICH, IV_PCT_VERY_RICH = 75, 90
CARRY_CHEAP, CARRY_RICH = -0.10, 0.30  # (IV-RV)/RV thresholds

# SKEW (25-delta risk reversal normalised by ATM IV)
SKEW_TARGET_DTE = 45
SKEW_DTE_RANGE = (21, 90)
RR_NEUTRAL_BAND = 0.05
RR_STRONG = 0.25
RR_BASELINE_WARN = 0.10  # deviation from the asset's normal skew that triggers ⚠ while label is neutral

# GAMMA (dealer gamma exposure from the ETF option book)
GEX_MAX_DTE = 60
GEX_FLIP_BAND_PCT = 1.0  # spot within ±1% of the flip -> 初起 (transition)
GEX_RATIO_BAND = 0.15  # |net / gross| below this -> book is balanced -> 初起 (transition)
GEX_MIN_OI = 20_000  # total OI below this -> proxy is too thin, flag ⚠

# VOL regime
REGIME_HIGH_PCT = 70
REGIME_LOW_PCT = 40
REGIME_VOV_PCT = 75
REGIME_TURN_CHANGE = 0.15  # +15% IV in 5 days from a low base -> 低Vol转折
