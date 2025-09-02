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

async def generate_ai_analysis(full_drug_data: dict) -> dict:
    """
    Generates the final analysis using Gemini LLM - same approach as demo.
    """
    drug_name = full_drug_data.get('source_data', {}).get('drug_name_source', 'Unknown')
    inn_name = full_drug_data.get('normalization', {}).get('inn_name', 'Unknown')
    
    # Build context summary
    regulatory_checks = full_drug_data.get('regulatory_checks', {}).get('regulatory_checks', {})
    pubmed_count = len(full_drug_data.get('pubmed_articles', []))
    dosage_check = full_drug_data.get('regulatory_checks', {}).get('dosage_check', {})
    
    # Count approvals
    approved_count = sum(1 for check in regulatory_checks.values() 
                        if isinstance(check, dict) and 
                        check.get('status') in ['Approved', 'Found'])
    
    prompt = f"""Проанализируй данные о препарате и дай GRADE оценку доказательности.

Препарат: {drug_name} (МНН: {inn_name})

Данные:
- Регуляторные статусы: {approved_count}/4 одобрений
- PubMed исследования: {pubmed_count} найдено
- Дозировка: {dosage_check.get('comparison_result', 'не проверена')}

Детали регуляторов:
- FDA: {regulatory_checks.get('FDA', {}).get('status', 'не проверен')}
- EMA: {regulatory_checks.get('EMA', {}).get('status', 'не проверен')}
- BNF: {regulatory_checks.get('BNF', {}).get('status', 'не проверен')}
- WHO EML: {regulatory_checks.get('WHO_EML', {}).get('status', 'не проверен')}

Дай оценку в формате JSON:
{{
  "ud_ai_grade": "High/Moderate/Low/Very Low",
  "ud_ai_justification": "краткое обоснование уровня",
  "ai_summary_note": "заметка для клинициста на русском языке"
}}

Критерии GRADE:
- High: множественные РКИ, одобрен регуляторами
- Moderate: некоторые РКИ, частичные одобрения
- Low: ограниченные данные
- Very Low: минимальные данные или противоречия"""
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.2, 
                "max_output_tokens": 1000,
                "response_mime_type": "application/json"
            }
        )
        
        response = await model.generate_content_async(prompt)
        
        try:
            analysis = json.loads(response.text.strip())
            
            # Validate required fields
            required_fields = ["ud_ai_grade", "ud_ai_justification", "ai_summary_note"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = "Не определено"
            
            print(f"✅ Generated analysis for {drug_name}: {analysis['ud_ai_grade']}")
            return analysis
            
        except json.JSONDecodeError:
            # Fallback parsing from text
            text = response.text
            analysis = {
                "ud_ai_grade": extract_grade_from_text(text),
                "ud_ai_justification": extract_justification_from_text(text),
                "ai_summary_note": extract_summary_from_text(text)
            }
            return analysis
        
    except Exception as e:
        print(f"❌ Error during analysis for {drug_name}: {e}")
        return {
            "ud_ai_grade": "Error",
            "ud_ai_justification": "Ошибка при генерации анализа",
            "ai_summary_note": "Не удалось сгенерировать анализ"
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
    
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
    return sentences[0] if sentences else "Обоснование не найдено"

def extract_summary_from_text(text: str) -> str:
    """Extract summary note from text response."""
    lines = text.split('\n')
    for line in lines:
        if 'заметка' in line.lower() or 'summary' in line.lower():
            return line.split(':', 1)[-1].strip()
    
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 15]
    return '. '.join(sentences[-2:]) if len(sentences) >= 2 else (sentences[-1] if sentences else "Заметка не сгенерирована")