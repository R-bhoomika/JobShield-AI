import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from fastapi import APIRouter, Form, File, UploadFile
import joblib

from backend.app.schemas.job import JobRequest
from backend.app.schemas.url import UrlRequest

from backend.app.services.smart_analyzer import analyze_job, guess_company, guess_location
from backend.app.services.job_scraper import extract_job_data
from backend.app.services.company_verify import verify_company, find_website_in_text
from backend.app.services.url_verify_ai import verify_url_ai
from backend.app.services.fraud_service import check_fraud_signals
from backend.app.services.consistency_service import compare_companies
from backend.app.services.ocr_service import extract_text_from_image


router = APIRouter()


# =========================================================
# LOAD ML MODEL
# =========================================================

model = joblib.load("ml/model/job_detector.pkl")
vectorizer = joblib.load("ml/model/vectorizer.pkl")


# =========================================================
# EXTRACT COMPANY + WEBSITE + LINKEDIN FROM JOB DESCRIPTION
# =========================================================


def _valid_extracted_company(name):
    """Reject OCR mistakes such as 'Noida Consulting' and poster labels."""
    name = re.sub(r"\s+", " ", (name or "")).strip(" .,:;|-")
    if not name:
        return ""

    invalid_starts = {
        "noida", "bengaluru", "bangalore", "mumbai", "delhi",
        "hyderabad", "chennai", "pune", "gurgaon", "gurugram",
        "kolkata", "mysuru", "mysore", "location", "eligibility",
        "experience", "industry", "associate", "freshers",
        "company", "job", "role", "information",
    }
    if name.split()[0].lower() in invalid_starts:
        return ""

    invalid_exact = {
        "consulting", "information technology", "technology consulting",
        "job role", "company verification",
    }
    if name.lower() in invalid_exact:
        return ""

    return name


def extract_company_details(text):

    company_name = ""
    website = ""
    linkedin = ""

    if not text:
        return {"company": "", "website": "", "linkedin": ""}

    # COMPANY NAME: use explicit labels first.
    company_patterns = [
        r"^\s*company\s+name\s*:\s*(.+)$",
        r"^\s*company\s*:\s*(.+)$",
    ]

    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            candidate = match.group(1).splitlines()[0].strip()
            company_name = _valid_extracted_company(candidate)
            if company_name:
                break

    # If OCR did not provide a trustworthy labelled company, use the
    # poster-aware company detector (logo/repeated brand/company patterns).
    if not company_name:
        company_name = _valid_extracted_company(guess_company(text))

    # OFFICIAL WEBSITE: only capture explicitly printed URLs here.
    website_patterns = [
        r"official\s+company\s+website\s*:?\s*(https?://[^\s\]\)]+)",
        r"official\s+website\s*:?\s*(https?://[^\s\]\)]+)",
        r"company\s+website\s*:?\s*(https?://[^\s\]\)]+)",
    ]

    for pattern in website_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            website = match.group(1).strip().rstrip(").,;")
            break

    # LINKEDIN: only capture an explicitly printed company-page URL.
    linkedin_patterns = [
        r"linkedin\s+company\s+page\s*:?\s*(https?://[^\s\]\)]+)",
        r"linkedin\s*:?\s*(https?://[^\s\]\)]+)",
        r"linkedin\s+page\s*:?\s*(https?://[^\s\]\)]+)",
    ]

    for pattern in linkedin_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            linkedin = match.group(1).strip().rstrip(").,;")
            break

    return {
        "company": company_name,
        "website": website,
        "linkedin": linkedin,
    }


# =========================================================
# LOCATION FALLBACK — read an explicit "Location:" line
# straight out of the JD/page text before we ever fall back
# to a web search.
# =========================================================


LOCATION_PATTERNS = [
    r"(?:job\s+)?locations?\s*:\s*(.+)",
    r"work\s+locations?\s*:\s*(.+)",
    r"office\s+locations?\s*:\s*(.+)",
    r"based\s+in\s*:?\s*([A-Za-z\s,]+)",
]


def extract_location_from_text(text):

    if not text:
        return ""

    # First use the poster-aware detector. It returns recognized city
    # names rather than the entire OCR row containing eligibility/role.
    location = guess_location(text)
    if location:
        return location

    # Fallback for ordinary text job descriptions.
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            loc = match.group(1).strip().splitlines()[0].strip(" .,")
            if loc and len(loc) < 150:
                return loc

    return ""


# =========================================================
# RESOLVING THE REAL HIRING COMPANY
# Job-board / article pages (e.g. a site republishing a "Honeywell"
# opening) often don't have a clean "Company:" line, and their <title>
# tag is usually the site's own branding, not the employer. So we never
# trust a raw page title as the company name — only a cleaned version,
# used strictly as a last resort after the JD text itself and Gemini's
# own extraction (which reads the full posting, not just the title).
# =========================================================

JOB_BOARD_BRANDS = [
    "jobcode", "naukri", "linkedin", "indeed", "glassdoor", "foundit",
    "shine", "timesjobs", "monster", "apna", "internshala", "hirist",
    "instahyre", "cutshort", "wellfound", "angel", "freshersworld",
    "iimjobs", "jooble", "simplyhired", "ziprecruiter",
]

GENERIC_JOB_WORDS = [
    "job portal", "official site", "official website", "apply now",
    "job openings", "opportunities", "opportunity", "vacancies",
    "vacancy", "careers", "career", "hiring", "jobs",
]


def clean_title_as_company(title):

    if not title:
        return ""

    # Page titles are usually "Role at Company | Site Name" or
    # "Company hiring Role - Site". Keep only the piece before the
    # first separator, which is most often the role/company chunk.
    t = re.split(r"[\|\u2013\u2014:]", title)[0].strip()

    if not t:
        return ""

    lowered = t.lower()

    # A recognizable job-board/aggregator brand name leaking into this
    # chunk means we can't trust it as a company name at all.
    if any(brand in lowered for brand in JOB_BOARD_BRANDS):
        return ""

    # Generic job-listing words ("Careers", "Hiring", "Job Openings")
    # commonly sit next to the company name rather than replacing it —
    # strip just those words instead of discarding the whole title.
    for word in GENERIC_JOB_WORDS:
        t = re.sub(re.escape(word), "", t, flags=re.IGNORECASE)

    t = re.sub(r"\s+", " ", t).strip(" -\u2013\u2014:")

    return t


def get_url_domain(url):

    if not url:
        return ""

    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def resolve_company_name(regex_company, ai_result, url_data):
    """
    Priority order for "who is actually hiring":
      1. An explicit "Company:" line pulled straight out of the JD text.
      2. Gemini's own extraction, which reads the full posting body and
         is specifically told to ignore job-board/publisher branding.
      3. A cleaned version of the scraped page's <title>, only as a
         last resort, and only if it doesn't look like site branding.
    """

    if regex_company:
        return regex_company

    gemini_name = ""
    if isinstance(ai_result, dict):
        gemini_name = (ai_result.get("company_name") or "").strip()

    if gemini_name:
        return gemini_name

    if url_data and url_data.get("title"):
        return clean_title_as_company(url_data.get("title"))

    return ""


# =========================================================
# SUSPICIOUS INDICATORS
# =========================================================

def detect_indicators(text, is_fake):

    indicators = []

    if not is_fake:
        return indicators

    suspicious_patterns = {

        "Registration fee detected": [
            "registration fee",
            "processing fee",
            "security deposit"
        ],

        "WhatsApp-only communication": [
            "whatsapp",
            "telegram only"
        ],

        "No interview requirement": [
            "no interview",
            "without interview",
            "direct joining"
        ],

        "Unrealistic income claim": [
            "earn daily",
            "earn money",
            "earn from home",
            "quick money",
            "easy money",
            "instant income",
            "guaranteed income",
            "₹5000 per day",
            "₹10000 per day"
        ],

        "Immediate joining pressure": [
            "join immediately",
            "urgent hiring",
            "limited seats"
        ]
    }

    for message, keywords in suspicious_patterns.items():

        for keyword in keywords:

            if keyword in text:

                # Ignore legitimate statement
                # such as "No registration fee"
                if (
                    keyword == "registration fee"
                    and "no registration fee" in text
                ):
                    continue

                indicators.append(message)

                break

    return indicators


# =========================================================
# COMPANY VERIFICATION
# =========================================================

def get_company_verification(company_details, exclude_domain=""):

    company_name = company_details["company"]
    website = company_details["website"]
    linkedin = company_details["linkedin"]

    if not company_name:
        return None

    return verify_company(company_name, website, linkedin, exclude_domain)


# =========================================================
# OUTPUT LINKS
# The top-level "official_website"/"linkedin" fields must always mirror
# the VERIFIED company result (checked against job-board/article/social
# domains) rather than the raw regex hint pulled straight out of the JD
# text -- otherwise an article page's own link can leak through as if it
# were the employer's official site. Only fall back to the raw hint if
# verification didn't run at all (e.g. no company name was resolved).
# =========================================================

def resolve_output_links(company_details, company_result):

    if company_result:
        return {
            "website": company_result.get("website") or "",
            "linkedin": company_result.get("linkedin") or "",
        }

    return {
        "website": company_details.get("website", ""),
        "linkedin": company_details.get("linkedin", ""),
    }


# =========================================================
# ML PREDICTION (shared helper)
# =========================================================

def run_ml_prediction(text_lower):

    vector = vectorizer.transform([text_lower])

    prediction = model.predict(vector)[0]
    probabilities = model.predict_proba(vector)[0]

    is_fake = prediction == 1

    if is_fake:
        confidence = round(float(probabilities[1]) * 100, 2)
    else:
        confidence = round(float(probabilities[0]) * 100, 2)

    label = "FAKE JOB" if is_fake else "LEGITIMATE JOB"

    return label, confidence, is_fake


# =========================================================
# BUILD THE "LIKELY FAKE" WARNING BANNER
# Feature 1: an immediate, reasoned warning when a posting looks fake,
# combining the ML verdict, keyword indicators, Gemini's red flags,
# and real web fraud-report signals.
# =========================================================

def build_fake_warning(is_fake, ai_confidence, indicators, gemini_analysis, fraud_signals):

    reasons = []

    if is_fake:
        reasons.append(f"The AI/ML model classified this posting as likely fake ({ai_confidence}% confidence).")

    reasons.extend(indicators)

    if isinstance(gemini_analysis, dict):
        reasons.extend(gemini_analysis.get("red_flags", []) or [])

    # NOTE: the fraud/negative-feedback signal is intentionally NOT added
    # to this banner's reasons -- it's shown exactly once, in the Company
    # Verification card, so the same line never appears twice on the page.
    fraud_flagged = bool(fraud_signals and fraud_signals.get("fraud_reports_found"))

    flagged = is_fake or fraud_flagged

    if not flagged:
        return None

    # de-duplicate while preserving order
    seen = set()
    unique_reasons = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique_reasons.append(reason)

    return {
        "flagged": True,
        "headline": "⚠️ This job posting is likely FAKE.",
        "reasons": unique_reasons,
    }


# =========================================================
# VERIFY URL
# =========================================================

@router.post("/verify-url")
def verify_url(data: UrlRequest):

    result = verify_url_ai(data.job_url)

    return {
        "verification": result
    }


# =========================================================
# PREDICT JOB FROM PASTED JOB DESCRIPTION
# =========================================================

@router.post("/predict")
def predict_job(job: JobRequest):

    original_text = job.text.strip()

    if not original_text:

        return {
            "error": "Job description is empty."
        }

    text = original_text.lower()

    company_details = extract_company_details(original_text)

    # Gemini reads the full JD, so it can often name the hiring company
    # even when there's no explicit "Company:" line — run it first so we
    # know who to verify/search fraud-signals for.
    ai_result = analyze_job(original_text)

    resolved_name = resolve_company_name(company_details["company"], ai_result, None)
    company_details = {**company_details, "company": resolved_name}

    # Posters/JDs often print the company's own link without a
    # "Website:" label -- pick it up if its domain matches the company.
    if not company_details.get("website"):
        company_details["website"] = find_website_in_text(original_text, resolved_name)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_company = executor.submit(get_company_verification, company_details)
        future_fraud = executor.submit(check_fraud_signals, company_details["company"])

        company_result = future_company.result()
        fraud_result = future_fraud.result()

    prediction, ai_confidence, is_fake = run_ml_prediction(text)

    indicators = detect_indicators(text, is_fake)

    if company_result is not None:
        # The place written in the posting itself always wins over a
        # location guessed from web-search snippets.
        posted_location = (
            extract_location_from_text(original_text)
            or (ai_result.get("company_location") if isinstance(ai_result, dict) else "")
        )
        if posted_location:
            company_result["location"] = posted_location
        elif not company_result.get("location"):
            company_result["location"] = "Unknown"

    fake_warning = build_fake_warning(is_fake, ai_confidence, indicators, ai_result, fraud_result)

    links = resolve_output_links(company_details, company_result)

    return {

        "prediction": prediction,

        "ai_confidence": ai_confidence,

        "indicators": indicators,

        "gemini_analysis": ai_result,

        "company_verification": company_result,

        "company_ai": "Temporarily Disabled",

        "fraud_signals": fraud_result,

        "fake_warning": fake_warning,

        "job_status": None,

        "consistency_check": None,

        # Useful if frontend wants these directly
        "company_name": company_details["company"],

        "official_website": links["website"],

        "linkedin": links["linkedin"]
    }


# =========================================================
# ANALYZE JOB DIRECTLY FROM URL
# =========================================================

@router.post("/analyze-url")
def analyze_url(data: UrlRequest):

    job = extract_job_data(data.job_url)

    job_status = {
        "status": job.get("job_status", "unknown"),
        "reason": job.get("job_status_reason", ""),
    }

    if "error" in job:
        error_payload = dict(job)
        error_payload["job_status"] = job_status
        return error_payload

    original_text = job.get("description", "").strip()

    if not original_text:

        return {
            "error": "Could not extract job description from URL.",
            "job_status": job_status,
        }

    text = original_text.lower()

    company_details = extract_company_details(original_text)
    source_domain = get_url_domain(data.job_url)

    # Gemini reads the whole scraped page, so it can identify the real
    # hiring company even on aggregator/article pages where there's no
    # "Company:" line and the <title> is just the publisher's branding.
    ai_result = analyze_job(original_text)

    resolved_name = resolve_company_name(company_details["company"], ai_result, job)
    company_details = {**company_details, "company": resolved_name}

    # Posters/JDs often print the company's own link without a
    # "Website:" label -- pick it up if its domain matches the company.
    if not company_details.get("website"):
        company_details["website"] = find_website_in_text(original_text, resolved_name)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_company = executor.submit(get_company_verification, company_details, source_domain)
        future_fraud = executor.submit(check_fraud_signals, company_details["company"])

        company_result = future_company.result()
        fraud_result = future_fraud.result()

    prediction, ai_confidence, is_fake = run_ml_prediction(text)

    indicators = detect_indicators(text, is_fake)

    if company_result is not None:
        # The place written in the posting itself always wins over a
        # location guessed from web-search snippets.
        posted_location = (
            extract_location_from_text(original_text)
            or (ai_result.get("company_location") if isinstance(ai_result, dict) else "")
        )
        if posted_location:
            company_result["location"] = posted_location
        elif not company_result.get("location"):
            company_result["location"] = "Unknown"

    fake_warning = build_fake_warning(is_fake, ai_confidence, indicators, ai_result, fraud_result)

    links = resolve_output_links(company_details, company_result)

    return {

        "title": job.get("title", ""),

        "prediction": prediction,

        "ai_confidence": ai_confidence,

        "indicators": indicators,

        "gemini_analysis": ai_result,

        "company_verification": company_result,

        "company_ai": "Temporarily Disabled",

        "fraud_signals": fraud_result,

        "fake_warning": fake_warning,

        "job_status": job_status,

        "consistency_check": None,

        "company_name": company_details["company"],

        "official_website": links["website"],

        "linkedin": links["linkedin"]
    }


# =========================================================
# ALL-IN-ONE MULTI-INPUT ANALYZER
# Feature 7: JD text + Job URL + screenshot image, all in a single call.
# Feature 6: cross-checks the company found in the JD text against the
# company found on the linked URL and flags a mismatch.
# Feature 4: independent I/O (Gemini / Tavily company lookup / Tavily
# fraud search) runs concurrently on a thread pool instead of serially.
# =========================================================

@router.post("/analyze")
async def analyze_combined(
    text: str = Form(default=""),
    job_url: str = Form(default=""),
    image: UploadFile = File(default=None),
):

    start_time = time.time()

    text = (text or "").strip()
    job_url = (job_url or "").strip()

    if not text and not job_url and image is None:
        return {
            "error": "Please provide a job description, a job URL, or a screenshot to analyze."
        }

    # -----------------------------------------------------
    # OCR (if a screenshot was provided)
    # -----------------------------------------------------

    ocr_text = ""
    ocr_error = None

    if image is not None:
        contents = await image.read()
        ocr_result = extract_text_from_image(contents)
        if ocr_result["success"]:
            ocr_text = ocr_result["text"]
        else:
            ocr_error = ocr_result.get("error")

    # -----------------------------------------------------
    # URL SCRAPE
    # -----------------------------------------------------

    url_data = None
    url_text = ""
    job_status = None

    if job_url:
        url_data = extract_job_data(job_url)

        job_status = {
            "status": url_data.get("job_status", "unknown"),
            "reason": url_data.get("job_status_reason", ""),
        }

        if "error" not in url_data:
            url_text = url_data.get("description", "")

    # -----------------------------------------------------
    # CHOOSE THE TEXT TO RUN THE CORE ANALYSIS ON
    # Priority: typed JD text > OCR'd screenshot text > scraped URL text
    # -----------------------------------------------------

    primary_text = text or ocr_text or url_text

    if not primary_text.strip():
        response = {
            "error": (
                job_status["reason"]
                if job_status and job_status.get("status") == "closed"
                else "Could not extract any analyzable text from the provided inputs."
            ),
            "job_status": job_status,
        }
        if ocr_error:
            response["ocr_error"] = ocr_error
        return response

    # -----------------------------------------------------
    # COMPANY DETAILS FROM EACH SOURCE SEPARATELY (for cross-check)
    # -----------------------------------------------------

    text_company = extract_company_details(text) if text else {"company": "", "website": "", "linkedin": ""}
    url_company = extract_company_details(url_text) if url_text else {"company": "", "website": "", "linkedin": ""}
    ocr_company = extract_company_details(ocr_text) if ocr_text else {"company": "", "website": "", "linkedin": ""}

    chosen_company = text_company if text_company["company"] else (
        ocr_company if ocr_company["company"] else url_company
    )

    # -----------------------------------------------------
    # GEMINI FIRST — it reads the full posting body, so it can name the
    # real hiring company even on aggregator/article pages that have no
    # "Company:" line and whose <title> is just the publisher's own
    # branding (e.g. a "jobcode.in" article sharing a Honeywell opening).
    # -----------------------------------------------------

    ai_result = analyze_job(primary_text)

    # If OCR produced a city/industry phrase (for example "Noida Consulting"),
    # prefer the poster-aware company result from the analyzer.
    ai_company = ""
    if isinstance(ai_result, dict):
        ai_company = _valid_extracted_company(ai_result.get("company_name", ""))

    chosen_company = dict(chosen_company)
    if ai_company and not _valid_extracted_company(chosen_company.get("company", "")):
        chosen_company["company"] = ai_company
    elif not chosen_company.get("company") and ai_company:
        chosen_company["company"] = ai_company

    if not chosen_company["company"]:
        chosen_company = dict(chosen_company)
        chosen_company["company"] = resolve_company_name(
            "", ai_result, url_data if url_data else None
        )

    # Same idea: use the company's own link if it is printed in the posting.
    if not chosen_company.get("website"):
        chosen_company = dict(chosen_company)
        chosen_company["website"] = find_website_in_text(
            primary_text, chosen_company["company"]
        )

    source_domain = get_url_domain(job_url)

    # -----------------------------------------------------
    # RUN INDEPENDENT I/O CONCURRENTLY
    # -----------------------------------------------------

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_company = executor.submit(get_company_verification, chosen_company, source_domain)
        future_fraud = executor.submit(check_fraud_signals, chosen_company["company"])

        company_result = future_company.result()
        fraud_result = future_fraud.result()

    prediction, ai_confidence, is_fake = run_ml_prediction(primary_text.lower())

    indicators = detect_indicators(primary_text.lower(), is_fake)

    if company_result is not None:
        # The place written in the posting itself always wins over a
        # location guessed from web-search snippets.
        posted_location = (
            extract_location_from_text(primary_text)
            or (ai_result.get("company_location") if isinstance(ai_result, dict) else "")
        )
        if posted_location:
            company_result["location"] = posted_location
        elif not company_result.get("location"):
            company_result["location"] = "Unknown"

    # -----------------------------------------------------
    # CROSS-INPUT CONSISTENCY (feature 6)
    # -----------------------------------------------------

    consistency_check = None

    if text_company["company"] and url_company["company"]:
        cmp_result = compare_companies(text_company["company"], url_company["company"])

        if cmp_result["comparable"] and cmp_result["match"] is False:
            consistency_check = {
                "mismatch": True,
                "message": (
                    f"Company mismatch: The provided URL and JD belong to different entities "
                    f"('{text_company['company']}' vs '{url_company['company']}'). "
                    "Please apply using one verified source."
                ),
                "similarity": cmp_result["similarity"],
            }
        else:
            consistency_check = {
                "mismatch": False,
                "message": "The company details in the JD and the URL match.",
                "similarity": cmp_result["similarity"],
            }

    fake_warning = build_fake_warning(is_fake, ai_confidence, indicators, ai_result, fraud_result)

    links = resolve_output_links(chosen_company, company_result)

    elapsed_ms = round((time.time() - start_time) * 1000)

    result = {

        "prediction": prediction,

        "ai_confidence": ai_confidence,

        "indicators": indicators,

        "gemini_analysis": ai_result,

        "company_verification": company_result,

        "company_ai": "Temporarily Disabled",

        "fraud_signals": fraud_result,

        "fake_warning": fake_warning,

        "job_status": job_status,

        "consistency_check": consistency_check,

        "company_name": chosen_company["company"],

        "official_website": links["website"],

        "linkedin": links["linkedin"],

        "sources_used": {
            "text_provided": bool(text),
            "url_provided": bool(job_url),
            "image_provided": image is not None,
        },

        "ocr_used": bool(ocr_text),

        "response_time_ms": elapsed_ms,
    }

    if url_data and "title" in url_data:
        result["title"] = url_data.get("title", "")

    if ocr_error:
        result["ocr_error"] = ocr_error

    return result
