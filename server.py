import os
import sys
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure UTF-8 stdout
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
logger = logging.getLogger("RenderBotServer")

# Import bot loop modules
from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter
from telegram_sender import TelegramSender

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Discord to Telegram Job Bot is Running 24/7 on Render!</h1>")

    def log_message(self, format, *args):
        # Suppress verbose HTTP server access logs
        return

def bot_loop():
    logger.info("Initializing 24/7 Continuous Discord Job Monitor on Render...")
    try:
        Config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file=Config.STATE_FILE)
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)
    telegram = TelegramSender(bot_token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    interval = 20  # check every 20 seconds
    iteration = 1

    while True:
        try:
            logger.info(f"=== Starting Scan Pass #{iteration} ===")
            total_new_posts = 0
            total_matches = 0

            for channel_id in Config.DISCORD_CHANNEL_IDS:
                try:
                    posts = fetcher.fetch_new_posts_from_channel(channel_id)
                    if not posts:
                        continue

                    total_new_posts += len(posts)
                    logger.info(f"Fetched {len(posts)} new post(s) from channel {channel_id}. Analyzing with Gemini AI...")

                    for post in posts:
                        author_safe = post['author'].encode('ascii', 'ignore').decode('ascii')
                        channel_safe = post['channel_name'].encode('ascii', 'ignore').decode('ascii')
                        logger.info(f" -> Evaluating post {post['id']} by {author_safe} in #{channel_safe}...")

                        evaluation = gemini.evaluate_post(
                            post_content=post["content"],
                            author=post["author"],
                            channel_name=post["channel_name"]
                        )

                        # Only update state if Gemini API call succeeded
                        if not evaluation.get("reasoning", "").startswith("API Error"):
                            fetcher.update_channel_state(channel_id, post["id"])

                        logger.info(
                            f"    Result: match={evaluation['is_match']}, "
                            f"role={evaluation['role_type']}, summary={evaluation['summary']}"
                        )

                        if evaluation["is_match"]:
                            total_matches += 1
                            logger.info(f"🚀 MATCH FOUND! Sending alert to Telegram for post {post['id']}...")
                            telegram.send_job_alert(post=post, evaluation=evaluation)

                except Exception as e:
                    logger.error(f"Error checking channel {channel_id}: {e}")

            fetcher.save_state()
            logger.info(f"=== Completed Pass #{iteration}: {total_new_posts} new posts analyzed, {total_matches} alerts sent ===")

        except Exception as e:
            logger.error(f"Unhandled error in bot loop iteration #{iteration}: {e}")

        iteration += 1
        time.sleep(interval)

def main():
    # Start bot loop in background daemon thread
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()

    # Start HTTP server for Render health checks
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"HTTP Health Server listening on 0.0.0.0:{port}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Render HTTP server...")
        server.server_close()

if __name__ == "__main__":
    main()
