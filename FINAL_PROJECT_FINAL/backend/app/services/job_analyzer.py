from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

# Get Gemini API key from .env
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(
        api_key=api_key
    )
else:
    print("[WARN] GEMINI_API_KEY is missing. Gemini-based analysis will be disabled.")
    client = None


def analyze_job(description):

    if client is None:
        return {
            "risk_score": 0,
            "verdict": "Gemini Unavailable",
            "red_flags": [],
            "explanation": "GEMINI_API_KEY is missing from .env, so AI analysis could not run.",
            "company_name": "",
            "company_location": "",
        }

    prompt = f"""
You are an AI job fraud detection expert.

Analyze the following job posting.

Job Description:
{description}

IMPORTANT: This text may come from a job-board or article page that
*republishes* a listing (e.g. a site like "jobcode.in" or "naukri.com"
sharing a "Honeywell" opening). Identify the ACTUAL HIRING COMPANY
mentioned inside the posting itself — never the name of the job board,
aggregator, or website that published/shared the article.

Return ONLY valid JSON.

Do NOT use markdown.
Do NOT use ```json.
Do NOT write anything outside the JSON.

Use this exact format:

{{
    "risk_score": 85,
    "verdict": "Likely Fake",
    "red_flags": [
        "Reason 1",
        "Reason 2"
    ],
    "explanation": "Explain why the job is fake or genuine.",
    "company_name": "The actual hiring company's name (not the job board/publisher), or empty string if unclear.",
    "company_location": "Best-guess primary company location (city, country), or empty string if unknown."
}}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # Get Gemini response
        text = response.text.strip()

        # Remove markdown if Gemini accidentally adds it
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        # Convert JSON text to Python dictionary
        result = json.loads(text)

        result.setdefault("company_name", "")
        result.setdefault("company_location", "")

        return result

    except json.JSONDecodeError as e:

        return {
            "risk_score": 0,
            "verdict": "Gemini Error",
            "red_flags": [],
            "explanation": f"Gemini returned invalid JSON: {str(e)}",
            "company_name": "",
            "company_location": "",
        }

    except Exception as e:

        return {
            "risk_score": 0,
            "verdict": "Gemini Error",
            "red_flags": [],
            "explanation": str(e),
            "company_name": "",
            "company_location": "",
        }
