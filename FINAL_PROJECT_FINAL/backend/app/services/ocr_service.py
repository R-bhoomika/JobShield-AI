import io
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini (vision) -- main method. No extra install needed, and it reads
# posters / advertisements / stylised text much better than Tesseract.
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types

    _GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    _gemini_client = genai.Client(api_key=_GEMINI_KEY) if _GEMINI_KEY else None
except Exception as _e:  # library missing / bad key
    print("[OCR] Gemini vision not available:", _e)
    _gemini_client = None
    types = None

# ---------------------------------------------------------------------------
# Tesseract -- backup method (needs the Tesseract program installed).
# ---------------------------------------------------------------------------
try:
    from PIL import Image
    import pytesseract

    PIL_AVAILABLE = True

    # Common Windows install locations, used if tesseract is not on PATH.
    for _path in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.exists(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break
except ImportError:
    PIL_AVAILABLE = False

GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_PROMPT = """
You are an expert OCR reader for job advertisements, recruitment posters,
flyers and screenshots.

Read the complete image. Preserve the visual grouping and labels. Do not
combine text from different boxes or columns.

Extract the following fields separately:
Company Name:
Job Role:
Job Locations:
Experience:
Eligibility:
Industry:
Official Website:
LinkedIn Company Page:
Email:
Phone:

Rules:
- Read the company logo/name at the top of the poster carefully.
- Do not treat a city name as a company name.
- Do not treat job role, eligibility, experience or industry as company name.
- Job Locations must contain every city listed under the LOCATION section.
- Keep job locations separate from company headquarters.
- Do not combine BTech/MTech, experience, job role or industry with locations.
- Extract website and LinkedIn only when those URLs are visibly printed.
- Do not invent or guess URLs or missing details.
- Return the extracted fields even when some values are blank.
- If possible, preserve city names in the order shown in the poster.

Return only the labelled fields. If no readable text exists, return exactly:
NO_TEXT
"""


def _mime_type(file_bytes):
    if PIL_AVAILABLE:
        try:
            fmt = (Image.open(io.BytesIO(file_bytes)).format or "").lower()
            return {
                "jpeg": "image/jpeg",
                "jpg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
                "gif": "image/gif",
                "bmp": "image/bmp",
            }.get(fmt, "image/png")
        except Exception:
            pass
    return "image/png"


def _ocr_with_gemini(file_bytes):
    if _gemini_client is None or types is None:
        raise RuntimeError("Gemini is not configured (check GEMINI_API_KEY in .env).")

    part = types.Part.from_bytes(data=file_bytes, mime_type=_mime_type(file_bytes))
    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[part, GEMINI_PROMPT],
    )
    text = (response.text or "").strip()
    if not text or text.upper() == "NO_TEXT":
        return ""
    return text


def _ocr_with_tesseract(file_bytes):
    if not PIL_AVAILABLE:
        raise RuntimeError("pillow / pytesseract are not installed.")

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    # Small images read badly -- make them bigger first.
    if image.width < 1200:
        scale = 1200 / image.width
        image = image.resize((1200, int(image.height * scale)))

    gray = image.convert("L")
    text = pytesseract.image_to_string(gray, config="--psm 6")
    return (text or "").strip()


def extract_text_from_image(file_bytes):
    """
    Reads the text from an uploaded job-posting image.
    1) Gemini vision (best for ads / posters)
    2) Tesseract as backup
    Always returns {"text", "success", "error"}; the real reason is also
    printed in the backend terminal.
    """

    if not file_bytes:
        return {"text": "", "success": False, "error": "The uploaded image is empty."}

    errors = []

    # 1) Gemini
    try:
        text = _ocr_with_gemini(file_bytes)
        if text:
            print("[OCR] Gemini read", len(text), "characters")
            return {"text": text, "success": True, "error": None}
        errors.append("Gemini: no readable text found in the image.")
    except Exception as e:
        print("[OCR] Gemini failed:", e)
        errors.append(f"Gemini: {e}")

    # 2) Tesseract
    try:
        text = _ocr_with_tesseract(file_bytes)
        if text:
            print("[OCR] Tesseract read", len(text), "characters")
            return {"text": text, "success": True, "error": None}
        errors.append("Tesseract: no readable text found in the image.")
    except Exception as e:
        print("[OCR] Tesseract failed:", e)
        errors.append(f"Tesseract: {e}")

    return {"text": "", "success": False, "error": " | ".join(errors)}
