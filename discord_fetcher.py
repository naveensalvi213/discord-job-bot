import requests
import json
import os
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

class DiscordFetcher:
    def __init__(self, token: str, state_file: str = "state.json"):
        self.token = token.strip()
        self.state_file = state_file
        self.state = self._load_state()
        self.headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        # Support both Bot tokens and User tokens automatically
        auth = self.token if (self.token.startswith("Bot ") or self.token.startswith("Bearer ")) else f"Bot {self.token}"
        return {
            "Authorization": auth,
            "User-Agent": "DiscordToTelegramNotifier/1.0"
        }

    def _load_state(self) -> Dict[str, str]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state file {self.state_file}: {e}")
        return {}

    def save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            logger.info("Saved updated state.")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Any:
        resp = requests.get(url, headers=self.headers, params=params)
        
        # If Bot authorization failed (e.g. 401), try raw User token format without "Bot " prefix
        if resp.status_code == 401 and self.headers["Authorization"].startswith("Bot "):
            raw_token = self.token.replace("Bot ", "").strip()
            alt_headers = {"Authorization": raw_token, "User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=alt_headers, params=params)
            if resp.status_code == 200:
                self.headers = alt_headers

        if resp.status_code != 200:
            logger.error(f"Discord API request failed ({resp.status_code}): {resp.text}")
            return None
        return resp.json()

    def fetch_channel_info(self, channel_id: str) -> Dict[str, Any]:
        url = f"{DISCORD_API_BASE}/channels/{channel_id}"
        return self._make_request(url) or {}

    def fetch_new_posts_from_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Fetches new posts/messages from a standard channel or forum threads in a channel.
        Returns a list of parsed post dicts sorted chronologically (oldest to newest).
        """
        last_seen_id = self.state.get(channel_id)
        channel_info = self.fetch_channel_info(channel_id)
        channel_name = channel_info.get("name", f"channel_{channel_id}")
        guild_id = channel_info.get("guild_id", "")
        channel_type = channel_info.get("type", 0)

        posts = []

        # Type 15 is GUILD_FORUM
        if channel_type == 15:
            posts.extend(self._fetch_forum_posts(channel_id, guild_id, channel_name, last_seen_id))
        else:
            posts.extend(self._fetch_text_channel_messages(channel_id, guild_id, channel_name, last_seen_id))

        # Sort posts by message/thread ID ascending (chronological order)
        posts.sort(key=lambda p: int(p["id"]))

        # Update state with the latest post ID if we found new posts
        if posts:
            newest_id = posts[-1]["id"]
            self.state[channel_id] = newest_id

        return posts

    def _fetch_text_channel_messages(self, channel_id: str, guild_id: str, channel_name: str, last_seen_id: str) -> List[Dict[str, Any]]:
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        params = {"limit": 50}
        
        if last_seen_id:
            params["after"] = last_seen_id
            params["limit"] = 100
        
        raw_msgs = self._make_request(url, params=params)
        if not raw_msgs or not isinstance(raw_msgs, list):
            # If no last_seen_id and empty list, initialize state with latest message if available
            if not last_seen_id and isinstance(raw_msgs, list) and not raw_msgs:
                pass
            return []

        # If it's the very first run (no last_seen_id), we only take the most recent 5 posts
        # so we don't spam historical messages, but record the newest as state.
        if not last_seen_id:
            logger.info(f"First run for channel #{channel_name} ({channel_id}). Fetching recent posts.")
            # raw_msgs from discord API comes newest first
            raw_msgs = raw_msgs[:5]

        posts = []
        for msg in raw_msgs:
            parsed = self._parse_message(msg, guild_id=guild_id, channel_name=channel_name)
            if parsed:
                posts.append(parsed)
        return posts

    def _fetch_forum_posts(self, forum_id: str, guild_id: str, forum_name: str, last_seen_id: str) -> List[Dict[str, Any]]:
        """
        Fetches active and archived threads for a forum channel.
        """
        posts = []
        threads = []

        # 1. Fetch active threads in guild
        if guild_id:
            active_url = f"{DISCORD_API_BASE}/guilds/{guild_id}/threads/active"
            active_res = self._make_request(active_url)
            if active_res and "threads" in active_res:
                threads.extend([t for t in active_res["threads"] if t.get("parent_id") == forum_id])

        # 2. Fetch archived public threads in forum
        archived_url = f"{DISCORD_API_BASE}/channels/{forum_id}/threads/archived/public"
        archived_res = self._make_request(archived_url)
        if archived_res and "threads" in archived_res:
            threads.extend(archived_res["threads"])

        for thread in threads:
            thread_id = thread["id"]
            thread_name = thread.get("name", "Forum Post")
            
            # Skip threads older than or equal to last_seen_id if available
            if last_seen_id and int(thread_id) <= int(last_seen_id):
                continue

            # Get starter message of thread
            msg_url = f"{DISCORD_API_BASE}/channels/{thread_id}/messages"
            msgs = self._make_request(msg_url, params={"limit": 1})
            if msgs and isinstance(msgs, list) and len(msgs) > 0:
                msg = msgs[0]
                parsed = self._parse_message(
                    msg, 
                    guild_id=guild_id, 
                    channel_name=f"{forum_name} -> {thread_name}",
                    thread_title=thread_name
                )
                if parsed:
                    # Use thread ID as post ID for tracking forum threads
                    parsed["id"] = thread_id
                    posts.append(parsed)

        return posts

    def _parse_message(self, msg: Dict[str, Any], guild_id: str, channel_name: str, thread_title: str = "") -> Dict[str, Any]:
        msg_id = msg["id"]
        channel_id = msg["channel_id"]
        author_data = msg.get("author", {})
        author_name = author_data.get("global_name") or author_data.get("username", "Unknown Author")
        content = msg.get("content", "").strip()
        
        # Gather attachments
        attachments = [att.get("url") for att in msg.get("attachments", []) if att.get("url")]
        
        # Gather embed titles and descriptions
        embed_texts = []
        for embed in msg.get("embeds", []):
            title = embed.get("title", "")
            desc = embed.get("description", "")
            if title or desc:
                embed_texts.append(f"{title}\n{desc}".strip())
        
        full_text = content
        if thread_title and thread_title not in full_text:
            full_text = f"Title: {thread_title}\n\n{full_text}"
        if embed_texts:
            full_text = f"{full_text}\n\n" + "\n".join(embed_texts)

        # Discord message permalink
        if guild_id:
            link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
        else:
            link = f"https://discord.com/channels/@me/{channel_id}/{msg_id}"

        return {
            "id": msg_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "author": author_name,
            "content": full_text.strip(),
            "attachments": attachments,
            "link": link,
            "timestamp": msg.get("timestamp", "")
        }
