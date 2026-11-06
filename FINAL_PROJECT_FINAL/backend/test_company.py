import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily = None

if TAVILY_API_KEY:
    tavily = TavilyClient(api_key=TAVILY_API_KEY)


def verify_company(company_name, website_from_jd="", linkedin_from_jd=""):

    company_name = company_name.strip()

    if not company_name:
        return {
            "company": "Company information not available",
            "website": "",
            "website_found": False,
            "linkedin": "",
            "linkedin_found": False,
            "trust_score": 0
        }

    # =====================================================
    # FIRST: USE WEBSITE/LINKEDIN FOUND DIRECTLY IN JD
    # =====================================================

    website = website_from_jd.strip()
    linkedin = linkedin_from_jd.strip()

    # =====================================================
    # IF WEBSITE IS NOT IN JD → SEARCH WITH TAVILY
    # =====================================================

    if not website and tavily:

        try:

            response = tavily.search(
                query=f'"{company_name}" official company website',
                search_depth="basic",
                max_results=5
            )

            for item in response.get("results", []):

                url = item.get("url", "")

                if not url:
                    continue

                blocked = [
                    "linkedin.com",
                    "facebook.com",
                    "instagram.com",
                    "twitter.com",
                    "x.com",
                    "youtube.com",
                    "glassdoor.com",
                    "indeed.com",
                    "naukri.com",
                    "ambitionbox.com",
                    "wikipedia.org"
                ]

                if any(domain in url.lower() for domain in blocked):
                    continue

                website = url
                break

        except Exception as e:

            print("Tavily website search error:", e)

    # =====================================================
    # IF LINKEDIN IS NOT IN JD → SEARCH WITH TAVILY
    # =====================================================

    if not linkedin and tavily:

        try:

            response = tavily.search(
                query=f'"{company_name}" LinkedIn company',
                search_depth="basic",
                max_results=5
            )

            for item in response.get("results", []):

                url = item.get("url", "")

                if "linkedin.com/company/" in url.lower():

                    linkedin = url
                    break

        except Exception as e:

            print("Tavily LinkedIn search error:", e)

    # =====================================================
    # TRUST SCORE
    # =====================================================

    trust_score = 0

    if website:
        trust_score += 50

    if linkedin:
        trust_score += 40

    if website and linkedin:
        trust_score += 10

    # =====================================================
    # RETURN
    # =====================================================

    return {
        "company": company_name,

        "website": website,
        "website_found": bool(website),

        "linkedin": linkedin,
        "linkedin_found": bool(linkedin),

        "trust_score": trust_score
    }