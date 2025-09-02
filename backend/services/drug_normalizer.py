import httpx
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# --- RxNav API Configuration ---
RXNAV_API_BASE_URL = "https://rxnav.nlm.nih.gov/REST"

async def _normalize_with_rxnav(drug_name: str, client: httpx.AsyncClient) -> str | None:
    """Tries to normalize a drug name to its INN using the RxNav API."""
    try:
        # Step 1: Find RxCUI for the drug name
        search_url = f"{RXNAV_API_BASE_URL}/rxcui.json"
        params = {"name": drug_name, "search": "2"}
        response = await client.get(search_url, params=params, timeout=10.0)
        response.raise_for_status()

        rxcui_data = response.json()
        rxcui_list = rxcui_data.get("idGroup", {}).get("rxnormId", [])
        
        if not rxcui_list:
            return None
            
        rxcui = rxcui_list[0]

        # Step 2: Get all related concepts and find the ingredient (IN)
        related_url = f"{RXNAV_API_BASE_URL}/rxcui/{rxcui}/allrelated.json"
        response = await client.get(related_url, timeout=10.0)
        response.raise_for_status()

        related_data = response.json()
        concept_groups = related_data.get("allRelatedGroup", {}).get("conceptGroup", [])

        for group in concept_groups:
            if group.get("tty") == "IN":
                concept_props = group.get("conceptProperties", [])
                if concept_props:
                    return concept_props[0].get("name")

        return None
    except Exception as e:
        print(f"RxNav API request failed: {e}")
        return None

async def _normalize_with_gemini(drug_name: str) -> str | None:
    """Uses Gemini to find the INN for a drug name - same as demo."""
    prompt = f"""Найди международное непатентованное наименование (МНН/INN) для препарата "{drug_name}".

Ответь ТОЛЬКО названием МНН на английском языке, без дополнительных слов.

Примеры:
Аспирин → Acetylsalicylic acid
Парацетамол → Paracetamol
Ибупрофен → Ibuprofen
Амоксициллин → Amoxicillin

Препарат: {drug_name}
МНН:"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 50}
        )
        response = await model.generate_content_async(prompt)
        result = response.text.strip()
        
        # Clean the response
        result = re.sub(r'^(МНН|INN):\s*', '', result, flags=re.IGNORECASE)
        result = result.strip()
        
        return result if result and len(result) > 2 else None
    except Exception as e:
        print(f"Error during Gemini normalization: {e}")
        return None

async def normalize_drug(drug_name: str) -> dict:
    """
    Orchestrates the drug normalization process - same logic as demo.
    """
    if not drug_name or not isinstance(drug_name, str) or not drug_name.strip():
        return {"inn_name": None, "source": "N/A", "confidence": "none"}

    drug_name = drug_name.strip()
    
    async with httpx.AsyncClient() as client:
        # Try RxNav first
        inn_name = await _normalize_with_rxnav(drug_name, client)
        if inn_name:
            return {"inn_name": inn_name, "source": "RxNav", "confidence": "high"}

        # Fallback to Gemini
        print(f"RxNav failed for '{drug_name}', trying Gemini...")
        inn_name = await _normalize_with_gemini(drug_name)
        if inn_name:
            return {"inn_name": inn_name, "source": "Gemini", "confidence": "medium"}

    return {"inn_name": None, "source": "N/A", "confidence": "none"}