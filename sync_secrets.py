import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

SECRETS = [
    "DISCORD_TOKEN",
    "DISCORD_CHANNEL_IDS",
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID"
]

def sync():
    print("Syncing secrets from .env to GitHub repository (naveensalvi213/discord-job-bot)...")
    missing = []
    for secret in SECRETS:
        val = os.getenv(secret, "").strip()
        if not val:
            missing.append(secret)
            continue
        
        cmd = ["gh", "secret", "set", secret, "--repo", "naveensalvi213/discord-job-bot", "--body", val]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] Set GitHub secret: {secret}")
        else:
            print(f"[ERROR] Failed to set {secret}: {result.stderr}")
    
    if missing:
        print(f"\n[!] The following secrets are missing from your .env file: {', '.join(missing)}")
        print("Please edit the .env file in this folder and run 'python sync_secrets.py' again.")
    else:
        print("\n[SUCCESS] All secrets successfully uploaded to GitHub!")

if __name__ == "__main__":
    sync()
