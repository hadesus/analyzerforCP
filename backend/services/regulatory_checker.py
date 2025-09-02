import httpx
import os
import json
import re
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# --- API Base URLs ---
OPENFDA_API_URL = "https://api.fda.gov/drug/label.json"
EMA_API_URL = "https://epi.developer.ema.europa.eu/api/retrieval/listbysearchparameter"

async def _check_fda(inn_name: str, client: httpx.AsyncClient) -> dict:
    """Checks drug status and gets dosage info from openFDA."""
    try:
        params = {'search': f'active_ingredient:"{inn_name}"', 'limit': 1}
        response = await client.get(OPENFDA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            # Extract dosage and administration text if available
            dosage_info = data["results"][0].get("dosage_and_administration", [""])[0]
            return {"status": "Likely Approved (Label Found)", "standard_dosage_text": dosage_info}
        return {"status": "Not Found", "standard_dosage_text": None}
    except Exception as e:
        print(f"Error checking FDA: {e}")
        return {"status": "Error", "standard_dosage_text": None}

async def _check_ema(inn_name: str, client: httpx.AsyncClient) -> dict:
    """Checks drug status with the EMA EPI API."""
    try:
        params = {'title': inn_name}
        response = await client.get(EMA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        # The API returns a list, if it's not empty, the drug is likely present
        if isinstance(data, list) and len(data) > 0:
            return {"status": "Likely Found"}
        return {"status": "Not Found"}
    except Exception as e:
        print(f"Error checking EMA: {e}")
        return {"status": "Error"}

async def _check_with_gemini(inn_name: str, regulator: str) -> dict:
    """Checks drug status against a regulator using Gemini with simple text parsing."""
    prompt = f"""Проверь статус препарата с МНН '{inn_name}' в регуляторном органе '{regulator}'.
    
    Ответь кратко: препарат одобрен (Approved), не одобрен (Not Approved) или статус неизвестен (Unknown).
    Добавь краткую заметку на русском языке."""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 200}
        )
        
        response = await model.generate_content_async(prompt)
        
        # Extract status from text response
        text = response.text.lower()
        if 'approved' in text or 'одобрен' in text:
            status = "Approved"
        elif 'not approved' in text or 'не одобрен' in text:
            status = "Not Approved"
        else:
            status = "Unknown"
        return {"status": status, "note": response.text.strip()[:200]}
        
    except Exception as e:
        print(f"Error checking {regulator} with Gemini: {e}")
        return {"status": "Error", "note": f"Ошибка при проверке: {str(e)}"}

async def _compare_dosages_with_gemini(source_dosage: str, standard_dosage_text: str) -> dict:
    """Uses Gemini with JSON schema to compare dosages."""
    if not source_dosage or not standard_dosage_text:
        return {"comparison_result": "mismatch"}

    prompt = f"""
Сравни две дозировки препарата:
1. Дозировка из протокола: "{source_dosage}"
2. Стандартная дозировка из инструкции: "{standard_dosage_text}"

Ответь одним словом:
- within_range (в пределах нормы)
- below_range (ниже нормы)  
- above_range (выше нормы)
- mismatch (невозможно сравнить)"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 50}
        )
        
        response = await model.generate_content_async(prompt)
        
        # Extract comparison result from text
        text = response.text.lower().strip()
        if 'within_range' in text or 'в пределах' in text:
            result = "within_range"
        elif 'below_range' in text or 'ниже' in text:
            result = "below_range"
        elif 'above_range' in text or 'выше' in text:
            result = "above_range"
        else:
            regulatory_results = {
                "regulatory_checks": {
                    "FDA": {"status": "Error"},
                    "EMA": {"status": "Error"},
                    "BNF": {"status": "Error"},
                    "WHO_EML": {"status": "Error"}
                },
                "dosage_check": {"comparison_result": "mismatch"}
            }
            
        return {"comparison_result": result}
        
    except Exception as e:
        print(f"Error comparing dosages with Gemini: {e}")
        return {"comparison_result": "mismatch"}

async def check_all_regulators(inn_name: str, source_dosage: str):
    """Orchestrates all regulatory and dosage checks."""
    async with httpx.AsyncClient() as client:
        # Run checks in parallel
        tasks = {
            "FDA": _check_fda(inn_name, client),
            "EMA": _check_ema(inn_name, client),
            "BNF": _check_with_gemini(inn_name, "BNF (British National Formulary)"),
            "WHO_EML": _check_with_gemini(inn_name, "WHO Essential Medicines List")
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Combine results
        regulatory_status = dict(zip(tasks.keys(), results))

        # Perform dosage check using FDA data
        fda_result = regulatory_results.get("regulatory_checks", {}).get("FDA", {})
        if isinstance(fda_result, dict) and fda_result.get("standard_dosage_text"):
            dosage_comparison = await _compare_dosages_with_gemini(source_dosage, fda_result["standard_dosage_text"])
            regulatory_results["dosage_check"] = dosage_comparison
        else:
            regulatory_results["dosage_check"] = {"comparison_result": "mismatch"}

        return regulatory_results