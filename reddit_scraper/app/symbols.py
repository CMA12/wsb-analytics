# app/symbols.py
from __future__ import annotations
from pathlib import Path
import json
from typing import Iterable, Set, Optional
import threading
import time

_CACHE_PATH = Path("app/resources/symbols_cache.json")
_LOCK = threading.Lock()
_STORE_SINGLETON = None

class SymbolStore:
    """
    Holds an uppercase set of valid symbols (e.g., AAPL, BRK.B).
    """
    def __init__(self) -> None:
        self._symbols: Set[str] = set()
        self.updated_at: Optional[float] = None

    def add_many(self, symbols: Iterable[str]) -> None:
        for s in symbols:
            if not s:
                continue
            s = s.strip().upper()
            # filter weird ones; allow dot-class e.g., BRK.B
            if 1 <= len(s) <= 6 and all(ch.isalpha() or ch == "." for ch in s):
                self._symbols.add(s)

    def is_valid(self, ticker: str) -> bool:
        if not ticker:
            return False
        return ticker.strip().upper() in self._symbols

    def count(self) -> int:
        return len(self._symbols)

    def load_from_cache(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self._symbols = set(x.upper() for x in data.get("symbols", []))
        self.updated_at = data.get("updated_at")

    def save_cache(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "symbols": sorted(self._symbols),
            "updated_at": time.time(),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

def get_symbol_store() -> SymbolStore:
    """
    Lazy singleton that loads from cache once.
    """
    global _STORE_SINGLETON
    with _LOCK:
        if _STORE_SINGLETON is None:
            store = SymbolStore()
            store.load_from_cache(_CACHE_PATH)
            _STORE_SINGLETON = store
        return _STORE_SINGLETON
