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
                provider TEXT NOT NULL, -- 'google', 'kakao', 'guest'
                email TEXT,
                name TEXT,
                picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (social_id, provider)
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
