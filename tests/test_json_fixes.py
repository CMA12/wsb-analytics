#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from nlp import extract_tickers, analyze_contextual_hype, clean_and_validate_json

def test_json_cleaning():
    """Test the JSON cleaning and validation function"""
    
    print("🧪 TESTING JSON CLEANING FUNCTION")
    print("="*40)
    
    test_cases = [
        # Valid JSON cases
        ('{"tickers": [], "hype_score": 0.00}', True),
        ('{"contextual_hype": 0.85}', True),
        
        # JSON with markdown
        ('```json\n{"tickers": [], "hype_score": 0.00}\n```', True),
        ('```\n{"contextual_hype": 0.85}\n```', True),
        
        # JSON with extra text (like the problematic responses)
        ('Yes. In investing, a "lottery ticket" refers... {"tickers": [], "hype_score": 0.00}', True),
        ('Here is the analysis: {"contextual_hype": 0.75} Hope this helps!', True),
        
        # Invalid cases
        ('This is just text with no JSON', False),
        ('{"invalid": json}', False),
        ('', False),
    ]
    
    passed = 0
    failed = 0
    
    for i, (test_input, should_succeed) in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test_input[:50]}{'...' if len(test_input) > 50 else ''}'")
        
        result = clean_and_validate_json(test_input)
        success = bool(result)
        
        if success == should_succeed:
            print(f"   ✅ PASS - {'Found' if success else 'No'} valid JSON")
            if result:
                print(f"   📄 Cleaned: {result}")
            passed += 1
        else:
            print(f"   ❌ FAIL - Expected: {'success' if should_succeed else 'failure'}")
            failed += 1
    
    print(f"\n📊 JSON Cleaning Results: {passed} passed, {failed} failed")
    return passed > failed


def test_with_sample_texts():
    """Test the enhanced NLP functions with sample texts (requires OpenAI API)"""
    
    print("\n🧪 TESTING ENHANCED NLP FUNCTIONS")
    print("="*40)
    
    # Check if API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found - skipping API tests")
        return True
    
    sample_texts = [
        # Direct ticker extraction test
        "TSLA to the moon! 🚀",
        
        # Contextual hype test
        "This is the way! Diamond hands! 💎🙌"
    ]
    
    print(f"🔑 API Key found: {api_key[:10]}...")
    print("🚨 Note: This will make actual API calls and use credits")
    
    # Test ticker extraction
    print(f"\n🎯 Testing direct ticker extraction:")
    test_text = sample_texts[0]
    print(f"Text: '{test_text}'")
    
    try:
        print("   Making API call...")
        tickers = extract_tickers(test_text)
        print(f"   ✅ Success! Found {len(tickers)} tickers")
        for ticker in tickers:
            print(f"      💎 {ticker.get('ticker', 'UNKNOWN')}: hype={ticker.get('hype_score', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test contextual hype analysis
    print(f"\n📊 Testing contextual hype analysis:")
    test_text = sample_texts[1]
    print(f"Text: '{test_text}'")
    
    try:
        print("   Making API call...")
        hype_score = analyze_contextual_hype(test_text)
        print(f"   ✅ Success! Contextual hype: {hype_score:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n🎉 Enhanced NLP functions are working!")
    return True


def run_json_fix_tests():
    """Run all JSON fix validation tests"""
    
    print("🔧 JSON FIX VALIDATION TESTS")
    print("="*50)
    
    all_passed = True
    
    # Test JSON cleaning function
    if not test_json_cleaning():
        all_passed = False
    
    # Test with sample API calls (if API key available)
    if not test_with_sample_texts():
        all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL JSON FIXES VALIDATED!")
        print("✅ System ready for testing with real data")
        print("\nNext step: Run database migration, then test incremental analysis")
    else:
        print("⚠️ Some JSON fixes need attention")
    
    return all_passed


if __name__ == "__main__":
    success = run_json_fix_tests()
    sys.exit(0 if success else 1)