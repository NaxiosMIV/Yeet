import random
from typing import List
import json
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger(__name__)

# English Letter Frequency (approximate percentage)
LETTER_WEIGHTS = {
    'E': 12.02, 'T': 9.10, 'A': 8.12, 'O': 7.68, 'I': 7.31, 'N': 6.95,
    'S': 6.28, 'R': 6.02, 'H': 5.92, 'D': 4.32, 'L': 3.98, 'U': 2.88,
    'C': 2.71, 'M': 2.61, 'F': 2.30, 'Y': 2.11, 'W': 2.09, 'G': 2.03,
    'P': 1.82, 'B': 1.49, 'V': 1.11, 'K': 0.69, 'X': 0.17, 'Q': 0.11,
    'J': 0.10, 'Z': 0.07
}

# Load Korean jamo weights
KOREAN_JAMO_WEIGHTS = None

def load_korean_weights():
    global KOREAN_JAMO_WEIGHTS
    if KOREAN_JAMO_WEIGHTS is None:
        weights_path = Path(__file__).parent.parent / 'data' / 'korean_jamo_weights.json'
        if weights_path.exists():
            with open(weights_path, 'r', encoding='utf-8') as f:
                KOREAN_JAMO_WEIGHTS = json.load(f)
        else:
            # Fallback to basic weights if file doesn't exist
            KOREAN_JAMO_WEIGHTS = {
                "chosung": {"ㅇ": 10.9, "ㄱ": 9.01, "ㄴ": 6.45, "ㄹ": 5.93, "ㅅ": 5.29},
                "jungsung": {"ㅏ": 7.79, "ㅣ": 5.4, "ㅗ": 4.82, "ㅜ": 4.54, "ㅓ": 4.05},
                "jongsung": {"ㄴ": 4.0, "ㅇ": 3.5, "ㄹ": 3.0, "ㄱ": 2.5}
            }
    return KOREAN_JAMO_WEIGHTS

def generate_weighted_tiles(count: int, lang: str = 'en') -> List[str]:
    """
    Generates a list of random letters/jamos based on their frequency in the given language.
    """
    if lang == 'ko':
        # Korean: Generate mix of 초성, 중성, 종성
        weights = load_korean_weights()
        
        # Determine distribution: ~40% 초성, ~40% 중성, ~20% 종성
        # This ensures players can form syllables (need cho+jung, optional jong)
        cho_count = int(count * 0.4)
        jung_count = int(count * 0.4)
        jong_count = count - cho_count - jung_count
        
        logger.debug(f"cho_count: {cho_count}, jung_count: {jung_count}, jong_count: {jong_count}")

        tiles = []
        
        # Generate 초성 tiles
        cho_jamos = list(weights['chosung'].keys())
        cho_weights = list(weights['chosung'].values())
        tiles.extend(random.choices(cho_jamos, weights=cho_weights, k=cho_count))
        
        # Generate 중성 tiles
        jung_jamos = list(weights['jungsung'].keys())
        jung_weights = list(weights['jungsung'].values())
        tiles.extend(random.choices(jung_jamos, weights=jung_weights, k=jung_count))
        
        # Generate 종성 tiles
        if jong_count > 0:
            jong_jamos = list(weights['jongsung'].keys())
            jong_weights = list(weights['jongsung'].values())
            tiles.extend(random.choices(jong_jamos, weights=jong_weights, k=jong_count))
        
        # Shuffle to mix tile types
        random.shuffle(tiles)
        return tiles
    else:
        # English
        letters = list(LETTER_WEIGHTS.keys())
        weights = list(LETTER_WEIGHTS.values())
        return random.choices(letters, weights=weights, k=count)
