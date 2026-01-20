import sys
import os
from collections import Counter

# Add the directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tiles import generate_weighted_tiles, LETTER_WEIGHTS

def verify_distribution(n=100000):
    tiles = generate_weighted_tiles(n)
    counts = Counter(tiles)
    
    print(f"Results for {n} tiles:")
    print(f"{'Letter':<8} | {'Expected %':<12} | {'Actual %':<12} | {'Diff':<8}")
    print("-" * 50)
    
    # Sort by expected weight descending
    for char, weight in sorted(LETTER_WEIGHTS.items(), key=lambda x: x[1], reverse=True):
        actual_pct = (counts[char] / n) * 100
        diff = actual_pct - weight
        print(f"{char:<8} | {weight:<12.2f} | {actual_pct:<12.2f} | {diff:+.2f}")

if __name__ == "__main__":
    verify_distribution()
