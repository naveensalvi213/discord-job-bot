import os
import requests
from dotenv import load_dotenv

load_dotenv()

RENDER_API_KEY = "rnd_K5ulfkKciZ2SiskcPvAdnSBzEgfy"
OWNER_ID = "tea-d9i4ifmrnols73ek32l0"
REPO_URL = "https://github.com/naveensalvi213/discord-job-bot"

env_vars = [
    {"key": "DISCORD_TOKEN", "value": os.getenv("DISCORD_TOKEN", "")},
    {"key": "DISCORD_CHANNEL_IDS", "value": os.getenv("DISCORD_CHANNEL_IDS", "")},
    {"key": "GEMINI_API_KEY", "value": os.getenv("GEMINI_API_KEY", "")},
    {"key": "TELEGRAM_BOT_TOKEN", "value": os.getenv("TELEGRAM_BOT_TOKEN", "")},
    {"key": "TELEGRAM_CHAT_ID", "value": os.getenv("TELEGRAM_CHAT_ID", "")}
]

payload = {
    "ownerId": OWNER_ID,
    "name": "discord-to-telegram-job-bot",
    "type": "web_service",
    "repo": REPO_URL,
    "autoDeploy": "yes",
    "branch": "main",
    "serviceDetails": {
        "env": "python",
        "plan": "free",
        "region": "singapore",
        "envSpecificDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "python server.py"
        },
        "envVars": env_vars
    }
}

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Content-Type": "application/json"
}

print("Creating Render Web Service for 24/7 Discord Job Bot...")
resp = requests.post("https://api.render.com/v1/services", json=payload, headers=headers)
print(f"Response Status: {resp.status_code}")
print(resp.text)
