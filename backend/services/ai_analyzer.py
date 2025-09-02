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

    return f"""
    Ты клинический фармаколог и эксперт по доказательной медицине. Проанализируй данные о препарате и предоставь финальную оценку.

    Данные о препарате:
    {context_str}

    Задачи:
    1. Присвой GRADE уровень доказательности: "High", "Moderate", "Low", или "Very Low"
    2. Дай краткое обоснование (1 предложение)
    3. Напиши краткую заметку на русском языке для клинициста (1-2 предложения)

    Учитывай:
    - Исходный уровень доказательности из протокола
    - Найденные исследования в PubMed
    - Статус регистрации в регуляторных органах
    - Соответствие дозировки стандартам
    """

async def generate_ai_analysis(full_drug_data: dict) -> dict:
    """
    Generates the final AI analysis using Gemini with JSON schema.
    """
    prompt = get_final_analysis_prompt(full_drug_data)

    try:
        # Configure model with JSON schema
        model_with_schema = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
                "response_schema": get_analysis_schema()
            }
        )
        
        response = await model_with_schema.generate_content_async(prompt)
        analysis = json.loads(response.text)
        
        print(f"Generated AI analysis for drug: {full_drug_data.get('source_data', {}).get('drug_name_source', 'Unknown')}")
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in AI analysis: {e}")
        print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка парсинга ответа ИИ.",
            "ai_summary_note": "Не удалось сгенерировать анализ из-за ошибки парсинга."
        }
    except Exception as e:
        print(f"Error during final AI analysis: {e}")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка при генерации анализа ИИ.",
            "ai_summary_note": "Произошла ошибка при генерации финального анализа."
        }

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