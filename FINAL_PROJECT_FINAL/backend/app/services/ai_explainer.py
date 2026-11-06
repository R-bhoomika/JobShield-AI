"""
JobShield – Generative AI explanation writer.

The risk SCORE and RED FLAGS come from your own rules + ML model (so they
never fail and have no limit). This file only asks a generative AI to WRITE
the explanation in simple words from those verified facts.

By default ONLY Groq (Llama) writes the explanation. If Groq is busy, the
fast model (Llama 3.1 8B) is tried first and the bigger one (Llama 3.3 70B)
second. If both fail, smart_analyzer.py uses its own written explanation, so
the page never shows an error.

(Gemini is OFF by default. To add it as a backup, set AI_PROVIDERS=groq,gemini)

.env settings
    GROQ_API_KEY=...             (free key: console.groq.com)
    AI_PROVIDERS=groq            (default; use groq,gemini to add a backup)
"""

import hashlib
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PROVIDERS = [p.strip().lower() for p in os.getenv("AI_PROVIDERS", "groq").split(",") if p.strip()]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# fast model first (highest free daily limit), bigger model as backup
GROQ_MODELS = [
    ("llama-3.1-8b-instant", "Llama 3.1 · Groq"),
    ("llama-3.3-70b-versatile", "Llama 3.3 · Groq"),
]
GEMINI_MODEL = "gemini-2.5-flash"

TIMEOUT = 12          # seconds per call, so the page never hangs
_cache = {}           # same facts -> same explanation, no extra API call

SYSTEM = (
    "You are JobShield AI. You explain job-scam checks to students in very simple, "
    "direct English. Use ONLY the facts you are given. Do not invent facts, names, "
    "numbers or links. Never say you are an AI. No markdown, no bullet points, no headings."
)


def _prompt(f):
    flags = "\n".join(f"- {x}" for x in f["flags"]) or "- none"
    good = "\n".join(f"- {x}" for x in f["positives"]) or "- none"
    web = (f.get("web_summary") or "").strip()[:350] or "not available"
    excerpt = (f.get("job_text") or "").strip()[:900]

    return f"""Write the explanation for a job-posting safety report.

Facts (already checked, do not change them):
Risk score: {f['risk']} out of 100 (0 = safe, 100 = very risky)
Verdict: {f['verdict']}
Company: {f.get('company') or 'not named in the posting'}
Warning signs found:
{flags}
Good signs found:
{good}
Web search summary about the company: {web}

Start of the job posting (for context only):
\"\"\"{excerpt}\"\"\"

Rules for your answer:
- 3 to 5 short sentences, plain text only.
- The FIRST sentence must be the main finding (for example the most serious warning sign, or that no strong scam signs were found).
- Then explain why it matters, using the facts above.
- End with one clear action the person should take.
- If the risk score is under 35, do not scare the reader."""


def _clean(text):
    text = re.sub(r"[*_`#>]+", "", text or "")
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 1000:
        text = text[:1000].rsplit(". ", 1)[0].rstrip(".") + "."
    return text


def _call_groq(user):
    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    last = "no answer"
    for model, label in GROQ_MODELS:
        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 320,
                },
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                text = _clean(r.json()["choices"][0]["message"]["content"])
                if text:
                    return text, label
                last = f"{model}: empty answer"
            else:
                last = f"{model}: {r.status_code} {r.text[:100]}"
        except Exception as e:
            last = f"{model}: {e}"

    raise RuntimeError(last)


def _call_gemini(user):
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    from google import genai

    client = genai.Client(api_key=GEMINI_KEY)
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=f"{SYSTEM}\n\n{user}")
    text = _clean(resp.text)
    if not text:
        raise RuntimeError("empty answer")
    return text, "Gemini 2.5 Flash"


_CALLERS = {"groq": _call_groq, "gemini": _call_gemini}


def generate_explanation(facts):
    """
    facts = {risk, verdict, company, flags[], positives[], web_summary, job_text}
    Returns {"text": "...", "by": "Llama 3.1 · Groq"} or None if every provider failed.
    """
    key = hashlib.sha256(
        repr((facts["risk"], facts["verdict"], facts.get("company"), facts["flags"], facts["positives"])).encode()
    ).hexdigest()

    if key in _cache:
        return _cache[key]

    user = _prompt(facts)

    for name in PROVIDERS:
        caller = _CALLERS.get(name)
        if caller is None:
            continue
        try:
            text, label = caller(user)
            result = {"text": text, "by": label}
            if len(_cache) > 200:
                _cache.clear()
            _cache[key] = result
            return result
        except Exception as e:
            print(f"[AI explainer] {name} failed -> trying next. Reason: {str(e)[:160]}")

    return None
