import json
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeminiFilter:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.use_new_sdk = True
            logger.info("Initialized Google GenAI client.")
        except Exception as e:
            logger.warning(f"Failed to load google.genai, using direct REST requests: {e}")
            self.use_new_sdk = False

    def evaluate_post(self, post_content: str, author: str, channel_name: str) -> Dict[str, Any]:
        """
        Analyzes post content using Gemini to check if it's someone HIRING an Editor or Thumbnail Designer.
        """
        if not post_content or len(post_content.strip()) < 5:
            return {"is_match": False, "role_type": "None", "summary": "", "reasoning": "Post content too short."}

        prompt = f"""You are an expert AI job classifier. Analyze the following Discord post.

Post Author: {author}
Discord Channel: {channel_name}
Post Content:
\"\"\"
{post_content}
\"\"\"

Your Task:
1. Determine if the post author is HIRING, LOOKING FOR, or NEEDING a Video Editor or Thumbnail Designer (or Graphic Designer for YouTube/video thumbnails).
2. CRITICAL DISTINCTION:
   - MATCH (is_match = true): The poster is HIRING / LOOKING TO BUY services (e.g. "Looking for an editor", "Hiring thumbnail designer", "Need someone to edit my videos", "[HIRING] Editor needed", "DM me your portfolio if you make thumbnails").
   - NO MATCH (is_match = false): The poster is SELLING / OFFERING their own services (e.g. "I am a video editor available for work", "For Hire: Thumbnail designer", "DM me if you need an editor").
   - NO MATCH (is_match = false): General conversation, feedback requests, self-promotion, or unrelated topics.

Respond EXCLUSIVELY in valid JSON format with the following fields:
{{
  "is_match": true or false,
  "role_type": "Video Editor" or "Thumbnail Designer" or "Both" or "None",
  "summary": "Concise 1-2 sentence summary of the job offer (budget, style, requirements if mentioned)",
  "reasoning": "Brief explanation why this post is or is not a hiring request"
}}
"""

        model_name = "gemini-3.6-flash"
        max_retries = 3
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                if self.use_new_sdk:
                    return self._evaluate_with_sdk(model_name, prompt)
                else:
                    return self._evaluate_with_rest(model_name, prompt)
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                    logger.warning(f"Gemini API attempt {attempt}/{max_retries} busy ({err_str}). Retrying in {attempt * 2}s...")
                    time.sleep(attempt * 2)
                else:
                    logger.error(f"Gemini API error on attempt {attempt}: {err_str}")
                    break

        return {"is_match": False, "role_type": "None", "summary": "", "reasoning": f"API Error: {str(last_err)}"}

    def _evaluate_with_sdk(self, model_name: str, prompt: str) -> Dict[str, Any]:
        from google.genai import types
        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        if response.text:
            return self._clean_and_parse_json(response.text)
        raise Exception("Empty response from Gemini SDK")

    def _evaluate_with_rest(self, model_name: str, prompt: str) -> Dict[str, Any]:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}
        }
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_and_parse_json(text)
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Gemini response payload: {resp.text}")

    def _clean_and_parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return {
            "is_match": bool(data.get("is_match", False)),
            "role_type": str(data.get("role_type", "None")),
            "summary": str(data.get("summary", "")),
            "reasoning": str(data.get("reasoning", ""))
        }
