import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

# --- AI Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# Export the model for use in other modules
gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0.1,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 8192,
    }
)

def get_analysis_schema():
    """Returns the JSON schema for AI analysis."""
    return {
        "type": "object",
        "properties": {
            "ud_ai_grade": {
                "type": "string",
                "description": "GRADE уровень доказательности"
            },
            "ud_ai_justification": {
                "type": "string", 
                "description": "Краткое обоснование присвоенного уровня"
            },
            "ai_summary_note": {
                "type": "string",
                "description": "Краткая заметка на русском языке для клинициста"
            }
        },
        "required": ["ud_ai_grade", "ud_ai_justification", "ai_summary_note"]
    }

def get_final_analysis_prompt(full_drug_data: dict) -> str:
    # Convert dict to a pretty JSON string for clear presentation in the prompt
    context_str = json.dumps(full_drug_data, indent=2, ensure_ascii=False)

    return f"""Ты система анализа клинических данных. Проанализируй данные о препарате и предоставь финальную оценку.

Данные о препарате:
{context_str}

Выполни анализ и предоставь:
1. ud_ai_grade: GRADE уровень доказательности ("High", "Moderate", "Low", "Very Low")
2. ud_ai_justification: краткое обоснование уровня (1 предложение)
3. ai_summary_note: заметка для клинициста на русском языке (1-2 предложения)

При оценке учитывай:
- Исходный уровень доказательности из протокола
- Найденные исследования в PubMed
- Статус регистрации в регуляторных органах
- Соответствие дозировки стандартам"""

def clean_and_parse_json(raw_text: str) -> dict:
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
        
        # Fallback to default structure
        print(f"Could not parse JSON, returning default structure. Raw text: {raw_text[:500]}...")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка парсинга ответа системы анализа.",
            "ai_summary_note": "Не удалось сгенерировать анализ из-за ошибки парсинга."
        }

def extract_grade_from_text(text: str) -> str:
    """Extract GRADE level from text response."""
    text_lower = text.lower()
    if 'high' in text_lower or 'высокий' in text_lower:
        return "High"
    elif 'moderate' in text_lower or 'умеренный' in text_lower:
        return "Moderate"
    elif 'very low' in text_lower or 'очень низкий' in text_lower:
        return "Very Low"
    elif 'low' in text_lower or 'низкий' in text_lower:
        return "Low"
    return "Unknown"

def extract_justification_from_text(text: str) -> str:
    """Extract justification from text response."""
    lines = text.split('\n')
    for line in lines:
        if 'обоснование' in line.lower() or 'justification' in line.lower():
            return line.split(':', 1)[-1].strip()
    # Return first meaningful sentence as fallback
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
    return sentences[0] if sentences else "Обоснование не найдено"

def extract_summary_from_text(text: str) -> str:
    """Extract summary note from text response."""
    lines = text.split('\n')
    for line in lines:
        if 'заметка' in line.lower() or 'summary' in line.lower():
            return line.split(':', 1)[-1].strip()
    # Return last meaningful sentences as fallback
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 15]
    return '. '.join(sentences[-2:]) if len(sentences) >= 2 else (sentences[-1] if sentences else "Заметка не сгенерирована")

async def generate_ai_analysis(full_drug_data: dict) -> dict:
    """
    Generates the final analysis using Gemini LLM.
    """
    prompt = get_final_analysis_prompt(full_drug_data)

    try:
        # Use simpler model configuration like demo
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.2, "max_output_tokens": 1000}
        )
        
        response = await model.generate_content_async(prompt)
        
        # Try JSON parsing first, then fallback to text extraction
        try:
            analysis = json.loads(response.text.strip())
        except json.JSONDecodeError:
            # Extract from text if JSON fails
            text = response.text
            analysis = {
                "ud_ai_grade": extract_grade_from_text(text),
                "ud_ai_justification": extract_justification_from_text(text),
                "ai_summary_note": extract_summary_from_text(text)
            }
        
        print(f"Generated analysis for drug: {full_drug_data.get('source_data', {}).get('drug_name_source', 'Unknown')}")
        return analysis
        
    except Exception as e:
        print(f"Error during final analysis: {e}")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка при генерации анализа.",
            "ai_summary_note": "Произошла ошибка при генерации финального анализа."
        }