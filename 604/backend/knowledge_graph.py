import networkx as nx
from typing import List, Dict, Any, Tuple
from config import settings


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_knowledge_graph()

    def _build_knowledge_graph(self):
        case_types = [
            "民间借贷纠纷", "合同纠纷", "买卖合同纠纷",
            "租赁合同纠纷", "劳动争议", "交通事故责任纠纷",
            "盗窃罪", "诈骗罪", "故意伤害罪", "抢劫罪",
        ]

        for case_type in case_types:
            self.graph.add_node(case_type, type="case_type")

        for law_id, law_content in settings.LAW_ARTICLES.items():
            self.graph.add_node(law_id, type="law_article", content=law_content)

        self._add_relations()

    def rebuild_graph(self):
        self.graph.clear()
        self._build_knowledge_graph()

    def _add_relations(self):
        relations = [
            ("民间借贷纠纷", "民法典-第六百六十七条", "适用"),
            ("民间借贷纠纷", "民法典-第六百八十条", "适用"),
            ("民间借贷纠纷", "民法典-第五百七十七条", "适用"),
            ("民间借贷纠纷", "民法典-第六百七十九条", "适用"),
            ("合同纠纷", "民法典-第五百零二条", "适用"),
            ("合同纠纷", "民法典-第五百七十七条", "适用"),
            ("合同纠纷", "民法典-第一百四十三条", "适用"),
            ("合同纠纷", "民法典-第五百零九条", "适用"),
            ("合同纠纷", "民法典-第五百八十五条", "适用"),
            ("买卖合同纠纷", "民法典-第五百零二条", "适用"),
            ("买卖合同纠纷", "民法典-第五百七十七条", "适用"),
            ("买卖合同纠纷", "民法典-第五百七十九条", "适用"),
            ("租赁合同纠纷", "民法典-第五百零二条", "适用"),
            ("租赁合同纠纷", "民法典-第五百七十七条", "适用"),
            ("劳动争议", "民事诉讼法-第六十七条", "适用"),
            ("劳动争议", "民事诉讼法-第一百二十二条", "适用"),
            ("劳动争议", "劳动法-第五十条", "适用"),
            ("劳动争议", "劳动合同法-第四十七条", "适用"),
            ("交通事故责任纠纷", "民事诉讼法-第六十七条", "适用"),
            ("交通事故责任纠纷", "民事诉讼法-第一百二十二条", "适用"),
            ("盗窃罪", "刑法-第二百六十四条", "适用"),
            ("盗窃罪", "刑法-第六十七条", "适用"),
            ("盗窃罪", "刑法-第七十二条", "适用"),
            ("诈骗罪", "刑法-第二百六十六条", "适用"),
            ("诈骗罪", "刑法-第六十七条", "适用"),
            ("故意伤害罪", "刑法-第二百三十四条", "适用"),
            ("故意伤害罪", "刑法-第六十七条", "适用"),
            ("抢劫罪", "刑法-第二百六十三条", "适用"),
            ("抢劫罪", "刑法-第六十五条", "适用"),
        ]

        for src, dst, relation in relations:
            self.graph.add_edge(src, dst, relation=relation)

        law_relations = [
            ("民法典-第六百六十七条", "民法典-第六百八十条", "关联"),
            ("民法典-第六百六十七条", "民法典-第六百七十九条", "关联"),
            ("民法典-第六百六十七条", "民法典-第五百七十七条", "关联"),
            ("民法典-第五百零二条", "民法典-第一百四十三条", "关联"),
            ("民法典-第五百零二条", "民法典-第五百七十七条", "关联"),
            ("民法典-第五百零二条", "民法典-第五百零九条", "关联"),
            ("民法典-第五百七十七条", "民法典-第五百八十五条", "关联"),
            ("民法典-第五百七十七条", "民法典-第五百七十九条", "关联"),
            ("刑法-第二百六十四条", "刑法-第六十七条", "关联"),
            ("刑法-第二百六十四条", "刑法-第七十二条", "关联"),
            ("刑法-第二百六十六条", "刑法-第六十七条", "关联"),
            ("刑法-第二百三十四条", "刑法-第六十七条", "关联"),
            ("刑法-第二百六十三条", "刑法-第六十五条", "关联"),
            ("刑法-第六十五条", "刑法-第六十七条", "关联"),
            ("刑法-第七十二条", "刑法-第六十七条", "关联"),
        ]

        for src, dst, relation in law_relations:
            self.graph.add_edge(src, dst, relation=relation)

    def recommend_law_articles(
        self,
        legal_entities: Dict[str, List[str]],
        key_points: List[str],
        case_type: str = None
    ) -> List[Dict[str, str]]:
        recommended = set()

        if case_type and case_type in self.graph:
            neighbors = list(self.graph.neighbors(case_type))
            for neighbor in neighbors:
                if self.graph.nodes[neighbor].get("type") == "law_article":
                    recommended.add(neighbor)

        keyword_mapping = {
            "借款": ["民法典-第六百六十七条", "民法典-第六百八十条", "民法典-第六百七十九条"],
            "借条": ["民法典-第六百六十七条", "民法典-第六百八十条"],
            "欠条": ["民法典-第六百六十七条"],
            "合同": ["民法典-第五百零二条", "民法典-第五百七十七条", "民法典-第一百四十三条", "民法典-第五百零九条"],
            "违约": ["民法典-第五百七十七条", "民法典-第五百八十五条"],
            "利息": ["民法典-第六百八十条"],
            "证据": ["民事诉讼法-第六十七条"],
            "起诉": ["民事诉讼法-第一百二十二条"],
            "诉讼": ["民事诉讼法-第六十七条", "民事诉讼法-第一百二十二条"],
            "盗窃": ["刑法-第二百六十四条", "刑法-第六十七条"],
            "诈骗": ["刑法-第二百六十六条", "刑法-第六十七条"],
            "伤害": ["刑法-第二百三十四条", "刑法-第六十七条"],
            "抢劫": ["刑法-第二百六十三条", "刑法-第六十五条"],
            "自首": ["刑法-第六十七条"],
            "累犯": ["刑法-第六十五条"],
            "缓刑": ["刑法-第七十二条"],
            "劳动": ["劳动法-第五十条", "劳动合同法-第四十七条"],
            "工资": ["劳动法-第五十条"],
            "经济补偿": ["劳动合同法-第四十七条"],
        }

        all_text = ' '.join(key_points) + ' ' + str(legal_entities)

        for keyword, laws in keyword_mapping.items():
            if keyword in all_text:
                recommended.update(laws)

        expanded = set()
        for law_id in recommended:
            expanded.add(law_id)
            if law_id in self.graph:
                for neighbor in self.graph.neighbors(law_id):
                    if self.graph.nodes[neighbor].get("type") == "law_article":
                        expanded.add(neighbor)

        result = []
        for law_id in expanded:
            content = settings.LAW_ARTICLES.get(law_id, "")
            if content:
                result.append({
                    "law_id": law_id,
                    "content": content,
                    "relevance": self._calculate_relevance(law_id, key_points)
                })

        result.sort(key=lambda x: x["relevance"], reverse=True)
        return result[:5]

    def _calculate_relevance(self, law_id: str, key_points: List[str]) -> float:
        content = settings.LAW_ARTICLES.get(law_id, "")
        if not content:
            return 0.0

        relevance = 0.0
        all_points_text = ' '.join(key_points)

        high_kw = ["借款", "合同", "违约", "利息", "证据", "起诉", "盗窃", "诈骗", "伤害", "抢劫", "自首", "累犯", "缓刑"]
        for kw in high_kw:
            if kw in content and kw in all_points_text:
                relevance += 0.3

        mid_kw = ["有效", "成立", "责任", "返还", "支付", "赔偿", "故意", "过失", "从重", "从轻", "减轻", "判处"]
        for kw in mid_kw:
            if kw in content and kw in all_points_text:
                relevance += 0.15

        return min(relevance, 1.0)

    def find_related_cases(self, case_type: str, law_articles: List[str]) -> List[str]:
        related = []

        if case_type in self.graph:
            for law in law_articles:
                if law in self.graph:
                    try:
                        paths = nx.shortest_path(self.graph, case_type, law)
                        related.extend(paths)
                    except nx.NetworkXNoPath:
                        pass

        return list(set(related))

    def get_case_type_laws(self, case_type: str) -> List[str]:
        laws = []
        if case_type in self.graph:
            for neighbor in self.graph.neighbors(case_type):
                if self.graph.nodes[neighbor].get("type") == "law_article":
                    laws.append(neighbor)
        return laws

    def get_graph_statistics(self) -> Dict[str, Any]:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "case_types": len([n for n, d in self.graph.nodes(data=True) if d.get("type") == "case_type"]),
            "law_articles": len([n for n, d in self.graph.nodes(data=True) if d.get("type") == "law_article"])
        }
