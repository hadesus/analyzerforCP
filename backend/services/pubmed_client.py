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
    A client for searching PubMed, with caching and rate limiting.
    Same logic as demo version.
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

    async def search_articles(self, inn_name: str, brand_name: str, disease_context: str, max_results=5) -> list:
        """
        Searches PubMed for articles - same approach as demo.
        """
        # Build search term like in demo
        drug_terms = [inn_name]
        if brand_name and brand_name != inn_name:
            drug_terms.append(brand_name)
        
        drug_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in drug_terms])
        
        # Add disease context if available
        context_query = ""
        if disease_context and disease_context.strip():
            context_query = f' AND "{disease_context}"[Title/Abstract]'
        
        # Focus on high-quality study types
        study_types = [
            '"randomized controlled trial"[Publication Type]',
            '"meta-analysis"[Publication Type]',
            '"systematic review"[Publication Type]',
            '"clinical trial"[Publication Type]'
        ]
        study_query = " OR ".join(study_types)
        
        search_term = f'({drug_query}){context_query} AND ({study_query})'
        
        cache_key = f"pubmed:{search_term}:{max_results}"
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

        logger.info(f"🔍 Searching PubMed for: {inn_name}")

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

            # Parse results - same format as demo
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
                logger.info(f"  📄 Found: {article['title'][:100]}...")

            # Cache results
            if redis_client:
                try:
                    await redis_client.set(cache_key, json.dumps(articles), ex=86400)
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")

            logger.info(f"✅ PubMed search completed: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"❌ PubMed search failed: {e}")
            return []