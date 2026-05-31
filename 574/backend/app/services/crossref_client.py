import httpx
import json
import time
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from datetime import datetime
import logging

from ..config import settings
from ..models.schemas import Paper, Author, SourceType

logger = logging.getLogger(__name__)


class CrossrefClient:
    BASE_URL = "https://api.crossref.org"
    USER_AGENT = "AcademicCitationAnalyzer/1.0 (mailto:research@example.com)"

    def __init__(self):
        self.timeout = settings.request_timeout
        self.rate_limit = settings.crossref_rate_limit
        self.last_request_time = 0
        self.min_interval = 1.0 / self.rate_limit

    def _wait_for_rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    async def search_papers(self, query: str, limit: int = 20) -> List[Paper]:
        self._wait_for_rate_limit()

        params = {
            "query": query,
            "rows": limit,
            "select": "DOI,title,author,issued,container-title,abstract,reference,is-referenced-by-count,URL",
            "mailto": "research@example.com"
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/works",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                papers = []
                for item in data.get("message", {}).get("items", []):
                    paper = self._parse_paper(item)
                    if paper:
                        papers.append(paper)

                return papers

        except Exception as e:
            logger.error(f"Crossref search error: {e}")
            return []

    async def get_paper(self, doi: str) -> Optional[Paper]:
        self._wait_for_rate_limit()

        encoded_doi = quote_plus(doi)
        params = {
            "select": "DOI,title,author,issued,container-title,abstract,reference,is-referenced-by-count,URL,subject"
        }
        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/works/{encoded_doi}",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_paper(data.get("message", {}))

        except Exception as e:
            logger.error(f"Crossref get paper error for {doi}: {e}")
            return None

    async def get_references(self, doi: str) -> List[str]:
        paper = await self.get_paper(doi)
        return paper.references if paper else []

    async def get_citations(self, doi: str, limit: int = 100) -> List[str]:
        self._wait_for_rate_limit()

        encoded_doi = quote_plus(doi)
        params = {
            "rows": limit,
            "select": "DOI"
        }
        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/works/{encoded_doi}/is-cited-by",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                citations = []
                for item in data.get("message", {}).get("items", []):
                    item_doi = item.get("DOI")
                    if item_doi:
                        citations.append(item_doi)

                return citations

        except Exception as e:
            logger.error(f"Crossref get citations error for {doi}: {e}")
            return []

    def _parse_paper(self, item: Dict[str, Any]) -> Optional[Paper]:
        try:
            doi = item.get("DOI")
            if not doi:
                return None

            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Untitled"

            authors = []
            for author_data in item.get("author", []):
                given = author_data.get("given", "")
                family = author_data.get("family", "")
                name = f"{given} {family}".strip() or family
                if name:
                    authors.append(Author(
                        name=name,
                        orcid=author_data.get("ORCID"),
                        affiliation=author_data.get("affiliation", [{}])[0].get("name") if author_data.get("affiliation") else None
                    ))

            issued = item.get("issued", {}).get("date-parts", [[None]])
            year = issued[0][0] if issued and issued[0] else None

            if not year:
                created = item.get("created", {}).get("date-parts", [[None]])
                year = created[0][0] if created and created[0] else datetime.now().year

            venue_list = item.get("container-title", [])
            venue = venue_list[0] if venue_list else "Unknown Venue"

            abstract = item.get("abstract")
            if abstract:
                abstract = self._clean_abstract(abstract)

            references = []
            for ref in item.get("reference", []):
                ref_doi = ref.get("DOI")
                if ref_doi:
                    references.append(ref_doi)

            citations = item.get("is-referenced-by-count", 0)
            url = item.get("URL")
            keywords = item.get("subject")

            return Paper(
                doi=doi,
                title=title,
                authors=authors,
                year=int(year),
                venue=venue,
                abstract=abstract,
                keywords=keywords,
                references=references,
                citations=int(citations),
                url=url,
                source=SourceType.CROSSREF
            )

        except Exception as e:
            logger.warning(f"Error parsing Crossref paper: {e}")
            return None

    def _clean_abstract(self, abstract: str) -> str:
        import re
        abstract = re.sub(r'<jats:[^>]+>', '', abstract)
        abstract = re.sub(r'</jats:[^>]+>', '', abstract)
        abstract = re.sub(r'<[^>]+>', '', abstract)
        return abstract.strip()

    async def get_papers_by_dois(self, dois: List[str]) -> List[Paper]:
        papers = []
        for doi in dois:
            paper = await self.get_paper(doi)
            if paper:
                papers.append(paper)
        return papers
