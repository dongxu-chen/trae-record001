import networkx as nx
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime
import logging
import math

from ..models.schemas import (
    Paper, RecommendedPaper, PaperRecommendations,
    CollaboratorInfo, CollaborationNetwork,
    CitationPrediction, BatchCitationPrediction
)

logger = logging.getLogger(__name__)


class PaperRecommender:
    def __init__(self, graph: nx.DiGraph, papers: Dict[str, Paper]):
        self.graph = graph
        self.papers = papers

    def recommend(
        self,
        target_doi: str,
        limit: int = 20,
        method: str = 'hybrid'
    ) -> PaperRecommendations:
        if target_doi not in self.graph:
            return PaperRecommendations(
                target_doi=target_doi,
                recommendations=[],
                algorithm=method
            )

        target_paper = self.papers.get(target_doi)
        if not target_paper:
            return PaperRecommendations(
                target_doi=target_doi,
                recommendations=[],
                algorithm=method
            )

        candidates = self._get_candidate_papers(target_doi)

        scored = []
        for doi in candidates:
            if doi == target_doi:
                continue

            paper = self.papers.get(doi)
            if not paper:
                continue

            if method == 'citation':
                score, reason = self._score_by_citation(target_doi, doi)
            elif method == 'content':
                score, reason = self._score_by_content(target_paper, paper)
            else:
                score, reason = self._score_hybrid(target_doi, target_paper, doi, paper)

            common_refs = self._get_common_references(target_doi, doi)
            common_cits = self._get_common_citations(target_doi, doi)

            scored.append(RecommendedPaper(
                doi=doi,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                venue=paper.venue,
                score=score,
                reason=reason,
                similarity=self._calculate_similarity(target_paper, paper),
                common_references=common_refs,
                common_citations=common_cits
            ))

        scored.sort(key=lambda x: x.score, reverse=True)

        return PaperRecommendations(
            target_doi=target_doi,
            recommendations=scored[:limit],
            algorithm=method
        )

    def _get_candidate_papers(self, target_doi: str) -> Set[str]:
        candidates = set()

        for ref in self.graph.successors(target_doi):
            candidates.add(ref)
            for ref2 in self.graph.successors(ref):
                candidates.add(ref2)

        for cit in self.graph.predecessors(target_doi):
            candidates.add(cit)
            for cit2 in self.graph.predecessors(cit):
                candidates.add(cit2)

        for node in self.graph.nodes():
            if len(candidates) < 100:
                candidates.add(node)

        return candidates

    def _score_by_citation(self, target_doi: str, doi: str) -> Tuple[float, str]:
        target_refs = set(self.graph.successors(target_doi))
        target_cits = set(self.graph.predecessors(target_doi))
        paper_refs = set(self.graph.successors(doi))
        paper_cits = set(self.graph.predecessors(doi))

        jaccard_refs = len(target_refs & paper_refs) / max(1, len(target_refs | paper_refs))
        jaccard_cits = len(target_cits & paper_cits) / max(1, len(target_cits | paper_cits))

        score = 0.6 * jaccard_refs + 0.4 * jaccard_cits

        reasons = []
        if jaccard_refs > 0.3:
            reasons.append("高参考文献重叠")
        if jaccard_cits > 0.1:
            reasons.append("共同引用关系")
        if self.graph.has_edge(target_doi, doi):
            score += 0.3
            reasons.append("直接引用")

        return score, "; ".join(reasons) if reasons else "基于引用网络"

    def _score_by_content(self, target: Paper, paper: Paper) -> Tuple[float, str]:
        target_keywords = set(target.keywords or [])
        paper_keywords = set(paper.keywords or [])

        target_words = set(target.title.lower().split())
        paper_words = set(paper.title.lower().split())

        keyword_sim = len(target_keywords & paper_keywords) / max(1, len(target_keywords | paper_keywords))
        title_sim = len(target_words & paper_words) / max(1, len(target_words | paper_words))

        score = 0.7 * keyword_sim + 0.3 * title_sim

        reasons = []
        if keyword_sim > 0.5:
            reasons.append("关键词高度匹配")
        if target.venue == paper.venue:
            score += 0.1
            reasons.append("相同发表期刊")

        return score, "; ".join(reasons) if reasons else "基于内容相似性"

    def _score_hybrid(
        self,
        target_doi: str,
        target_paper: Paper,
        doi: str,
        paper: Paper
    ) -> Tuple[float, str]:
        cit_score, cit_reason = self._score_by_citation(target_doi, doi)
        con_score, con_reason = self._score_by_content(target_paper, paper)

        score = 0.55 * cit_score + 0.45 * con_score

        reasons = []
        if cit_score > 0.3:
            reasons.append(cit_reason)
        if con_score > 0.2:
            reasons.append(con_reason)

        return score, "; ".join(reasons) if reasons else "综合推荐"

    def _calculate_similarity(self, target: Paper, paper: Paper) -> float:
        target_keywords = set(target.keywords or [])
        paper_keywords = set(paper.keywords or [])

        if not target_keywords or not paper_keywords:
            return 0.0

        return len(target_keywords & paper_keywords) / len(target_keywords | paper_keywords)

    def _get_common_references(self, doi1: str, doi2: str) -> List[str]:
        refs1 = set(self.graph.successors(doi1))
        refs2 = set(self.graph.successors(doi2))
        common = refs1 & refs2
        return list(common)[:5]

    def _get_common_citations(self, doi1: str, doi2: str) -> List[str]:
        cits1 = set(self.graph.predecessors(doi1))
        cits2 = set(self.graph.predecessors(doi2))
        common = cits1 & cits2
        return list(common)[:5]


class CollaboratorFinder:
    def __init__(self, graph: nx.DiGraph, papers: Dict[str, Paper]):
        self.graph = graph
        self.papers = papers
        self.author_papers = self._build_author_index()

    def _build_author_index(self) -> Dict[str, List[str]]:
        author_papers = defaultdict(list)
        for paper in self.papers.values():
            for author in paper.authors:
                author_papers[author.name].append(paper.doi)
        return author_papers

    def find_collaborators(self, author_name: str, limit: int = 20) -> CollaborationNetwork:
        target_papers = self.author_papers.get(author_name, [])

        if not target_papers:
            return CollaborationNetwork(
                target_author=author_name,
                existing_collaborators=[],
                potential_collaborators=[]
            )

        target_authors = self._get_target_authors(target_papers)
        existing = self._find_existing_collaborators(author_name, target_papers)
        potential = self._find_potential_collaborators(author_name, target_papers, target_authors)

        return CollaborationNetwork(
            target_author=author_name,
            existing_collaborators=existing,
            potential_collaborators=potential[:limit]
        )

    def _get_target_authors(self, target_papers: List[str]) -> Set[str]:
        authors = set()
        for doi in target_papers:
            paper = self.papers.get(doi)
            if paper:
                for author in paper.authors:
                    authors.add(author.name)
        return authors

    def _find_existing_collaborators(
        self,
        author_name: str,
        target_papers: List[str]
    ) -> List[CollaboratorInfo]:
        collaborators = defaultdict(lambda: {
            'papers': [],
            'affiliation': None,
            'orcid': None
        })

        for doi in target_papers:
            paper = self.papers.get(doi)
            if not paper:
                continue

            for author in paper.authors:
                if author.name == author_name:
                    continue

                collaborators[author.name]['papers'].append(doi)
                if author.affiliation:
                    collaborators[author.name]['affiliation'] = author.affiliation
                if author.orcid:
                    collaborators[author.name]['orcid'] = author.orcid

        result = []
        for name, data in collaborators.items():
            paper_count = len(data['papers'])
            score = paper_count * 0.8 + self._calculate_impact(data['papers']) * 0.2

            result.append(CollaboratorInfo(
                name=name,
                orcid=data['orcid'],
                affiliation=data['affiliation'],
                paper_count=paper_count,
                collaboration_score=min(1.0, score),
                common_papers=data['papers'][:10],
                research_overlap=self._extract_research_overlap(data['papers']),
                potential_impact=self._calculate_impact(data['papers']),
                match_reason=f"已共同发表 {paper_count} 篇论文"
            ))

        result.sort(key=lambda x: x.collaboration_score, reverse=True)
        return result[:10]

    def _find_potential_collaborators(
        self,
        author_name: str,
        target_papers: List[str],
        target_authors: Set[str]
    ) -> List[CollaboratorInfo]:
        candidates = defaultdict(lambda: {
            'common_refs': set(),
            'common_cits': set(),
            'keywords': set(),
            'affiliation': None,
            'orcid': None,
            'paper_count': 0
        })

        target_refs = set()
        target_cits = set()
        target_keywords = set()

        for doi in target_papers:
            target_refs.update(self.graph.successors(doi))
            target_cits.update(self.graph.predecessors(doi))
            paper = self.papers.get(doi)
            if paper and paper.keywords:
                target_keywords.update(paper.keywords)

        for doi in self.graph.nodes():
            paper = self.papers.get(doi)
            if not paper:
                continue

            paper_refs = set(self.graph.successors(doi))
            paper_cits = set(self.graph.predecessors(doi))
            paper_keywords = set(paper.keywords or [])

            ref_overlap = len(target_refs & paper_refs)
            cit_overlap = len(target_cits & paper_cits)
            keyword_overlap = len(target_keywords & paper_keywords)

            if ref_overlap + cit_overlap + keyword_overlap < 2:
                continue

            for author in paper.authors:
                if author.name == author_name or author.name in target_authors:
                    continue

                candidates[author.name]['common_refs'].update(target_refs & paper_refs)
                candidates[author.name]['common_cits'].update(target_cits & paper_cits)
                candidates[author.name]['keywords'].update(target_keywords & paper_keywords)
                candidates[author.name]['paper_count'] += 1
                if author.affiliation:
                    candidates[author.name]['affiliation'] = author.affiliation
                if author.orcid:
                    candidates[author.name]['orcid'] = author.orcid

        result = []
        for name, data in candidates.items():
            ref_score = len(data['common_refs']) / max(1, len(target_refs))
            cit_score = len(data['common_cits']) / max(1, len(target_cits))
            kw_score = len(data['keywords']) / max(1, len(target_keywords))

            score = 0.4 * ref_score + 0.3 * cit_score + 0.3 * kw_score

            reasons = []
            if ref_score > 0.2:
                reasons.append(f"{len(data['common_refs'])} 篇共同参考文献")
            if cit_score > 0.1:
                reasons.append(f"{len(data['common_cits'])} 个共同引用")
            if kw_score > 0.3:
                reasons.append(f"{len(data['keywords'])} 个研究主题重叠")

            result.append(CollaboratorInfo(
                name=name,
                orcid=data['orcid'],
                affiliation=data['affiliation'],
                paper_count=data['paper_count'],
                collaboration_score=min(1.0, score),
                common_papers=list(data['common_refs'])[:5],
                research_overlap=list(data['keywords'])[:5],
                potential_impact=score * 10,
                match_reason="; ".join(reasons) if reasons else "基于研究相似性"
            ))

        result.sort(key=lambda x: x.collaboration_score, reverse=True)
        return result

    def _calculate_impact(self, papers: List[str]) -> float:
        total_citations = 0
        for doi in papers:
            paper = self.papers.get(doi)
            if paper:
                total_citations += paper.citations
        return math.log1p(total_citations / 100)

    def _extract_research_overlap(self, papers: List[str]) -> List[str]:
        keywords = []
        for doi in papers[:5]:
            paper = self.papers.get(doi)
            if paper and paper.keywords:
                keywords.extend(paper.keywords)

        counts = Counter(keywords)
        return [k for k, v in counts.most_common(5)]


class CitationPredictor:
    def __init__(self, graph: nx.DiGraph, papers: Dict[str, Paper]):
        self.graph = graph
        self.papers = papers
        self.current_year = datetime.now().year

    def predict(self, doi: str) -> Optional[CitationPrediction]:
        paper = self.papers.get(doi)
        if not paper:
            return None

        age = self.current_year - paper.year
        if age < 0:
            age = 0

        current_citations = paper.citations

        features = self._extract_features(doi, paper, age, current_citations)

        pred_1y = self._predict_citations(current_citations, age, features, 1)
        pred_3y = self._predict_citations(current_citations, age, features, 3)
        pred_5y = self._predict_citations(current_citations, age, features, 5)

        growth_rate = (pred_3y - current_citations) / max(1, current_citations)

        confidence = self._calculate_confidence(features, age)

        key_factors = self._identify_key_factors(features)

        return CitationPrediction(
            doi=doi,
            title=paper.title,
            current_citations=current_citations,
            age_years=float(age),
            predicted_citations_1y=pred_1y,
            predicted_citations_3y=pred_3y,
            predicted_citations_5y=pred_5y,
            confidence_score=confidence,
            growth_rate=growth_rate,
            key_factors=key_factors
        )

    def predict_batch(self, dois: List[str]) -> BatchCitationPrediction:
        predictions = []
        for doi in dois:
            pred = self.predict(doi)
            if pred:
                predictions.append(pred)

        return BatchCitationPrediction(
            predictions=predictions,
            model_version="1.0.0",
            prediction_date=datetime.now().isoformat()
        )

    def _extract_features(
        self,
        doi: str,
        paper: Paper,
        age: int,
        citations: int
    ) -> Dict[str, float]:
        features = {}

        features['recent_growth'] = self._estimate_recent_growth(doi, citations, age)

        features['pagerank'] = self.graph.nodes[doi].get('pagerank', 0.0) if doi in self.graph else 0.0

        features['venue_quality'] = self._estimate_venue_quality(paper.venue)

        features['reference_quality'] = self._estimate_reference_quality(doi)

        features['citation_velocity'] = citations / max(1, age) if age > 0 else citations

        features['author_impact'] = self._estimate_author_impact(paper)

        return features

    def _estimate_recent_growth(self, doi: str, citations: int, age: int) -> float:
        if age == 0:
            return citations * 2

        in_degree = self.graph.in_degree(doi) if doi in self.graph else 0
        avg_yearly = citations / max(1, age)

        if in_degree > avg_yearly:
            return 1.2
        elif in_degree > 0:
            return 0.8 + (in_degree / avg_yearly) * 0.2
        else:
            return 0.5

    def _estimate_venue_quality(self, venue: str) -> float:
        top_venues = {'Nature', 'Science', 'Cell', 'NeurIPS', 'ICML', 'CVPR', 'ACL', 'ICLR', 'KDD', 'WWW'}

        venue_lower = venue.lower()
        for tv in top_venues:
            if tv.lower() in venue_lower:
                return 0.9

        if 'Conference' in venue or 'Symposium' in venue:
            return 0.6

        if 'Journal' in venue or 'Transactions' in venue:
            return 0.7

        return 0.5

    def _estimate_reference_quality(self, doi: str) -> float:
        if doi not in self.graph:
            return 0.5

        refs = list(self.graph.successors(doi))
        if not refs:
            return 0.5

        total_quality = 0
        for ref in refs:
            ref_paper = self.papers.get(ref)
            if ref_paper:
                total_quality += self._estimate_venue_quality(ref_paper.venue)

        return total_quality / len(refs)

    def _estimate_author_impact(self, paper: Paper) -> float:
        if not paper.authors:
            return 0.5

        total_citations = 0
        for author in paper.authors:
            author_cits = 0
            for p in self.papers.values():
                if any(a.name == author.name for a in p.authors):
                    author_cits += p.citations
            total_citations += author_cits

        avg_citations = total_citations / len(paper.authors)
        return min(1.0, math.log1p(avg_citations) / 10)

    def _predict_citations(
        self,
        current: int,
        age: int,
        features: Dict[str, float],
        years_ahead: int
    ) -> int:
        base_growth = features['recent_growth']

        venue_factor = features['venue_quality']
        ref_factor = features['reference_quality']
        author_factor = features['author_impact']
        velocity_factor = min(2.0, features['citation_velocity'] / 50)

        decay = 1.0
        if age > 10:
            decay = max(0.1, 1 - (age - 10) * 0.05)

        growth_rate = base_growth * venue_factor * ref_factor * author_factor * velocity_factor * decay

        annual_growth = [
            current * growth_rate * (0.8 ** i)
            for i in range(years_ahead)
        ]

        prediction = current + sum(annual_growth)

        return max(current, int(round(prediction)))

    def _calculate_confidence(self, features: Dict[str, float], age: int) -> float:
        confidence = 0.5

        if features['pagerank'] > 0:
            confidence += 0.1

        if features['venue_quality'] > 0.7:
            confidence += 0.1

        if age >= 2:
            confidence += 0.15
        elif age >= 1:
            confidence += 0.05

        if features['citation_velocity'] > 0:
            confidence += 0.1

        return min(0.95, confidence)

    def _identify_key_factors(self, features: Dict[str, float]) -> List[str]:
        factors = []

        if features['venue_quality'] > 0.8:
            factors.append("发表于顶级期刊/会议")

        if features['citation_velocity'] > 10:
            factors.append("引用增长速度快")

        if features['recent_growth'] > 1.0:
            factors.append("近期影响力上升趋势明显")

        if features['reference_quality'] > 0.7:
            factors.append("参考文献质量高")

        if features['author_impact'] > 0.7:
            factors.append("作者团队影响力高")

        return factors[:4]
