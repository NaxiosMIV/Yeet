import json
from server.core.config import DATA_DIR, WORDS_JSON_PATH

def count_words():
    total_words = 0
    
    # Check specifically for the main dictionary file
    if WORDS_JSON_PATH.exists():
        try:
            with open(WORDS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                total_words = len(data.keys())
        except Exception as e:
            print(f"Error reading {WORDS_JSON_PATH.name}: {e}")
    else:
        # Fallback: count all json files in data dir
        for file_path in DATA_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_words += len(data.keys())
            except Exception as e:
                print(f"Error reading {file_path.name}: {e}")

    print(f"TOTAL_WORDS: {total_words}")
    return total_words

if __name__ == "__main__":
    count_words()
