import httpx
import json
import time
import re
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from datetime import datetime
import logging

from ..config import settings
from ..models.schemas import Paper, Author, SourceType

logger = logging.getLogger(__name__)


class DBLPClient:
    BASE_URL = "https://dblp.org/search/publ/api"
    PUB_URL = "https://dblp.org/rec"

    def __init__(self):
        self.timeout = settings.request_timeout
        self.rate_limit = settings.dblp_rate_limit
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
            "q": query,
            "format": "json",
            "h": limit,
            "f": 0,
            "compl": "author"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                papers = []
                hits = data.get("result", {}).get("hits", {}).get("hit", [])
                for hit in hits:
                    paper = self._parse_paper(hit.get("info", {}))
                    if paper:
                        papers.append(paper)

                return papers

        except Exception as e:
            logger.error(f"DBLP search error: {e}")
            return []

    async def get_paper(self, key: str) -> Optional[Paper]:
        self._wait_for_rate_limit()

        try:
            url = f"{self.PUB_URL}/{key}.xml"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_xml_paper(response.text, key)

        except Exception as e:
            logger.error(f"DBLP get paper error for {key}: {e}")
            return None

    def _parse_paper(self, info: Dict[str, Any]) -> Optional[Paper]:
        try:
            key = info.get("key")
            if not key:
                return None

            title = info.get("title", "Untitled")
            doi = info.get("doi", f"dblp:{key}")

            authors = []
            authors_data = info.get("authors", {}).get("author", [])
            if isinstance(authors_data, dict):
                authors_data = [authors_data]

            for author_data in authors_data:
                name = author_data.get("text", "")
                pid = author_data.get("@pid")
                if name:
                    authors.append(Author(
                        name=name,
                        orcid=None,
                        affiliation=None
                    ))

            year_str = info.get("year")
            year = int(year_str) if year_str else datetime.now().year

            venue = info.get("venue", "Unknown Venue")
            url = info.get("url")
            pages = info.get("pages")
            volume = info.get("volume")
            number = info.get("number")

            if volume and number:
                venue = f"{venue}, Vol. {volume}, No. {number}"
            if pages:
                venue = f"{venue}, pp. {pages}"

            return Paper(
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                abstract=None,
                keywords=None,
                references=[],
                citations=0,
                url=url,
                source=SourceType.DBLP
            )

        except Exception as e:
            logger.warning(f"Error parsing DBLP paper: {e}")
            return None

    def _parse_xml_paper(self, xml_content: str, key: str) -> Optional[Paper]:
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_content)

            title_elem = root.find(".//title")
            title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

            doi_elem = root.find(".//doi")
            doi = doi_elem.text if doi_elem is not None and doi_elem.text else f"dblp:{key}"

            authors = []
            for author_elem in root.findall(".//author"):
                name = author_elem.text
                if name:
                    authors.append(Author(name=name))

            year_elem = root.find(".//year")
            year = int(year_elem.text) if year_elem is not None and year_elem.text else datetime.now().year

            journal_elem = root.find(".//journal")
            booktitle_elem = root.find(".//booktitle")
            venue = journal_elem.text if journal_elem is not None else \
                    booktitle_elem.text if booktitle_elem is not None else "Unknown Venue"

            ee_elem = root.find(".//ee")
            url = ee_elem.text if ee_elem is not None else None

            references = []
            for ref_elem in root.findall(".//ref"):
                ref_key = ref_elem.get("key")
                if ref_key:
                    references.append(f"dblp:{ref_key}")

            return Paper(
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                abstract=None,
                keywords=None,
                references=references,
                citations=0,
                url=url,
                source=SourceType.DBLP
            )

        except Exception as e:
            logger.warning(f"Error parsing DBLP XML paper: {e}")
            return None

    async def get_references(self, key: str) -> List[str]:
        paper = await self.get_paper(key)
        return paper.references if paper else []

    async def get_citations(self, key: str) -> List[str]:
        self._wait_for_rate_limit()

        try:
            url = f"https://dblp.org/rec/{key}/%23citedby"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_citations_html(response.text)

        except Exception as e:
            logger.error(f"DBLP get citations error for {key}: {e}")
            return []

    def _parse_citations_html(self, html: str) -> List[str]:
        citations = []
        try:
            pattern = r'href="https://dblp\.org/rec/([^"]+)"'
            matches = re.findall(pattern, html)
            for match in matches:
                if match and not match.startswith("#"):
                    citations.append(f"dblp:{match}")
        except Exception as e:
            logger.warning(f"Error parsing DBLP citations: {e}")
        return list(set(citations))[:100]
