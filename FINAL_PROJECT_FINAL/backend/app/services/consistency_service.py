import difflib
import re

# Common legal/company suffixes stripped before comparing so
# "Acme Pvt Ltd" and "Acme Technologies Inc." are recognised as the
# same underlying company.
SUFFIXES = {
    "pvt", "ltd", "limited", "llp", "llc", "inc", "corporation", "corp",
    "technologies", "technology", "tech", "solutions", "systems",
    "services", "group", "co", "company", "private",
}


def normalize_company_name(name):
    if not name:
        return ""

    n = name.lower()
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    words = [w for w in n.split() if w not in SUFFIXES]
    return " ".join(words).strip()


def compare_companies(name_a, name_b, threshold=0.55):
    """
    Returns whether two company name strings likely refer to the same
    entity. Used to cross-check the company found in a pasted JD against
    the company found on the linked job URL.
    """

    a = normalize_company_name(name_a)
    b = normalize_company_name(name_b)

    if not a or not b:
        return {"comparable": False, "match": None, "similarity": 0.0}

    ratio = difflib.SequenceMatcher(None, a, b).ratio()

    substring_match = a in b or b in a

    match = ratio >= threshold or substring_match

    return {
        "comparable": True,
        "match": match,
        "similarity": round(ratio * 100, 1),
    }
