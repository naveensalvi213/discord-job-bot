import os
import json
from dotenv import load_dotenv

# Load .env file if available (for local testing)
load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
    
    # Comma-separated list of channel IDs or forum channel IDs
    _raw_channel_ids = os.getenv("DISCORD_CHANNEL_IDS", "").strip()
    DISCORD_CHANNEL_IDS = [
        cid.strip() for cid in _raw_channel_ids.replace("\n", ",").split(",") if cid.strip()
    ]
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    STATE_FILE = os.getenv("STATE_FILE", "state.json")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.DISCORD_TOKEN:
            missing.append("DISCORD_TOKEN")
        if not cls.DISCORD_CHANNEL_IDS:
            missing.append("DISCORD_CHANNEL_IDS")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
