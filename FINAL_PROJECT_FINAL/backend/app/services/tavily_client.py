import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# NOTE: we no longer hard-crash the whole backend if the key is missing.
# Instead every service that needs Tavily checks `tavily_client is None`
# and degrades gracefully (returns "unknown" instead of raising),
# so the rest of the app (ML prediction, Gemini analysis) keeps working
# even if this one integration isn't configured.
if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
else:
    print("[WARN] TAVILY_API_KEY not found in .env — web verification features will be limited.")
    tavily_client = None
