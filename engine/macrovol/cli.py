"""Command line entry point.

    python -m macrovol.cli run            # daily refresh -> data/latest.json
    python -m macrovol.cli run --mode weekly
    python -m macrovol.cli run --offline  # rebuild from cached raw data only
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .cache import Cache
from .config import ASSET_BY_KEY, CACHE_DIR, DATA_DIR
from .snapshot import build_snapshot, write_outputs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="macrovol", description="Direction x volatility signal engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="fetch data, score every asset and write the snapshot JSON")
    run.add_argument("--mode", choices=["daily", "weekly"], default="daily",
                     help="label stored in the snapshot (weekly runs are meant for the Friday COT release)")
    run.add_argument("--out", type=Path, default=DATA_DIR, help="output directory (default: <repo>/data)")
    run.add_argument("--assets", nargs="*", help="subset of asset keys, e.g. ES ZN")
    run.add_argument("--offline", action="store_true", help="use cached raw data only, no network")
    run.add_argument("--skip-options", action="store_true", help="skip option chains (faster; Skew/Gamma become 无数据)")
    run.add_argument("--intraday", action="store_true", help="keep today's partially completed session")
    run.add_argument("--cache-hours", type=float, default=6.0, help="reuse cached raw data younger than this")
    run.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="raw provider cache (default: <repo>/data/cache)")
    run.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("yfinance", "urllib3", "peewee", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    cache = Cache(args.cache_dir, offline=args.offline, max_age_hours=args.cache_hours)
    assets = None
    if args.assets:
        unknown = [k for k in args.assets if k not in ASSET_BY_KEY]
        if unknown:
            print(f"unknown asset keys: {unknown}", file=sys.stderr)
            return 2
        assets = [ASSET_BY_KEY[k] for k in args.assets]

    snap = build_snapshot(cache, mode=args.mode, assets=assets, skip_options=args.skip_options, intraday=args.intraday)
    paths = write_outputs(snap, args.out)
    print(f"as_of prices={snap['as_of']['prices']} cot={snap['as_of']['cot']} options={snap['as_of']['options']}")
    for a in snap["assets"]:
        print(f"  {a['key']:<4} 短 {a['short']['label']:<12} 长 {a['long']['label']:<14} Vega {a['vega']['label']:<6} "
              f"Skew {a['skew']['label']:<8} Gamma {a['gamma']['label']:<10} 体制 {a['regime']['label']:<8} heat {a['heat']['value']}")
    for s in snap["sources"]:
        if s["status"] != "ok":
            print(f"  [{s['status']}] {s['name']}: {s['detail']}")
    print(f"wrote {paths['latest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
