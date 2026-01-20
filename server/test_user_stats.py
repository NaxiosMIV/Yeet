"""
게임 종료 시 user_stats 업데이트 테스트 스크립트
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.database import get_db_connection, save_game_result, get_or_create_user

async def test_user_stats_update():
    conn = await get_db_connection()
    
    try:
        # 1. 테스트용 유저 2명 생성
        print("=== 테스트 유저 생성 ===")
        
        user1_info = {
            "social_id": "test_user_1",
            "provider": "guest",
            "name": "Test Player 1"
        }
        user2_info = {
            "social_id": "test_user_2", 
            "provider": "guest",
            "name": "Test Player 2"
        }
        
        user1_uuid = await get_or_create_user(user1_info)
        user2_uuid = await get_or_create_user(user2_info)
        
        print(f"User 1 UUID: {user1_uuid}")
        print(f"User 2 UUID: {user2_uuid}")
        
        # 2. 기존 user_stats 확인
        print("\n=== 게임 전 user_stats 확인 ===")
        stats_before = await conn.fetch("""
            SELECT * FROM user_stats WHERE user_uuid IN ($1::uuid, $2::uuid)
        """, str(user1_uuid), str(user2_uuid))
        
        for stat in stats_before:
            print(f"  {stat}")
        if not stats_before:
            print("  (아직 user_stats 레코드 없음)")
        
        # 3. 게임 결과 저장 (user1이 승자)
        print("\n=== 게임 결과 저장 ===")
        players_data = {
            str(user1_uuid): {"name": "Test Player 1", "score": 100, "color": "#FF0000", "hand": []},
            str(user2_uuid): {"name": "Test Player 2", "score": 50, "color": "#00FF00", "hand": []}
        }
        
        game_id = await save_game_result("TEST_ROOM", players_data)
        print(f"Game ID: {game_id}")
        
        # 4. 게임 후 user_stats 확인
        print("\n=== 게임 후 user_stats 확인 ===")
        stats_after = await conn.fetch("""
            SELECT user_uuid, total_games, total_score, total_wins 
            FROM user_stats 
            WHERE user_uuid IN ($1::uuid, $2::uuid)
            ORDER BY total_score DESC
        """, str(user1_uuid), str(user2_uuid))
        
        for stat in stats_after:
            print(f"  UUID: {stat['user_uuid']}")
            print(f"    - total_games: {stat['total_games']}")
            print(f"    - total_score: {stat['total_score']}")
            print(f"    - total_wins: {stat['total_wins']}")
        
        # 5. 두 번째 게임 테스트 (누적 확인)
        print("\n=== 두 번째 게임 결과 저장 (user2 승리) ===")
        players_data2 = {
            str(user1_uuid): {"name": "Test Player 1", "score": 30, "color": "#FF0000", "hand": []},
            str(user2_uuid): {"name": "Test Player 2", "score": 80, "color": "#00FF00", "hand": []}
        }
        
        game_id2 = await save_game_result("TEST_ROOM_2", players_data2)
        print(f"Game ID: {game_id2}")
        
        print("\n=== 두 게임 후 최종 user_stats ===")
        stats_final = await conn.fetch("""
            SELECT user_uuid, total_games, total_score, total_wins 
            FROM user_stats 
            WHERE user_uuid IN ($1::uuid, $2::uuid)
            ORDER BY total_score DESC
        """, str(user1_uuid), str(user2_uuid))
        
        for stat in stats_final:
            print(f"  UUID: {stat['user_uuid']}")
            print(f"    - total_games: {stat['total_games']} (예상: 2)")
            print(f"    - total_score: {stat['total_score']}")
            print(f"    - total_wins: {stat['total_wins']}")
        
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_user_stats_update())
