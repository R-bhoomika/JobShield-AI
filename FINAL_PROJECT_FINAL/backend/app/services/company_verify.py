import re
from urllib.parse import urlparse

from backend.app.services.tavily_client import tavily_client

BLOCKED_DOMAINS = [
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
    "wellfound.com",
    "crunchbase.com",
    "wikipedia.org",
    # job-board / aggregator / article sites that *republish* listings —
    # never the hiring company's own site, so never treat these as the
    # "official website" even if they show up in search results.
    "foundit.in",
    "shine.com",
    "timesjobs.com",
    "monsterindia.com",
    "monster.com",
    "apna.co",
    "internshala.com",
    "hirist.tech",
    "hirist.com",
    "instahyre.com",
    "cutshort.io",
    "angel.co",
    "freshersworld.com",
    "iimjobs.com",
    "jobcode.in",
    "jooble.org",
    "simplyhired.com",
    "ziprecruiter.com",
    # news / media outlets that write ARTICLES *about* companies and
    # hiring drives — these are publishers, never the employer's own site.
    "economictimes.indiatimes.com",
    "indiatimes.com",
    "timesofindia.indiatimes.com",
    "indianexpress.com",
    "ndtv.com",
    "news18.com",
    "hindustantimes.com",
    "thehindu.com",
    "business-standard.com",
    "moneycontrol.com",
    "livemint.com",
    "businesstoday.in",
    "zeenews.india.com",
    "financialexpress.com",
    "deccanherald.com",
    "thequint.com",
    "yourstory.com",
    "inc42.com",
    # general content / discussion / social platforms
    "medium.com",
    "quora.com",
    "reddit.com",
    "pinterest.com",
    "blogspot.com",
    "wordpress.com",
    "tumblr.com",
    "scribd.com",
    "substack.com",
]


def _empty_result(company_name):
    return {
        "company": company_name or "Unknown",
        "website": "",
        "website_found": False,
        "linkedin": "",
        "linkedin_found": False,
        "trust_score": 0,
        "location": "",
    }


def _registrable_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _is_untrustworthy(url, exclude_domain=""):
    """
    A domain we must never report back as the company's "official
    website"/"LinkedIn" — either a known publisher/social/job-board
    domain, or the very page the listing itself was scraped from (a job
    board or article page is the publisher, not the employer). This is
    applied both to candidates pulled from search results AND to hints
    lifted straight out of the JD/page text — a "Company Website:" line
    scraped from an article page can just as easily point back at that
    article site, so text hints are never trusted blindly.
    """

    if not url:
        return True

    url_lower = url.lower()
    domain = _registrable_domain(url)

    if any(blocked in url_lower for blocked in BLOCKED_DOMAINS):
        return True

    if "google.com" in url_lower:
        return True

    if exclude_domain and domain and (domain == exclude_domain or exclude_domain in url_lower):
        return True

    return False


COMPANY_STOPWORDS = {
    "pvt", "ltd", "limited", "llp", "llc", "inc", "incorporated",
    "corporation", "corp", "technologies", "technology", "tech",
    "solutions", "systems", "services", "group", "co", "company",
    "private", "india", "the", "and", "global",
}


def _company_slug_tokens(company_name):
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (company_name or "").lower())
    return [w for w in cleaned.split() if w not in COMPANY_STOPWORDS and len(w) >= 3]


def _domain_matches_company(url, company_name):
    """
    Best-effort check that a candidate "official website" domain actually
    looks like it belongs to this company, rather than being some other
    unrelated site that merely turned up in the search results (e.g. a
    review aggregator, a partner's site, or another company entirely).
    """

    domain = _registrable_domain(url)
    if not domain:
        return False

    domain_root = domain.split(".")[0]

    for token in _company_slug_tokens(company_name):
        if token in domain_root or domain_root in token:
            return True

    return False


LINKEDIN_NOISE_WORDS = ("job", "career", "recruit", "hiring", "staffing", "placement", "vacanc")


def _linkedin_slug(url):
    """'https://in.linkedin.com/company/Oracle/' -> 'oracle'"""
    m = re.search(r"linkedin\.com/company/([^/?#]+)", (url or "").lower())
    return re.sub(r"[^a-z0-9]", "", m.group(1)) if m else ""


def _linkedin_score(url, company_name):
    """
    How well a LinkedIn company page matches the company we are checking.
    0 = no match (reject). Higher = better match.
    This stops a random page (e.g. a recruitment company) from being
    reported as the company's LinkedIn just because it was the first
    linkedin.com/company/ link in the search results.
    """
    slug = _linkedin_slug(url)
    if len(slug) < 3:
        return 0

    tokens = [re.sub(r"[^a-z0-9]", "", t) for t in _company_slug_tokens(company_name)]
    tokens = [t for t in tokens if t]
    if not tokens:
        return 0

    full_name = "".join(tokens)

    if slug == full_name or slug in tokens:
        score = 100
    elif any(t in slug or slug in t for t in tokens):
        score = 50
    else:
        return 0

    # A slug like "xyz-jobs" / "xyz-careers" is usually a recruiter page,
    # not the company itself -- unless the company name has that word too.
    name_lower = (company_name or "").lower()
    if any(n in slug for n in LINKEDIN_NOISE_WORDS) and not any(n in name_lower for n in LINKEDIN_NOISE_WORDS):
        score -= 40

    return score


def _best_linkedin_match(urls, company_name, min_score=30):
    best_url, best_score = "", 0
    for url in urls:
        if "linkedin.com/company/" not in (url or "").lower():
            continue
        score = _linkedin_score(url, company_name)
        if score > best_score:
            best_url, best_score = url, score
    return best_url if best_score >= min_score else ""


def _extract_location_from_results(results, company_name=""):
    """
    Lightweight heuristic: look for a 'headquartered in <place>' /
    'based in <place>' / 'located in <place>' phrase inside the search
    snippets Tavily already returned -- avoids an extra network call.
    """
    patterns = [
        r"headquartered in ([A-Za-z\s,]{3,40}?)(?:\.|,? and\b|,? with\b|\n|$)",
        r"headquarters (?:is |are )?(?:in|at) ([A-Za-z\s,]{3,40}?)(?:\.|,? and\b|,? with\b|\n|$)",
        r"based in ([A-Za-z\s,]{3,40}?)(?:\.|,? and\b|,? with\b|\n|$)",
        r"located in ([A-Za-z\s,]{3,40}?)(?:\.|,? and\b|,? with\b|\n|$)",
    ]

    tokens = _company_slug_tokens(company_name)

    for result in results:
        content = result.get("content", "") or ""
        title = result.get("title", "") or ""

        # Only trust a snippet that is actually about THIS company. Without
        # this, "based in Oklahoma" from some unrelated page was used.
        if tokens and not any(t in f"{title} {content}".lower() for t in tokens):
            continue

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                loc = match.group(1).strip().rstrip(",").strip()
                if loc:
                    return loc

    return ""


def find_website_in_text(text, company_name):
    """
    Posters / JDs often print the company's own link ("apply at
    https://www.cskm.com/vacancy") without a "Website:" label. Return the
    site root of the first link whose domain looks like the company name.
    Job boards / social sites / news sites are ignored.
    """
    for url in re.findall(r"https?://[^\s\]\)>\"']+", text or "", flags=re.IGNORECASE):
        url = url.rstrip(".,;")
        if _is_untrustworthy(url):
            continue
        if _domain_matches_company(url, company_name):
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def verify_company(company_name, known_website="", known_linkedin="", exclude_domain=""):
    """
    Verify a company's official website + LinkedIn page, and pull its
    primary location. `known_website` / `known_linkedin` are hints already
    pulled straight out of the JD text (e.g. "Company Website: https://...")
    -- if present AND they don't point back at a job-board/article/social
    domain or the scraped page's own domain, we trust and confirm them
    instead of re-searching from scratch. Otherwise we discard the hint
    and fall back to a real web search.

    `exclude_domain` is the domain of the page the JD/URL was scraped
    from (e.g. a job-board article that republished the listing). We
    never want to report that domain back as the company's "official
    website" -- it's the publisher, not the employer.
    """

    company_name = (company_name or "").strip()
    exclude_domain = (exclude_domain or "").lower()
    if exclude_domain.startswith("www."):
        exclude_domain = exclude_domain[4:]

    if not company_name:
        return _empty_result(company_name)

    # Discard any text-extracted hint that turns out to point at a
    # job-board/article/social domain or the source page itself.
    if known_website and _is_untrustworthy(known_website, exclude_domain):
        known_website = ""

    # LinkedIn hint: "linkedin.com" is in BLOCKED_DOMAINS (so the website check
    # above would always throw it away). For LinkedIn we instead keep the hint
    # only if it is a real company page that matches the company name.
    if known_linkedin and not _best_linkedin_match([known_linkedin], company_name):
        known_linkedin = ""

    if tavily_client is None:
        # Degrade gracefully: still return anything we already know from the JD.
        result = _empty_result(company_name)
        if known_website:
            result["website"] = known_website
            result["website_found"] = True
            result["trust_score"] += 50
        if known_linkedin:
            result["linkedin"] = known_linkedin
            result["linkedin_found"] = True
            result["trust_score"] += 40
        return result

    # =====================================================
    # SEARCH FOR OFFICIAL WEBSITE + LINKEDIN + LOCATION
    # =====================================================

    try:
        response = tavily_client.search(
            query=f'"{company_name}" official website LinkedIn headquarters location',
            search_depth="basic",
            max_results=10,
        )
        results = response.get("results", [])

    except Exception as e:
        print("Tavily Error:", e)
        result = _empty_result(company_name)
        result["error"] = str(e)
        return result

    # =====================================================
    # LINKEDIN
    # =====================================================

    linkedin_url = known_linkedin or ""

    if not linkedin_url:
        # 1) LinkedIn-only search (much less noisy than the mixed search above)
        linkedin_candidates = []
        try:
            li_response = tavily_client.search(
                query=f"{company_name} company LinkedIn",
                search_depth="basic",
                max_results=5,
                include_domains=["linkedin.com"],
            )
            linkedin_candidates += [r.get("url", "") for r in li_response.get("results", [])]
        except Exception as e:
            print("LinkedIn search error:", e)

        # 2) also look in the first search results
        linkedin_candidates += [r.get("url", "") for r in results]

        # Only accept a page whose name matches the company. If nothing
        # matches we return empty ("Not Available") instead of a wrong page.
        linkedin_url = _best_linkedin_match(linkedin_candidates, company_name)

    # =====================================================
    # OFFICIAL WEBSITE
    # Prefer a candidate whose domain actually looks like it belongs to
    # this company; only fall back to "first non-blocked result" if
    # nothing matches, so we don't silently hand back some unrelated
    # site (another article, a review page, a partner's domain) as if
    # it were the employer's own website.
    # =====================================================

    website_url = known_website or ""

    if not website_url:
        candidates = [
            result.get("url", "")
            for result in results
            if result.get("url") and not _is_untrustworthy(result.get("url"), exclude_domain)
        ]

        matched = [url for url in candidates if _domain_matches_company(url, company_name)]

        if matched:
            # Only return a domain that plausibly belongs to this company.
            # Never label an unrelated first search result as official.
            website_url = matched[0]
        else:
            website_url = ""

    # =====================================================
    # LOCATION (best-effort from search snippets)
    # =====================================================

    location = _extract_location_from_results(results, company_name)

    # =====================================================
    # TRUST SCORE
    # =====================================================

    trust_score = 0

    if website_url:
        trust_score += 50

    if linkedin_url:
        trust_score += 40

    if website_url and linkedin_url:
        trust_score += 10

    return {
        "company": company_name,
        "website": website_url,
        "website_found": bool(website_url),
        "linkedin": linkedin_url,
        "linkedin_found": bool(linkedin_url),
        "trust_score": trust_score,
        "location": location,
    }
