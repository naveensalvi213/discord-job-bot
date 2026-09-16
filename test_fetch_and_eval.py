import sys
import os
import json
import logging

from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter
from telegram_sender import TelegramSender

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_run():
    print("=== TESTING DISCORD FETCH & GEMINI CLASSIFICATION ===", flush=True)
    
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")

    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file="test_state.json")
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)
    telegram = TelegramSender(bot_token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    total_channels = len(Config.DISCORD_CHANNEL_IDS)
    print(f"Total Configured Channels: {total_channels}", flush=True)

    total_posts_found = 0
    matched_posts = []

    for idx, cid in enumerate(Config.DISCORD_CHANNEL_IDS, 1):
        try:
            posts = fetcher.fetch_new_posts_from_channel(cid)
            print(f"[{idx}/{total_channels}] Channel {cid} -> {len(posts)} post(s) fetched.", flush=True)
            total_posts_found += len(posts)

            for p in posts:
                print(f"   Analyzing post {p['id']} by {p['author']} in #{p['channel_name']}...", flush=True)
                eval_res = gemini.evaluate_post(p["content"], p["author"], p["channel_name"])
                print(f"   -> Match: {eval_res['is_match']} | Role: {eval_res['role_type']} | Summary: {eval_res['summary']}", flush=True)
                
                if eval_res["is_match"]:
                    matched_posts.append((p, eval_res))
        except Exception as e:
            print(f"[{idx}/{total_channels}] Error checking channel {cid}: {e}", flush=True)

    print("\n================ FINAL TEST SUMMARY ================", flush=True)
    print(f"Channels Checked: {total_channels}", flush=True)
    print(f"Total Posts Fetched & Sent to Gemini: {total_posts_found}", flush=True)
    print(f"Total Hiring Matches Found: {len(matched_posts)}", flush=True)
    print("====================================================", flush=True)

    if matched_posts:
        print("\nSending matched job alerts to Telegram group...", flush=True)
        for p, eval_res in matched_posts:
            telegram.send_job_alert(p, eval_res)
        print("Alerts sent successfully to Telegram!", flush=True)

if __name__ == "__main__":
    test_run()
