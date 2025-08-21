#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from nlp import extract_tickers

# Test with a WSB-style comment
test_text = "YOLO'd my entire 401k into TSLA 420C expiring Friday. Diamond hands or food stamps. Papa Elon take me to Mars 🚀🚀🚀"

print("Testing LLM ticker extraction...")
print(f"Input: {test_text}")
print()

try:
    results = extract_tickers(test_text)
    print("Results:")
    for result in results:
        print(f"  Ticker: {result['ticker']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Hype Score: {result.get('hype_score', 'N/A')}")
        print(f"  Method: {result['method']}")
        print(f"  Company: {result.get('company_name', 'N/A')}")
        print()
        
except Exception as e:
    print(f"Error: {e}")