import requests
from bs4 import BeautifulSoup

from backend.app.services.availability_service import check_availability

HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137 Safari/537.36"
}


def extract_job_data(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        soup = BeautifulSoup(response.text, "html.parser")

        title = (
            soup.title.get_text(strip=True)
            if soup.title
            else "Unknown Company"
        )

        # Remove unnecessary elements
        for tag in soup(["script", "style", "noscript", "header", "footer"]):
            tag.decompose()

        description = soup.get_text(" ", strip=True)

        # -----------------------------------------------------
        # AVAILABILITY CHECK
        # Run this BEFORE the "too short" bail-out below, since a
        # closed listing often renders a short "no longer available"
        # message rather than a full job description.
        # -----------------------------------------------------

        availability = check_availability(response.status_code, description)

        if response.status_code != 200:
            return {
                "error": f"Unable to access webpage (HTTP {response.status_code})",
                "job_status": availability["status"],
                "job_status_reason": availability["reason"],
            }

        if availability["status"] == "closed":
            return {
                "error": "Job is no longer available",
                "job_status": "closed",
                "job_status_reason": availability["reason"],
                "title": title,
            }

        if len(description) < 200:
            return {
                "error":
                "Job description could not be extracted. This website may require JavaScript or login.",
                "job_status": "unknown",
                "job_status_reason": "Page content was too short to analyze.",
            }

        return {
            "title": title,
            "description": description[:8000],
            "job_status": availability["status"],
            "job_status_reason": availability["reason"],
        }

    except Exception as e:

        return {
            "error": str(e),
            "job_status": "unknown",
            "job_status_reason": "The page could not be reached.",
        }
