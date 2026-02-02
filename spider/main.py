#!/usr/bin/env python3
"""
SonicHunter Spider
Automatically monitors Telegram music channels and indexes tracks 24/7
"""

import os
import asyncio
import logging
from telethon import TelegramClient, events
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
DUMP_CHANNEL_ID = int(os.getenv("DUMP_CHANNEL_ID"))  # Your private channel
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "sonichunter")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Parse target channels from env
TARGET_CHANNELS_STR = os.getenv("TARGET_CHANNELS", "")
TARGET_CHANNELS = [
    int(ch.strip()) for ch in TARGET_CHANNELS_STR.split(",") if ch.strip()
] if TARGET_CHANNELS_STR else []

client = TelegramClient('sessions/spider_session', API_ID, API_HASH)
db_pool = None


async def index_track(file_id, artist, title, duration, file_size, source_channel_id, source_message_id):
    """Save track metadata to database"""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                """INSERT INTO tracks 
                   (file_id, artist, title, duration, file_size, source_channel_id, source_message_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   ON CONFLICT (file_id) DO NOTHING""",
                file_id, artist, title, duration, file_size, source_channel_id, source_message_id
            )
            logger.info(f"✅ Indexed: {artist} - {title} ({duration}s)")
        except Exception as e:
            logger.error(f"Error indexing track: {e}")


@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def handler(event):
    """Monitor channels for new audio files"""
    try:
        if event.message.audio:
            audio = event.message.audio
            
            # Extract metadata from audio tags
            artist = audio.performer or "Unknown Artist"
            title = audio.title or "Unknown Title"
            duration = audio.duration or 0
            file_size = audio.size
            file_id = ""
            
            # Forward to dump channel to get file_id
            forwarded = await client.forward_messages(DUMP_CHANNEL_ID, event.message)
            if forwarded and forwarded.audio:
                file_id = forwarded.audio.file_id
            
            # Index in database
            if file_id:
                await index_track(
                    file_id=file_id,
                    artist=artist,
                    title=title,
                    duration=duration,
                    file_size=file_size,
                    source_channel_id=event.chat_id,
                    source_message_id=event.message.id
                )
                logger.info(f"🎵 Found: {artist} - {title} from channel {event.chat_id}")
    
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)


async def seed_existing_tracks():
    """Index existing tracks from target channels (backfill)"""
    logger.info("🌱 Seeding database from target channels...")
    
    for channel_id in TARGET_CHANNELS:
        try:
            logger.info(f"Scanning channel {channel_id}...")
            count = 0
            
            async for message in client.iter_messages(channel_id, limit=500):
                if message.audio:
                    audio = message.audio
                    artist = audio.performer or "Unknown Artist"
                    title = audio.title or "Unknown Title"
                    duration = audio.duration or 0
                    file_size = audio.size
                    
                    # Forward to get file_id
                    forwarded = await client.forward_messages(DUMP_CHANNEL_ID, message)
                    if forwarded and forwarded.audio:
                        file_id = forwarded.audio.file_id
                        await index_track(
                            file_id=file_id,
                            artist=artist,
                            title=title,
                            duration=duration,
                            file_size=file_size,
                            source_channel_id=channel_id,
                            source_message_id=message.id
                        )
                        count += 1
                        
                        # Rate limit to avoid flood
                        await asyncio.sleep(0.5)
            
            logger.info(f"✅ Seeded {count} tracks from channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error seeding channel {channel_id}: {e}")
            continue


async def main():
    global db_pool
    
    logger.info("🕷️  Starting SonicHunter Spider...")
    
    # Connect to PostgreSQL
    db_pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=2,
        max_size=10
    )
    logger.info("✅ Connected to PostgreSQL")
    
    # Start Telethon client
    await client.start(phone=PHONE)
    logger.info("✅ Telethon client started")
    
    if not TARGET_CHANNELS:
        logger.warning("⚠️  No target channels configured. Add channel IDs to .env (TARGET_CHANNELS)")
    else:
        logger.info(f"📡 Monitoring {len(TARGET_CHANNELS)} channels: {TARGET_CHANNELS}")
        
        # Optional: Seed existing tracks on first start
        # await seed_existing_tracks()
    
    logger.info("✅ Spider is running. Monitoring for new tracks...")
    
    # Keep running
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Spider stopped")
