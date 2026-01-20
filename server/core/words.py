from core.database import get_db_connection
from core.logging_config import get_logger
from core.double_array_trie import DoubleArrayTrie, BidirectionalTrie
import random

logger = get_logger(__name__)

# language -> word -> (length, score)
word_cache = {}
# language -> length -> List[str]
words_by_length = {}
# language -> BidirectionalTrie
word_trie = {} 

async def load_words_to_memory():
    global word_cache, words_by_length, word_trie
    try:
        conn = await get_db_connection()
        rows = await conn.fetch("SELECT word, lang, length, score FROM dictionary")

        # Initialize caches
        word_cache = {}
        words_by_length = {}

        for row in rows:
            word = row['word']
            lang = row['lang']
            length = row['length']
            score = row['score']

            if lang not in word_cache:
                word_cache[lang] = {}
            if lang not in words_by_length:
                words_by_length[lang] = {}
            
            word_cache[lang][word] = (length, score)
            
            if length not in words_by_length[lang]:
                words_by_length[lang][length] = []
            words_by_length[lang][length].append(word)
            
        await conn.close()
        logger.info(f"Loaded words for {len(word_cache)} languages.")
        for lang in word_cache:
            logger.info(f"  - {lang}: {len(word_cache[lang])} words")
        
        # Build BidirectionalTrie for each language (prefix + suffix validation)
        for lang, words_dict in word_cache.items():
            logger.info(f"Building BidirectionalTrie for {lang}...")
            trie = BidirectionalTrie()
            trie.build(list(words_dict.keys()))
            word_trie[lang] = trie
            logger.info(f"  - {lang} BidirectionalTrie built, {len(trie)} words")
        
        return word_cache
    except Exception as e:
        logger.error(f"데이터 로드 중 오류 발생: {e}")
        return {}

def get_word_in_cache(word: str, lang: str = 'en'):
    target_word = word.upper() if lang == 'en' else word
    lang_cache = word_cache.get(lang, {})
    
    if target_word in lang_cache:
        length, score = lang_cache[target_word]
        logger.debug(f"Cache hit for word [{lang}]: {target_word}")
        return {
            "is_valid": True,
            "word": target_word,
            "length": length,
            "score": score
        }
    return {"is_valid": False, "word": target_word}

def get_random_word(min_length: int = 6, max_length: int = None, exact_length: int = None, lang: str = 'en'):
    """
    words_by_length 인덱스를 사용하여 무작위로 단어를 뽑습니다.
    """
    logger.debug(f"get_random_word called for {lang} with min_length={min_length}, max_length={max_length}, exact_length={exact_length}")
    
    lang_words = words_by_length.get(lang, {})
    if not lang_words:
        return None

    if exact_length:
        eligible_words = lang_words.get(exact_length, [])
    else:
        eligible_words = []
        possible_lengths = [l for l in lang_words.keys() if l >= min_length]
        if max_length:
            possible_lengths = [l for l in possible_lengths if l <= max_length]
        
        for l in possible_lengths:
            eligible_words.extend(lang_words[l])
        
    if not eligible_words:
        return None
    return random.choice(eligible_words)

def has_valid_prefix(prefix: str, lang: str = 'en') -> bool:
    """
    Check if the given prefix could lead to a valid word.
    
    Uses BidirectionalTrie for both prefix and suffix lookup.
    This allows words to be built from either direction.
    
    Args:
        prefix: The string to check (actually checks both prefix AND suffix)
        lang: Language code ('en' or 'ko')
        
    Returns:
        True if at least one valid word contains this as prefix OR suffix
    """
    if not prefix:
        return True
        
    target = prefix.upper() if lang == 'en' else prefix
    
    if lang not in word_trie:
        logger.debug(f"No Trie for language {lang}, allowing")
        return True
    
    # Check both prefix and suffix (bidirectional)
    result = word_trie[lang].has_substring(target)
    logger.debug(f"Bidirectional check [{lang}]: '{target}' -> {result}")
    return result
