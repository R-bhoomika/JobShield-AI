import re
from urllib.parse import urlparse

from backend.app.services.tavily_client import tavily_client

# How close (in characters) a scam/fraud word must be to the company name
# for the page to count as "about this company".
PROXIMITY_CHARS = 80

# "This company IS fake" signals.
# NOTE: "fraud" alone is not enough -- real companies (like Oracle) sell
# "fraud detection / prevention" products, so those phrases are ignored.
STRONG_PATTERNS = [
    r"\bscam(?:s|mer|mers)?\b",
    r"\bfraud(?:ulent)?\b(?!\s+(?:detection|prevention|management|analytics|investigation|"
    r"risk|monitoring|protection|control|solution|solutions|software|system|systems|"
    r"platform|service|services))",
    r"\bfake\s+(?:job|company|firm|employer)",
    r"\bnot\s+legit",
    r"\billegit",
    r"\brip[\s-]?off\b",
]

# Softer "people had a bad experience" signals.
NEGATIVE_PATTERNS = [
    r"\bcomplaints?\b",
    r"\bcheated\b",
    r"\bduped\b",
    r"\bbeware\b",
    r"\bmoney\s+asked\b",
]

# Words that mean "scammers USE this company's name", i.e. the company is
# real and is being impersonated. That is NOT the same as "company is fake".
IMPERSONATION_PATTERNS = [
    r"impersonat",
    r"\bpos(?:e|es|ed|ing)\s+as\b",
    r"\bpretend",
    r"\bclaiming\s+to\s+be\b",
    r"\bin\s+the\s+name\s+of\b",
    r"\busing\s+the\s+name\b",
    r"\bon\s+behalf\s+of\b",
    r"\bfake\s+(?:recruiter|recruiters|offer|offers|offer\s+letter|job\s+offers?|hr|interview|interviews|email|emails|website|websites|domain|domains)\b",
    r"\bphishing\b",
    r"\bspoof",
    r"\bfalsely\s+(?:claim|claiming)",
    r"\bfake\s+jobs?\s+(?:offers?|postings?|ads?|advertisements?|messages?)\s+(?:using|in|from|claiming)",
]

COMPANY_STOPWORDS = {
    "pvt", "ltd", "limited", "llp", "llc", "inc", "incorporated",
    "corporation", "corp", "technologies", "technology", "tech",
    "solutions", "systems", "services", "group", "co", "company",
    "private", "india", "the", "and", "global",
}

# A strong "fake company" flag needs at least this many different websites.
MIN_STRONG_SOURCES = 2
# Soft "negative feedback" is weaker evidence, so ask for more.
MIN_NEGATIVE_SOURCES = 3


def _empty_result():
    return {
        "checked": False,
        "fraud_reports_found": False,
        "impersonation_risk": False,
        "reasons": [],
    }


def _company_tokens(company_name):
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (company_name or "").lower())
    tokens = [t for t in cleaned.split() if len(t) >= 3 and t not in COMPANY_STOPWORDS]
    # if the name was ONLY stopwords (e.g. "Global Tech"), fall back to all words
    if not tokens:
        tokens = [t for t in cleaned.split() if len(t) >= 3]
    return tokens


def _positions(pattern_list, text):
    spots = []
    for pattern in pattern_list:
        spots.extend(m.start() for m in re.finditer(pattern, text))
    return spots


def _company_positions(tokens, text):
    spots = []
    for token in tokens:
        spots.extend(m.start() for m in re.finditer(r"\b" + re.escape(token), text))
    return spots


def _near(spots_a, spots_b, distance=PROXIMITY_CHARS):
    return any(abs(a - b) <= distance for a in spots_a for b in spots_b)


def _domain(url):
    try:
        netloc = urlparse(url or "").netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def check_fraud_signals(company_name):
    """
    Search the open web for scam / fraud-report chatter about a company.

    A result only counts if the scam/fraud word appears NEXT TO the company
    name (not just somewhere on the same page), and pages that are about
    scammers *pretending to be* the company are treated as "impersonation
    risk" instead of "company is fake". A real, reputable company is often
    impersonated by fake recruiters -- that must not mark the company itself
    as fake.

    Returns AT MOST one short, plain-language reason.
    """

    company_name = (company_name or "").strip()

    if not company_name:
        return _empty_result()

    if tavily_client is None:
        result = _empty_result()
        result["error"] = "Web fraud-signal search is unavailable (TAVILY_API_KEY not configured)."
        return result

    try:
        response = tavily_client.search(
            query=f'"{company_name}" scam OR fraud OR "fake company" complaints reviews',
            search_depth="basic",
            max_results=8,
        )
        results = response.get("results", [])

    except Exception as e:
        result = _empty_result()
        result["error"] = str(e)
        return result

    tokens = _company_tokens(company_name)

    strong_sources = set()
    negative_sources = set()
    impersonation_sources = set()

    for item in results:
        title = (item.get("title") or "").lower()
        content = (item.get("content") or "").lower()
        combined = f"{title} {content}"
        source = _domain(item.get("url")) or combined[:40]

        company_spots = _company_positions(tokens, combined)

        # Skip sources that don't mention this company at all.
        if tokens and not company_spots:
            continue

        strong_spots = _positions(STRONG_PATTERNS, combined)
        negative_spots = _positions(NEGATIVE_PATTERNS, combined)
        is_impersonation = any(re.search(p, combined) for p in IMPERSONATION_PATTERNS)

        strong_near = _near(company_spots, strong_spots)
        negative_near = _near(company_spots, negative_spots)

        if not strong_near and not negative_near:
            continue

        if is_impersonation:
            # Scammers are using this company's name -> company is real.
            impersonation_sources.add(source)
            continue

        if strong_near:
            strong_sources.add(source)
        elif negative_near:
            negative_sources.add(source)

    if len(strong_sources) >= MIN_STRONG_SOURCES:
        reasons = ["This company has been reported as fake based on online sources."]
    elif len(negative_sources) >= MIN_NEGATIVE_SOURCES:
        reasons = ["Negative feedback about this company was found online."]
    else:
        reasons = []

    return {
        "checked": True,
        "fraud_reports_found": bool(reasons),
        # True when fake recruiters are reported to use this company's name.
        # This does NOT mean the company is fake.
        "impersonation_risk": bool(impersonation_sources) and not reasons,
        "reasons": reasons,
    }
