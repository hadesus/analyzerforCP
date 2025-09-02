import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Set up the model with JSON response mode
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config
)

def get_extraction_schema():
    """Returns the JSON schema for drug extraction."""
    return {
        "type": "object",
        "properties": {
            "drugs": {
                "type": "array",
                "description": "Список извлеченных лекарственных средств",
                "items": {
                    "type": "object",
                    "properties": {
                        "drug_name_source": {
                            "type": "string",
                            "description": "Точное название препарата как указано в тексте"
                        },
                        "dosage_source": {
                            "type": "string", 
                            "description": "Дозировка и режим как указано в тексте"
                        },
                        "route_source": {
                            "type": "string",
                            "description": "Путь введения как указано в тексте"
                        },
                        "evidence_level_source": {
                            "type": "string",
                            "description": "Уровень доказательности если указан в тексте"
                        },
                        "context_indication": {
                            "type": "string", 
                            "description": "Клинический контекст или показание для назначения"
                        }
                    },
                    "required": ["drug_name_source"]
                }
            }
        },
        "required": ["drugs"]
    }

def get_extraction_prompt(text: str):
    return f"""
    Проанализируй следующий текст из клинического протокола и извлеки все упоминания лекарственных средств.
    
    Для каждого препарата извлеки:
    - drug_name_source: точное название как указано в тексте
    - dosage_source: дозировка и режим приема
    - route_source: путь введения (перорально, в/в, в/м и т.д.)
    - evidence_level_source: уровень доказательности (УДД/УУР) если указан
    - context_indication: клинический контекст или показание
    
    Текст для анализа:
    ---
    {text}
    ---
    """
def clean_and_parse_json(raw_text: str) -> dict:
    """
    Attempts to clean and parse potentially malformed JSON from Gemini.
    """
    try:
        # First, try direct parsing
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"Initial JSON parse failed: {e}")
        
        # Try to clean common issues
        cleaned_text = raw_text.strip()
        
        # Remove any markdown code blocks
        cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
        cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
        
        # Try to fix unterminated strings by finding the last complete object
        try:
            # Find the last complete closing brace
            last_brace = cleaned_text.rfind('}')
            if last_brace != -1:
                # Try parsing up to the last complete brace
                truncated_text = cleaned_text[:last_brace + 1]
                return json.loads(truncated_text)
        except json.JSONDecodeError:
            pass
        
        # If all else fails, try to extract just the drugs array
        try:
            # Look for drugs array pattern
            drugs_match = re.search(r'"drugs"\s*:\s*\[(.*?)\]', cleaned_text, re.DOTALL)
            if drugs_match:
                drugs_content = drugs_match.group(1)
                # Try to reconstruct a valid JSON
                reconstructed = f'{{"drugs": [{drugs_content}]}}'
                return json.loads(reconstructed)
        except json.JSONDecodeError:
            pass
        
        # Final fallback - return empty structure
        print(f"Could not parse JSON, returning empty structure. Raw text: {raw_text[:500]}...")
        return {"drugs": []}

async def extract_drugs_from_text(text: str) -> list:
    """
    Uses Gemini with JSON schema to extract drug information from clinical protocol text.
    """
    if not text or not text.strip():
        return []

    prompt = get_extraction_prompt(text)
    
    try:
        # Configure the model to use JSON schema
        model_with_schema = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",
                "response_schema": get_extraction_schema()
            }
        )
        
        response = await model_with_schema.generate_content_async(prompt)
        
        # Parse the JSON response
        result_data = clean_and_parse_json(response.text)
        
        # Extract the drugs array
        extracted_drugs = result_data.get("drugs", [])
        
        print(f"Successfully extracted {len(extracted_drugs)} drugs from text")
        return extracted_drugs
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error after cleaning: {e}")
        print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        return {"error": "Failed to parse AI response as JSON", "details": str(e)}
    except Exception as e:
        print(f"Error during Gemini extraction: {e}")
        return {"error": "Failed to extract data using AI", "details": str(e)}