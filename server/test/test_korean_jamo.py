"""
Test Korean Jamo Utilities
"""
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.korean_utils import (
    decompose_syllable, compose_syllable,
    decompose_word, compose_word,
    is_valid_syllable_pattern
)

def test_syllable_decomposition():
    print("Testing syllable decomposition...")
    
    test_cases = [
        ('한', ('ㅎ', 'ㅏ', 'ㄴ')),
        ('글', ('ㄱ', 'ㅡ', 'ㄹ')),
        ('사', ('ㅅ', 'ㅏ', '')),
        ('과', ('ㄱ', 'ㅘ', '')),
    ]
    
    for syllable, expected in test_cases:
        result = decompose_syllable(syllable)
        assert result == expected, f"Failed: {syllable} -> {result}, expected {expected}"
    print("✓ Syllable decomposition passed!")

def test_syllable_composition():
    print("\nTesting syllable composition...")
    
    test_cases = [
        (('ㅎ', 'ㅏ', 'ㄴ'), '한'),
        (('ㄱ', 'ㅡ', 'ㄹ'), '글'),
        (('ㅅ', 'ㅏ', ''), '사'),
        (('ㄱ', 'ㅘ', ''), '과'),
    ]
    
    for (cho, jung, jong), expected in test_cases:
        result = compose_syllable(cho, jung, jong)
        assert result == expected, f"Failed: {(cho, jung, jong)} -> {result}, expected {expected}"
    print("✓ Syllable composition passed!")

def test_word_decomposition():
    print("\nTesting word decomposition...")
    
    test_cases = [
        ('사과', 'ㅅㅏㄱㅘ'),
        ('한글', 'ㅎㅏㄴㄱㅡㄹ'),
        ('컴퓨터', 'ㅋㅓㅁㅍㅠㅌㅓ'),
        ('프로그래밍', 'ㅍㅡㄹㅗㄱㅡㄹㅐㅁㅣㅇ'),
    ]
    
    for word, expected in test_cases:
        result = decompose_word(word)
        print(f"  {word} -> {result}")
        assert result == expected, f"Failed: {word} -> {result}, expected {expected}"
    print("✓ Word decomposition passed!")

def test_word_composition():
    print("\nTesting word composition...")
    
    test_cases = [
        ('ㅅㅏㄱㅘ', '사과'),
        ('ㅎㅏㄴㄱㅡㄹ', '한글'),
        ('ㅋㅓㅁㅍㅠㅌㅓ', '컴퓨터'),
    ]
    
    for jamos, expected in test_cases:
        result = compose_word(jamos)
        print(f"  {jamos} -> {result}")
        assert result == expected, f"Failed: {jamos} -> {result}, expected {expected}"
    print("✓ Word composition passed!")

def test_pattern_validation():
    print("\nTesting syllable pattern validation...")
    
    valid_patterns = [
        'ㅅㅏ',      # 사
        'ㅅㅏㄱ',    # 삭
        'ㅅㅏㄱㅘ',  # 사과
        'ㅎㅏㄴㄱㅡㄹ',  # 한글
    ]
    
    invalid_patterns = [
        'ㅅㄱ',      # No vowel
        'ㅏㅏ',      # No initial consonant
        'ㄱㄴㄷ',    # Only consonants
    ]
    
    for pattern in valid_patterns:
        result = is_valid_syllable_pattern(pattern)
        assert result == True, f"Should be valid: {pattern}"
    print(f"  ✓ All {len(valid_patterns)} valid patterns passed")
    
    for pattern in invalid_patterns:
        result = is_valid_syllable_pattern(pattern)
        assert result == False, f"Should be invalid: {pattern}"
    print(f"  ✓ All {len(invalid_patterns)} invalid patterns correctly rejected")
    
    print("✓ Pattern validation passed!")

def test_roundtrip():
    print("\nTesting roundtrip decompose->compose...")
    
    test_words = ['사과', '한글', '프로그래밍', '대한민국', '컴퓨터과학']
    
    for word in test_words:
        jamos = decompose_word(word)
        reconstructed = compose_word(jamos)
        print(f"  {word} -> {jamos} -> {reconstructed}")
        assert word == reconstructed, f"Roundtrip failed: {word} != {reconstructed}"
    
    print("✓ Roundtrip test passed!")

if __name__ == "__main__":
    print("=" * 50)
    print("Korean Jamo Utilities Test Suite")
    print("=" * 50)
    
    test_syllable_decomposition()
    test_syllable_composition()
    test_word_decomposition()
    test_word_composition()
    test_pattern_validation()
    test_roundtrip()
    
    print("\n" + "=" * 50)
    print("✨ All tests passed!")
    print("=" * 50)
