import requests
import html
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_job_alert(self, post: Dict[str, Any], evaluation: Dict[str, Any]) -> bool:
        """
        Formats and sends a Telegram notification for a matched job post.
        """
        role_type = evaluation.get("role_type", "Job Opportunity")
        summary = evaluation.get("summary", "")
        author = post.get("author", "Unknown Author")
        channel_name = post.get("channel_name", "Discord Channel")
        content = post.get("content", "")
        link = post.get("link", "#")

        # Truncate content snippet if too long
        max_snippet_len = 500
        content_snippet = content if len(content) <= max_snippet_len else content[:max_snippet_len] + "..."

        # Escape HTML special characters to prevent Telegram parse errors
        safe_role = html.escape(role_type)
        safe_author = html.escape(author)
        safe_channel = html.escape(channel_name)
        safe_summary = html.escape(summary)
        safe_snippet = html.escape(content_snippet)

        emoji = "🎬" if "Editor" in role_type else ("🎨" if "Thumbnail" in role_type else "🎯")

        message = (
            f"<b>{emoji} NEW JOB OPPORTUNITY!</b>\n\n"
            f"🎯 <b>Looking For:</b> <code>{safe_role}</code>\n"
            f"👤 <b>Posted By:</b> {safe_author}\n"
            f"💬 <b>Channel:</b> #{safe_channel}\n\n"
            f"💡 <b>AI Summary:</b>\n<i>{safe_summary}</i>\n\n"
            f"📄 <b>Original Post:</b>\n<blockquote>{safe_snippet}</blockquote>\n\n"
            f"🔗 <a href=\"{link}\">👉 Click Here to Open Discord Post</a>"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=10)
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info(f"Successfully sent alert to Telegram for message {post.get('id')}")
                return True
            else:
                logger.error(f"Failed to send Telegram message ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error calling Telegram API: {e}")
            return False
