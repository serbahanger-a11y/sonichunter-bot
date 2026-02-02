# 🎵 SonicHunter Bot

> Next-Gen Telegram Music Discovery Bot with lightning-fast inline search, trigram fuzzy matching, and auto-indexing

## ✨ Features

- **🎯 Trigram Search** - Finds tracks even with typos using PostgreSQL pg_trgm
- **⚡ Redis Caching** - Instant response for repeated queries
- **🕷 Auto-Indexing** - Telethon spider automatically indexes music from channels
- **📊 Search Analytics** - Tracks popular queries to improve results
- **👥 Crowdsourcing** - Users can submit missing tracks

## 🚀 Quick Start

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/serbahanger-a11y/sonichunter-bot/main/install.sh | bash
```

### Manual Setup

1. **Clone repository**
```bash
git clone https://github.com/serbahanger-a11y/sonichunter-bot.git
cd sonichunter-bot
```

2. **Configure environment**
```bash
cp .env.example .env
nano .env
```

3. **Launch with Docker**
```bash
docker-compose up -d
```

## 💻 Stack

- **Python 3.12**
- **Aiogram 3.x** - Telegram Bot Framework
- **Telethon** - MTProto API for indexing
- **PostgreSQL + pg_trgm** - Fuzzy search database
- **Redis** - Response caching
- **Docker + Docker Compose** - Containerization

## 🛠 Management Commands

```bash
# View logs
docker-compose logs -f bot

# Restart bot
docker-compose restart bot

# Stop all services
docker-compose down

# Update bot
git pull && docker-compose up -d --build
```

## 📝 License

MIT
