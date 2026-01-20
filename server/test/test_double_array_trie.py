"""
Test Double Array Trie Implementation
"""
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.double_array_trie import DoubleArrayTrie


def test_empty_trie():
    """Test operations on empty trie."""
    print("Testing empty trie...")
    trie = DoubleArrayTrie()
    trie.build([])
    
    assert trie.search("test") == False, "Empty trie should not find any word"
    assert trie.has_prefix("") == True, "Empty prefix should always be valid"
    assert trie.has_prefix("a") == True, "Unbuilt trie should be permissive"
    
    print("✓ Empty trie tests passed!")


def test_single_word():
    """Test trie with a single word."""
    print("\nTesting single word...")
    trie = DoubleArrayTrie()
    trie.build(["hello"])
    
    assert trie.search("hello") == True, "Should find 'hello'"
    assert trie.search("hell") == False, "Should not find incomplete 'hell'"
    assert trie.search("helloo") == False, "Should not find 'helloo'"
    assert trie.search("world") == False, "Should not find 'world'"
    
    print("✓ Single word tests passed!")


def test_prefix_check():
    """Test prefix checking functionality."""
    print("\nTesting prefix checking...")
    trie = DoubleArrayTrie()
    trie.build(["hello", "help", "helicopter", "world"])
    
    # Valid prefixes
    assert trie.has_prefix("h") == True, "'h' is a valid prefix"
    assert trie.has_prefix("he") == True, "'he' is a valid prefix"
    assert trie.has_prefix("hel") == True, "'hel' is a valid prefix"
    assert trie.has_prefix("hell") == True, "'hell' is a valid prefix"
    assert trie.has_prefix("hello") == True, "'hello' is a valid prefix (exact match)"
    assert trie.has_prefix("heli") == True, "'heli' is a valid prefix"
    
    # Invalid prefixes
    assert trie.has_prefix("hx") == False, "'hx' is not a valid prefix"
    assert trie.has_prefix("hellop") == False, "'hellop' is not a valid prefix"
    assert trie.has_prefix("z") == False, "'z' is not a valid prefix"
    
    print("✓ Prefix checking tests passed!")


def test_multiple_words():
    """Test trie with multiple words."""
    print("\nTesting multiple words...")
    trie = DoubleArrayTrie()
    words = ["apple", "app", "application", "banana", "band", "bandana"]
    trie.build(words)
    
    for word in words:
        assert trie.search(word) == True, f"Should find '{word}'"
    
    # Non-existent words
    assert trie.search("appl") == False, "'appl' is not a complete word"
    assert trie.search("ban") == False, "'ban' is not a complete word"
    assert trie.search("bananas") == False, "'bananas' is not in the trie"
    
    print("✓ Multiple words tests passed!")


def test_korean_jamo():
    """Test trie with Korean jamo strings."""
    print("\nTesting Korean jamo strings...")
    trie = DoubleArrayTrie()
    
    # These are jamo representations
    words = [
        "ㅅㅏㄱㅘ",      # 사과
        "ㅅㅏㄹㅣ",      # 사리
        "ㅅㅏㄹㅏㅁ",    # 사람
        "ㅎㅏㄴㄱㅡㄹ",  # 한글
    ]
    trie.build(words)
    
    # Exact matches
    assert trie.search("ㅅㅏㄱㅘ") == True, "Should find 사과 jamos"
    assert trie.search("ㅎㅏㄴㄱㅡㄹ") == True, "Should find 한글 jamos"
    
    # Prefix checks
    assert trie.has_prefix("ㅅ") == True, "'ㅅ' is a valid prefix"
    assert trie.has_prefix("ㅅㅏ") == True, "'ㅅㅏ' is a valid prefix"
    assert trie.has_prefix("ㅅㅏㄱ") == True, "'ㅅㅏㄱ' is a valid prefix (사과 prefix)"
    assert trie.has_prefix("ㅎㅏ") == True, "'ㅎㅏ' is a valid prefix"
    
    # Invalid prefixes
    assert trie.has_prefix("ㅁ") == False, "'ㅁ' is not a valid prefix"
    assert trie.has_prefix("ㅅㅏㅇ") == False, "'ㅅㅏㅇ' is not a valid prefix"
    
    print("✓ Korean jamo tests passed!")


def test_case_sensitivity():
    """Test that trie is case-sensitive."""
    print("\nTesting case sensitivity...")
    trie = DoubleArrayTrie()
    trie.build(["Hello", "WORLD", "test"])
    
    assert trie.search("Hello") == True
    assert trie.search("hello") == False
    assert trie.search("HELLO") == False
    assert trie.search("WORLD") == True
    assert trie.search("world") == False
    assert trie.search("test") == True
    
    print("✓ Case sensitivity tests passed!")


def test_memory_and_size():
    """Test memory reporting."""
    print("\nTesting memory reporting...")
    trie = DoubleArrayTrie()
    trie.build(["a", "ab", "abc", "abcd", "abcde"])
    
    assert len(trie) > 0, "Trie should have non-zero size"
    assert trie.memory_usage() > 0, "Memory usage should be positive"
    
    print(f"  Trie array size: {len(trie)}")
    print(f"  Memory usage: {trie.memory_usage()} bytes")
    print("✓ Memory tests passed!")


if __name__ == "__main__":
    print("=" * 50)
    print("Double Array Trie Test Suite")
    print("=" * 50)
    
    test_empty_trie()
    test_single_word()
    test_prefix_check()
    test_multiple_words()
    test_korean_jamo()
    test_case_sensitivity()
    test_memory_and_size()
    
    # Test BidirectionalTrie
    print("\n" + "=" * 50)
    print("BidirectionalTrie Tests")
    print("=" * 50)
    
    from core.double_array_trie import BidirectionalTrie
    
    print("\nTesting BidirectionalTrie suffix validation...")
    btrie = BidirectionalTrie()
    btrie.build(["hello", "world", "caring", "playing", "testing"])
    
    # Prefix checks (should work like regular trie)
    assert btrie.has_prefix("hel") == True, "'hel' should be valid prefix"
    assert btrie.has_prefix("wor") == True, "'wor' should be valid prefix"
    assert btrie.has_prefix("xyz") == False, "'xyz' should be invalid prefix"
    
    # Suffix checks
    assert btrie.has_suffix("ing") == True, "'ing' should be valid suffix"
    assert btrie.has_suffix("llo") == True, "'llo' should be valid suffix (hello)"
    assert btrie.has_suffix("rld") == True, "'rld' should be valid suffix (world)"
    assert btrie.has_suffix("xyz") == False, "'xyz' should be invalid suffix"
    
    # Substring checks (prefix OR suffix)
    assert btrie.has_substring("hel") == True, "'hel' valid as prefix"
    assert btrie.has_substring("ing") == True, "'ing' valid as suffix"
    assert btrie.has_substring("xyz") == False, "'xyz' invalid"
    
    print("✓ BidirectionalTrie suffix tests passed!")
    
    print("\nTesting BidirectionalTrie with Korean jamo...")
    ko_trie = BidirectionalTrie()
    ko_words = [
        "ㅅㅏㄱㅘ",      # 사과
        "ㅅㅏㄹㅏㅁ",    # 사람
        "ㅎㅏㄴㄱㅡㄹ",  # 한글
    ]
    ko_trie.build(ko_words)
    
    # Korean prefix
    assert ko_trie.has_prefix("ㅅㅏ") == True, "'ㅅㅏ' valid prefix"
    
    # Korean suffix (reversed: 과 -> ㅘㄱ reversed from ㄱㅘ)
    assert ko_trie.has_suffix("ㄱㅘ") == True, "'ㄱㅘ' valid suffix (사과)"
    assert ko_trie.has_suffix("ㄱㅡㄹ") == True, "'ㄱㅡㄹ' valid suffix (한글)"
    
    print("✓ Korean BidirectionalTrie tests passed!")

    print("\n" + "=" * 50)
    print("✨ All tests passed!")
    print("=" * 50)

