import json
import os
import networkx as nx
from typing import List, Dict, Set, Optional

from config import Config


class KnowledgeGraph:
    def __init__(self, kg_path: str = None):
        self.kg_path = kg_path or Config.KG_PATH
        self.graph = nx.DiGraph()
        self.entity_index: Dict[str, Dict] = {}
        self.name_to_id: Dict[str, str] = {}
        self.alias_to_id: Dict[str, str] = {}
        
        self.abbreviation_map: Dict[str, str] = {}
        self.colloquial_map: Dict[str, str] = {}
        self._build_mapping_tables()
        
        if os.path.exists(self.kg_path):
            self._load_from_file()
        else:
            self._create_default_graph()

    def _load_from_file(self):
        with open(self.kg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for entity in data.get('entities', []):
            self._add_entity(entity)
        
        for relation in data.get('relations', []):
            self._add_relation(relation)

    def _create_default_graph(self):
        default_entities = [
            {'id': 'brand_1', 'name': '苹果', 'type': '品牌', 'alias': ['Apple']},
            {'id': 'brand_2', 'name': '华为', 'type': '品牌', 'alias': ['HUAWEI']},
            {'id': 'category_1', 'name': '手机', 'type': '品类', 'alias': ['移动电话', '智能手机']},
            {'id': 'category_2', 'name': '笔记本电脑', 'type': '品类', 'alias': ['笔记本', '手提电脑']},
            {'id': 'category_3', 'name': '耳机', 'type': '品类', 'alias': ['耳麦', '耳塞']},
        ]
        
        default_relations = [
            {'source': 'brand_1', 'target': 'category_1', 'type': '生产'},
            {'source': 'brand_1', 'target': 'category_2', 'type': '生产'},
            {'source': 'brand_2', 'target': 'category_1', 'type': '生产'},
        ]
        
        for entity in default_entities:
            self._add_entity(entity)
        
        for relation in default_relations:
            self._add_relation(relation)

    def _add_entity(self, entity: Dict):
        entity_id = entity['id']
        self.graph.add_node(entity_id, **entity)
        self.entity_index[entity_id] = entity
        
        name = entity['name']
        self.name_to_id[name] = entity_id
        
        for alias in entity.get('alias', []):
            self.alias_to_id[alias] = entity_id

    def _build_mapping_tables(self):
        brand_abbreviations = {
            'HW': '华为',
            '华为主': '华为',
            'XM': '小米',
            'MI': '小米',
            '米': '小米',
            'AP': '苹果',
            'apple': '苹果',
            '水果': '苹果',
            'SX': '三星',
            'SN': '索尼',
            'DE': '戴尔',
            '戴': '戴尔',
            'LX': '联想',
            '联': '联想',
            'HP': '惠普',
            '惠': '惠普',
            'HS': '华硕',
            'LJ': '罗技',
        }
        
        brand_colloquials = {
            '菊花': '华为',
            '菊花厂': '华为',
            '粗粮': '小米',
            '雷布斯': '小米',
            '美帝良心想': '联想',
            '败家之眼': '华硕',
            '灯厂': '雷蛇',
            '牙膏厂': '英特尔',
            '农企': 'AMD',
            '老黄': '英伟达',
        }
        
        category_abbreviations = {
            'NB': '笔记本电脑',
            'PC': '电脑',
            'TV': '电视',
            'DP': '显示器',
            'EP': '耳机',
        }
        
        category_colloquials = {
            '本本': '笔记本电脑',
            '笔电': '笔记本电脑',
            '爱机': '手机',
            '爪机': '手机',
            '板板': '平板电脑',
            '大电视': '电视',
        }
        
        for abbr, full in brand_abbreviations.items():
            self.abbreviation_map[abbr.lower()] = full
        
        for col, formal in brand_colloquials.items():
            self.colloquial_map[col.lower()] = formal
        
        for abbr, full in category_abbreviations.items():
            self.abbreviation_map[abbr.lower()] = full
        
        for col, formal in category_colloquials.items():
            self.colloquial_map[col.lower()] = formal

    def _add_relation(self, relation: Dict):
        self.graph.add_edge(
            relation['source'],
            relation['target'],
            type=relation['type']
        )

    def add_entity(self, entity_id: str, name: str, entity_type: str, alias: List[str] = None):
        entity = {
            'id': entity_id,
            'name': name,
            'type': entity_type,
            'alias': alias or []
        }
        self._add_entity(entity)

    def add_relation(self, source_id: str, target_id: str, relation_type: str):
        relation = {
            'source': source_id,
            'target': target_id,
            'type': relation_type
        }
        self._add_relation(relation)

    def normalize_term(self, term: str) -> str:
        term_lower = term.lower()
        
        if term_lower in self.abbreviation_map:
            return self.abbreviation_map[term_lower]
        
        if term_lower in self.colloquial_map:
            return self.colloquial_map[term_lower]
        
        return term

    def get_entity_by_name(self, name: str) -> Optional[Dict]:
        normalized_name = self.normalize_term(name)
        
        entity_id = self.name_to_id.get(normalized_name) or self.alias_to_id.get(normalized_name)
        if entity_id:
            return self.entity_index.get(entity_id)
        
        entity_id = self.name_to_id.get(name) or self.alias_to_id.get(name)
        if entity_id:
            return self.entity_index.get(entity_id)
        
        return None

    def recognize_abbreviation(self, term: str) -> Optional[str]:
        return self.abbreviation_map.get(term.lower())

    def recognize_colloquial(self, term: str) -> Optional[str]:
        return self.colloquial_map.get(term.lower())

    def add_abbreviation(self, abbr: str, full_name: str):
        self.abbreviation_map[abbr.lower()] = full_name

    def add_colloquial(self, colloquial: str, formal_name: str):
        self.colloquial_map[colloquial.lower()] = formal_name

    def get_all_abbreviations(self) -> Dict[str, str]:
        return self.abbreviation_map.copy()

    def get_all_colloquials(self) -> Dict[str, str]:
        return self.colloquial_map.copy()

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict]:
        return self.entity_index.get(entity_id)

    def get_related_entities(self, entity_id: str, relation_type: str = None) -> List[Dict]:
        if entity_id not in self.graph:
            return []
        
        related = []
        for neighbor in self.graph.neighbors(entity_id):
            edge_data = self.graph.get_edge_data(entity_id, neighbor)
            if relation_type is None or edge_data.get('type') == relation_type:
                related.append(self.entity_index.get(neighbor))
        
        return related

    def get_brands_for_category(self, category_name: str) -> List[Dict]:
        category_entity = self.get_entity_by_name(category_name)
        if not category_entity:
            return []
        
        category_id = category_entity['id']
        brands = []
        
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            if node_data.get('type') == '品牌':
                if self.graph.has_edge(node, category_id) and \
                   self.graph.get_edge_data(node, category_id).get('type') == '生产':
                    brands.append(node_data)
        
        return brands

    def get_categories_for_brand(self, brand_name: str) -> List[Dict]:
        brand_entity = self.get_entity_by_name(brand_name)
        if not brand_entity:
            return []
        
        return self.get_related_entities(brand_entity['id'], '生产')

    def get_all_brands(self) -> List[Dict]:
        return [e for e in self.entity_index.values() if e.get('type') == '品牌']

    def get_all_categories(self) -> List[Dict]:
        return [e for e in self.entity_index.values() if e.get('type') == '品类']

    def get_all_specs(self) -> List[Dict]:
        return [e for e in self.entity_index.values() if e.get('type') == '规格']

    def expand_query_terms(self, query_terms: List[str]) -> Set[str]:
        expanded_terms = set(query_terms)
        
        for term in query_terms:
            entity = self.get_entity_by_name(term)
            if entity:
                expanded_terms.add(entity['name'])
                for alias in entity.get('alias', []):
                    expanded_terms.add(alias)
                
                if entity.get('type') == '品牌':
                    categories = self.get_categories_for_brand(entity['name'])
                    for cat in categories:
                        expanded_terms.add(cat['name'])
                        for alias in cat.get('alias', []):
                            expanded_terms.add(alias)
                
                elif entity.get('type') == '品类':
                    brands = self.get_brands_for_category(entity['name'])
                    for brand in brands:
                        expanded_terms.add(brand['name'])
                        for alias in brand.get('alias', []):
                            expanded_terms.add(alias)
        
        return expanded_terms

    def save(self, save_path: str = None):
        save_path = save_path or self.kg_path
        
        entities = list(self.entity_index.values())
        relations = []
        
        for u, v, data in self.graph.edges(data=True):
            relations.append({
                'source': u,
                'target': v,
                'type': data.get('type')
            })
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump({'entities': entities, 'relations': relations}, f, ensure_ascii=False, indent=2)

    def get_graph_stats(self) -> Dict:
        return {
            'total_entities': len(self.entity_index),
            'total_relations': self.graph.number_of_edges(),
            'brands_count': len(self.get_all_brands()),
            'categories_count': len(self.get_all_categories()),
            'specs_count': len(self.get_all_specs()),
            'abbreviations_count': len(self.abbreviation_map),
            'colloquials_count': len(self.colloquial_map)
        }
