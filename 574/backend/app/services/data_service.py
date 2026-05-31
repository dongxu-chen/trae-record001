from typing import List, Optional, Dict, Any
import logging
import hashlib
import json

from ..models.schemas import Paper, SourceType
from .crossref_client import CrossrefClient
from .dblp_client import DBLPClient

logger = logging.getLogger(__name__)


class DataService:
    def __init__(self):
        self.crossref = CrossrefClient()
        self.dblp = DBLPClient()
        self._paper_cache: Dict[str, Paper] = {}

    async def search_papers(self, query: str, source: SourceType = SourceType.CROSSREF, limit: int = 20) -> List[Paper]:
        logger.info(f"Searching {source} for: {query}")

        try:
            if source == SourceType.CROSSREF:
                papers = await self.crossref.search_papers(query, limit)
            elif source == SourceType.DBLP:
                papers = await self.dblp.search_papers(query, limit)
            else:
                papers = []

            for paper in papers:
                self._paper_cache[paper.doi] = paper

            logger.info(f"Found {len(papers)} papers")
            return papers

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_paper(self, doi: str) -> Optional[Paper]:
        if doi in self._paper_cache:
            return self._paper_cache[doi]

        try:
            if doi.startswith("dblp:"):
                key = doi.replace("dblp:", "")
                paper = await self.dblp.get_paper(key)
            else:
                paper = await self.crossref.get_paper(doi)

            if paper:
                self._paper_cache[doi] = paper

            return paper

        except Exception as e:
            logger.error(f"Get paper error for {doi}: {e}")
            return None

    async def get_papers(self, dois: List[str]) -> List[Paper]:
        papers = []
        for doi in dois:
            paper = await self.get_paper(doi)
            if paper:
                papers.append(paper)
        return papers

    async def get_references(self, doi: str) -> List[str]:
        try:
            if doi.startswith("dblp:"):
                key = doi.replace("dblp:", "")
                return await self.dblp.get_references(key)
            else:
                return await self.crossref.get_references(doi)
        except Exception as e:
            logger.error(f"Get references error for {doi}: {e}")
            return []

    async def get_citations(self, doi: str) -> List[str]:
        try:
            if doi.startswith("dblp:"):
                key = doi.replace("dblp:", "")
                return await self.dblp.get_citations(key)
            else:
                return await self.crossref.get_citations(doi)
        except Exception as e:
            logger.error(f"Get citations error for {doi}: {e}")
            return []

    def get_cache_key(self, prefix: str, *args) -> str:
        key_str = f"{prefix}:{':'.join(str(a) for a in args)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def build_citation_network(
        self,
        seed_dois: List[str],
        depth: int = 2,
        max_nodes: int = 200
    ) -> Dict[str, Any]:
        visited = set()
        queue = [(doi, 0) for doi in seed_dois]
        papers: Dict[str, Paper] = {}
        edges: List[tuple] = []

        logger.info(f"Building citation network from {len(seed_dois)} seeds, depth={depth}")

        while queue and len(visited) < max_nodes:
            doi, current_depth = queue.pop(0)

            if doi in visited or current_depth > depth:
                continue

            visited.add(doi)

            paper = await self.get_paper(doi)
            if not paper:
                continue

            papers[doi] = paper

            if current_depth < depth:
                references = await self.get_references(doi)
                for ref_doi in references:
                    if ref_doi not in visited:
                        edges.append((doi, ref_doi))
                        queue.append((ref_doi, current_depth + 1))

                if current_depth < depth // 2:
                    citations = await self.get_citations(doi)
                    for cit_doi in citations[:20]:
                        if cit_doi not in visited:
                            edges.append((cit_doi, doi))
                            queue.append((cit_doi, current_depth + 1))

        for source, target in edges:
            if source not in papers:
                paper = await self.get_paper(source)
                if paper:
                    papers[source] = paper
            if target not in papers:
                paper = await self.get_paper(target)
                if paper:
                    papers[target] = paper

        valid_edges = [(s, t) for s, t in edges if s in papers and t in papers]

        logger.info(f"Network built: {len(papers)} nodes, {len(valid_edges)} edges")

        return {
            "papers": list(papers.values()),
            "edges": valid_edges,
            "node_count": len(papers),
            "edge_count": len(valid_edges)
        }
