#!/bin/bash
set -e

echo "🚀 SonicHunter Bot - Automated Installation"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "❌ Please run as root"
   exit 1
fi

echo "✅ Updating system..."
apt update && apt upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "✅ Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "✅ Installing Docker Compose..."
    apt install docker-compose -y
else
    echo "✅ Docker Compose already installed"
fi

# Install git
if ! command -v git &> /dev/null; then
    echo "✅ Installing git..."
    apt install git -y
fi

echo "✅ Cloning repository..."
cd /root
rm -rf sonichunter-bot
git clone https://github.com/serbahanger-a11y/sonichunter-bot.git
cd sonichunter-bot

echo "✅ Creating .env file..."
cp .env.example .env

echo ""
echo "⚠️  IMPORTANT: Edit the .env file with your credentials:"
echo "   nano /root/sonichunter-bot/.env"
echo ""
echo "Fill in:"
echo "  - BOT_TOKEN=your_bot_token"
echo "  - DB_PASSWORD=strong_password"
echo "  - SPIDER_API_ID=your_api_id"
echo "  - SPIDER_API_HASH=your_api_hash"
echo "  - SPIDER_PHONE=your_phone"
echo ""
echo "After editing, run:"
echo "  cd /root/sonichunter-bot && docker-compose up -d"
echo ""
echo "✅ Installation complete!"
echo "✅ Repository: /root/sonichunter-bot"
