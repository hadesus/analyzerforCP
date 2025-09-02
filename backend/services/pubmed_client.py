import os
import time
import json
import asyncio
from collections import deque
import redis.asyncio as redis
from Bio import Entrez
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")
PUBMED_API_EMAIL = os.getenv("PUBMED_API_EMAIL")

if not PUBMED_API_EMAIL:
    raise ValueError("PUBMED_API_EMAIL not found in environment variables.")

Entrez.api_key = PUBMED_API_KEY
Entrez.email = PUBMED_API_EMAIL

# Redis client for caching
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost"))

class PubMedClient:
    """
    A client for searching PubMed, with caching and rate limiting.
    """
    def __init__(self, reqs_per_second=9):
        self.req_interval = 1.0 / reqs_per_second
        self.request_timestamps = deque()

    async def _rate_limit(self):
        """Ensures that requests do not exceed the rate limit."""
        while self.request_timestamps:
            time_since_oldest_req = time.monotonic() - self.request_timestamps[0]
            if time_since_oldest_req > 1.0:
                self.request_timestamps.popleft()
            else:
                break

        if len(self.request_timestamps) >= 9:
            wait_time = self.req_interval - (time.monotonic() - self.request_timestamps[-1])
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.request_timestamps.append(time.monotonic())

    async def search_articles(self, inn_name: str, brand_name: str, disease_context: str, max_results=5) -> list:
        """
        Searches PubMed for articles, handling caching and rate limiting.
        """
        search_term_base = f'({inn_name}[Title/Abstract] OR "{brand_name}"[Title/Abstract]) AND ("{disease_context}"[Title/Abstract])'
        publication_types = '"randomized controlled trial"[Publication Type] OR "meta-analysis"[Publication Type] OR "systematic review"[Publication Type]'
        search_term = f'({search_term_base}) AND ({publication_types})'

        cache_key = f"pubmed:{search_term}:{max_results}"

        # 1. Check cache first
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            print(f"Cache hit for PubMed query: {search_term}")
            return json.loads(cached_result)

        print(f"Cache miss for PubMed query. Searching: {search_term}")

        try:
            # 2. If not in cache, perform search (with rate limiting)
            await self._rate_limit()
            handle = Entrez.esearch(db="pubmed", term=search_term, retmax=max_results, sort="relevance")
            record = Entrez.read(handle)
            handle.close()

            pmids = record["IdList"]
            if not pmids:
                return []

            await self._rate_limit()
            handle = Entrez.efetch(db="pubmed", id=pmids, rettype="medline", retmode="dict")
            records = handle.read()
            handle.close()

            # 3. Parse results
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

            # 4. Store in cache (e.g., for 24 hours)
            await redis_client.set(cache_key, json.dumps(articles), ex=86400)

            return articles

        except Exception as e:
            print(f"An error occurred during PubMed search: {e}")
            return []
