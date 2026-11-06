import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)


def verify_company_ai(company):

    model = genai.GenerativeModel(
        "gemini-2.0-flash"
    )

    prompt = f"""
You are a company verification assistant.

Determine whether the following company is real.

Company:
{company}

Return ONLY in this format:

Company:
Verified:
Industry:
Official Website:
Country:
Summary:
"""

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Gemini Error: {str(e)}"