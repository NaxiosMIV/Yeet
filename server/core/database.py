import asyncpg
from dotenv import load_dotenv
from fastapi import HTTPException
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db_connection()
    try:
        # Make dictionary table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dictionary (
                word TEXT PRIMARY KEY,
                length INTEGER,
                score INTEGER
            );
        """)
        # Make users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                social_id TEXT,
                provider TEXT NOT NULL, -- 'google', 'guest'
                email TEXT,
                name TEXT,
                picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (social_id, provider)
            );
        """)
        # Make games table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id SERIAL PRIMARY KEY,
                room_code TEXT,
                winner_uuid UUID REFERENCES users(user_uuid),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Make game_stats table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                stat_id SERIAL PRIMARY KEY,
                game_id INTEGER REFERENCES games(game_id),
                user_uuid UUID REFERENCES users(user_uuid),
                score INTEGER,
                rank INTEGER
            );
        """)
    finally:
        await conn.close()

async def get_or_create_user(user_info: dict):
    conn = await get_db_connection()
    try:
        # social_id와 provider의 조합으로 유저를 찾음
        user_uuid = await conn.fetchval("""
            SELECT user_uuid FROM users WHERE social_id = $1 AND provider = $2
        """, user_info["social_id"], user_info["provider"])
        if user_uuid is None:
            # 유저가 없으면 생성
            user_uuid = await conn.fetchval("""
                INSERT INTO users (social_id, provider, email, name, picture) 
                VALUES ($1, $2, $3, $4, $5)
                RETURNING user_uuid
            """, user_info["social_id"], user_info["provider"], user_info.get("email"), user_info.get("name"), user_info.get("picture"))
        return user_uuid
    except Exception as e:
        print(f"Database error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        await conn.close()

async def save_game_result(room_code: str, players: dict):
    """게임 결과를 DB에 저장"""
    conn = await get_db_connection()
    try:
        # 1. 승리자 찾기 (최고 점수)
        if not players:
            return
            
        # players는 {player_uuid: {"name": ..., "score": ...}} 형태라고 가정
        sorted_players = sorted(players.items(), key=lambda x: x[1]["score"], reverse=True)
        winner_uuid = sorted_players[0][0]
        
        # 2. game 레코드 생성
        game_id = await conn.fetchval("""
            INSERT INTO games (room_code, winner_uuid) VALUES ($1, $2::uuid)
            RETURNING game_id
        """, room_code, winner_uuid)
        
        # 3. 각 플레이어별 통계 저장
        for rank, (p_uuid, data) in enumerate(sorted_players, 1):
            await conn.execute("""
                INSERT INTO game_stats (game_id, user_uuid, score, rank)
                VALUES ($1, $2::uuid, $3, $4)
            """, game_id, p_uuid, data["score"], rank)
            
        return game_id
    except Exception as e:
        print(f"Database error in save_game_result: {e}")
        return None
    finally:
        await conn.close()


async def get_user_by_social_id(social_id: str, provider: str):
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow("""
            SELECT * FROM users WHERE social_id = $1 AND provider = $2
        """, social_id, provider)
        return dict(user) if user else None
    except Exception as e:
        print(f"Database error in get_user_by_social_id: {e}")
        return None
    finally:
        await conn.close()


async def get_user_by_uuid(user_uuid: str):
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow("""
            SELECT social_id, provider, email, name, picture FROM users WHERE user_uuid = $1::uuid
        """, user_uuid)
        return dict(user) if user else None
    except Exception as e:
        print(f"Database error in get_user_by_uuid: {e}")
        return None
    finally:
        await conn.close()
