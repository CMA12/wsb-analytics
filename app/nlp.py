# LLM-based ticker extraction for Reddit financial content
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def llm_extractor(text: str) -> list:
    """
    Extract tickers using LLM with proper confidence scoring and hype analysis.
    
    Returns list of dicts:
    [{"ticker": "TSLA", "span": (0,4), "confidence": 0.95, "method": "llm", "hype_score": 0.87, "company_name": "Tesla Inc."}]
    
    Args:
        text (str): Text content to analyze for tickers
        
    Returns:
        list: List of ticker extraction results with metadata
    """
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    # Load system prompt from file (use app directory path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "resources", "system_prompt.md")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    try:
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages = [
                {"role":"system", "content":system_prompt},
                {"role": "user", "content": text}
                ]
        )

        # Extract the JSON content from response
        llm_response = response.choices[0].message.content.strip()
        
        # Clean up response - remove any markdown code blocks if present
        if llm_response.startswith('```'):
            llm_response = llm_response.split('\n', 1)[1]
        if llm_response.endswith('```'):
            llm_response = llm_response.rsplit('\n', 1)[0]
        
        # Parse JSON response from LLM
        parsed_response = json.loads(llm_response)
        
        # Convert LLM format to existing code format
        results = []
        
        hype_score = parsed_response.get("hype_score", 0.0)
        
        for ticker_info in parsed_response.get("tickers", []):
            symbol = ticker_info.get("symbol", "").upper()
            company_name = ticker_info.get("name", "")
            
            # Find ticker position in original text using improved span detection
            span_start, span_end = find_ticker_span(text, symbol)
            
            # Calculate confidence based on multiple factors
            confidence = calculate_extraction_confidence(symbol, company_name, hype_score, span_start != -1)
            
            results.append({
                "ticker": symbol,
                "span": (span_start, span_end),
                "confidence": confidence,
                "method": "llm",
                "hype_score": hype_score,
                "company_name": company_name
            })
        
        return results
        
    except json.JSONDecodeError as e:
        print(f"[LLM] Failed to parse response as JSON: {e}")
        print(f"[LLM] Raw response: {llm_response}")
        return []
        
    except Exception as e:
        print(f"[LLM] Error during extraction: {e}")
        return []


def find_ticker_span(text: str, ticker: str) -> tuple[int, int]:
    """
    Find the best span position for a ticker in text using multiple strategies.
    
    Args:
        text (str): Original text to search in
        ticker (str): Ticker symbol to find
        
    Returns:
        tuple: (start_pos, end_pos) or (-1, -1) if not found
    """
    if not text or not ticker:
        return (-1, -1)
    
    # Strategy 1: Look for $TICKER format first (most reliable)
    dollar_pattern = rf'\${re.escape(ticker)}\b'
    match = re.search(dollar_pattern, text, re.IGNORECASE)
    if match:
        return (match.start(), match.end())
    
    # Strategy 2: Look for standalone ticker with word boundaries
    word_pattern = rf'\b{re.escape(ticker)}\b'
    match = re.search(word_pattern, text, re.IGNORECASE)
    if match:
        return (match.start(), match.end())
    
    # Strategy 3: Simple case-insensitive find as fallback
    upper_text = text.upper()
    upper_ticker = ticker.upper()
    start = upper_text.find(upper_ticker)
    if start != -1:
        return (start, start + len(ticker))
    
    # Not found
    return (-1, -1)


def calculate_extraction_confidence(ticker: str, company_name: str, hype_score: float, span_found: bool) -> float:
    """
    Calculate extraction confidence based on multiple factors.
    
    Args:
        ticker (str): Ticker symbol
        company_name (str): Company name from LLM
        hype_score (float): Hype score from LLM (not used in confidence calculation)
        span_found (bool): Whether ticker was found in text
        
    Returns:
        float: Confidence score between 0.0 and 1.0
    """
    # Base confidence from LLM response quality
    base_confidence = 0.8
    
    # Adjust based on company name presence (indicates LLM recognition)
    if company_name and company_name.strip():
        base_confidence += 0.1
    
    # Adjust based on ticker length (longer = more specific)
    if len(ticker) <= 2:
        base_confidence -= 0.1  # Short tickers might be false positives
    elif len(ticker) >= 4:
        base_confidence += 0.05  # Longer tickers are more specific
    
    # Penalize if ticker not found in text
    if not span_found:
        base_confidence -= 0.2
    
    # Cap confidence between 0.3 and 1.0
    return max(0.3, min(1.0, base_confidence))


# Main function that the rest of your code calls
def extract_tickers(text: str):
    """
    Main ticker extraction function - uses LLM for intelligent extraction.
    This maintains the same interface so your existing code doesn't break.
    """
    return llm_extractor(text)


if __name__ == "__main__":
    print("\n[LLM Ticker Extraction Test]")
    s = "YOLO $TSLA 300C exp 09/20/2025 🚀🚀 diamond hands. AAPL price target 300."
    for item in extract_tickers(s):
        print(item)