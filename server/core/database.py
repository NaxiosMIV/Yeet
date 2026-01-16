import asyncpg
from core.config import DATABASE_URL

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db_connection()
    try:
        await conn.execute("DROP TABLE IF EXISTS dictionary;")
        await conn.execute("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY,
                length INTEGER,
                score INTEGER
            );
        """)
        print("Database initialized (table 'dictionary' created).")
    finally:
        await conn.close()
