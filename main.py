import logging
import sys
from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter
from telegram_sender import TelegramSender

# Configure clean logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DiscordToTelegramBot")

def main():
    logger.info("Starting Discord to Telegram Job Post Monitor...")
    
    try:
        Config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file=Config.STATE_FILE)
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)
    telegram = TelegramSender(bot_token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    total_new_posts = 0
    total_matches = 0

    for channel_id in Config.DISCORD_CHANNEL_IDS:
        logger.info(f"Checking Discord Channel ID: {channel_id}...")
        try:
            posts = fetcher.fetch_new_posts_from_channel(channel_id)
            total_new_posts += len(posts)

            if not posts:
                logger.info(f"No new posts found in channel {channel_id}.")
                continue

            logger.info(f"Fetched {len(posts)} new post(s) from channel {channel_id}. Analyzing with Gemini AI...")

            for post in posts:
                logger.info(f"Evaluating post {post['id']} by {post['author']} from #{post['channel_name']}...")
                
                evaluation = gemini.evaluate_post(
                    post_content=post["content"],
                    author=post["author"],
                    channel_name=post["channel_name"]
                )

                logger.info(
                    f"Result for post {post['id']}: match={evaluation['is_match']}, "
                    f"role={evaluation['role_type']}, reasoning={evaluation['reasoning']}"
                )

                if evaluation["is_match"]:
                    total_matches += 1
                    logger.info(f"🚀 MATCH FOUND! Sending alert to Telegram for post {post['id']}...")
                    telegram.send_job_alert(post=post, evaluation=evaluation)

        except Exception as e:
            logger.error(f"Error processing channel {channel_id}: {e}", exc_info=True)

    # Save state after checking all channels
    fetcher.save_state()

    logger.info(f"Done! Checked {len(Config.DISCORD_CHANNEL_IDS)} channel(s). "
                f"New posts analyzed: {total_new_posts}, Job alerts sent: {total_matches}.")

if __name__ == "__main__":
    main()
