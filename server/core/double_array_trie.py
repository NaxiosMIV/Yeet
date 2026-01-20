"""
Simple Trie Implementation (Dict-based)

A fast, memory-efficient Trie using nested dictionaries.
Much faster to build than Double Array Trie while maintaining
the same O(m) lookup time.
"""

from typing import List, Dict
from core.logging_config import get_logger

logger = get_logger(__name__)


class DoubleArrayTrie:
    """
    Simple Trie using nested dictionaries for efficient prefix lookup.
    
    Despite the name (kept for backward compatibility), this is a 
    dict-based Trie that builds much faster than true Double Array Trie.
    """
    
    # Special marker for end of word
    END_MARKER = '\x00'
    
    def __init__(self):
        self.root: Dict = {}
        self._word_count = 0
        self._built = False
    
    def build(self, words: List[str]) -> None:
        """
        Build the Trie from a list of words.
        
        Args:
            words: List of words to add to the trie
        """
        self.root = {}
        self._word_count = 0
        
        for word in words:
            self._insert(word)
        
        self._built = True
        logger.info(f"Built Trie with {self._word_count} words")
    
    def _insert(self, word: str) -> None:
        """Insert a single word into the trie."""
        node = self.root
        for char in word:
            if char not in node:
                node[char] = {}
            node = node[char]
        node[self.END_MARKER] = True
        self._word_count += 1
    
    def search(self, word: str) -> bool:
        """
        Check if a word exists in the trie.
        
        Args:
            word: The word to search for
            
        Returns:
            True if the exact word exists, False otherwise
        """
        if not self._built:
            return False
        
        node = self.root
        for char in word:
            if char not in node:
                return False
            node = node[char]
        
        return self.END_MARKER in node
    
    def has_prefix(self, prefix: str) -> bool:
        """
        Check if any word in the trie starts with the given prefix.
        
        Args:
            prefix: The prefix to check
            
        Returns:
            True if at least one word starts with this prefix, False otherwise
        """
        if not self._built:
            return True  # No trie built, be permissive
        
        if not prefix:
            return True  # Empty prefix matches everything
        
        # Empty trie (no words) - be permissive
        if not self.root:
            return True
        
        node = self.root
        for char in prefix:
            if char not in node:
                return False
            node = node[char]
        
        return True  # Found all chars in prefix
    
    def __len__(self) -> int:
        """Return the number of words in the trie."""
        return self._word_count
    
    def memory_usage(self) -> int:
        """Return approximate memory usage in bytes."""
        import sys
        return sys.getsizeof(self.root)
