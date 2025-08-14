# regex for filtering irrelevant posts and comments
import re

#load blacklist / whitelist / WSB jargon abbr.
def load_set(path: str) -> set:
    items = set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    items.add(line)
    except FileNotFoundError:
        pass
    return items


# compile once
UPPER_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
DOLLAR_TICKER_RE = re.compile(r"\$[A-Za-z]{1,5}\b")

# load resources
TICKERS = load_set("resources/tickers.txt")
STOP = load_set("resources/stoplist.txt")

FIN_CUES = set()
try:
    with open("resources/finance_cues.txt", "r", encoding="utf-8") as f:
        FIN_CUES = {ln.strip().lower() for ln in f if ln.strip()}
except FileNotFoundError:
    pass

def _nearby_cues(lower_text: str, start: int, end: int, window: int = 30) -> int:
    """Count finance cues within ±window characters around a span."""
    L = max(0, start - window)
    R = min(len(lower_text), end + window)
    chunk = lower_text[L:R]
    return sum(1 for cue in FIN_CUES if cue and cue in chunk)


# extract tickesr and stoplist
def extract_tickers(text: str):
    """
    Return a list of dicts:
      { 'ticker': 'TSLA', 'span': (start, end), 'confidence': float, 'method': 'dollar'|'regex' }
    Confidence heuristic (v1):
      - base 0.90 for $TICKER
      - base 0.60 for bare uppercase, +0.03 per nearby finance cue (±30 chars), capped
    """
    if not text:
        return []

    lower = text.lower()
    results = {}

    # $TICKER (precise)
    for m in DOLLAR_TICKER_RE.finditer(text):
        t = m.group()[1:].upper()
        if t in TICKERS and t not in STOP:
            cues = _nearby_cues(lower, m.start(), m.end())
            conf = 0.90 + min(cues * 0.02, 0.10)  # 0.90–1.00
            key = (t, m.start(), m.end())
            results[key] = {
                "ticker": t,
                "span": (m.start(), m.end()),
                "confidence": round(conf, 3),
                "method": "dollar",
            }

    # bare uppercase (need at least one cue)
    for m in UPPER_TICKER_RE.finditer(text):
        t = m.group().upper()
        if t in TICKERS and t not in STOP:
            cues = _nearby_cues(lower, m.start(), m.end())
            if cues > 0:
                conf = 0.60 + min(cues * 0.03, 0.15)  # 0.60–0.75
                key = (t, m.start(), m.end())
                # prefer dollar if both match same span
                if key not in results:
                    results[key] = {
                        "ticker": t,
                        "span": (m.start(), m.end()),
                        "confidence": round(conf, 3),
                        "method": "regex",
                    }

    # return sorted by confidence desc, then ticker
    return sorted(results.values(), key=lambda d: (-d["confidence"], d["ticker"]))



if __name__ == "__main__":
    print("\n[detailed tests]")
    s = "YOLO $TSLA 300C exp 09/20/2025 🚀🚀 diamond hands. AAPL price target 300."
    for item in extract_tickers(s):
        print(item)


