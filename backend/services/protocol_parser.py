import os
import json
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
        result_data = json.loads(response.text)
        
        # Extract the drugs array
        extracted_drugs = result_data.get("drugs", [])
        
        print(f"Successfully extracted {len(extracted_drugs)} drugs from text")
        return extracted_drugs
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        return {"error": "Failed to parse AI response as JSON", "details": str(e)}
    except Exception as e:
        print(f"Error during Gemini extraction: {e}")
        return {"error": "Failed to extract data using AI", "details": str(e)}