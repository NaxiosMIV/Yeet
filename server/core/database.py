import asyncpg
from dotenv import load_dotenv
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

async def get_user(email: str):
    conn = await get_db_connection()
    try:
        return await conn.fetchval("""
            SELECT * FROM users WHERE email = $1
        """, email)
    finally:
        await conn.close()
