# LLM-based ticker extraction for Reddit financial content
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def clean_and_validate_json(response: str) -> str:
    """
    Clean and validate JSON response from LLM, handling common formatting issues.
    
    Args:
        response (str): Raw response from LLM
        
    Returns:
        str: Cleaned JSON string, or empty string if invalid
    """
    if not response:
        return ""
    
    # Remove common prefixes and suffixes
    response = response.strip()
    
    # Remove markdown code blocks
    if response.startswith('```json'):
        response = response[7:]
    elif response.startswith('```'):
        response = response[3:]
    
    if response.endswith('```'):
        response = response[:-3]
    
    response = response.strip()
    
    # Try to extract JSON from response if it contains other text
    json_start = response.find('{')
    json_end = response.rfind('}') + 1
    
    if json_start != -1 and json_end > json_start:
        potential_json = response[json_start:json_end]
        
        # Validate it's actually JSON
        try:
            json.loads(potential_json)
            return potential_json
        except json.JSONDecodeError:
            pass
    
    # Try the full response as JSON
    try:
        json.loads(response)
        return response
    except json.JSONDecodeError:
        return ""


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

    # Try up to 2 times to get valid JSON
    for attempt in range(2):
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
            
            # Clean up response and validate JSON
            cleaned_response = clean_and_validate_json(llm_response)
            if not cleaned_response:
                if attempt == 0:
                    print(f"[LLM] Attempt {attempt + 1} failed, retrying...")
                    continue
                else:
                    print(f"[LLM] Failed to extract valid JSON after {attempt + 1} attempts: {llm_response[:200]}...")
                    return []
            
            # Parse JSON response from LLM
            parsed_response = json.loads(cleaned_response)
            break  # Success, exit retry loop
            
        except json.JSONDecodeError as e:
            if attempt == 0:
                print(f"[LLM] JSON parse error on attempt {attempt + 1}, retrying...")
                continue
            else:
                print(f"[LLM] Failed to parse JSON after {attempt + 1} attempts: {e}")
                return []
        except Exception as e:
            print(f"[LLM] Error during extraction: {e}")
            return []
    
    # Convert LLM format to existing code format (only reached if parsing succeeded)
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


def analyze_contextual_hype(text: str) -> float:
    """
    Analyze text for contextual hype sentiment without requiring ticker mentions.
    Used for inheriting tickers from post context when comments don't mention tickers directly.
    
    Args:
        text (str): Text content to analyze for hype sentiment
        
    Returns:
        float: Contextual hype score between 0.0 and 1.0
    """
    if not text or len(text.strip()) < 3:
        return 0.0
    
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    contextual_prompt = """CRITICAL: You must respond with ONLY valid JSON. No explanations, no commentary, no additional text.

Task: Analyze Reddit comment text for financial hype sentiment (without requiring ticker mentions).

Analyze for excitement/support that could apply to financial investments:
- Positive sentiment and excitement (🚀, moon, diamond hands, LFG, etc.)
- Supporting language ("This is the way", "I'm in", "Let's go")  
- Emotional investment language ("YOLO", "all in", "diamond hands")
- Enthusiastic punctuation (!!!, ALL CAPS)
- Emoji usage that suggests excitement

Ignore negative sentiment, neutral discussion, off-topic content.

MANDATORY: Return ONLY this exact JSON format:
{"contextual_hype": 0.XX}

Score scale:
0.00-0.29: No hype/neutral/negative
0.30-0.49: Mild positive sentiment
0.50-0.69: Moderate excitement
0.70-0.89: High enthusiasm
0.90-1.00: Extreme hype

Examples:
Input: "This is the way! Diamond hands 💎🙌"
Output: {"contextual_hype": 0.85}

Input: "Not sure about this trade"
Output: {"contextual_hype": 0.10}

REMEMBER: ONLY return the JSON object. NO other text."""

    # Try up to 2 times to get valid JSON
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": contextual_prompt},
                    {"role": "user", "content": text}
                ]
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # Clean up response and validate JSON
            cleaned_response = clean_and_validate_json(llm_response)
            if not cleaned_response:
                if attempt == 0:
                    print(f"[CONTEXTUAL] Attempt {attempt + 1} failed, retrying...")
                    continue
                else:
                    print(f"[CONTEXTUAL] Failed to extract valid JSON after {attempt + 1} attempts: {llm_response[:200]}...")
                    return 0.0
            
            # Parse JSON response
            parsed_response = json.loads(cleaned_response)
            contextual_hype = parsed_response.get("contextual_hype", 0.0)
            
            # Ensure score is in valid range
            return max(0.0, min(1.0, float(contextual_hype)))
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 0:
                print(f"[CONTEXTUAL] Parse error on attempt {attempt + 1}, retrying...")
                continue
            else:
                print(f"[CONTEXTUAL] Failed to parse hype analysis after {attempt + 1} attempts: {e}")
                return 0.0
        except Exception as e:
            print(f"[CONTEXTUAL] Error during hype analysis: {e}")
            return 0.0


def inherit_tickers_with_context(post_tickers: list, contextual_hype: float, post_reddit_id: str) -> list:
    """
    Create inherited ticker records from post context with contextual hype scoring.
    
    Args:
        post_tickers (list): List of ticker dicts from the post
        contextual_hype (float): Contextual hype score from comment analysis  
        post_reddit_id (str): Reddit ID of the source post
        
    Returns:
        list: List of inherited ticker records
    """
    if not post_tickers or contextual_hype < 0.3:  # Threshold for inheritance
        return []
    
    inherited_results = []
    
    for ticker_data in post_tickers:
        # Create inherited ticker with contextual hype
        inherited_ticker = {
            "ticker": ticker_data.get("ticker", "").upper(),
            "span": (-1, -1),  # No span for inherited tickers
            "confidence": min(0.75, contextual_hype + 0.2),  # Cap at 0.75 for inherited
            "method": "contextual_inheritance",
            "hype_score": contextual_hype,
            "company_name": ticker_data.get("company_name", ""),
            "inheritance_source": "post_context",
            "context_post_id": post_reddit_id
        }
        inherited_results.append(inherited_ticker)
    
    return inherited_results


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