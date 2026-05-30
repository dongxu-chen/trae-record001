from neo4j import GraphDatabase
from typing import List, Dict, Any
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

class Neo4jDatabase:
    def __init__(self):
        self.driver = None

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            print("Neo4j连接成功")
        except Exception as e:
            print(f"Neo4j连接失败: {e}")
            raise

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_query(self, query: str, parameters: Dict = None):
        if not self.driver:
            raise Exception("数据库未连接")
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def create_disease(self, name: str, **kwargs):
        query = """
        MERGE (d:Disease {name: $name})
        SET d.description = $description,
            d.department = $department,
            d.is_rare = $is_rare,
            d.paragraphs = $paragraphs,
            d.source = $source
        RETURN d
        """
        return self.execute_query(query, {
            "name": name,
            "description": kwargs.get("description", ""),
            "department": kwargs.get("department", ""),
            "is_rare": kwargs.get("is_rare", False),
            "paragraphs": kwargs.get("paragraphs", []),
            "source": kwargs.get("source", "医疗知识图谱")
        })

    def create_symptom(self, name: str, description: str = "", **kwargs):
        query = """
        MERGE (s:Symptom {name: $name})
        SET s.description = $description,
            s.is_rare = $is_rare
        RETURN s
        """
        return self.execute_query(query, {
            "name": name,
            "description": description,
            "is_rare": kwargs.get("is_rare", False)
        })

    def create_medicine(self, name: str, **kwargs):
        query = """
        MERGE (m:Medicine {name: $name})
        SET m.category = $category,
            m.usage = $usage,
            m.description = $description,
            m.is_rare = $is_rare
        RETURN m
        """
        return self.execute_query(query, {
            "name": name,
            "category": kwargs.get("category", ""),
            "usage": kwargs.get("usage", ""),
            "description": kwargs.get("description", ""),
            "is_rare": kwargs.get("is_rare", False)
        })

    def create_relation(self, from_node: str, from_type: str, 
                        relation: str,
                        to_node: str, to_type: str,
                        properties: Dict = None):
        prop_str = ""
        if properties:
            prop_parts = []
            for k, v in properties.items():
                if isinstance(v, str):
                    prop_parts.append(f"r.{k} = '{v}'")
                elif isinstance(v, (int, float, bool)):
                    prop_parts.append(f"r.{k} = {v}")
                elif isinstance(v, list):
                    prop_parts.append(f"r.{k} = {v}")
            if prop_parts:
                prop_str = "SET " + ", ".join(prop_parts)
        
        query = f"""
        MATCH (a:{from_type} {{name: $from_node}})
        MATCH (b:{to_type} {{name: $to_node}})
        MERGE (a)-[r:{relation}]->(b)
        {prop_str}
        RETURN type(r) as relation
        """
        return self.execute_query(query, {"from_node": from_node, "to_node": to_node})

    def search_disease_by_symptom(self, symptom: str) -> List[Dict]:
        query = """
        MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom {name: $symptom})
        RETURN d.name as disease, d.description as description,
               d.is_rare as is_rare, d.paragraphs as paragraphs
        """
        return self.execute_query(query, {"symptom": symptom})

    def search_medicine_by_disease(self, disease: str) -> List[Dict]:
        query = """
        MATCH (d:Disease)-[:TREATED_BY]->(m:Medicine)
        WHERE d.name = $disease
        RETURN m.name as medicine, m.usage as usage, m.category as category,
               m.description as description
        """
        return self.execute_query(query, {"disease": disease})

    def get_disease_info(self, disease: str) -> List[Dict]:
        query = """
        MATCH (d:Disease {name: $disease})
        OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
        OPTIONAL MATCH (d)-[:TREATED_BY]->(m:Medicine)
        RETURN d.name as name,
               d.description as description,
               d.is_rare as is_rare,
               d.paragraphs as paragraphs,
               d.source as source,
               collect(DISTINCT s.name) as symptoms,
               collect(DISTINCT m.name) as medicines
        """
        return self.execute_query(query, {"disease": disease})

    def fuzzy_search_disease(self, keyword: str) -> List[Dict]:
        query = """
        MATCH (d:Disease)
        WHERE d.name CONTAINS $keyword OR d.description CONTAINS $keyword
        RETURN d.name as name, d.description as description, d.is_rare as is_rare
        LIMIT 10
        """
        return self.execute_query(query, {"keyword": keyword})

    def get_disease_and_relations(self, disease_name: str) -> Dict:
        result = {}
        
        disease_info = self.get_disease_info(disease_name)
        if disease_info:
            result["disease"] = disease_info[0]
        
        symptoms = self.execute_query("""
            MATCH (d:Disease {name: $name})-[:HAS_SYMPTOM]->(s:Symptom)
            RETURN s.name as name, s.description as description, s.is_rare as is_rare
            """, {"name": disease_name})
        result["symptoms"] = symptoms
        
        medicines = self.execute_query("""
            MATCH (d:Disease {name: $name})-[:TREATED_BY]->(m:Medicine)
            RETURN m.name as name, m.usage as usage, m.category as category,
                   m.description as description
            """, {"name": disease_name})
        result["medicines"] = medicines
        
        departments = self.execute_query("""
            MATCH (d:Disease {name: $name})-[:BELONGS_TO]->(dep:Department)
            RETURN dep.name as name
            """, {"name": disease_name})
        result["departments"] = departments
        
        return result

    def get_paragraphs_for_disease(self, disease_name: str) -> List[Dict]:
        query = """
        MATCH (d:Disease {name: $name})
        RETURN d.paragraphs as paragraphs
        """
        result = self.execute_query(query, {"name": disease_name})
        if result and result[0].get("paragraphs"):
            return result[0]["paragraphs"]
        return []

    def find_paragraph_containing(self, disease_name: str, keyword: str) -> Dict:
        paragraphs = self.get_paragraphs_for_disease(disease_name)
        for idx, para in enumerate(paragraphs):
            para_text = para if isinstance(para, str) else para.get("text", "")
            if keyword in para_text:
                return {
                    "paragraph_index": idx,
                    "paragraph_text": para_text,
                    "keyword": keyword
                }
        return {}

    def create_interaction_relation(self, drug_a: str, drug_b: str,
                                     severity: str, description: str,
                                     mechanism: str, recommendation: str):
        query = """
        MATCH (a:Medicine {name: $drug_a})
        MATCH (b:Medicine {name: $drug_b})
        MERGE (a)-[r:INTERACTS_WITH]->(b)
        SET r.severity = $severity,
            r.description = $description,
            r.mechanism = $mechanism,
            r.recommendation = $recommendation
        RETURN type(r) as relation
        """
        return self.execute_query(query, {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "severity": severity,
            "description": description,
            "mechanism": mechanism,
            "recommendation": recommendation
        })

    def check_drug_interaction(self, drug_names: List[str]) -> List[Dict]:
        interactions = []
        for i, drug_a in enumerate(drug_names):
            for drug_b in drug_names[i+1:]:
                query = """
                MATCH (a:Medicine {name: $drug_a})-[r:INTERACTS_WITH]->(b:Medicine {name: $drug_b})
                RETURN a.name as drug_a, b.name as drug_b,
                       r.severity as severity, r.description as description,
                       r.mechanism as mechanism, r.recommendation as recommendation
                """
                result = self.execute_query(query, {"drug_a": drug_a, "drug_b": drug_b})
                
                if not result:
                    query_reverse = """
                    MATCH (a:Medicine {name: $drug_b})-[r:INTERACTS_WITH]->(b:Medicine {name: $drug_a})
                    RETURN a.name as drug_a, b.name as drug_b,
                           r.severity as severity, r.description as description,
                           r.mechanism as mechanism, r.recommendation as recommendation
                    """
                    result = self.execute_query(query_reverse, {"drug_a": drug_a, "drug_b": drug_b})
                
                interactions.extend(result)
        return interactions

    def get_emergency_symptoms(self) -> List[Dict]:
        query = """
        MATCH (s:Symptom)
        WHERE s.is_emergency = true
        RETURN s.name as name, s.description as description
        """
        return self.execute_query(query)
