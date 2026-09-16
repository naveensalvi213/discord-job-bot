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
        last_seen_id = self.state.get(channel_id)
        channel_info = self.fetch_channel_info(channel_id)
        channel_name = channel_info.get("name", channel_id)
        guild_id = channel_info.get("guild_id", "")
        channel_type = channel_info.get("type", 0)

        posts = []

        if channel_type == 15:
            posts.extend(self._fetch_forum_posts(channel_id, guild_id, channel_name, last_seen_id))
        else:
            posts.extend(self._fetch_text_channel_messages(channel_id, guild_id, channel_name, last_seen_id))

        posts.sort(key=lambda p: int(p["id"]))

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

        # Sort threads newest first and limit to 10 most recent
        threads.sort(key=lambda t: int(t["id"]), reverse=True)
        threads = threads[:10]

        for thread in threads:
            thread_id = thread["id"]
            thread_name = thread.get("name", "Forum Post")
            
            if last_seen_id and int(thread_id) <= int(last_seen_id):
                continue

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
