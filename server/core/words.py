from core.database import get_db_connection
from core.logging_config import get_logger
import random

logger = get_logger(__name__)

word_cache = {}

async def load_words_to_memory():
    global word_cache
    try:
        conn = await get_db_connection()
        rows = await conn.fetch("SELECT word, length, score FROM dictionary")

        word_cache = {row['word']: (row['length'], row['score']) for row in rows}
        await conn.close()

        return word_cache
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        return {}

def get_word_in_cache(word: str):
    upper_word = word.upper()
    if upper_word in word_cache:
        length, score = word_cache[upper_word]
        return {
            "is_valid": True,
            "word": upper_word,
            "length": length,
            "score": score
        }
    return {"is_valid": False, "word": upper_word}

def get_random_word(min_length: int = 6):
    eligible_words = [word for word, (length, score) in word_cache.items() if length >= min_length]
    if not eligible_words:
        return None
    return random.choice(eligible_words)
