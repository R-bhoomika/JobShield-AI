import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    print("❌ TAVILY_API_KEY not found in .env")
    exit()

print("✅ Tavily API key found")

client = TavilyClient(api_key=api_key)

response = client.search(
    query="Microsoft official website LinkedIn company",
    search_depth="basic",
    max_results=5
)

print("\n========== SEARCH RESULTS ==========\n")

for result in response.get("results", []):

    print("--------------------------------")
    print("TITLE:", result.get("title"))
    print("URL:", result.get("url"))
    print("CONTENT:", result.get("content", "")[:300])

print("\n===================================")
print("✅ Tavily test completed")