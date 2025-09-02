import httpx
import os
import json
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")

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
    """Checks drug status against a regulator using Gemini."""
    prompt = f"Is the drug with International Nonproprietary Name '{inn_name}' approved by the '{regulator}'? Provide a one-word status: 'Approved', 'Not Approved', or 'Unknown'. Also, provide a very brief, one-sentence note in Russian. Return as a JSON object with keys 'status' and 'note'."
    try:
        response = await gemini_model.generate_content_async(prompt)
        
        # Clean the response more thoroughly
        json_response_text = response.text.strip()
        json_response_text = json_response_text.replace("```json", "").replace("```", "")
        json_response_text = json_response_text.strip()
        
        # Find the first '{' and last '}' to extract just the JSON object
        start_idx = json_response_text.find('{')
        end_idx = json_response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_response_text = json_response_text[start_idx:end_idx + 1]
        
        # Remove newlines that might break JSON parsing
        json_response_text = json_response_text.replace('\n', ' ').replace('\r', ' ')
        
        return json.loads(json_response_text)
    except Exception as e:
        print(f"Error checking {regulator} with Gemini: {e}")
        return {"status": "Error", "note": str(e)}

async def _compare_dosages_with_gemini(source_dosage: str, standard_dosage_text: str) -> dict:
    """Uses Gemini to compare source dosage with standard dosage text."""
    if not source_dosage or not standard_dosage_text:
        return {"comparison_result": "Not enough data"}

    prompt = f"""
    Analyze and compare two drug dosages.
    1. Source Dosage from clinical trial: "{source_dosage}"
    2. Standard Dosage from official label: "{standard_dosage_text}"

    Based on your analysis, classify the Source Dosage relative to the Standard Dosage.
    Your output must be a single JSON object with one key "comparison_result" and one of the following four string values:
    - "within_range": The source dosage is within the standard therapeutic range.
    - "below_range": The source dosage is lower than the standard therapeutic range.
    - "above_range": The source dosage is higher than the standard therapeutic range.
    - "mismatch": The route or frequency is fundamentally different, or it's impossible to compare.

    Provide only the JSON object.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        
        # Clean the response more thoroughly
        json_response_text = response.text.strip()
        json_response_text = json_response_text.replace("```json", "").replace("```", "")
        json_response_text = json_response_text.strip()
        
        # Find the first '{' and last '}' to extract just the JSON object
        start_idx = json_response_text.find('{')
        end_idx = json_response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_response_text = json_response_text[start_idx:end_idx + 1]
        
        # Remove newlines that might break JSON parsing
        json_response_text = json_response_text.replace('\n', ' ').replace('\r', ' ')
        
        return json.loads(json_response_text)
    except Exception as e:
        print(f"Error comparing dosages with Gemini: {e}")
        return {"comparison_result": "Error"}

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
            dosage_comparison = {"comparison_result": "Standard dosage not found"}

        return {
            "regulatory_checks": regulatory_status,
            "dosage_check": dosage_comparison
        }
