# Tests Directory

Test scripts for development and validation.

## 🧪 **Available Tests**

### **LLM Extraction Testing**
```bash
poetry run python tests/test_extraction.py
```
- Tests LLM ticker extraction directly
- Validates extraction accuracy
- Quick feedback on NLP performance

### **Scraping Integration Tests**
```bash
poetry run python tests/test_scraping.py
```
- Tests Reddit API integration
- Validates database storage
- Includes both simple and targeted scraping tests

### **Batch Analysis Testing**
```bash
poetry run python tests/test_batch_analysis.py
```
- Tests batch analysis functionality
- Validates two-phase architecture
- Limited scope for fast testing

## 🔧 **Development Usage**

Run tests during development to ensure:
- ✅ Reddit API connection works
- ✅ LLM extraction functions correctly  
- ✅ Database operations succeed
- ✅ Two-phase architecture operates properly

Tests use limited data to avoid long execution times and high API costs.