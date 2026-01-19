from core.database import get_db_connection
from core.logging_config import get_logger
import random

logger = get_logger(__name__)

word_cache = {}
words_by_length = {} # int -> List[str]

async def load_words_to_memory():
    global word_cache, words_by_length
    try:
        conn = await get_db_connection()
        rows = await conn.fetch("SELECT word, length, score FROM dictionary")

        word_cache = {row['word']: (row['length'], row['score']) for row in rows}
        
        # 길이별 인덱싱 생성
        words_by_length = {}
        for word, (length, score) in word_cache.items():
            if length not in words_by_length:
                words_by_length[length] = []
            words_by_length[length].append(word)
            
        await conn.close()
        logger.info(f"Loaded {len(word_cache)} words and indexed by {len(words_by_length)} lengths.")
        return word_cache
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        return {}

def get_word_in_cache(word: str):
    upper_word = word.upper()
    if upper_word in word_cache:
        length, score = word_cache[upper_word]
        logger.debug(f"Cache hit for word: {upper_word}")
        return {
            "is_valid": True,
            "word": upper_word,
            "length": length,
            "score": score
        }
    return {"is_valid": False, "word": upper_word}

def get_random_word(min_length: int = 6, max_length: int = None, exact_length: int = None):
    """
    words_by_length 인덱스를 사용하여 무작위로 단어를 뽑습니다.
    """
    logger.debug(f"get_random_word called with min_length={min_length}, max_length={max_length}, exact_length={exact_length}")
    
    if exact_length:
        eligible_words = words_by_length.get(exact_length, [])
    else:
        # 범위 내의 모든 길이에 해당하는 리스트를 합칩니다.
        # 여전히 리스트를 합치는 과정이 있지만, 전체 단어장을 순회하는 것보다는 훨씬 빠릅니다.
        eligible_words = []
        possible_lengths = [l for l in words_by_length.keys() if l >= min_length]
        if max_length:
            possible_lengths = [l for l in possible_lengths if l <= max_length]
        
        for l in possible_lengths:
            eligible_words.extend(words_by_length[l])
        
    if not eligible_words:
        return None
    return random.choice(eligible_words)
