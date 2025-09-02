import os
import time
import json
import asyncio
import logging
import re
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
    Enhanced PubMed client that finds relevant studies for drugs in disease context.
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

    def _extract_disease_from_context(self, context: str) -> str:
        """Extract main disease/condition from context for better PubMed search."""
        if not context:
            return ""
        
        # Enhanced disease extraction patterns
        disease_patterns = [
            # Russian patterns
            r'(диабет[а-я]*)',
            r'(гипертони[а-я]*)',
            r'(астм[а-я]*)',
            r'(пневмони[а-я]*)',
            r'(инфекци[а-я]*)',
            r'(воспалени[а-я]*)',
            r'(артрит[а-я]*)',
            r'(депресси[а-я]*)',
            r'(тревог[а-я]*)',
            r'(эпилепси[а-я]*)',
            r'(мигрен[а-я]*)',
            r'(бол[а-я]*)',
            r'(рак[а-я]*)',
            r'(опухол[а-я]*)',
            r'(лейкеми[а-я]*)',
            r'(лимфом[а-я]*)',
            r'(саркома[а-я]*)',
            r'(карцином[а-я]*)',
            r'(ишеми[а-я]*)',
            r'(инфаркт[а-я]*)',
            r'(инсульт[а-я]*)',
            r'(тромбоз[а-я]*)',
            r'(эмболи[а-я]*)',
            # English patterns
            r'(diabetes?)',
            r'(hypertension)',
            r'(asthma)',
            r'(pneumonia)',
            r'(infection)',
            r'(inflammation)',
            r'(arthritis)',
            r'(depression)',
            r'(anxiety)',
            r'(epilepsy)',
            r'(migraine)',
            r'(pain)',
            r'(cancer)',
            r'(tumor)',
            r'(leukemia)',
            r'(lymphoma)',
            r'(sarcoma)',
            r'(carcinoma)',
            r'(ischemia)',
            r'(infarction)',
            r'(stroke)',
            r'(thrombosis)',
            r'(embolism)'
        ]
        
        context_lower = context.lower()
        for pattern in disease_patterns:
            match = re.search(pattern, context_lower)
            if match:
                disease = match.group(1)
                logger.info(f"🎯 Extracted disease from context: {disease}")
                return disease
        
        # If no specific disease found, return first meaningful words
        words = [w for w in context.split()[:4] if len(w) > 3]
        result = ' '.join(words) if words else ""
        logger.info(f"🎯 Using general context: {result}")
        return result

    async def search_articles_for_drug(self, inn_name: str, brand_name: str, context: str, max_results=5) -> list:
        """
        Enhanced PubMed search that finds relevant studies for a drug in disease context.
        """
        if not inn_name or inn_name.lower() in ['unknown', 'не определен', '']:
            logger.warning(f"❌ Cannot search PubMed without valid INN name")
            return []

        # Extract main disease from context
        main_disease = self._extract_disease_from_context(context)
        
        # Build comprehensive search strategies
        search_strategies = []
        
        # Strategy 1: Drug + Disease + High-quality studies
        if main_disease:
            drug_terms = [f'"{inn_name}"[Title/Abstract]']
            if brand_name and brand_name != inn_name:
                drug_terms.append(f'"{brand_name}"[Title/Abstract]')
            
            drug_query = " OR ".join(drug_terms)
            disease_query = f'("{main_disease}"[Title/Abstract] OR "{main_disease}"[MeSH Terms])'
            study_types = '"systematic review"[Publication Type] OR "meta-analysis"[Publication Type] OR "randomized controlled trial"[Publication Type]'
            
            search_strategies.append({
                "query": f'({drug_query}) AND {disease_query} AND ({study_types}) AND ("last 10 years"[PDat])',
                "description": f"High-quality studies for {inn_name} in {main_disease}"
            })
        
        # Strategy 2: Drug + Any clinical studies
        drug_terms = [f'"{inn_name}"[Title/Abstract]']
        if brand_name and brand_name != inn_name:
            drug_terms.append(f'"{brand_name}"[Title/Abstract]')
        
        drug_query = " OR ".join(drug_terms)
        study_types = '"clinical trial"[Publication Type] OR "randomized controlled trial"[Publication Type] OR "review"[Publication Type]'
        
        search_strategies.append({
            "query": f'({drug_query}) AND ({study_types}) AND ("last 10 years"[PDat])',
            "description": f"Clinical studies for {inn_name}"
        })
        
        # Strategy 3: Broad drug search
        search_strategies.append({
            "query": f'"{inn_name}"[Title/Abstract] AND ("last 15 years"[PDat])',
            "description": f"General studies for {inn_name}"
        })

        # Try each strategy until we find results
        for i, strategy in enumerate(search_strategies):
            cache_key = f"pubmed_v3:{strategy['query']}:{max_results}"
            logger.info(f"🔍 Strategy {i+1}: {strategy['description']}")
            logger.info(f"🔍 Query: {strategy['query']}")

            # Check cache first
            if redis_client:
                try:
                    cached_result = await redis_client.get(cache_key)
                    if cached_result:
                        logger.info(f"✅ Cache hit for strategy {i+1}")
                        return json.loads(cached_result)
                except Exception as e:
                    logger.warning(f"Redis cache read failed: {e}")

            try:
                # Perform search with rate limiting
                await self._rate_limit()
                
                handle = Entrez.esearch(
                    db="pubmed", 
                    term=strategy["query"], 
                    retmax=max_results, 
                    sort="relevance"
                )
                record = Entrez.read(handle)
                handle.close()

                pmids = record["IdList"]
                if pmids:
                    logger.info(f"✅ Strategy {i+1} found {len(pmids)} articles")
                    
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
                        abstract_preview = abstract[:300] + "..." if len(abstract) > 300 else abstract
                        
                        # Extract authors (first 3)
                        authors = rec.get("AU", [])
                        author_str = ", ".join(authors[:3])
                        if len(authors) > 3:
                            author_str += " et al."
                        
                        article = {
                            "pmid": rec.get("PMID"),
                            "title": rec.get("TI", "No title available"),
                            "authors": author_str,
                            "journal": rec.get("TA", "N/A"),
                            "publication_date": rec.get("DP", "N/A"),
                            "publication_type": pub_type_str,
                            "abstract_preview": abstract_preview,
                            "link": f"https://pubmed.ncbi.nlm.nih.gov/{rec.get('PMID')}/"
                        }
                        articles.append(article)
                        logger.info(f"  📄 Found: {article['title'][:80]}... ({pub_type_str})")

                    # Cache results
                    if redis_client:
                        try:
                            await redis_client.set(cache_key, json.dumps(articles), ex=86400)  # 24 hours
                        except Exception as e:
                            logger.warning(f"Redis cache write failed: {e}")

                    logger.info(f"✅ PubMed search completed: {len(articles)} articles")
                    return articles
                else:
                    logger.info(f"❌ Strategy {i+1} found no results, trying next...")
                    
            except Exception as e:
                logger.error(f"❌ Strategy {i+1} failed: {e}")
                continue

        logger.warning(f"❌ All PubMed search strategies failed for {inn_name}")
        return []