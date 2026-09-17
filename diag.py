import sys
import os
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter

def run_diag():
    print("=== LIVE DIAGNOSTIC CHECK ACROSS ALL 34 CHANNELS ===", flush=True)
    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file="state.json")
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)

    total_posts = 0
    keyword_matched_posts = 0
    hiring_matches = []

    for idx, cid in enumerate(Config.DISCORD_CHANNEL_IDS, 1):
        try:
            # Fetch recent posts
            posts = fetcher._fetch_text_channel_messages(cid, "", f"channel_{cid}", last_seen_id=None)
            if not posts:
                # Try forum threads
                posts = fetcher._fetch_forum_posts(cid, "", f"forum_{cid}", last_seen_id=None)

            posts = posts[:5]
            total_posts += len(posts)

            for p in posts:
                has_kw = gemini.has_relevant_keywords(p['content'])
                if has_kw:
                    keyword_matched_posts += 1
                    res = gemini.evaluate_post(p['content'], p['author'], p['channel_name'])
                    author_clean = p['author'].encode('ascii', 'ignore').decode('ascii')
                    chan_clean = p['channel_name'].encode('ascii', 'ignore').decode('ascii')
                    snip = p['content'][:70].replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')

                    print(f"[{idx}/34] Post in #{chan_clean} by {author_clean}:", flush=True)
                    print(f"  Snippet: \"{snip}...\"", flush=True)
                    print(f"  Gemini Decision -> Match: {res['is_match']} | Role: {res['role_type']} | Reasoning: {res['reasoning']}\n", flush=True)

                    if res['is_match']:
                        hiring_matches.append((p, res))

        except Exception as e:
            print(f"[{idx}/34] Error on channel {cid}: {e}", flush=True)

    print("================ DIAGNOSTIC SUMMARY ================", flush=True)
    print(f"Total Recent Posts Inspected: {total_posts}", flush=True)
    print(f"Posts Containing Editing/Thumbnail Keywords: {keyword_matched_posts}", flush=True)
    print(f"Posts Classified by Gemini as HIRING Requests: {len(hiring_matches)}", flush=True)
    print("====================================================", flush=True)

if __name__ == "__main__":
    run_diag()
