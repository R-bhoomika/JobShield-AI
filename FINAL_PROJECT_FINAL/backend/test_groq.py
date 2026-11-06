"""
Run this ONCE to check that your Groq key works:

    python test_groq.py

It reads GROQ_API_KEY from the .env file in the same folder (or the folder
you run it from) and asks Groq for a short answer.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GROQ_API_KEY")

if not key:
    print("❌ GROQ_API_KEY not found. Add this line to your .env file:")
    print("   GROQ_API_KEY=your_key_here")
    raise SystemExit(1)

r = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user",
             "content": "In 2 simple sentences, why is asking for a registration fee in a job offer a scam sign?"}
        ],
        "max_tokens": 120,
    },
    timeout=15,
)

print("Status:", r.status_code)

if r.status_code == 200:
    print("✅ Groq works! Answer:\n")
    print(r.json()["choices"][0]["message"]["content"])
elif r.status_code == 401:
    print("❌ Key is wrong or expired. Make a new key at console.groq.com")
elif r.status_code == 429:
    print("⏳ Rate limit reached. Wait a minute and try again.")
else:
    print("❌ Problem:", r.text[:300])
