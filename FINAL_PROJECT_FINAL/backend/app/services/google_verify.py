import os
import requests

from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"

print("Loading:", env_path)

load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("GEMINI_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

print("API:", API_KEY)
print("CX:", SEARCH_ENGINE_ID)