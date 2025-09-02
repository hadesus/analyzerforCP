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
    Uses the same approach as the demo version for reliable extraction.
    """
    if not text or not text.strip():
        logger.warning("❌ Empty text provided")
        return []

    logger.info(f"📄 Analyzing text of length: {len(text)}")

    # Use the exact same prompt structure as demo
    prompt = f"""Проанализируй следующий текст клинического протокола и извлеки все упоминания лекарственных препаратов.

Для каждого препарата предоставь следующую информацию в формате JSON:

{{
  "drugs": [
    {{
      "drug_name_source": "точное название препарата как указано в тексте",
      "dosage_source": "дозировка (например: 10 мг, 500 мг/сут, 1 таблетка)",
      "route_source": "путь введения (например: перорально, внутривенно, местно)",
      "context_indication": "контекст применения или показание"
    }}
  ]
}}

ВАЖНО: 
- Извлекай ВСЕ упоминания лекарственных средств
- Используй точные названия из текста
- Если информация отсутствует, используй пустую строку ""
- Ответ должен быть валидным JSON

Текст протокола:
---
{text[:50000]}
---

JSON ответ:"""
    
    try:
        logger.info("🤖 Sending request to Gemini...")
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
            parsed_data = json.loads(response.text)
            drugs_list = parsed_data.get("drugs", [])
            
            # Convert to expected format
            formatted_drugs = []
            for drug in drugs_list:
                formatted_drug = {
                    "drug_name_source": drug.get("drug_name_source", ""),
                    "dosage_source": drug.get("dosage_source", ""),
                    "route_source": drug.get("route_source", ""),
                    "context_indication": drug.get("context_indication", "")
                }
                if formatted_drug["drug_name_source"]:  # Only add if has name
                    formatted_drugs.append(formatted_drug)
                    logger.info(f"  📋 Found drug: {formatted_drug['drug_name_source']}")
            
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
                        "dosage_source": "",
                        "route_source": "",
                        "context_indication": ""
                    })
                    logger.info(f"  📋 Fallback found: {drug_name}")
    
    logger.info(f"✅ Fallback extracted {len(drugs)} drugs")
    return drugs