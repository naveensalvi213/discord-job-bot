import sys
import os
import logging

# Set UTF-8 encoding for Windows stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter
from telegram_sender import TelegramSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TestBatch")

def run_test():
    logger.info("Starting 24-Hour / Recent Posts Test Batch with Gemini AI...")
    
    # Remove state.json temporarily to re-evaluate recent posts
    if os.path.exists("state.json"):
        try:
            os.remove("state.json")
            logger.info("Cleared previous state.json to fetch recent posts.")
        except Exception as e:
            logger.warning(f"Could not remove state.json: {e}")

    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file="state.json")
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)
    telegram = TelegramSender(bot_token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    total_posts = 0
    matched_count = 0

    for idx, cid in enumerate(Config.DISCORD_CHANNEL_IDS, 1):
        logger.info(f"[{idx}/{len(Config.DISCORD_CHANNEL_IDS)}] Checking Channel ID: {cid}...")
        try:
            posts = fetcher.fetch_new_posts_from_channel(cid)
            total_posts += len(posts)

            if not posts:
                logger.info(f"No recent posts in channel {cid}.")
                continue

            logger.info(f"Fetched {len(posts)} recent post(s) from channel {cid}. Evaluating with Gemini AI...")

            for post in posts:
                author_safe = post['author'].encode('ascii', 'ignore').decode('ascii')
                channel_safe = post['channel_name'].encode('ascii', 'ignore').decode('ascii')
                logger.info(f" -> Evaluating post {post['id']} by {author_safe} in #{channel_safe}...")

                evaluation = gemini.evaluate_post(
                    post_content=post["content"],
                    author=post["author"],
                    channel_name=post["channel_name"]
                )

                logger.info(
                    f"    Result: match={evaluation['is_match']}, "
                    f"role={evaluation['role_type']}, summary={evaluation['summary']}"
                )

                if evaluation["is_match"]:
                    matched_count += 1
                    logger.info(f"🚀 MATCH FOUND! Forwarding alert to Telegram for post {post['id']}...")
                    telegram.send_job_alert(post=post, evaluation=evaluation)

        except Exception as e:
            logger.error(f"Error checking channel {cid}: {e}")

    logger.info("================ TEST BATCH COMPLETED ================")
    logger.info(f"Total Channels Checked: {len(Config.DISCORD_CHANNEL_IDS)}")
    logger.info(f"Total Posts Evaluated by Gemini: {total_posts}")
    logger.info(f"Total Matches Forwarded to Telegram: {matched_count}")
    logger.info("=======================================================")

if __name__ == "__main__":
    run_test()
