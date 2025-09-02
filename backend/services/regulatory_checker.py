import httpx
import os
import json
import re
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# --- API Base URLs ---
OPENFDA_API_URL = "https://api.fda.gov/drug/label.json"
EMA_API_URL = "https://epi.developer.ema.europa.eu/api/retrieval/listbysearchparameter"

def get_regulatory_check_schema():
    """Returns JSON schema for regulatory checks."""
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Статус препарата: Approved, Not Approved, или Unknown"
            },
            "note": {
                "type": "string",
                "description": "Краткая заметка на русском языке"
            }
        },
        "required": ["status", "note"]
    }

def get_dosage_comparison_schema():
    """Returns JSON schema for dosage comparison."""
    return {
        "type": "object",
        "properties": {
            "comparison_result": {
                "type": "string",
                "enum": ["within_range", "below_range", "above_range", "mismatch"],
                "description": "Результат сравнения дозировок"
            }
        },
        "required": ["comparison_result"]
    }

def clean_and_parse_json(raw_text: str, fallback_dict: dict) -> dict:
    """
    Attempts to clean and parse potentially malformed JSON from Gemini.
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"Initial JSON parse failed: {e}")
        
        # Clean common issues
        cleaned_text = raw_text.strip()
        cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
        cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
        
        try:
            # Find the last complete closing brace
            last_brace = cleaned_text.rfind('}')
            if last_brace != -1:
                truncated_text = cleaned_text[:last_brace + 1]
                return json.loads(truncated_text)
        except json.JSONDecodeError:
            pass
        
        # Return fallback
        print(f"Could not parse JSON, returning fallback. Raw text: {raw_text[:500]}...")
        return fallback_dict

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
    """Checks drug status against a regulator using Gemini."""
    prompt = f"""Проверь статус препарата с МНН '{inn_name}' 
    в регуляторном органе '{regulator}'.
    
    Верни в JSON формате:
    - status: "Approved", "Not Approved", или "Unknown"
    - note: краткая заметка на русском языке (1 предложение)"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 200}
        )
        
        response = await model.generate_content_async(prompt)
        
        # Try to parse JSON, fallback to safe defaults
        try:
            return json.loads(response.text.strip())
        except json.JSONDecodeError:
            # Extract status from text if JSON parsing fails
            text = response.text.lower()
            if 'approved' in text or 'одобрен' in text:
                status = "Approved"
            elif 'not approved' in text or 'не одобрен' in text:
                status = "Not Approved"
            else:
                status = "Unknown"
            return {"status": status, "note": "Статус определен из текстового ответа"}
        
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
    
    Классифицируй дозировку из протокола относительно стандартной:
    - within_range: в пределах терапевтического диапазона
    - below_range: ниже терапевтического диапазона  
    - above_range: выше терапевтического диапазона
    - mismatch: невозможно сравнить (разные пути введения, частота и т.д.)
    """
    
    try:
        model_with_schema = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "response_schema": get_dosage_comparison_schema()
            }
        )
        
        response = await model_with_schema.generate_content_async(prompt)
        return clean_and_parse_json(response.text, {"comparison_result": "mismatch"})
        
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
        fda_result = regulatory_status.get("FDA", {})
        if isinstance(fda_result, dict) and fda_result.get("standard_dosage_text"):
            dosage_comparison = await _compare_dosages_with_gemini(source_dosage, fda_result["standard_dosage_text"])
        else:
            dosage_comparison = {"comparison_result": "mismatch"}

        return {
            "regulatory_checks": regulatory_status,
            "dosage_check": dosage_comparison
        }