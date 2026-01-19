import requests
from bs4 import BeautifulSoup
import json
from core.logging_config import get_logger

logger = get_logger(__name__)
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import WORDS_JSON_PATH, DATA_DIR

# 단어들을 웹에서 크롤링 해주는 파이썬 파일
def get_words_from_page(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.find_all('a', class_="btn btn-default radius-0 relative fullwidth h-50 fs-22 fw-600")
        
        page_data = []
        for el in elements:
            word = ""
            for content in el.contents:
                if isinstance(content, str):
                    word = content.strip()
                    if word:
                        break
            if not word: continue
            
            span = el.find('span')
            try:
                score = int(span.get_text().strip()) if span else 0
            except ValueError:
                score = 0
                
            page_data.append((word.lower(), len(word), score))
        return page_data
    except Exception:
        return []

def scrape_words():
    base_url = "https://scrabble123.com/scrabble-twl-dictionary/words-with-letter-/page/{}"
    words_data = {}
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if WORDS_JSON_PATH.exists():
        try:
            with open(WORDS_JSON_PATH, "r", encoding="utf-8") as f:
                words_data = json.load(f)
        except:
            pass

    page = 1
    max_workers = 5
    consecutive_empty = 0
    
    logger.info(f"Starting scrape from {base_url.format(1)}")
    
    while consecutive_empty < 3:
        urls = [base_url.format(p) for p in range(page, page + max_workers)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(get_words_from_page, url): url for url in urls}
            
            new_words_in_batch = 0
            for future in as_completed(future_to_url):
                results = future.result()
                if results:
                    for word, length, score in results:
                        if word not in words_data:
                            words_data[word] = [length, score]
                            new_words_in_batch += 1
            
            if new_words_in_batch == 0:
                consecutive_empty += 1
            else:
                consecutive_empty = 0
            
            page += max_workers
            
        with open(WORDS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(words_data, f, indent=4)
        
        logger.info(f"Processed up to page {page-1}. Total words: {len(words_data)}. New in last batch: {new_words_in_batch}")
        time.sleep(0.3)
        
    logger.info(f"Final count: {len(words_data)} words saved to {WORDS_JSON_PATH}")

if __name__ == "__main__":
    scrape_words()
