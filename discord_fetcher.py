import requests
import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

class DiscordFetcher:
    def __init__(self, token: str, state_file: str = "state.json"):
        self.token = token.strip()
        self.state_file = state_file
        self.state = self._load_state()
        self.headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
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

    def update_channel_state(self, channel_id: str, message_id: str):
        current_seen = self.state.get(channel_id)
        if not current_seen or int(message_id) > int(current_seen):
            self.state[channel_id] = message_id

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Any:
        resp = requests.get(url, headers=self.headers, params=params)
        
        if resp.status_code in (401, 403) and self.headers["Authorization"].startswith("Bot "):
            raw_token = self.token.replace("Bot ", "").strip()
            alt_headers = {"Authorization": raw_token, "User-Agent": "Mozilla/5.0"}
            resp_alt = requests.get(url, headers=alt_headers, params=params)
            if resp_alt.status_code == 200:
                self.headers = alt_headers
                return resp_alt.json()

        if resp.status_code != 200:
            logger.debug(f"Discord API request {url} returned HTTP {resp.status_code}")
            return None
        return resp.json()

    def fetch_channel_info(self, channel_id: str) -> Dict[str, Any]:
        url = f"{DISCORD_API_BASE}/channels/{channel_id}"
        res = self._make_request(url)
        return res if isinstance(res, dict) else {}

    def fetch_new_posts_from_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Dual-mode fetcher: checks both standard text messages and forum threads for the channel.
        Removes dependency on restricted /channels/{id} endpoint.
        """
        last_seen_id = self.state.get(channel_id)
        channel_info = self.fetch_channel_info(channel_id)
        channel_name = channel_info.get("name", channel_id)
        guild_id = channel_info.get("guild_id", "")

        # If channel is untracked (first run/restart), initialize baseline state with latest message ID and do NOT send old posts
        if not last_seen_id:
            latest_id = self._get_latest_post_id_for_channel(channel_id, guild_id, channel_name)
            if latest_id:
                logger.info(f"Channel {channel_id} untracked. Initializing baseline state to latest message {latest_id}")
                self.state[channel_id] = latest_id
                self.save_state()
            return []

        posts = []

        # 1. Try standard text channel messages
        text_msgs = self._fetch_text_channel_messages(channel_id, guild_id, channel_name, last_seen_id)
        if text_msgs:
            posts.extend(text_msgs)

        # 2. Try forum threads (if channel is a forum or has threads)
        forum_posts = self._fetch_forum_posts(channel_id, guild_id, channel_name, last_seen_id)
        if forum_posts:
            posts.extend(forum_posts)

        # Remove duplicate post IDs if any
        unique_posts = {}
        for p in posts:
            unique_posts[p["id"]] = p

        sorted_posts = list(unique_posts.values())
        sorted_posts.sort(key=lambda p: int(p["id"]))
        return sorted_posts

    def _get_latest_post_id_for_channel(self, channel_id: str, guild_id: str, channel_name: str) -> str:
        """
        Fetches the current most recent post/thread ID for a channel to set baseline state.
        """
        candidate_ids = []
        
        # Check text channel latest message
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        raw_msgs = self._make_request(url, params={"limit": 1})
        if raw_msgs and isinstance(raw_msgs, list) and len(raw_msgs) > 0:
            candidate_ids.append(int(raw_msgs[0]["id"]))

        # Check forum archived threads latest
        archived_url = f"{DISCORD_API_BASE}/channels/{channel_id}/threads/archived/public"
        archived_res = self._make_request(archived_url)
        if archived_res and "threads" in archived_res:
            for t in archived_res.get("threads", []):
                candidate_ids.append(int(t["id"]))

        if candidate_ids:
            return str(max(candidate_ids))
        return ""

    def _fetch_text_channel_messages(self, channel_id: str, guild_id: str, channel_name: str, last_seen_id: str) -> List[Dict[str, Any]]:
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        params = {"limit": 50}
        
        if last_seen_id:
            params["after"] = last_seen_id
            params["limit"] = 100
        
        raw_msgs = self._make_request(url, params=params)
        if not raw_msgs or not isinstance(raw_msgs, list):
            return []

        if not last_seen_id:
            raw_msgs = raw_msgs[:5]

        posts = []
        for msg in raw_msgs:
            parsed = self._parse_message(msg, guild_id=guild_id, channel_name=channel_name)
            if parsed:
                posts.append(parsed)
        return posts

    def _fetch_forum_posts(self, forum_id: str, guild_id: str, forum_name: str, last_seen_id: str) -> List[Dict[str, Any]]:
        posts = []
        threads = []

        if guild_id:
            active_url = f"{DISCORD_API_BASE}/guilds/{guild_id}/threads/active"
            active_res = self._make_request(active_url)
            if active_res and "threads" in active_res:
                threads.extend([t for t in active_res["threads"] if t.get("parent_id") == forum_id])

        archived_url = f"{DISCORD_API_BASE}/channels/{forum_id}/threads/archived/public"
        archived_res = self._make_request(archived_url)
        if archived_res and "threads" in archived_res:
            threads.extend([t for t in archived_res.get("threads", []) if t.get("parent_id") == forum_id])

        # Filter out threads older than or equal to last_seen_id
        valid_threads = []
        for t in threads:
            t_id = t["id"]
            if last_seen_id and int(t_id) <= int(last_seen_id):
                continue
            valid_threads.append(t)

        valid_threads.sort(key=lambda t: int(t["id"]), reverse=True)
        valid_threads = valid_threads[:15]

        for thread in valid_threads:
            thread_id = thread["id"]
            thread_name = thread.get("name", "Forum Post")

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
                    parsed["id"] = thread_id
                    posts.append(parsed)

        return posts

    def _parse_message(self, msg: Dict[str, Any], guild_id: str, channel_name: str, thread_title: str = "") -> Dict[str, Any]:
        msg_id = msg["id"]
        channel_id = msg["channel_id"]
        author_data = msg.get("author", {})
        author_name = author_data.get("global_name") or author_data.get("username", "Unknown Author")
        content = msg.get("content", "").strip()
        
        attachments = [att.get("url") for att in msg.get("attachments", []) if att.get("url")]
        
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
