
import re
import json
import sys
from pathlib import Path
from collections import Counter

# Add server directory to path to import korean_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.korean_utils import decompose_word, CHOSUNG_LIST, JUNGSUNG_LIST, JONGSUNG_LIST

def process_korean_words():
    file_path = r'c:\workspace\Yeet\server\data\korean_words.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract words from the 'const nouns = [...]' array
    words = re.findall(r"'([^']+)'", content)
    
    print(f"Total words found: {len(words)}")
    
    # Calculate jamo frequency
    jamo_counter = Counter()
    word_data = {}
    
    for word in words:
        # Decompose word into jamos
        jamo_str = decompose_word(word)
        jamo_length = len(jamo_str)
        
        if jamo_length >= 2:  # At least one syllable (초성 + 중성)
            # Store with jamo string as key
            # Score = length for now (will adjust later with weights)
            word_data[jamo_str] = [jamo_length, jamo_length]
            jamo_counter.update(jamo_str)
    
    print(f"Processed {len(word_data)} words into jamo format")
    
    # Save word data
    with open(r'c:\workspace\Yeet\server\data\korean_words.json', 'w', encoding='utf-8') as f:
        json.dump(word_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(word_data)} jamo-decomposed words to korean_words.json")
    
    # Calculate jamo frequencies for tiles
    total_jamos = sum(jamo_counter.values())
    
    # Separate by type
    cho_freq = {j: jamo_counter[j] for j in CHOSUNG_LIST if j in jamo_counter}
    jung_freq = {j: jamo_counter[j] for j in JUNGSUNG_LIST if j in jamo_counter}
    jong_freq = {j: jamo_counter[j] for j in JONGSUNG_LIST[1:] if j in jamo_counter}  # Exclude empty
    
    # Calculate percentages
    cho_weights = {j: round((count / total_jamos) * 100, 2) for j, count in cho_freq.items()}
    jung_weights = {j: round((count / total_jamos) * 100, 2) for j, count in jung_freq.items()}
    jong_weights = {j: round((count / total_jamos) * 100, 2) for j, count in jong_freq.items()}
    
    print("\nTop 10 초성 (Chosung) frequencies:")
    for j, w in sorted(cho_weights.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {j}: {w}%")
    
    print("\nTop 10 중성 (Jungsung) frequencies:")
    for j, w in sorted(jung_weights.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {j}: {w}%")
    
    print("\nTop 10 종성 (Jongsung) frequencies:")
    for j, w in sorted(jong_weights.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {j}: {w}%")
    
    # Save weights
    weights_data = {
        "chosung": cho_weights,
        "jungsung": jung_weights,
        "jongsung": jong_weights
    }
    
    with open(r'c:\workspace\Yeet\server\data\korean_jamo_weights.json', 'w', encoding='utf-8') as f:
        json.dump(weights_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved jamo weights to korean_jamo_weights.json")

if __name__ == "__main__":
    process_korean_words()
