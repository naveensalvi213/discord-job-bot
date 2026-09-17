import sys
import os
import requests
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter

def inspect():
    print("=== 7-HOUR DISCORD POSTS DIAGNOSTIC REPORT ===", flush=True)
    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file="state.json")
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)

    total_channels = len(Config.DISCORD_CHANNEL_IDS)
    total_posts_inspected = 0
    keyword_matched_posts = []
    hiring_matches = []

    for idx, cid in enumerate(Config.DISCORD_CHANNEL_IDS, 1):
        try:
            info = fetcher.fetch_channel_info(cid)
            cname = info.get("name", str(cid)).encode("ascii", "ignore").decode("ascii")
            ctype = info.get("type", 0)

            # Fetch recent posts without last_seen_id filter to inspect all recent activity
            if ctype == 15: # Forum
                posts = fetcher._fetch_forum_posts(cid, info.get("guild_id", ""), cname, last_seen_id=None)[:10]
            else:
                posts = fetcher._fetch_text_channel_messages(cid, info.get("guild_id", ""), cname, last_seen_id=None)[:10]

            total_posts_inspected += len(posts)

            for p in posts:
                has_kw = gemini.has_relevant_keywords(p["content"])
                if has_kw:
                    res = gemini.evaluate_post(p["content"], p["author"], p["channel_name"])
                    author_clean = p["author"].encode("ascii", "ignore").decode("ascii")
                    snip = p["content"][:80].replace("\n", " ").encode("ascii", "ignore").decode("ascii")
                    item = {
                        "channel_id": cid,
                        "channel_name": cname,
                        "author": author_clean,
                        "snippet": snip,
                        "post_id": p["id"],
                        "eval": res
                    }
                    keyword_matched_posts.append(item)
                    if res.get("is_match"):
                        hiring_matches.append(item)

        except Exception as e:
            print(f"[{idx}/{total_channels}] Error checking channel {cid}: {e}", flush=True)

    print("\n================ DIAGNOSTIC FINDINGS ================", flush=True)
    print(f"Total Channels Checked: {total_channels}", flush=True)
    print(f"Total Posts Inspected Across 34 Channels: {total_posts_inspected}", flush=True)
    print(f"Posts Matching Target Keywords ({gemini.__class__.__name__}): {len(keyword_matched_posts)}", flush=True)
    print(f"Posts Classified as HIRING Requests: {len(hiring_matches)}", flush=True)
    print("=====================================================\n", flush=True)

    if keyword_matched_posts:
        print("--- KEYWORD MATCHED POSTS & GEMINI EVALUATIONS ---", flush=True)
        for i, item in enumerate(keyword_matched_posts, 1):
            ev = item["eval"]
            print(f"{i}. Channel #{item['channel_name']} | Author: {item['author']}", flush=True)
            print(f"   Snippet: \"{item['snippet']}...\"", flush=True)
            print(f"   Gemini Result: match={ev.get('is_match')} | role={ev.get('role_type')} | summary: {ev.get('summary')}", flush=True)
            print(f"   Reasoning: {ev.get('reasoning')}\n", flush=True)

if __name__ == "__main__":
    inspect()
