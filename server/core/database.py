import asyncpg
from core.config import DATABASE_URL

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db_connection()
    try:
        await conn.execute("""
            DROP TABLE IF EXISTS dictionary;
        """)
        await conn.execute("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY,
                length INTEGER,
                score INTEGER
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

async def create_user(email: str, name: str, picture: str):
    conn = await get_db_connection()
    try:
        return await conn.execute("""   
            INSERT INTO users (email, name, picture) VALUES ($1, $2, $3)
        """, email, name, picture)
    finally:
        await conn.close()