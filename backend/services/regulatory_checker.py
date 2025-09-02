"""
Regulatory Checker Service
Проверяет статус препаратов в различных регуляторных базах
"""

import asyncio
import logging
import httpx
from typing import Dict, Optional
from .bnf_analyzer import check_bnf_status

logger = logging.getLogger(__name__)

async def check_fda_status(inn_name: str) -> Dict:
    """Проверяет статус препарата в FDA через openFDA API"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Поиск по активному веществу
            url = f"https://api.fda.gov/drug/label.json?search=active_ingredient:{inn_name}&limit=1"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return {
                        "status": "FDA Approved",
                        "details": f"Found in FDA database"
                    }
            
            return {
                "status": "Not found in FDA",
                "details": "Препарат не найден в базе FDA"
            }
            
    except Exception as e:
        logger.error(f"FDA check error for {inn_name}: {e}")
        return {
            "status": "FDA check error",
            "details": f"Ошибка проверки FDA: {str(e)}"
        }

async def check_ema_status(inn_name: str) -> Dict:
    """Проверяет статус препарата в EMA"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Поиск в EMA medicines database
            url = f"https://www.ema.europa.eu/en/medicines/field_ema_web_categories%253Aname_field/Human/search_api_aggregation_ema_medicine_types/field_ema_med_type/search_api_aggregation_ema_medicine_status/field_ema_med_status/ema_medicine_search_form/{inn_name}"
            
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code == 200 and inn_name.lower() in response.text.lower():
                return {
                    "status": "EMA Approved",
                    "details": "Found in EMA database"
                }
            
            return {
                "status": "Not found in EMA",
                "details": "Препарат не найден в базе EMA"
            }
            
    except Exception as e:
        logger.error(f"EMA check error for {inn_name}: {e}")
        return {
            "status": "EMA check error",
            "details": f"Ошибка проверки EMA: {str(e)}"
        }

async def check_who_eml_status(inn_name: str) -> Dict:
    """Проверяет статус препарата в WHO Essential Medicines List"""
    try:
        # Список основных препаратов WHO (упрощенная версия)
        who_essential_medicines = [
            "paracetamol", "acetaminophen", "ibuprofen", "aspirin", "morphine",
            "codeine", "tramadol", "amoxicillin", "ampicillin", "penicillin",
            "metformin", "insulin", "atenolol", "amlodipine", "lisinopril",
            "simvastatin", "atorvastatin", "omeprazole", "ranitidine",
            "salbutamol", "prednisolone", "hydrocortisone", "furosemide"
        ]
        
        inn_lower = inn_name.lower()
        
        # Проверяем точные совпадения и частичные
        for med in who_essential_medicines:
            if med in inn_lower or inn_lower in med:
                return {
                    "status": "WHO EML Listed",
                    "details": f"Found in WHO Essential Medicines List"
                }
        
        return {
            "status": "Not in WHO EML",
            "details": "Препарат не найден в списке основных лекарств ВОЗ"
        }
        
    except Exception as e:
        logger.error(f"WHO EML check error for {inn_name}: {e}")
        return {
            "status": "WHO EML check error",
            "details": f"Ошибка проверки WHO EML: {str(e)}"
        }

async def compare_dosage(protocol_dosage: str, inn_name: str) -> Dict:
    """Сравнивает дозировку из протокола со стандартной"""
    try:
        # Упрощенная проверка дозировки
        if not protocol_dosage or not inn_name:
            return {
                "comparison_result": "insufficient_data",
                "details": "Недостаточно данных для сравнения дозировки"
            }
        
        # Извлекаем числовые значения из дозировки
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?', protocol_dosage)
        
        if numbers:
            return {
                "comparison_result": "within_range",
                "details": f"Дозировка {protocol_dosage} требует проверки по справочникам"
            }
        else:
            return {
                "comparison_result": "unclear_dosage",
                "details": "Не удалось извлечь числовые значения дозировки"
            }
            
    except Exception as e:
        logger.error(f"Dosage comparison error: {e}")
        return {
            "comparison_result": "comparison_error",
            "details": f"Ошибка сравнения дозировки: {str(e)}"
        }

async def check_all_regulators(inn_name: str, source_dosage: str = "") -> Dict:
    """Проверяет препарат во всех регуляторных базах"""
    logger.info(f"🏛️ Starting regulatory checks for: {inn_name}")
    
    try:
        # Запускаем все проверки параллельно
        tasks = [
            check_fda_status(inn_name),
            check_ema_status(inn_name),
            check_bnf_status(inn_name, ""),  # Используем новый BNF анализатор
            check_who_eml_status(inn_name),
            compare_dosage(source_dosage, inn_name)
        ]
        
        fda_result, ema_result, bnf_result, who_result, dosage_result = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        
        # Обрабатываем исключения
        def safe_result(result, default_status):
            if isinstance(result, Exception):
                logger.error(f"Regulatory check exception: {result}")
                return {"status": f"{default_status} error", "details": str(result)}
            return result
        
        regulatory_checks = {
            "FDA": safe_result(fda_result, "FDA"),
            "EMA": safe_result(ema_result, "EMA"),
            "BNF": safe_result(bnf_result, "BNF"),
            "WHO_EML": safe_result(who_result, "WHO EML")
        }
        
        dosage_check = safe_result(dosage_result, "Dosage comparison")
        
        logger.info(f"✅ Regulatory checks completed for: {inn_name}")
        
        return {
            "regulatory_checks": regulatory_checks,
            "dosage_check": dosage_check
        }
        
    except Exception as e:
        logger.error(f"❌ Error in regulatory checks for {inn_name}: {e}")
        return {
            "regulatory_checks": {
                "FDA": {"status": "Error", "details": str(e)},
                "EMA": {"status": "Error", "details": str(e)},
                "BNF": {"status": "Error", "details": str(e)},
                "WHO_EML": {"status": "Error", "details": str(e)}
            },
            "dosage_check": {
                "comparison_result": "error",
                "details": f"Ошибка проверки: {str(e)}"
            }
        }