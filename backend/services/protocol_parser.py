import os
import json
import re
import traceback
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

logger.info("✅ Gemini API key found, configuring...")
genai.configure(api_key=GEMINI_API_KEY)
logger.info("✅ Gemini configured successfully")

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
    Uses Gemini to extract drug information from clinical protocol text.
    Simplified approach based on demo version.
    """
    if not text or not text.strip():
        logger.warning("❌ Empty text provided")
        return []

    logger.info(f"📄 Analyzing text of length: {len(text)}")

    prompt = f"""Найди все лекарственные препараты в тексте клинического протокола.

Для каждого препарата верни:
- Название препарата
- Дозировку (если указана)
- Путь введения (если указан)
- Контекст использования

Текст:
---
{text[:30000]}
---

Ответь списком препаратов, каждый с новой строки в формате:
Препарат: [название] | Дозировка: [доза] | Путь: [введение] | Контекст: [использование]"""
    
    try:
        logger.info("🤖 Sending request to Gemini...")
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 4000
            }
        )
        
        response = await model.generate_content_async(prompt)
        
        if not response or not response.text:
            logger.error("❌ Empty response from Gemini")
            return []
        
        logger.info(f"✅ Gemini response received: {len(response.text)} chars")
        logger.debug(f"Gemini response: {response.text[:500]}...")
        
        # Parse simple text response instead of JSON
        drugs = parse_text_response(response.text)
        logger.info(f"✅ Extracted {len(drugs)} drugs")
        return drugs
        
    except Exception as e:
        logger.error(f"❌ Error during Gemini extraction: {e}")
        logger.error(traceback.format_exc())
        traceback.print_exc()
        return []

def parse_text_response(text: str) -> list:
    """Parse simple text response from Gemini."""
    logger.info("📋 Parsing Gemini text response...")
    drugs = []
    lines = text.strip().split('\n')
    logger.info(f"Processing {len(lines)} lines from response")
    
    for line in lines:
        line = line.strip()
        if not line or not 'Препарат:' in line:
            continue
            
        try:
            # Parse format: Препарат: [название] | Дозировка: [доза] | Путь: [введение] | Контекст: [использование]
            parts = line.split('|')
            
            drug_name = ""
            dosage = ""
            route = ""
            context = ""
            
            for part in parts:
                part = part.strip()
                if part.startswith('Препарат:'):
                    drug_name = part.replace('Препарат:', '').strip()
                elif part.startswith('Дозировка:'):
                    dosage = part.replace('Дозировка:', '').strip()
                elif part.startswith('Путь:'):
                    route = part.replace('Путь:', '').strip()
                elif part.startswith('Контекст:'):
                    context = part.replace('Контекст:', '').strip()
            
            if drug_name:
                drug = {
                    "drug_name_source": drug_name,
                    "dosage_source": dosage,
                    "route_source": route,
                    "context_indication": context
                }
                drugs.append(drug)
                logger.info(f"  📋 Found drug: {drug_name}")
                
        except Exception as e:
            logger.error(f"❌ Error parsing line '{line}': {e}")
            continue
    
    logger.info(f"✅ Successfully parsed {len(drugs)} drugs from response")
    return drugs