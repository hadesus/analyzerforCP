import os
import time
import json
import asyncio
import logging
from collections import deque
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
from Bio import Entrez
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# --- Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")
PUBMED_API_EMAIL = os.getenv("PUBMED_API_EMAIL")

if not PUBMED_API_EMAIL:
    raise ValueError("PUBMED_API_EMAIL not found in environment variables.")

Entrez.api_key = PUBMED_API_KEY
Entrez.email = PUBMED_API_EMAIL

# Redis client for caching (optional)
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
    except Exception as e:
        print(f"Redis connection failed: {e}. Continuing without caching.")
        redis_client = None

class PubMedClient:
    """
    Enhanced PubMed client with better search strategies and disease context.
    """
    def __init__(self, reqs_per_second=9):
        self.req_interval = 1.0 / reqs_per_second
        self.request_timestamps = deque()

    async def _rate_limit(self):
        """Ensures that requests do not exceed the rate limit."""
        current_time = time.monotonic()
        
        # Remove timestamps older than 1 second
        while self.request_timestamps:
            if current_time - self.request_timestamps[0] > 1.0:
                self.request_timestamps.popleft()
            else:
                break

        # If we have too many recent requests, wait
        if len(self.request_timestamps) >= 9:
            wait_time = self.req_interval
            await asyncio.sleep(wait_time)

        self.request_timestamps.append(current_time)

    def _extract_disease_context(self, context_indication: str) -> str:
        """Extract main disease/condition from context for better PubMed search."""
        if not context_indication:
            return ""
        
        # Common medical terms that indicate diseases/conditions
        disease_keywords = [
            'диабет', 'гипертония', 'астма', 'пневмония', 'инфекция', 'воспаление',
            'артрит', 'депрессия', 'тревога', 'эпилепсия', 'мигрень', 'боль',
            'рак', 'опухоль', 'лейкемия', 'лимфома', 'саркома', 'карцинома',
            'ишемия', 'инфаркт', 'инсульт', 'тромбоз', 'эмболия',
            'diabetes', 'hypertension', 'asthma', 'pneumonia', 'infection', 'inflammation',
            'arthritis', 'depression', 'anxiety', 'epilepsy', 'migraine', 'pain',
            'cancer', 'tumor', 'leukemia', 'lymphoma', 'sarcoma', 'carcinoma',
            'ischemia', 'infarction', 'stroke', 'thrombosis', 'embolism'
        ]
        
        context_lower = context_indication.lower()
        found_diseases = [keyword for keyword in disease_keywords if keyword in context_lower]
        
        if found_diseases:
            return found_diseases[0]  # Return the first found disease
        
        # If no specific disease found, return first few words
        words = context_indication.split()[:3]
        return ' '.join(words) if words else ""

    async def search_articles(self, inn_name: str, brand_name: str, disease_context: str, max_results=5) -> list:
        """
        Enhanced PubMed search with better disease context integration.
        """
        if not inn_name or inn_name.lower() in ['unknown', 'не определен']:
            logger.warning(f"❌ Cannot search PubMed without valid INN name")
            return []

        # Extract main disease from context
        main_disease = self._extract_disease_context(disease_context)
        
        # Build comprehensive search query
        drug_terms = [inn_name]
        if brand_name and brand_name != inn_name:
            drug_terms.append(brand_name)
        
        # Create drug query with both INN and brand name
        drug_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in drug_terms])
        
        # Add disease context if available
        context_query = ""
        if main_disease:
            context_query = f' AND ("{main_disease}"[Title/Abstract] OR "{main_disease}"[MeSH Terms])'
        
        # Prioritize high-quality study types
        study_types = [
            '"randomized controlled trial"[Publication Type]',
            '"meta-analysis"[Publication Type]',
            '"systematic review"[Publication Type]',
            '"clinical trial"[Publication Type]',
            '"review"[Publication Type]'
        ]
        study_query = " OR ".join(study_types)
        
        # Build final search term
        search_term = f'({drug_query}){context_query} AND ({study_query}) AND ("last 10 years"[PDat])'
        
        cache_key = f"pubmed_v2:{search_term}:{max_results}"
        logger.info(f"🔍 PubMed search: {search_term}")

        # Check cache first
        if redis_client:
            try:
                cached_result = await redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"✅ Cache hit for PubMed query")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        logger.info(f"🔍 Searching PubMed for: {inn_name} (context: {main_disease})")

        try:
            # Perform search with rate limiting
            await self._rate_limit()
            
            handle = Entrez.esearch(
                db="pubmed", 
                term=search_term, 
                retmax=max_results, 
                sort="relevance"
            )
            record = Entrez.read(handle)
            handle.close()

            pmids = record["IdList"]
            if not pmids:
                logger.info(f"❌ No PubMed articles found for {inn_name}")
                
                # Try broader search without disease context
                if main_disease:
                    logger.info(f"🔄 Trying broader search without disease context...")
                    broader_search = f'({drug_query}) AND ({study_query}) AND ("last 10 years"[PDat])'
                    
                    await self._rate_limit()
                    handle = Entrez.esearch(
                        db="pubmed", 
                        term=broader_search, 
                        retmax=max_results, 
                        sort="relevance"
                    )
                    record = Entrez.read(handle)
                    handle.close()
                    pmids = record["IdList"]
                
                if not pmids:
                    return []

            logger.info(f"✅ Found {len(pmids)} PubMed articles")

            # Fetch article details
            await self._rate_limit()
            
            handle = Entrez.efetch(
                db="pubmed", 
                id=pmids, 
                rettype="medline", 
                retmode="dict"
            )
            records = handle.read()
            handle.close()

            # Parse results with enhanced metadata
            articles = []
            for rec in records:
                # Extract publication type
                pub_types = rec.get("PT", [])
                pub_type_str = ", ".join(pub_types) if pub_types else "Article"
                
                # Extract abstract if available
                abstract = rec.get("AB", "")
                abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                
                article = {
                    "pmid": rec.get("PMID"),
                    "title": rec.get("TI", "No title available"),
                    "authors": rec.get("AU", []),
                    "journal": rec.get("TA", "N/A"),
                    "publication_date": rec.get("DP", "N/A"),
                    "publication_type": pub_type_str,
                    "abstract_preview": abstract_preview,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{rec.get('PMID')}/"
                }
                articles.append(article)
                logger.info(f"  📄 Found: {article['title'][:100]}... ({pub_type_str})")

            # Cache results
            if redis_client:
                try:
                    await redis_client.set(cache_key, json.dumps(articles), ex=86400)  # 24 hours
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")

            logger.info(f"✅ PubMed search completed: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"❌ PubMed search failed: {e}")
            return []

    async def search_articles_by_disease(self, disease_term: str, max_results=10) -> list:
        """
        Search for general articles about a disease/condition.
        """
        if not disease_term:
            return []
            
        # Build disease-focused search
        search_term = f'"{disease_term}"[Title/Abstract] AND ("systematic review"[Publication Type] OR "meta-analysis"[Publication Type]) AND ("last 5 years"[PDat])'
        
        cache_key = f"pubmed_disease:{disease_term}:{max_results}"
        logger.info(f"🔍 Disease-focused PubMed search: {search_term}")

        # Check cache first
        if redis_client:
            try:
                cached_result = await redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"✅ Cache hit for disease query")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        try:
            await self._rate_limit()
            
            handle = Entrez.esearch(
                db="pubmed", 
                term=search_term, 
                retmax=max_results, 
                sort="relevance"
            )
            record = Entrez.read(handle)
            handle.close()

            pmids = record["IdList"]
            if not pmids:
                return []

            # Fetch article details
            await self._rate_limit()
            
            handle = Entrez.efetch(
                db="pubmed", 
                id=pmids, 
                rettype="medline", 
                retmode="dict"
            )
            records = handle.read()
            handle.close()

            articles = []
            for rec in records:
                article = {
                    "pmid": rec.get("PMID"),
                    "title": rec.get("TI", "No title available"),
                    "authors": rec.get("AU", []),
                    "journal": rec.get("TA", "N/A"),
                    "publication_date": rec.get("DP", "N/A"),
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{rec.get('PMID')}/"
                }
                articles.append(article)

            # Cache results
            if redis_client:
                try:
                    await redis_client.set(cache_key, json.dumps(articles), ex=86400)
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")

            return articles

        except Exception as e:
            logger.error(f"❌ Disease PubMed search failed: {e}")
            return []