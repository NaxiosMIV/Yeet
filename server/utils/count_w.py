import json
import sys
from core.logging_config import get_logger

logger = get_logger(__name__)
from core.config import DATA_DIR, WORDS_JSON_PATH

def count_words():
    total_words = 0
    
    # Check specifically for the main dictionary file
    if WORDS_JSON_PATH.exists():
        try:
            with open(WORDS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                total_words = len(data.keys())
        except Exception as e:
            logger.error(f"Error reading {WORDS_JSON_PATH.name}: {e}")
    else:
        # Fallback: count all json files in data dir
        for file_path in DATA_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_words += len(data.keys())
            except Exception as e:
                logger.error(f"Error reading {file_path.name}: {e}")

    logger.info(f"TOTAL_WORDS: {total_words}")
    return total_words

if __name__ == "__main__":
    count_words()
