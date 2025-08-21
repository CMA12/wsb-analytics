#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

print("Testing imports after refactoring...")

try:
    from nlp import extract_tickers
    print("✅ nlp.py imported successfully")
    
    from db import supabase
    print("✅ db.py imported successfully")
    
    from symbols import get_symbol_store
    print("✅ symbols.py imported successfully")
    
    print("\n🎉 All imports working correctly after refactoring!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()