"""Tiny on-disk cache so the engine can be re-run offline and stays polite to data providers."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd


class Cache:
    def __init__(self, root: Path, offline: bool = False, max_age_hours: float = 6.0):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.max_age = max_age_hours * 3600

    def _path(self, key: str, ext: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self.root / f"{safe}.{ext}"

    def _fresh(self, p: Path) -> bool:
        if not p.exists():
            return False
        if self.offline:
            return True
        return (time.time() - p.stat().st_mtime) < self.max_age

    # -- DataFrame -----------------------------------------------------------
    def get_df(self, key: str) -> pd.DataFrame | None:
        p = self._path(key, "csv")
        if not self._fresh(p):
            return None
        try:
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            return df
        except Exception:
            return None

    def put_df(self, key: str, df: pd.DataFrame) -> None:
        df.to_csv(self._path(key, "csv"))

    # -- JSON ----------------------------------------------------------------
    def get_json(self, key: str) -> Any | None:
        p = self._path(key, "json")
        if not self._fresh(p):
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def put_json(self, key: str, obj: Any) -> None:
        self._path(key, "json").write_text(json.dumps(obj))

    def stale_df(self, key: str) -> pd.DataFrame | None:
        """Return whatever is on disk regardless of age (fallback when a provider is down)."""
        p = self._path(key, "csv")
        if not p.exists():
            return None
        try:
            return pd.read_csv(p, index_col=0, parse_dates=True)
        except Exception:
            return None

    def stale_json(self, key: str) -> Any | None:
        p = self._path(key, "json")
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
