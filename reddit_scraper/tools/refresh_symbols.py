import pandas as pd
from pathlib import Path
import json

SRC_DIR = Path("app/resources/symbol_sources")
CACHE_PATH = Path("app/resources/symbols_cache.json")

def load_symbols_from_csv(path: Path) -> set:
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return set()

    # Find the column containing symbols
    cols = [c for c in df.columns if c.strip().lower() in ("symbol", "ticker", "code")]
    if not cols:
        print(f"No symbol column found in {path}")
        return set()

    col = cols[0]
    syms = set()
    for sym in df[col].dropna():
        s = str(sym).strip().upper()
        # Allow dot-class like BRK.B but filter out weird junk
        if s and all(ch.isalpha() or ch == "." for ch in s):
            syms.add(s)
    return syms

def main():
    all_syms = set()
    for csv_path in SRC_DIR.glob("*.csv"):
        syms = load_symbols_from_csv(csv_path)
        print(f"{csv_path.name}: loaded {len(syms)} symbols")
        all_syms.update(syms)

    print(f"Total unique symbols: {len(all_syms)}")
    CACHE_PATH.write_text(json.dumps(sorted(all_syms)), encoding="utf-8")
    print(f"Saved to {CACHE_PATH}")

if __name__ == "__main__":
    main()
