"""
Double Array Trie (DAT) Implementation

A space-efficient Trie implementation using two arrays (base, check).
Supports:
- Exact word search: O(m) where m = word length
- Prefix checking: O(m) to verify if a prefix could lead to valid words
"""

from typing import List, Dict, Optional
from core.logging_config import get_logger

logger = get_logger(__name__)


class DoubleArrayTrie:
    """
    Double Array Trie for efficient word lookup and prefix validation.
    
    Uses two arrays:
    - base[]: Contains base values for state transitions
    - check[]: Contains parent state verification
    
    A transition from state s with character c goes to state t where:
    - t = base[s] + code(c)
    - check[t] == s (verification)
    """
    
    # Special markers
    END_MARKER = '\x00'  # End of word marker
    
    def __init__(self):
        self.base: List[int] = []
        self.check: List[int] = []
        self.char_to_code: Dict[str, int] = {}
        self.code_to_char: Dict[int, str] = {}
        self._built = False
    
    def _build_alphabet(self, words: List[str]) -> None:
        """Build character to code mapping from all words."""
        chars = set()
        for word in words:
            for char in word:
                chars.add(char)
        chars.add(self.END_MARKER)
        
        # Sort for deterministic ordering, END_MARKER gets code 1
        sorted_chars = sorted(chars - {self.END_MARKER})
        
        self.char_to_code = {self.END_MARKER: 1}
        self.code_to_char = {1: self.END_MARKER}
        
        for i, char in enumerate(sorted_chars, start=2):
            self.char_to_code[char] = i
            self.code_to_char[i] = char
        
        logger.debug(f"Built alphabet with {len(self.char_to_code)} characters")
    
    def _get_code(self, char: str) -> int:
        """Get code for a character, 0 if not in alphabet."""
        return self.char_to_code.get(char, 0)
    
    def _ensure_size(self, size: int) -> None:
        """Ensure arrays are at least the given size."""
        if len(self.base) < size:
            extend_by = size - len(self.base)
            self.base.extend([0] * extend_by)
            self.check.extend([-1] * extend_by)
    
    def _find_base(self, codes: List[int]) -> int:
        """Find a base value that doesn't cause collisions."""
        if not codes:
            return 1
        
        min_code = min(codes)
        base = 1
        
        while True:
            collision = False
            for code in codes:
                pos = base + code
                self._ensure_size(pos + 1)
                if self.check[pos] != -1:
                    collision = True
                    break
            
            if not collision:
                return base
            base += 1
            
            # Safety limit to prevent infinite loops
            if base > len(self.base) + len(codes) * 2:
                self._ensure_size(base + max(codes) + 1)
        
        return base
    
    def build(self, words: List[str]) -> None:
        """
        Build the Double Array Trie from a list of words.
        
        Args:
            words: List of words to add to the trie
        """
        if not words:
            self._built = True
            return
        
        # Build alphabet
        self._build_alphabet(words)
        
        # Sort words for deterministic building
        words = sorted(set(words))
        
        # Initialize arrays (state 0 is root)
        initial_size = max(len(self.char_to_code) * 2, 1024)
        self.base = [0] * initial_size
        self.check = [-1] * initial_size
        self.check[0] = 0  # Root state
        
        # Build trie using BFS-like approach
        # Each entry: (state, prefix, word_indices)
        from collections import deque
        
        # Group words by first character
        word_data = [(w + self.END_MARKER, i) for i, w in enumerate(words)]
        queue = deque([(0, 0, list(range(len(words))))])  # (state, depth, word_indices)
        
        while queue:
            state, depth, indices = queue.popleft()
            
            # Group by character at current depth
            char_groups: Dict[str, List[int]] = {}
            for idx in indices:
                word = words[idx] + self.END_MARKER
                if depth < len(word):
                    char = word[depth]
                    if char not in char_groups:
                        char_groups[char] = []
                    char_groups[char].append(idx)
            
            if not char_groups:
                continue
            
            # Find suitable base value
            codes = [self._get_code(c) for c in char_groups.keys()]
            base_val = self._find_base(codes)
            self.base[state] = base_val
            
            # Set transitions
            for char, group_indices in char_groups.items():
                code = self._get_code(char)
                next_state = base_val + code
                self._ensure_size(next_state + 1)
                self.check[next_state] = state
                
                if char != self.END_MARKER:
                    queue.append((next_state, depth + 1, group_indices))
        
        self._built = True
        logger.info(f"Built DAT with {len(words)} words, array size: {len(self.base)}")
    
    def _traverse(self, text: str) -> tuple:
        """
        Traverse the trie with given text.
        
        Returns:
            (success, final_state, consumed_length)
            - success: True if entire text was traversed
            - final_state: Last valid state reached
            - consumed_length: How many characters were consumed
        """
        if not self._built or not text:
            return (True, 0, 0)
        
        state = 0
        for i, char in enumerate(text):
            code = self._get_code(char)
            if code == 0:
                return (False, state, i)
            
            next_state = self.base[state] + code
            if next_state >= len(self.check) or self.check[next_state] != state:
                return (False, state, i)
            
            state = next_state
        
        return (True, state, len(text))
    
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
        
        # Empty trie has no words
        if len(self.char_to_code) <= 1:  # Only END_MARKER or less
            return False
        
        success, state, _ = self._traverse(word)
        if not success:
            return False
        
        # Check for end marker
        end_code = self._get_code(self.END_MARKER)
        end_state = self.base[state] + end_code
        
        if end_state >= len(self.check):
            return False
        
        return self.check[end_state] == state
    
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
        if len(self.char_to_code) <= 1:
            return True
        
        success, _, consumed = self._traverse(prefix)
        return success and consumed == len(prefix)
    
    def __len__(self) -> int:
        """Return the size of the base array."""
        return len(self.base)
    
    def memory_usage(self) -> int:
        """Return approximate memory usage in bytes."""
        # Each int is typically 28 bytes in Python, but in list ~8 bytes reference
        # Plus int object overhead
        import sys
        return (sys.getsizeof(self.base) + sys.getsizeof(self.check) + 
                sys.getsizeof(self.char_to_code) + sys.getsizeof(self.code_to_char))
