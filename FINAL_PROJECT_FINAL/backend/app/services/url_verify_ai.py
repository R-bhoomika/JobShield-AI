from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=_api_key) if _api_key else None


def verify_url_ai(url):

    if client is None:
        return {
            "company": "",
            "official": False,
            "trust_score": 0,
            "status": "Gemini Unavailable",
            "reason": "GEMINI_API_KEY is missing from .env.",
            "red_flags": [],
        }

    prompt = f"""
You are a cybersecurity expert.

Analyze this company website URL.

URL:
{url}

Determine:

1. Company Name
2. Is this the official company website?
3. Trust Score (0-100)
4. Status (Verified or Suspicious)
5. Explain why.
6. Mention any red flags.

Return ONLY valid JSON.

{{
  "company": "",
  "official": true,
  "trust_score": 95,
  "status": "Verified",
  "reason": "",
  "red_flags": []
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = (
            response.text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        return json.loads(text)

    except Exception as e:
        return {
            "company": "",
            "official": False,
            "trust_score": 0,
            "status": "Gemini Error",
            "reason": str(e),
            "red_flags": []
        }