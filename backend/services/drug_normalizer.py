import httpx
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
# Load environment variables from .env file located in the parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# --- RxNav API Configuration ---
RXNAV_API_BASE_URL = "https://rxnav.nlm.nih.gov/REST"


async def _normalize_with_rxnav(drug_name: str, client: httpx.AsyncClient) -> str | None:
    """Tries to normalize a drug name to its INN using the RxNav API."""
    try:
        # Step 1: Find RxCUI for the drug name
        search_url = f"{RXNAV_API_BASE_URL}/rxcui.json"
        params = {"name": drug_name, "search": "2"} # search=2 enables normalized search
        response = await client.get(search_url, params=params)
        response.raise_for_status()

        rxcui_data = response.json()
        rxcui = rxcui_data.get("idGroup", {}).get("rxnormId", [None])[0]

        if not rxcui:
            return None

        # Step 2: Get all related concepts and find the ingredient (IN)
        related_url = f"{RXNAV_API_BASE_URL}/rxcui/{rxcui}/allrelated.json"
        response = await client.get(related_url)
        response.raise_for_status()

        related_data = response.json()
        concept_groups = related_data.get("allRelatedGroup", {}).get("conceptGroup", [])

        for group in concept_groups:
            if group.get("tty") == "IN":
                # Found the ingredient, return its name
                return group.get("conceptProperties", [{}])[0].get("name")

        return None # IN not found
    except httpx.HTTPStatusError as e:
        print(f"RxNav API request failed: {e}")
        return None
    except Exception as e:
        print(f"An error occurred during RxNav normalization: {e}")
        return None

async def _normalize_with_gemini(drug_name: str) -> str | None:
    """Uses Gemini as a fallback to find the INN for a drug name."""
    prompt = f"What is the International Nonproprietary Name (INN) for the drug '{drug_name}'? Please return only the INN name and nothing else. For example, if the input is 'Lipitor', the output should be 'Atorvastatin'."
    try:
        response = await gemini_model.generate_content_async(prompt)
        # Simple cleaning, assuming the model follows instructions
        return response.text.strip()
    except Exception as e:
        print(f"An error occurred during Gemini normalization: {e}")
        return None

async def normalize_drug(drug_name: str) -> dict:
    """
    Orchestrates the drug normalization process.
    Tries RxNav API first, then falls back to Gemini.
    """
    if not drug_name or not isinstance(drug_name, str) or not drug_name.strip():
        return {"inn_name": None, "source": "N/A", "confidence": "none"}

    async with httpx.AsyncClient() as client:
        # Try RxNav first
        inn_name = await _normalize_with_rxnav(drug_name, client)
        if inn_name:
            return {"inn_name": inn_name, "source": "RxNav", "confidence": "high"}

        # Fallback to Gemini
        print(f"RxNav failed for '{drug_name}', falling back to Gemini.")
        inn_name = await _normalize_with_gemini(drug_name)
        if inn_name:
            # Gemini's response is less structured, so confidence is lower.
            # A real system might have more checks here.
            return {"inn_name": inn_name, "source": "Gemini", "confidence": "medium"}

    return {"inn_name": None, "source": "N/A", "confidence": "none"}
