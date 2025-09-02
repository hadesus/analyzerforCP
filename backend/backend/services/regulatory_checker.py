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
        response = await client.get(OPENFDA_API_URL, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            dosage_info = data["results"][0].get("dosage_and_administration", [""])[0]
            return {"status": "Approved", "standard_dosage_text": dosage_info}
        return {"status": "Not Found", "standard_dosage_text": None}
    except Exception as e:
        print(f"Error checking FDA: {e}")
        return {"status": "Error", "standard_dosage_text": None}

async def _check_ema(inn_name: str, client: httpx.AsyncClient) -> dict:
    """Checks drug status with the EMA EPI API."""
    try:
        params = {'title': inn_name}
        response = await client.get(EMA_API_URL, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            return {"status": "Found"}
        return {"status": "Not Found"}
    except Exception as e:
        print(f"Error checking EMA: {e}")
        return {"status": "Error"}

async def _check_with_gemini(inn_name: str, regulator: str) -> dict:
    """Checks drug status against a regulator using Gemini."""
    prompt = f"""Проверь, включен ли препарат с МНН "{inn_name}" в {regulator}.

Ответь одним словом:
- Found (если препарат есть в формуляре)
- Not Found (если препарата нет)
- Unknown (если неизвестно)

Препарат: {inn_name}
Формуляр: {regulator}
Статус:"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 50}
        )
        
        response = await model.generate_content_async(prompt)
        text = response.text.strip().lower()
        
        if 'found' in text and 'not found' not in text:
            status = "Found"
        elif 'not found' in text:
            status = "Not Found"
        else:
            status = "Unknown"
            
        return {"status": status}
        
    except Exception as e:
        print(f"Error checking {regulator} with Gemini: {e}")
        return {"status": "Error"}

async def _compare_dosages_with_gemini(source_dosage: str, standard_dosage_text: str) -> dict:
    """Uses Gemini to compare dosages."""
    if not source_dosage or not standard_dosage_text:
        return {"comparison_result": "mismatch"}

    prompt = f"""Сравни дозировки препарата:

Дозировка из протокола: "{source_dosage}"
Стандартная дозировка: "{standard_dosage_text}"

Ответь одним словом:
- within_range (дозировка в норме)
- below_range (дозировка ниже нормы)
- above_range (дозировка выше нормы)
- mismatch (невозможно сравнить)

Результат:"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.1, "max_output_tokens": 50}
        )
        
        response = await model.generate_content_async(prompt)
        text = response.text.strip().lower()
        
        if 'within_range' in text:
            result = "within_range"
        elif 'below_range' in text:
            result = "below_range"
        elif 'above_range' in text:
            result = "above_range"
        else:
            result = "mismatch"
            
        return {"comparison_result": result}
        
    except Exception as e:
        print(f"Error comparing dosages: {e}")
        return {"comparison_result": "mismatch"}

async def check_all_regulators(inn_name: str, source_dosage: str):
    """Orchestrates all regulatory and dosage checks."""
    async with httpx.AsyncClient() as client:
        # Run checks in parallel
        tasks = {
            "FDA": _check_fda(inn_name, client),
            "EMA": _check_ema(inn_name, client),
            "BNF": _check_with_gemini(inn_name, "British National Formulary (BNF)"),
            "WHO_EML": _check_with_gemini(inn_name, "WHO Essential Medicines List")
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                print(f"Error in {name} check: {e}")
                results[name] = {"status": "Error"}

        # Perform dosage check using FDA data
        fda_result = results.get("FDA", {})
        if isinstance(fda_result, dict) and fda_result.get("standard_dosage_text"):
            dosage_comparison = await _compare_dosages_with_gemini(
                source_dosage, 
                fda_result["standard_dosage_text"]
            )
        else:
            dosage_comparison = {"comparison_result": "mismatch"}

        return {
            "regulatory_checks": results,
            "dosage_check": dosage_comparison
        }