#!/usr/bin/env python3
"""
SonicHunter Main Bot
Handles inline queries with trigram search
"""

import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineQuery, InlineQueryResultCachedAudio
import asyncpg
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "sonichunter")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None
redis_client = None


async def search_tracks(query: str, limit: int = 20):
    """Trigram search with typo tolerance"""
    async with db_pool.acquire() as conn:
        # Increment search stats
        await conn.execute(
            """INSERT INTO search_stats (query, count) 
               VALUES ($1, 1)
               ON CONFLICT (query) DO UPDATE 
               SET count = search_stats.count + 1, 
                   last_searched_at = NOW()""",
            query
        )
        
        # Perform trigram search
        results = await conn.fetch(
            """SELECT id, file_id, artist, title, duration
               FROM tracks
               WHERE LOWER(COALESCE(artist, '') || ' ' || COALESCE(title, '')) % LOWER($1)
               ORDER BY similarity(
                   LOWER(COALESCE(artist, '') || ' ' || COALESCE(title, '')), 
                   LOWER($1)
               ) DESC
               LIMIT $2""",
            query, limit
        )
        return results


@dp.inline_query()
async def inline_search(inline_query: InlineQuery):
    """Handle inline queries: @botname <search query>"""
    query = inline_query.query.strip()
    
    if not query:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return
    
    logger.info(f"Search: '{query}' from user {inline_query.from_user.id}")
    
    try:
        # Check Redis cache first
        cache_key = f"search:{query.lower()}"  
        cached = await redis_client.get(cache_key)
        
        if cached:
            logger.info(f"Cache hit for '{query}'")
            results = eval(cached)  # Safe because we control the data
        else:
            results = await search_tracks(query)
            # Cache for 5 minutes
            await redis_client.setex(cache_key, 300, str([(r['id'], r['file_id'], r['artist'], r['title'], r['duration']) for r in results]))
        
        # Build inline results
        inline_results = []
        for track in results:
            inline_results.append(
                InlineQueryResultCachedAudio(
                    id=str(track['id']),
                    audio_file_id=track['file_id'],
                    caption=f"🎵 {track['artist']} - {track['title']}"
                )
            )
        
        await inline_query.answer(
            inline_results,
            cache_time=300,
            is_personal=False
        )
        
    except Exception as e:
        logger.error(f"Error in inline_search: {e}", exc_info=True)
        await inline_query.answer([], cache_time=1)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎧 *SonicHunter Bot*\n\n"
        "Быстрый поиск музыки в любом чате!\n\n"
        "Используй: `@sonichunter dj overdose zigzag`\n\n"
        "Триграммный поиск найдёт трек даже с опечатками.",
        parse_mode="Markdown"
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Show bot statistics"""
    async with db_pool.acquire() as conn:
        total_tracks = await conn.fetchval("SELECT COUNT(*) FROM tracks")
        total_searches = await conn.fetchval("SELECT SUM(count) FROM search_stats")
    
    await message.answer(
        f"📊 *SonicHunter Stats*\n\n"
        f"🎵 Tracks in database: {total_tracks:,}\n"
        f"🔍 Total searches: {total_searches:,}",
        parse_mode="Markdown"
    )


async def main():
    global db_pool, redis_client
    
    logger.info("Starting SonicHunter Bot...")
    
    # Connect to PostgreSQL
    db_pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=5,
        max_size=20
    )
    logger.info("✅ Connected to PostgreSQL")
    
    # Connect to Redis
    redis_client = await redis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}",
        decode_responses=True
    )
    logger.info("✅ Connected to Redis")
    
    # Start bot
    logger.info("✅ Bot started and ready")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
