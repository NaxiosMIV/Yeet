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
        user = await conn.fetchval("""
            SELECT * FROM users WHERE email = $1
        """, user_info["email"])
        if user is None:
            return await conn.fetchval("""
                INSERT INTO users (email, name, picture, provider, social_id) VALUES ($1, $2, $3, $4, $5)
                RETURNING user_uuid
            """, user_info["email"], user_info["name"], user_info["picture"], user_info["provider"], user_info["social_id"])
        return user
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        await conn.close()
