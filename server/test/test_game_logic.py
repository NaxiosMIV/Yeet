import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add the directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.core.game import GameRoom, Player

async def test_game_logic():
    print("Starting Game Logic Verification...")
    room = GameRoom("TEST1")
    
    # 1. Verify Board Structure (Dictionary)
    print("\n1. Verifying Board Structure...")
    assert isinstance(room.board, dict), f"Expected board to be dict, got {type(room.board)}"
    print("✓ Board is a dictionary")
    
    # 2. Verify Initial Word Placement
    print("\n2. Verifying Initial Word Placement...")
    assert len(room.board) > 0, "Board should not be empty after initialization"
    for pos, tile in room.board.items():
        assert isinstance(pos, tuple) and len(pos) == 2, f"Invalid key: {pos}"
        assert tile['x'] == pos[0] and tile['y'] == pos[1], f"Mismatch in tile data: {tile} at {pos}"
    print("✓ Initial word correctly placed in dictionary structure")

    # 3. Verify get_state conversion
    print("\n3. Verifying get_state conversion...")
    state = room.get_state()
    assert isinstance(state['board'], list), f"state['board'] should be list, got {type(state['board'])}"
    assert len(state['board']) == len(room.board), "State board length mismatch"
    print("✓ get_state correctly converts board dict to list")

    # 4. Verify Race Condition Protection (Basic Lock Check)
    print("\n4. Verifying asyncio.Lock presence...")
    assert hasattr(room, 'lock'), "GameRoom should have a lock attribute"
    assert isinstance(room.lock, asyncio.Lock), "lock attribute should be an asyncio.Lock"
    print("✓ asyncio.Lock is present")

    # 5. Verify Invalid Word Penalty
    print("\n5. Verifying Invalid Word Penalty...")
    mock_ws = MagicMock()
    mock_ws.send_json = MagicMock(side_effect=lambda x: asyncio.sleep(0)) # Mock async send_json
    player = Player("p1", "TestPlayer", mock_ws)
    room.add_player(player)
    player.score = 50
    player.hand = ["X", "Y", "Z"] # Junk tiles
    
    # Simulate placing a tile that forms an invalid word
    # Initial word is at (start_x+i, 0). Let's place at (start_x, 1)
    start_tile = list(room.board.values())[0]
    tx, ty = start_tile['x'], start_tile['y'] + 1
    
    success, error = await room.handle_place_tile(tx, ty, "X", "p1", "#FFFFFF")
    assert success, f"Failed to place tile: {error}"
    
    # Wait for the timer or manually call finalize
    pending = room.pending_tiles[0]
    gid = pending['v_group_id']
    
    print("   Finalizing invalid group...")
    await room.finalize_pending_group(gid, 'v')
    
    assert player.score == 40, f"Expected score 40 after penalty, got {player.score}"
    assert len(room.pending_tiles) == 0, "Pending tiles should be cleared"
    print("✓ Invalid word penalty (-10) applied correctly")

    print("\nAll tests passed!")

if __name__ == "__main__":
    asyncio.run(test_game_logic())
