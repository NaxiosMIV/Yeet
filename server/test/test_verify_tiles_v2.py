import sys
import os
from collections import Counter
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tiles import TileBag, load_korean_weights
from core.korean_utils import get_jamo_type

def test_korean_distribution_and_vowel_health(n=2000):
    bag = TileBag(lang='ko')
    bag.REFILL_THRESHOLD = 30 # Override for comparison
    min_vowels = 100
    
    drawn_tiles = []
    
    for i in range(n):
        tile = bag.draw(1)[0]
        drawn_tiles.append(tile)
        
        # Check current bag health
        vowels_in_bag = sum(1 for t in bag.bag if get_jamo_type(t) == 'jung')
        min_vowels = min(min_vowels, vowels_in_bag)
        
    counts = Counter(drawn_tiles)
    total = len(drawn_tiles)
    
    cho_or_jong = sum(1 for t in drawn_tiles if get_jamo_type(t) in ['cho', 'jong'])
    jung_count = sum(1 for t in drawn_tiles if get_jamo_type(t) == 'jung')
    
    print(f"Results for {total} tiles:")
    print(f"Consonants (Cho+Jong): {cho_or_jong} ({cho_or_jong/total*100:.1f}%) - Expected ~54%")
    print(f"Vowels (Jung):         {jung_count} ({jung_count/total*100:.1f}%) - Expected ~46%")
    print(f"Minimum vowels ever in bag: {min_vowels}")
    
    if min_vowels > 0:
        print("✓ Vowel health maintained! Vowels never dropped to zero.")
    else:
        print("✗ Vowel health failure! Vowels dropped to zero.")

if __name__ == "__main__":
    test_korean_distribution_and_vowel_health()
