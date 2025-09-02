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

async def extract_drugs_from_text(text: str) -> list:
    """
    Uses Gemini to extract drug information from clinical protocol text.
    Uses the same unified approach as the demo version for better extraction.
    """
    if not text or not text.strip():
        logger.warning("❌ Empty text provided")
        return []

    logger.info(f"📄 Analyzing text of length: {len(text)}")

    # Use the same unified prompt structure as the demo for better results
    prompt = f"""Проанализируй следующий текст из клинического протокола. Твоя задача - выступить в роли эксперта по оценке медицинских технологий.

Выполни следующие шаги:
1. Извлеки ВСЕ упомянутые в тексте лекарственные средства.
2. Для КАЖДОГО лекарства, предоставь следующую информацию в виде JSON объекта:
   - "drug_name_source": (String) Название препарата, как оно указано в тексте.
   - "inn_name": (String) Международное непатентованное наименование (МНН) на английском языке. Если не можешь определить, напиши "Unknown".
   - "dosage_source": (String) Дозировка и способ введения, как указано в тексте.
   - "route_source": (String) Путь введения (перорально, внутривенно, местно и т.д.).
   - "context_indication": (String) Контекст применения или показание из протокола.

ВАЖНО: 
- Извлекай ВСЕ упоминания лекарственных средств, включая витамины, БАДы, вакцины
- Используй точные названия из текста
- МНН должно быть на английском языке для поиска в международных базах
- Если информация отсутствует, используй пустую строку ""
- Ответ должен быть валидным JSON

Верни ТОЛЬКО JSON объект с ключом "drugs", который является массивом объектов, описанных выше. Не добавляй никаких пояснений или текста до или после JSON.

Текст протокола (первые 50000 символов):
---
{text[:50000]}
---

JSON ответ:"""
    
    try:
        logger.info("🤖 Sending unified extraction request to Gemini...")
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8000,
                "response_mime_type": "application/json"
            }
        )
        
        response = await model.generate_content_async(prompt)
        
        if not response or not response.text:
            logger.error("❌ Empty response from Gemini")
            return []
        
        logger.info(f"✅ Gemini response received: {len(response.text)} chars")
        logger.debug(f"Raw Gemini response: {response.text[:1000]}...")
        
        # Parse JSON response
        try:
            # Clean the response from possible ```json ... ``` wrappers
            cleaned_response = response.text.strip()
            cleaned_response = re.sub(r'^```json\s*|```\s*$', '', cleaned_response, flags=re.MULTILINE)
            
            parsed_data = json.loads(cleaned_response)
            drugs_list = parsed_data.get("drugs", [])
            
            # Validate and format drugs
            formatted_drugs = []
            for drug in drugs_list:
                if not drug.get("drug_name_source"):
                    continue
                    
                formatted_drug = {
                    "drug_name_source": drug.get("drug_name_source", "").strip(),
                    "inn_name": drug.get("inn_name", "").strip(),
                    "dosage_source": drug.get("dosage_source", "").strip(),
                    "route_source": drug.get("route_source", "").strip(),
                    "context_indication": drug.get("context_indication", "").strip()
                }
                
                # Skip if no meaningful data
                if formatted_drug["drug_name_source"]:
                    formatted_drugs.append(formatted_drug)
                    logger.info(f"  📋 Found drug: {formatted_drug['drug_name_source']} (INN: {formatted_drug['inn_name']})")
            
            logger.info(f"✅ Successfully extracted {len(formatted_drugs)} drugs")
            return formatted_drugs
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.error(f"Raw response: {response.text}")
            
            # Fallback: try to extract drugs from text
            return extract_drugs_from_text_fallback(response.text)
        
    except Exception as e:
        logger.error(f"❌ Error during Gemini extraction: {e}")
        logger.error(traceback.format_exc())
        return []

def extract_drugs_from_text_fallback(text: str) -> list:
    """Fallback extraction when JSON parsing fails."""
    logger.info("🔄 Using fallback text extraction...")
    drugs = []
    
    # Look for drug patterns in text
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to find drug names (common patterns)
        drug_patterns = [
            r'"drug_name_source":\s*"([^"]+)"',
            r'"name_author":\s*"([^"]+)"',
            r'препарат[:\s]+([А-Яа-яA-Za-z\s\-]+)',
            r'лекарство[:\s]+([А-Яа-яA-Za-z\s\-]+)',
            r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)\s*(?:\d+\s*мг|\d+\s*г|таблетк)'
        ]
        
        for pattern in drug_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                drug_name = match.strip()
                if len(drug_name) > 2 and drug_name not in [d["drug_name_source"] for d in drugs]:
                    drugs.append({
                        "drug_name_source": drug_name,
                        "inn_name": "",
                        "dosage_source": "",
                        "route_source": "",
                        "context_indication": ""
                    })
                    logger.info(f"  📋 Fallback found: {drug_name}")
    
    logger.info(f"✅ Fallback extracted {len(drugs)} drugs")
    return drugs