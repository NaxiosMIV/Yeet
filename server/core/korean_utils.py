"""
Korean Jamo (자모) Decomposition and Composition Utilities

Handles conversion between Korean syllables and their constituent jamos (consonants and vowels).
"""

# Hangul Unicode Constants
HANGUL_BASE = 0xAC00  # '가'
HANGUL_END = 0xD7A3   # '힣'

# Jamo Lists
# 초성 (Initial consonants) - 19 characters
CHOSUNG_LIST = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 중성 (Medial vowels) - 21 characters
JUNGSUNG_LIST = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 
    'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'
]

# 종성 (Final consonants) - 28 characters (0 = no final consonant)
JONGSUNG_LIST = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 
    'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 
    'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# All jamos that can appear as tiles
ALL_CHOSUNG = set(CHOSUNG_LIST)
ALL_JUNGSUNG = set(JUNGSUNG_LIST)
ALL_JONGSUNG = set(JONGSUNG_LIST[1:])  # Exclude empty string


def is_hangul_syllable(char: str) -> bool:
    """Check if a character is a complete Hangul syllable."""
    if len(char) != 1:
        return False
    code = ord(char)
    return HANGUL_BASE <= code <= HANGUL_END


def decompose_syllable(syllable: str) -> tuple:
    """
    Decompose a single Hangul syllable into its jamos.
    
    Args:
        syllable: A single Hangul character (e.g., '한')
        
    Returns:
        Tuple of (초성, 중성, 종성). 종성 is empty string if no final consonant.
        
    Example:
        decompose_syllable('한') -> ('ㅎ', 'ㅏ', 'ㄴ')
        decompose_syllable('가') -> ('ㄱ', 'ㅏ', '')
    """
    if not is_hangul_syllable(syllable):
        return (syllable, '', '')  # Return as-is if not Hangul
    
    code = ord(syllable) - HANGUL_BASE
    
    jong_idx = code % 28
    jung_idx = ((code - jong_idx) // 28) % 21
    cho_idx = ((code - jong_idx) // 28) // 21
    
    cho = CHOSUNG_LIST[cho_idx]
    jung = JUNGSUNG_LIST[jung_idx]
    jong = JONGSUNG_LIST[jong_idx]
    
    return (cho, jung, jong)


def compose_syllable(cho: str, jung: str, jong: str = '') -> str:
    """
    Compose jamos into a Hangul syllable.
    
    Args:
        cho: 초성 (initial consonant)
        jung: 중성 (medial vowel)
        jong: 종성 (final consonant, optional)
        
    Returns:
        A complete Hangul syllable
        
    Example:
        compose_syllable('ㅎ', 'ㅏ', 'ㄴ') -> '한'
        compose_syllable('ㄱ', 'ㅏ') -> '가'
    """
    if cho not in CHOSUNG_LIST or jung not in JUNGSUNG_LIST:
        return cho + jung + jong  # Return concatenated if invalid
    
    cho_idx = CHOSUNG_LIST.index(cho)
    jung_idx = JUNGSUNG_LIST.index(jung)
    jong_idx = JONGSUNG_LIST.index(jong) if jong else 0
    
    code = HANGUL_BASE + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx
    return chr(code)


def decompose_word(word: str) -> str:
    """
    Decompose a Korean word into a jamo string.
    
    Args:
        word: Korean word (e.g., '사과')
        
    Returns:
        Jamo string (e.g., 'ㅅㅏㄱㅘ')
        
    Example:
        decompose_word('사과') -> 'ㅅㅏㄱㅘ'
        decompose_word('한글') -> 'ㅎㅏㄴㄱㅡㄹ'
    """
    jamos = []
    for char in word:
        if is_hangul_syllable(char):
            cho, jung, jong = decompose_syllable(char)
            jamos.append(cho)
            jamos.append(jung)
            if jong:
                jamos.append(jong)
        else:
            jamos.append(char)  # Keep non-Hangul as-is
    return ''.join(jamos)


def compose_word(jamos: str) -> str:
    """
    Compose a jamo string into a Korean word.
    
    Args:
        jamos: Jamo string (e.g., 'ㅅㅏㄱㅘ')
        
    Returns:
        Korean word (e.g., '사과')
        
    Note: This assumes the jamos form valid syllable patterns.
    Invalid patterns will be concatenated as-is.
    """
    result = []
    i = 0
    
    while i < len(jamos):
        # Try to build a syllable
        if i < len(jamos) and jamos[i] in ALL_CHOSUNG:
            cho = jamos[i]
            i += 1
            
            # Check for middle vowel
            if i < len(jamos) and jamos[i] in ALL_JUNGSUNG:
                jung = jamos[i]
                i += 1
                
                # Check for optional final consonant
                jong = ''
                if i < len(jamos) and jamos[i] in ALL_JONGSUNG:
                    # Peek ahead: is next char a vowel? If so, this is initial consonant of next syllable
                    if i + 1 < len(jamos) and jamos[i + 1] in ALL_JUNGSUNG:
                        # Don't consume as jong
                        pass
                    else:
                        jong = jamos[i]
                        i += 1
                
                result.append(compose_syllable(cho, jung, jong))
            else:
                # No vowel after consonant, just append
                result.append(cho)
        else:
            # Not a valid start, just append
            result.append(jamos[i])
            i += 1
    
    return ''.join(result)


def is_valid_syllable_pattern(jamos: str) -> bool:
    """
    Check if a jamo sequence forms valid Korean syllable patterns.
    
    A valid pattern is: (초성 + 중성 + 종성?)+ 
    Each syllable must have at least 초성+중성.
    
    Args:
        jamos: Jamo string to validate
        
    Returns:
        True if forms valid syllable pattern(s), False otherwise
        
    Example:
        is_valid_syllable_pattern('ㅅㅏ') -> True (사)
        is_valid_syllable_pattern('ㅅㅏㄱ') -> True (삭)
        is_valid_syllable_pattern('ㅅㅏㄱㅘ') -> True (사과)
        is_valid_syllable_pattern('ㅅㄱ') -> False (no vowel)
        is_valid_syllable_pattern('ㅏㅏ') -> False (no initial consonant)
    """
    if not jamos:
        return False
    
    i = 0
    syllable_count = 0
    
    while i < len(jamos):
        # Must start with 초성
        if i >= len(jamos) or jamos[i] not in ALL_CHOSUNG:
            return False
        i += 1
        
        # Must have 중성
        if i >= len(jamos) or jamos[i] not in ALL_JUNGSUNG:
            return False
        i += 1
        
        # Optional 종성
        if i < len(jamos) and jamos[i] in ALL_JONGSUNG:
            # Check if this could be 초성 of next syllable
            if i + 1 < len(jamos) and jamos[i + 1] in ALL_JUNGSUNG:
                # This consonant starts next syllable, don't consume
                pass
            else:
                # Consume as 종성
                i += 1
        
        syllable_count += 1
    
    return syllable_count > 0


def get_jamo_type(jamo: str) -> str:
    """
    Get the type of a jamo character.
    
    Returns:
        'cho' for 초성, 'jung' for 중성, 'jong' for 종성, 'unknown' otherwise
    """
    if jamo in ALL_CHOSUNG:
        return 'cho'
    elif jamo in ALL_JUNGSUNG:
        return 'jung'
    elif jamo in ALL_JONGSUNG:
        return 'jong'
    else:
        return 'unknown'
