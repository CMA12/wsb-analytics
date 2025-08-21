# Scripts Directory

Production scripts for the Reddit Financial Scraper.

## 🚀 **Two-Phase Architecture Scripts**

### **Phase 1: Fast Data Collection**
```bash
python scripts/scrape_fast.py
```
- Scrapes Reddit posts + comments rapidly (no LLM analysis)
- Stores raw text data in Supabase
- ~40 comments/second processing speed
- No API costs during scraping

### **Phase 2: Batch Analysis**  
```bash
python scripts/analyze_batch.py
```
- Processes stored text with LLM for ticker extraction
- Runs independently on your schedule
- Handles analysis errors gracefully
- Cost-optimized batch processing

## 🗄️ **Database Management**

### **Clear Database**
```bash
python scripts/clear_database.py
```
- Removes all posts, comments, and tickers from Supabase
- Use before fresh scraping runs

### **Schema Migration**
```bash
python scripts/migrate_database.py
```
- Provides SQL commands for adding new database columns
- Run SQL in Supabase dashboard to add hype_score and company_name columns

## 💡 **Usage Pattern**

Run from the root directory:

1. **Clear old data**: `poetry run python scripts/clear_database.py`
2. **Scrape fresh data**: `poetry run python scripts/scrape_fast.py` 
3. **Analyze when ready**: `poetry run python scripts/analyze_batch.py`
4. **Repeat as needed**

Each script runs independently and handles errors gracefully.