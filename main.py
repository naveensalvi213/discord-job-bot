import logging
import sys
import time
import argparse
from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter
from telegram_sender import TelegramSender

# Configure UTF-8 encoding for Windows stdout logging
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DiscordToTelegramBot")

def run_pass(fetcher: DiscordFetcher, gemini: GeminiFilter, telegram: TelegramSender) -> tuple:
    total_new_posts = 0
    total_matches = 0

    for channel_id in Config.DISCORD_CHANNEL_IDS:
        try:
            posts = fetcher.fetch_new_posts_from_channel(channel_id)
            if not posts:
                continue

            total_new_posts += len(posts)
            logger.info(f"Fetched {len(posts)} new post(s) from channel {channel_id}. Evaluating with Gemini AI...")

            for post in posts:
                logger.info(f"Evaluating post {post['id']} by {post['author']} from #{post['channel_name']}...")
                
                evaluation = gemini.evaluate_post(
                    post_content=post["content"],
                    author=post["author"],
                    channel_name=post["channel_name"]
                )

                # Only advance channel state if evaluation succeeded without generic API error
                if not evaluation.get("reasoning", "").startswith("API Error"):
                    fetcher.update_channel_state(channel_id, post["id"])

                logger.info(
                    f"Result for post {post['id']}: match={evaluation['is_match']}, "
                    f"role={evaluation['role_type']}, summary={evaluation['summary']}"
                )

                if evaluation["is_match"]:
                    total_matches += 1
                    logger.info(f"🚀 MATCH FOUND! Sending alert to Telegram for post {post['id']}...")
                    telegram.send_job_alert(post=post, evaluation=evaluation)

        except Exception as e:
            logger.error(f"Error processing channel {channel_id}: {e}", exc_info=True)

    fetcher.save_state()
    return total_new_posts, total_matches

def main():
    parser = argparse.ArgumentParser(description="Discord to Telegram Job Post Monitor")
    parser.add_argument("--duration", type=int, default=240, help="Total seconds to run in a continuous check loop (default: 240s)")
    parser.add_argument("--interval", type=int, default=20, help="Interval in seconds between check iterations (default: 20s)")
    args = parser.parse_args()

    logger.info("Starting Discord to Telegram Job Post Monitor...")
    
    try:
        Config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file=Config.STATE_FILE)
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)
    telegram = TelegramSender(bot_token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    start_time = time.time()
    iteration = 1
    grand_total_posts = 0
    grand_total_matches = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= args.duration:
            logger.info(f"Completed continuous monitoring duration ({int(elapsed)}s). Exiting loop cleanly.")
            break

        logger.info(f"--- Loop Iteration {iteration} (Elapsed: {int(elapsed)}s / {args.duration}s) ---")
        new_posts, matches = run_pass(fetcher, gemini, telegram)
        grand_total_posts += new_posts
        grand_total_matches += matches

        iteration += 1
        time.sleep(args.interval)

    logger.info(f"Run Summary: Checked {len(Config.DISCORD_CHANNEL_IDS)} channels across {iteration-1} pass(es). "
                f"Total New Posts Analyzed: {grand_total_posts}, Total Job Alerts Sent: {grand_total_matches}.")

if __name__ == "__main__":
    main()
