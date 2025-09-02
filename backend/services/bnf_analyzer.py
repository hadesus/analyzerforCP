"""
BNF Analysis Service
Анализирует соответствие препаратов справочникам BNF
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

class BNFAnalyzer:
    def __init__(self):
        self.bnf_data = {}
        self.load_bnf_files()
    
    def load_bnf_files(self):
        """Загружает BNF справочники из текстовых файлов"""
        bnf_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'bnf')
        
        bnf_files = {
            'adult': 'bnf_84_british2022-2023.txt',
            'children': 'bnf_children_2022-2023.txt'
        }
        
        for category, filename in bnf_files.items():
            filepath = os.path.join(bnf_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.bnf_data[category] = content
                        logger.info(f"✅ Loaded BNF {category}: {len(content)} characters")
                except Exception as e:
                    logger.error(f"❌ Error loading BNF {category}: {e}")
            else:
                logger.warning(f"⚠️ BNF file not found: {filepath}")
                self.bnf_data[category] = ""
    
    def search_drug_in_bnf(self, drug_name: str, inn_name: str = "") -> Dict:
        """Ищет препарат в справочниках BNF"""
        if not self.bnf_data:
            return {
                "status": "BNF files not available",
                "found_in": [],
                "details": "BNF справочники не загружены"
            }
        
        search_terms = [drug_name.lower()]
        if inn_name and inn_name.lower() != drug_name.lower():
            search_terms.append(inn_name.lower())
        
        found_in = []
        details = []
        
        for category, content in self.bnf_data.items():
            if not content:
                continue
                
            content_lower = content.lower()
            
            for term in search_terms:
                if self._find_drug_mentions(term, content_lower):
                    found_in.append(category)
                    # Извлекаем контекст вокруг найденного препарата
                    context = self._extract_drug_context(term, content)
                    if context:
                        details.append(f"BNF {category}: {context[:200]}...")
                    break
        
        if found_in:
            status = f"Found in BNF {', '.join(found_in)}"
        else:
            status = "Not found in BNF"
        
        return {
            "status": status,
            "found_in": found_in,
            "details": "; ".join(details) if details else "Препарат не найден в загруженных справочниках BNF"
        }
    
    def _find_drug_mentions(self, drug_name: str, content: str) -> bool:
        """Ищет упоминания препарата в тексте"""
        # Ищем точные совпадения и вариации
        patterns = [
            rf'\b{re.escape(drug_name)}\b',  # Точное совпадение
            rf'\b{re.escape(drug_name)}s?\b',  # С возможным 's' в конце
            rf'\b{re.escape(drug_name[:-1])}\w*\b' if len(drug_name) > 3 else None,  # Частичное совпадение
        ]
        
        for pattern in patterns:
            if pattern and re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_drug_context(self, drug_name: str, content: str) -> str:
        """Извлекает контекст вокруг найденного препарата"""
        try:
            # Ищем первое упоминание препарата
            pattern = rf'\b{re.escape(drug_name)}\b'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if match:
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                context = content[start:end].strip()
                
                # Очищаем контекст от лишних символов
                context = re.sub(r'\s+', ' ', context)
                return context
            
        except Exception as e:
            logger.error(f"Error extracting context for {drug_name}: {e}")
        
        return ""
    
    def get_bnf_stats(self) -> Dict:
        """Возвращает статистику загруженных BNF файлов"""
        stats = {}
        for category, content in self.bnf_data.items():
            stats[category] = {
                "loaded": bool(content),
                "size": len(content),
                "estimated_drugs": len(re.findall(r'\b[A-Z][a-z]+(?:ine|ol|am|ide|ate|ium)\b', content)) if content else 0
            }
        return stats

# Глобальный экземпляр анализатора
bnf_analyzer = BNFAnalyzer()

async def check_bnf_status(inn_name: str, brand_name: str = "") -> Dict:
    """Проверяет статус препарата в BNF справочниках"""
    try:
        # Используем и МНН и торговое название для поиска
        search_name = inn_name if inn_name else brand_name
        result = bnf_analyzer.search_drug_in_bnf(search_name, inn_name)
        
        logger.info(f"BNF check for {search_name}: {result['status']}")
        return result
        
    except Exception as e:
        logger.error(f"Error checking BNF status for {inn_name}: {e}")
        return {
            "status": "Error checking BNF",
            "found_in": [],
            "details": f"Ошибка при проверке BNF: {str(e)}"
        }