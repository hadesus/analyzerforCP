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

# Set up the model with JSON response mode - following demo approach
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
    """Returns the JSON schema for drug extraction - following demo structure."""
    return {
        "type": "object",
        "properties": {
            "drugs": {
                "type": "array",
                "description": "Список извлеченных лекарственных средств",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Наименование лекарственного средства"
                        },
                        "innEnglish": {
                            "type": "string", 
                            "description": "МНН на английском языке"
                        },
                        "dosage": {
                            "type": "string",
                            "description": "Дозировка"
                        },
                        "route": {
                            "type": "string",
                            "description": "Путь введения"
                        },
                        "frequency": {
                            "type": "string",
                            "description": "Режим дозирования"
                        },
                        "duration": {
                            "type": "string", 
                            "description": "Продолжительность терапии"
                        }
                    },
                    "required": ["name"]
                }
            }
        },
        "required": ["drugs"]
    }

def get_extraction_prompt(text: str):
    """Returns extraction prompt following demo approach."""
    return f"""Проанализируй следующий текст клинического протокола. Извлеки все упоминания лекарственных средств.
Для каждого лекарства укажи:
- "name": (String) наименование лекарственного средства (стандартизированное, если возможно).
- "innEnglish": (String) международное непатентованное наименование (МНН) на английском языке, если известно или легко определяется. Если нет, оставь пустым.
- "dosage": (String) дозировка (например, "10 мг", "500 мг/сут").
- "route": (String) путь введения (например, "перорально", "сублингвально"). ВАЖНО: Предоставляй ТОЛЬКО краткое, точное значение (1-3 слова), без каких-либо дополнительных комментариев, пояснений, вопросов или повторений в этом поле. Например: "сублингвально", "внутримышечно", "местно (аппликация)".
- "frequency": (String) режим дозирования (например, "2 раза в день", "каждые 8 часов").
- "duration": (String) продолжительность терапии (например, "7 дней", "до исчезновения симптомов").

Текст протокола (первые 100000 символов):
---
{text[:100000]} 
---
Предоставь ответ в формате JSON согласно следующей схеме. Если информация отсутствует, используй null или пустую строку."""

def robust_json_parse(raw_text: str) -> dict:
    """
    Robust JSON parsing with multiple fallback strategies.
    """
    if not raw_text or not raw_text.strip():
        return {"drugs": []}
    
    # Clean the text
    cleaned_text = raw_text.strip()
    
    # Remove markdown code blocks
    cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
    cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
    cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
    
    # Try direct parsing first
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        print(f"Direct JSON parse failed: {e}")
    
    # Strategy 1: Find and fix unterminated strings
    try:
        # Look for common patterns of unterminated strings and fix them
        fixed_text = cleaned_text
        
        # Fix unterminated strings at the end
        if fixed_text.count('"') % 2 != 0:
            # Odd number of quotes - likely unterminated string
            last_quote_pos = fixed_text.rfind('"')
            if last_quote_pos != -1:
                # Check if we're in the middle of a value
                after_quote = fixed_text[last_quote_pos + 1:].strip()
                if after_quote and not after_quote.startswith(',') and not after_quote.startswith('}'):
                    # Add closing quote
                    fixed_text = fixed_text[:last_quote_pos + 1] + '"' + fixed_text[last_quote_pos + 1:]
        
        return json.loads(fixed_text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Find the last complete object
    try:
        # Find all complete JSON objects
        brace_count = 0
        last_complete_pos = -1
        
        for i, char in enumerate(cleaned_text):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_complete_pos = i
        
        if last_complete_pos != -1:
            truncated_text = cleaned_text[:last_complete_pos + 1]
            return json.loads(truncated_text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Extract just the drugs array
    try:
        # Look for drugs array pattern with more flexible regex
        drugs_pattern = r'"drugs"\s*:\s*\[(.*?)\]'
        drugs_match = re.search(drugs_pattern, cleaned_text, re.DOTALL)
        
        if drugs_match:
            drugs_content = drugs_match.group(1).strip()
            
            # Try to fix common issues in the drugs array
            if drugs_content:
                # Ensure proper object separation
                if not drugs_content.endswith('}') and not drugs_content.endswith(']'):
                    # Find the last complete object
                    last_brace = drugs_content.rfind('}')
                    if last_brace != -1:
                        drugs_content = drugs_content[:last_brace + 1]
                
                reconstructed = f'{{"drugs": [{drugs_content}]}}'
                return json.loads(reconstructed)
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Strategy 4: Try to extract individual drug objects
    try:
        # Find all drug objects
        drug_pattern = r'\{[^{}]*"name"\s*:\s*"[^"]*"[^{}]*\}'
        drug_matches = re.findall(drug_pattern, cleaned_text)
        
        if drug_matches:
            drugs = []
            for match in drug_matches:
                try:
                    drug_obj = json.loads(match)
                    drugs.append(drug_obj)
                except json.JSONDecodeError:
                    continue
            
            if drugs:
                return {"drugs": drugs}
    except Exception:
        pass
    
    # Final fallback
    print(f"All JSON parsing strategies failed. Raw text sample: {cleaned_text[:500]}...")
    return {"drugs": []}

async def extract_drugs_from_text(text: str) -> list:
    """
    Uses Gemini with JSON schema to extract drug information from clinical protocol text.
    Following the demo approach for better reliability.
    """
    if not text or not text.strip():
        return []

    prompt = get_extraction_prompt(text)
    
    try:
        # Configure the model to use JSON schema - following demo
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
        
        if not response or not response.text:
            print("Empty response from Gemini")
            return []
        
        print(f"Raw Gemini response: {response.text[:500]}...")
        
        # Parse the JSON response with robust parsing
        result_data = robust_json_parse(response.text)
        
        # Extract the drugs array
        extracted_drugs = result_data.get("drugs", [])
        
        # Convert to the format expected by the rest of the pipeline
        converted_drugs = []
        for drug in extracted_drugs:
            if isinstance(drug, dict) and drug.get("name"):
                converted_drug = {
                    "drug_name_source": drug.get("name", ""),
                    "dosage_source": drug.get("dosage", ""),
                    "route_source": drug.get("route", ""),
                    "context_indication": f"{drug.get('frequency', '')} {drug.get('duration', '')}".strip()
                }
                converted_drugs.append(converted_drug)
        
        print(f"Successfully extracted {len(converted_drugs)} drugs from text")
        return converted_drugs
        
    except Exception as e:
        print(f"Error during Gemini extraction: {e}")
        return []