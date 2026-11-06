"""
JobShield – smart job analyzer (no Gemini needed for the score).

Why this file exists
--------------------
Gemini stops working after 15-20 checks (rate limit / 503 "high demand"), so
the AI Analysis section kept failing. This analyzer replaces it with:

  1. RULES  – a scam-pattern engine that runs on your own computer.
              Free, instant and has NO usage limit.
  2. ML     – your own trained model (ml/model/job_detector.pkl), also local.
  3. TAVILY – optional web evidence (a short summary + sources) for the
              company. This is the only part that uses Tavily credits.
  4. GENAI  – ai_explainer.py asks Groq (Llama) to WRITE the explanation
              from the facts above. If Groq is down, our own text is used.

It returns the SAME dictionary shape that job_analyzer.analyze_job() returned
(risk_score, verdict, red_flags, explanation, company_name, company_location)
plus a few extra fields, so predict.py only needs a one-line import change.
"""

import re

from backend.app.services.tavily_client import tavily_client

try:
    from backend.app.services.ai_explainer import generate_explanation
except Exception as _e:  # keeps the analyzer working even if this file is missing
    print("[Analyzer] AI explainer not available:", _e)
    generate_explanation = None

# Set to False if you want ZERO Tavily credits used by this analyzer.
USE_TAVILY_EVIDENCE = True


# =====================================================================
# ML MODEL (loaded once, only if the files exist)
# =====================================================================

_ml = {"loaded": False, "model": None, "vectorizer": None}


def _ml_fake_probability(text):
    """Chance (0-100) that your ML model thinks the job is fake, or None."""
    if not _ml["loaded"]:
        _ml["loaded"] = True
        try:
            import joblib
            _ml["model"] = joblib.load("ml/model/job_detector.pkl")
            _ml["vectorizer"] = joblib.load("ml/model/vectorizer.pkl")
        except Exception as e:
            print("[Analyzer] ML model not loaded:", e)

    if _ml["model"] is None:
        return None

    try:
        vec = _ml["vectorizer"].transform([text.lower()])
        return float(_ml["model"].predict_proba(vec)[0][1]) * 100
    except Exception as e:
        print("[Analyzer] ML prediction failed:", e)
        return None


# =====================================================================
# SCAM RULES
# (key, red-flag text, regex, points)
# =====================================================================

_NEG = re.compile(
    r"\b(?:no|not|never|without|zero|free\s+of|doesn'?t|don'?t|do\s+not|does\s+not|nor)\b[^.\n]*$",
    re.IGNORECASE,
)

MONEY = r"(?:rs\.?|₹|inr)"

RULES = [
    (
        "fee",
        "Asks for a fee or deposit before the job",
        r"\b(?:registration|processing|security|training|joining|application|verification|kit|"
        r"refundable|admission|onboarding|documentation|medical|uniform|id\s*card)\s*"
        r"(?:fees?|charges?|deposit|amount|cost)\b"
        r"|\b(?:pay|deposit|transfer|send)\s*" + MONEY + r"\s*\d[\d,]*\s*(?:to|for|as|towards|before)\b"
        r"|" + MONEY + r"\s*\d[\d,]*\s*(?:as|for|towards)\s*(?:a\s*)?"
        r"(?:registration|security|processing|training|deposit|fee)",
        40,
    ),
    (
        "no_interview",
        "Promises a job without a proper interview",
        r"\b(?:no|without|zero)\s+interview|\bdirect\s+(?:joining|selection|hiring|offer)\b"
        r"|\binstant\s+(?:joining|selection|offer|hiring)\b|\bselection\s+guaranteed"
        r"|\bguaranteed\s+(?:job|selection|placement)\b|100\s*%\s*(?:job\s*)?(?:guarantee|placement)",
        28,
    ),
    (
        "income",
        "Promises unrealistic or daily income",
        r"\bearn\s*(?:up\s*to\s*)?" + MONEY + r"?\s*\d[\d,]*\s*(?:/|per|a)?\s*(?:day|daily|week|weekly|hour|hr)\b"
        r"|\b(?:daily|weekly)\s+(?:payment|payout|income|salary)\b|\bquick\s+money|\beasy\s+money"
        r"|\binstant\s+(?:income|payment|money)\b|\bguaranteed\s+(?:income|earning|earnings|salary)\b"
        r"|\bearn\s+(?:from|at)\s+home\b|\bearn\s+money\s+online\b"
        r"|" + MONEY + r"\s*\d{4,6}\s*(?:/|per)\s*day\b",
        25,
    ),
    (
        "sensitive",
        "Asks you to send Aadhaar, PAN, bank details or OTP up front",
        r"(?:send|share|submit|provide|upload|give)[^.\n]{0,40}"
        r"(?:aadhaar|aadhar|pan\s*card|bank\s*(?:account|details|passbook)|passport\s*copy|otp|cvv|atm\s*pin|password|upi\s*pin)",
        25,
    ),
    (
        "selected",
        "Says you are \"selected\" without any real hiring process",
        r"\bcongratulations\b|\byou\s+(?:have\s+been|are)\s+(?:selected|shortlisted|chosen)\b",
        15,
    ),
    (
        "messenger",
        "Wants you to contact only through WhatsApp or Telegram",
        r"\b(?:whatsapp|telegram)\b",
        15,
    ),
    (
        "free_email",
        "Uses a free email address (Gmail/Yahoo) instead of a company email",
        r"[\w.+-]+@(?:gmail|yahoo|outlook|hotmail|rediffmail|ymail|protonmail|proton)\.\w+",
        14,
    ),
    (
        "short_link",
        "Uses a short link or chat-app link instead of an official website",
        r"\b(?:bit\.ly|tinyurl\.com|t\.me|wa\.me|cutt\.ly|shorturl\.at|goo\.gl)\b",
        12,
    ),
    (
        "urgency",
        "Pushes you to join or apply in a hurry",
        r"\burgent(?:ly)?\s+(?:hiring|requirement|required|opening)|\bimmediate\s+joining|\bjoin\s+immediately"
        r"|\blimited\s+(?:seats|vacancies|slots|positions)|\bhurry\b|\blast\s+(?:date|chance)\s+today",
        8,
    ),
]

POSITIVE_RULES = [
    (
        "no_fee_statement",
        "States clearly that no fee is charged",
        r"\b(?:no|zero)\s+(?:registration\s+)?(?:fees?|charges?)\b|never\s+ask\s+for\s+(?:money|payment|fee)"
        r"|do(?:es)?\s+not\s+(?:charge|ask\s+for)\s+(?:any\s+)?(?:fee|money)",
        5,
    ),
]

JOB_BOARDS = (
    "naukri", "linkedin", "indeed", "glassdoor", "foundit", "shine", "timesjobs", "monster",
    "apna", "internshala", "hirist", "instahyre", "cutshort", "wellfound", "jobcode", "jooble",
    "simplyhired", "ziprecruiter", "freshersworld", "iimjobs", "facebook", "instagram", "youtube",
)

STRUCTURE_WORDS = (
    "responsibilit", "qualification", "requirement", "experience", "skills", "benefits",
    "about us", "about the", "job description", "role", "eligibility", "apply",
)

TASK_JOB = r"\b(?:data\s+entry|typing|copy\s*[-/]?\s*paste|form\s+filling|ad\s+posting|captcha|like\s+and\s+subscribe|product\s+review)\b"
NO_EXP = r"\b(?:no\s+experience|freshers?|any\s+qualification|10th\s+pass|12th\s+pass|no\s+skills?|without\s+experience|no\s+qualification)\b"


def _find(pattern, text):
    """First match that is NOT negated ("no registration fee" is ignored)."""
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        before = text[max(0, m.start() - 30): m.start()]
        if _NEG.search(before):
            continue
        return m
    return None


def _monthly_max(text):
    """Biggest monthly salary (in rupees) mentioned in the text, or 0."""
    best = 0
    pattern = (
        MONEY + r"\s*([\d,]{4,9})(?:\s*(?:-|to)\s*" + MONEY + r"?\s*([\d,]{4,9}))?"
        r"\s*(?:/|per|a)?\s*(?:month|mo\b|pm\b|monthly)"
    )
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        for g in m.groups():
            if g:
                try:
                    best = max(best, int(g.replace(",", "")))
                except ValueError:
                    pass
    return best


# =====================================================================
# COMPANY NAME + LOCATION (read from the text itself)
# =====================================================================

ORG_SUFFIX = (
    r"(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Limited|Ltd\.?|LLP|LLC|Inc\.?|Corp\.?|Corporation|"
    r"Technologies|Technology|Solutions|Systems|Services|Infotech|Industries|Enterprises|School|"
    r"College|University|Hospital|Institute|Academy|Bank|Group|Labs|Software|Consultancy|"
    r"Consulting|Foundation|Trust)"
)

WORD = r"[A-Z][A-Za-z0-9&.'\-]*"

BAD_NAMES = {
    "job", "jobs", "hiring", "vacancy", "apply", "description", "requirements", "home", "the",
    "our", "this", "you", "your", "india", "least", "us", "we", "team", "role", "position",
}

CITIES = (
    "New Delhi", "Delhi", "Bengaluru", "Bangalore", "Mumbai", "Hyderabad", "Chennai", "Pune",
    "Kolkata", "Mangaluru", "Mangalore", "Noida", "Gurgaon", "Gurugram", "Ahmedabad", "Jaipur",
    "Bangaluru", "Kochi", "Coimbatore", "Mysuru", "Mysore", "Lucknow", "Chandigarh", "Indore", "Bhopal",
    "Nagpur", "Thiruvananthapuram", "Visakhapatnam", "Patna", "Surat", "Vadodara", "Goa",
    "Shivamogga", "Hubballi", "Belagavi", "Udupi", "Remote",
)


def _clean_name(name):
    name = re.sub(r"\s+", " ", name or "").strip(" .,-|:")
    if not name or name.lower() in BAD_NAMES:
        return ""
    if any(b in name.lower() for b in JOB_BOARDS):
        return ""
    return name[:60]



# words that appear on posters but are never a company name
POSTER_WORDS = {
    "hiring", "alert", "associate", "freshers", "fresher", "experience", "eligibility", "location",
    "industry", "comment", "email", "follow", "disclaimer", "company", "job", "role", "jobs",
    "opening", "openings", "vacancy", "urgent", "walk", "interview", "apply", "years", "year",
    "information", "technology", "software", "engineer", "developer", "analyst", "manager",
    "executive", "intern", "trainee", "graduate", "btech", "mtech", "bba", "mba", "bca", "mca",
    "python", "java", "javascript", "react", "sql", "linux", "excel", "remote", "full", "time",
    "part", "salary", "about", "join", "great", "new", "latest", "career", "careers",
    "responsibilities", "requirements", "overview", "summary", "description", "qualification",
    "qualifications", "skills", "benefits", "position", "vacancies", "notification", "recruitment",
    "important", "general", "scientist", "designer", "tester", "consultant", "officer", "specialist",
    "architect", "senior", "junior", "data", "teacher", "teachers", "wanted", "required",
}


def _is_place_or_generic(word):
    w = word.strip(" .,-/|").lower()
    return w in POSTER_WORDS or any(w == c.lower() for c in CITIES)


def _brand_from_top(text):
    """Poster/screenshot text usually starts with the company logo word
    (e.g. 'Capgemini') and repeats it. Pick that before any guessing."""
    lines = [l.strip() for l in text.splitlines() if l.strip()][:6]
    if not lines:
        return ""

    def ok(word):
        return (
            re.fullmatch(r"[A-Za-z][A-Za-z0-9&.\-]{3,24}", word)
            and not _is_place_or_generic(word)
            and (word[0].isupper())
        )

    # a) the very first line is a single word, e.g. "Capgemini"
    first = re.sub(r"[^A-Za-z0-9&.\- ]", "", lines[0]).split()
    if len(first) == 1 and ok(first[0]):
        return _clean_name(" ".join(first))

    # b) one capitalised word repeated in the first lines
    top = " ".join(lines)
    counts = {}
    for w in re.findall(r"\b[A-Za-z][A-Za-z0-9&\-]{4,24}\b", top):
        if ok(w):
            counts[w.lower()] = counts.get(w.lower(), 0) + 1
    for w, n in sorted(counts.items(), key=lambda x: -x[1]):
        if n >= 2:
            # all occurrences must be capitalised (rules out normal words)
            occ = re.findall(r"\b" + re.escape(w) + r"\b", top, flags=re.IGNORECASE)
            if all(o[0].isupper() for o in occ):
                return _clean_name(occ[0].capitalize() if occ[0].isupper() and len(occ[0]) > 1 and occ[0].isupper() and occ[0] == occ[0].upper() else occ[0])
    return ""



def _valid_company_candidate(name):
    """Reject poster labels, job roles, and city + industry combinations."""
    name = _clean_name(name)
    if not name:
        return ""

    words = name.split()
    if not words:
        return ""

    # A city cannot be the first word of an employer name in this
    # extraction path (e.g. "Noida Consulting").
    if _is_place_or_generic(words[0]):
        return ""

    # These are job-role / poster descriptors, not company identifiers.
    invalid_phrases = {
        "associate", "freshers", "fresher", "hiring alert",
        "information technology", "technology consulting",
        "job role", "industry", "eligibility",
    }
    if name.lower() in invalid_phrases:
        return ""

    if any(w.lower() in POSTER_WORDS for w in words):
        # Allow genuine company names containing common business words only
        # when they are not the entire candidate.
        if len(words) == 1 or all(w.lower() in POSTER_WORDS for w in words):
            return ""

    return name


def guess_company(text):
    if not text:
        return ""

    # 1) Explicit company label has the highest priority.
    m = re.search(
        r"^\s*company(?:\s+name)?\s*:\s*(.+)$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if m:
        candidate = m.group(1).splitlines()[0].strip(" .,:;|-")
        valid = _valid_company_candidate(candidate)
        if valid:
            return valid

    # 2) Poster / screenshot: company logo is commonly at the top.
    brand = _valid_company_candidate(_brand_from_top(text))
    if brand:
        return brand

    # 3) OCR may read the logo more than once. A repeated distinctive
    # capitalized word is a useful company signal (e.g. Capgemini).
    top_text = " ".join(
        line.strip() for line in text.splitlines()[:15] if line.strip()
    )
    counts = {}
    for word in re.findall(r"\b[A-Z][A-Za-z0-9&.-]{3,24}\b", top_text):
        if _is_place_or_generic(word):
            continue
        counts[word.lower()] = counts.get(word.lower(), 0) + 1

    repeated = [
        word for word, count in counts.items()
        if count >= 2
    ]
    if repeated:
        # Prefer the most frequently repeated candidate, preserving its
        # original capitalization from the OCR text.
        candidate = max(repeated, key=lambda word: counts[word])
        original = re.search(
            r"\b" + re.escape(candidate) + r"\b",
            top_text,
            flags=re.IGNORECASE,
        )
        if original:
            valid = _valid_company_candidate(original.group(0))
            if valid:
                return valid

    # 4) Organization names ending in a legal/business suffix.
    line_re = re.compile(
        r"^(?:about\s+)?(" + WORD
        + r"(?:\s+[A-Z&][A-Za-z0-9&.'\-]*){0,5}\s+"
        + ORG_SUFFIX + r")\b"
    )

    for line in text.splitlines():
        line = line.strip()
        if 3 <= len(line) <= 80:
            match = line_re.match(line)
            if match:
                valid = _valid_company_candidate(match.group(1))
                if valid:
                    return valid

    anywhere_re = (
        r"\b(" + WORD
        + r"(?:\s+[A-Z&][A-Za-z0-9&.'\-]*){0,4}\s+"
        + ORG_SUFFIX + r")\b"
    )
    for match in re.finditer(anywhere_re, text):
        valid = _valid_company_candidate(match.group(1))
        if valid:
            return valid

    # 5) Hiring phrases.
    patterns = (
        r"\b(" + WORD + r"(?:\s+[A-Z][A-Za-z0-9&.'\-]*){0,3})"
        r"\s+(?:is|are)\s+(?:hiring|looking\s+for|seeking|recruiting)",
        r"\b(?:careers?|openings?|vacancy|hiring|jobs?)\s+at\s+("
        + WORD + r"(?:\s+[A-Z][A-Za-z0-9&.'\-]*){0,3})",
        r"\bjoin\s+(" + WORD + r"(?:\s+[A-Z][A-Za-z0-9&.'\-]*){0,3})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            valid = _valid_company_candidate(match.group(1))
            if valid:
                return valid

    # 6) "Role at Company" fallback, only accept a non-generic name.
    match = re.search(
        r"\b(?:at|with)\s+("
        + WORD + r"(?:\s+[A-Z][A-Za-z0-9&.'\-]*){0,2})"
        r"\s*(?:[.,|\n(]|$)",
        text[:500],
    )
    if match:
        valid = _valid_company_candidate(match.group(1))
        if valid:
            return valid

    return ""


def guess_location(text):
    """Return job-posting cities, not a company headquarters or OCR row."""
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # First look for a clearly labelled location line.
    for index, line in enumerate(lines):
        label_match = re.match(
            r"^(?:(?:job|work|office)\s+)?locations?\s*:?\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )
        if not label_match:
            continue

        same_line = label_match.group(1).strip(" ,:-")
        nearby_text = same_line

        # Some OCR engines put the value on the next line(s).
        if not nearby_text:
            nearby_text = " ".join(lines[index + 1:index + 4])

        found = []
        for city in sorted(CITIES, key=len, reverse=True):
            if re.search(r"\b" + re.escape(city) + r"\b", nearby_text, re.IGNORECASE):
                if city.lower() not in [item.lower() for item in found]:
                    found.append(city)

        if found:
            # Preserve the order in which cities appear in the poster.
            positions = []
            for city in found:
                match = re.search(
                    r"\b" + re.escape(city) + r"\b",
                    nearby_text,
                    re.IGNORECASE,
                )
                positions.append((match.start() if match else 99999, city))
            return ", ".join(city for _, city in sorted(positions))

        if same_line and len(same_line) <= 100:
            return same_line

    # Poster OCR can flatten the label and city values into one line.
    # Only return recognized city names, never the entire OCR row.
    found_positions = []
    for city in CITIES:
        match = re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE)
        if match:
            found_positions.append((match.start(), city))

    # De-duplicate aliases while preserving text order.
    found_positions.sort()
    result = []
    for _, city in found_positions:
        if city.lower() not in [item.lower() for item in result]:
            result.append(city)

    return ", ".join(result)


# =====================================================================
# MAIN ANALYSIS
# =====================================================================

def _lower_first(s):
    return s[:1].lower() + s[1:] if s else s


def _build_explanation(risk, flags, positives, company):
    n = len(flags)

    if risk >= 65:
        top = flags[0][0] if flags else "several risk signs"
        text = f"This job posting shows {n} warning sign{'s' if n != 1 else ''}, and the most serious one is that it {_lower_first(top)}."
        others = [f[0] for f in flags[1:4]]
        if others:
            text += " Other signs: " + "; ".join(_lower_first(o) for o in others) + "."
        if any(f[2] == "fee" for f in flags):
            text += " Legitimate employers never ask candidates to pay money to get a job."
        text += " Treat it as likely fake until you confirm it on the company's official website."
        return text

    if risk >= 35:
        listed = "; ".join(_lower_first(f[0]) for f in flags[:3]) or "some details look unusual"
        return (
            f"Some points in this posting look unusual: {listed}. "
            "This does not prove it is a scam, but verify the company and the recruiter "
            "before you share documents or pay anything."
        )

    text = "No strong scam signs were found in this job posting."
    if positives:
        text += " Good signs: " + "; ".join(_lower_first(p[0]) for p in positives[:3]) + "."
    if flags:
        text += " One small point to check: " + _lower_first(flags[0][0]) + "."
    text += " Still apply only through the company's official website."
    return text


def _web_evidence(company):
    if not USE_TAVILY_EVIDENCE or not company or tavily_client is None:
        return None
    try:
        resp = tavily_client.search(
            query=f'Is "{company}" a legitimate employer? job offer scam reviews',
            search_depth="basic",
            max_results=4,
            include_answer=True,
        )
        summary = (resp.get("answer") or "").strip()
        sources = [
            {"title": (r.get("title") or "")[:90], "url": r.get("url") or ""}
            for r in resp.get("results", [])[:3]
            if r.get("url")
        ]
        if not summary and not sources:
            return None
        return {"summary": summary, "sources": sources}
    except Exception as e:
        print("[Analyzer] Tavily evidence failed:", e)
        return None


def analyze_job(description):
    text = (description or "").strip()

    if not text:
        return {
            "risk_score": 0,
            "verdict": "No Text",
            "red_flags": [],
            "explanation": "There was no job text to analyze.",
            "company_name": "",
            "company_location": "",
        }

    company = guess_company(text)
    location = guess_location(text)

    flags = []       # (label, points, key)
    positives = []   # (label, points, key)

    # ---- scam rules ----
    for key, label, pattern, points in RULES:
        if _find(pattern, text):
            flags.append((label, points, key))

    # messenger only: no official email or website -> extra warning
    has_messenger = any(f[2] == "messenger" for f in flags)
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))
    has_link = bool(re.search(r"https?://|www\.", text, flags=re.IGNORECASE))
    if has_messenger and not has_email and not has_link:
        flags.append(("Gives no official email or website to contact", 10, "no_contact"))

    # high pay with no experience / simple tasks
    monthly = _monthly_max(text)
    if monthly >= 40000 and re.search(NO_EXP, text, flags=re.IGNORECASE):
        flags.append(("Offers very high pay for a job that needs no experience", 20, "high_pay"))
    elif re.search(TASK_JOB, text, flags=re.IGNORECASE) and (monthly >= 25000 or any(f[2] == "income" for f in flags)):
        flags.append(("Simple task job (typing / data entry) with unusually high pay", 15, "task_pay"))

    # no company named
    if not company:
        flags.append(("No clear hiring company is named", 10, "no_company"))

    # very short text
    words = len(text.split())
    if words < 25:
        flags.append(("Gives very little detail about the job", 8, "short"))

    # shouting
    caps = len(re.findall(r"\b[A-Z]{4,}\b", text))
    if text.count("!") >= 3 or caps >= 6:
        flags.append(("Uses many exclamation marks or ALL CAPS", 6, "shouting"))

    # ---- good signs ----
    for key, label, pattern, points in POSITIVE_RULES:
        if re.search(pattern, text, flags=re.IGNORECASE):
            positives.append((label, points, key))

    emails = re.findall(r"[\w.+-]+@([\w-]+\.[\w.]+)", text)
    if emails and not any(f[2] == "free_email" for f in flags):
        positives.append(("Contact uses a company email domain", 6, "company_email"))

    for url in re.findall(r"https?://[^\s\]\)>\"']+", text, flags=re.IGNORECASE):
        host = re.sub(r"^https?://(?:www\.)?", "", url.lower()).split("/")[0]
        if not any(b in host for b in JOB_BOARDS) and not any(s in host for s in ("bit.ly", "t.me", "wa.me", "tinyurl")):
            positives.append(("Links to an official company website", 6, "official_link"))
            break

    structure = sum(1 for w in STRUCTURE_WORDS if w in text.lower())
    if structure >= 5:
        positives.append(("Has a detailed, well-structured description", 8, "structured"))
    elif structure >= 3:
        positives.append(("Has a clear job description", 5, "structured"))

    # ---- score ----
    flags.sort(key=lambda f: f[1], reverse=True)

    bad_total = sum(f[1] for f in flags)
    good_total = min(sum(p[1] for p in positives), 15)

    rule_score = max(0, min(100, bad_total - (good_total if bad_total else 0)))

    ml_prob = _ml_fake_probability(text)

    if ml_prob is None:
        risk = rule_score
    else:
        # the ML model can raise a low rule score, but can never hide a clear scam
        risk = max(rule_score, round(0.5 * rule_score + 0.5 * ml_prob))

    risk = int(max(0, min(100, round(risk))))

    verdict = "Likely Fake" if risk >= 65 else "Suspicious" if risk >= 35 else "Looks Genuine"

    web = _web_evidence(company)

    # Written explanation: GenAI first (Groq), our own text as backup.
    explanation = _build_explanation(risk, flags, positives, company)
    explanation_by = "JobShield rules"

    if generate_explanation is not None:
        ai = generate_explanation({
            "risk": risk,
            "verdict": verdict,
            "company": company,
            "flags": [f[0] for f in flags],
            "positives": [p[0] for p in positives],
            "web_summary": (web or {}).get("summary", ""),
            "job_text": text,
        })
        if ai:
            explanation = ai["text"]
            explanation_by = ai["by"]

    breakdown = [{"label": f[0], "points": f[1], "type": "risk"} for f in flags]
    breakdown += [{"label": p[0], "points": -p[1], "type": "good"} for p in positives]

    return {
        "risk_score": risk,
        "verdict": verdict,
        "red_flags": [f[0] for f in flags],
        "explanation": explanation,
        "company_name": company,
        "company_location": location,
        # extra fields used by the new AI Analysis screen
        "positives": [p[0] for p in positives],
        "score_breakdown": breakdown,
        "components": {
            "rules": rule_score,
            "ml": None if ml_prob is None else round(ml_prob),
        },
        "web_evidence": web,
        "explanation_by": explanation_by,
        "engine": "rules+ml+genai" + ("+tavily" if USE_TAVILY_EVIDENCE else ""),
    }