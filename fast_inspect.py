import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from discord_fetcher import DiscordFetcher
from gemini_filter import GeminiFilter

def run():
    print("=== FAST 7-HOUR DIAGNOSTIC REPORT ===", flush=True)
    fetcher = DiscordFetcher(token=Config.DISCORD_TOKEN, state_file="state.json")
    gemini = GeminiFilter(api_key=Config.GEMINI_API_KEY)

    total_channels = len(Config.DISCORD_CHANNEL_IDS)
    total_posts = 0
    keyword_matches = 0
    hiring_matches = []

    for idx, cid in enumerate(Config.DISCORD_CHANNEL_IDS, 1):
        try:
            # Fetch recent posts directly
            msgs = fetcher._fetch_text_channel_messages(cid, "", "channel", last_seen_id=None)
            if not msgs:
                msgs = fetcher._fetch_forum_posts(cid, "", "forum", last_seen_id=None)

            msgs = msgs[:5]
            total_posts += len(msgs)

            print(f"[{idx}/{total_channels}] Channel {cid} -> {len(msgs)} post(s)", flush=True)

            for p in msgs:
                has_kw = gemini.has_relevant_keywords(p['content'])
                if has_kw:
                    keyword_matches += 1
                    res = gemini.evaluate_post(p['content'], p['author'], p['channel_name'])
                    author_clean = p['author'].encode('ascii', 'ignore').decode('ascii')
                    snip = p['content'][:70].replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')

                    print(f"   -> Post by {author_clean}: \"{snip}...\"", flush=True)
                    print(f"      Match: {res['is_match']} | Role: {res['role_type']} | Reasoning: {res['reasoning']}", flush=True)

                    if res['is_match']:
                        hiring_matches.append((p, res))

        except Exception as e:
            print(f"[{idx}/{total_channels}] Error: {e}", flush=True)

    print("\n================ SUMMARY ================", flush=True)
    print(f"Channels Checked: {total_channels}", flush=True)
    print(f"Total Posts Inspected: {total_posts}", flush=True)
    print(f"Keyword Matches: {keyword_matches}", flush=True)
    print(f"Hiring Matches: {len(hiring_matches)}", flush=True)
    print("==========================================", flush=True)

if __name__ == "__main__":
    run()
