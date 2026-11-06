CLOSED_PHRASES = [
    "job has been filled",
    "position has been filled",
    "no longer accepting applications",
    "this job is no longer available",
    "job is no longer available",
    "posting has expired",
    "job posting has expired",
    "job expired",
    "vacancy closed",
    "position closed",
    "position is closed",
    "no longer active",
    "applications are closed",
    "no longer accepting",
    "this position is no longer",
    "job not found",
    "page not found",
    "requisition has been closed",
    "this requisition is no longer",
    "we are no longer hiring for this role",
    "this vacancy is closed",
]


def check_availability(status_code, page_text):
    """
    Decide whether a scraped job page represents an active listing.
    Checked in two ways:
      1. HTTP status: a 404 / 410 is a hard "gone".
      2. Text content: many ATS platforms return HTTP 200 but render a
         "this job is no longer available" message on the page itself.
    """

    if status_code in (404, 410):
        return {
            "status": "closed",
            "reason": f"The page returned HTTP {status_code}, indicating the listing no longer exists.",
        }

    text_lower = (page_text or "").lower()

    for phrase in CLOSED_PHRASES:
        if phrase in text_lower:
            return {
                "status": "closed",
                "reason": f"The page text indicates the listing is closed (matched: \"{phrase}\").",
            }

    return {
        "status": "active",
        "reason": "No closure indicators were detected on the page.",
    }
