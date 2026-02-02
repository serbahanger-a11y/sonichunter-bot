-- PostgreSQL Init Script for SonicHunter
-- Creates database schema with trigram search support

-- Enable trigram extension for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Main tracks table
CREATE TABLE IF NOT EXISTS tracks (
    id BIGSERIAL PRIMARY KEY,
    file_id TEXT UNIQUE NOT NULL,           -- Telegram file_id (unique key)
    artist VARCHAR(255),                     -- Artist name
    title VARCHAR(255),                      -- Track title
    duration INTEGER,                        -- Duration in seconds
    file_size BIGINT,                        -- File size in bytes
    source_channel_id BIGINT,                -- Channel where track was found
    source_message_id BIGINT,                -- Message ID in source channel
    added_at TIMESTAMP DEFAULT NOW(),       -- When track was indexed
    updated_at TIMESTAMP DEFAULT NOW()      -- Last update timestamp
);

-- GIN index for trigram search (CRITICAL for speed)
-- This allows searching with typos: "bili aish" finds "Billie Eilish"
CREATE INDEX IF NOT EXISTS tracks_artist_trgm_idx ON tracks USING GIN (artist gin_trgm_ops);
CREATE INDEX IF NOT EXISTS tracks_title_trgm_idx ON tracks USING GIN (title gin_trgm_ops);

-- Combined search index for artist + title
CREATE INDEX IF NOT EXISTS tracks_search_idx ON tracks USING GIN (
    (LOWER(COALESCE(artist, '') || ' ' || COALESCE(title, ''))) gin_trgm_ops
);

-- Regular indexes for exact lookups
CREATE INDEX IF NOT EXISTS tracks_file_id_idx ON tracks (file_id);
CREATE INDEX IF NOT EXISTS tracks_added_at_idx ON tracks (added_at DESC);

-- Channels table (Spider targets)
CREATE TABLE IF NOT EXISTS channels (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT UNIQUE NOT NULL,      -- Telegram channel ID
    channel_username VARCHAR(255),           -- Channel @username
    channel_title VARCHAR(255),              -- Channel display name
    is_active BOOLEAN DEFAULT TRUE,         -- Is spider monitoring this?
    added_at TIMESTAMP DEFAULT NOW(),
    last_indexed_at TIMESTAMP               -- Last time spider checked this channel
);

-- User submissions table (Crowdsourcing)
CREATE TABLE IF NOT EXISTS user_submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,                 -- Telegram user ID
    track_id BIGINT REFERENCES tracks(id),   -- Track that was submitted
    submitted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS user_submissions_user_idx ON user_submissions (user_id);

-- Search statistics (for caching hot queries)
CREATE TABLE IF NOT EXISTS search_stats (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,                     -- Search query
    count INTEGER DEFAULT 1,                 -- How many times searched
    last_searched_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS search_stats_query_idx ON search_stats (query);
CREATE INDEX IF NOT EXISTS search_stats_count_idx ON search_stats (count DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_tracks_updated_at BEFORE UPDATE ON tracks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Materialized view for top 100 most searched queries (Redis fallback)
CREATE MATERIALIZED VIEW IF NOT EXISTS top_searches AS
    SELECT query, count, last_searched_at 
    FROM search_stats 
    ORDER BY count DESC 
    LIMIT 100;

CREATE INDEX IF NOT EXISTS top_searches_idx ON top_searches (query);
