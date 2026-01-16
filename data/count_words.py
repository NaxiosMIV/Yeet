import json
import os

data_dir = r"c:\workspace\Yeet\data"
total_words = 0

for filename in os.listdir(data_dir):
    if filename.endswith(".json"):
        file_path = os.path.join(data_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                total_words += len(data.keys())
        except Exception as e:
            print(f"Error reading {filename}: {e}")

print(f"TOTAL_WORDS:{total_words}")
