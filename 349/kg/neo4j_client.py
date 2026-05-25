import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver, Session
from config import NEO4J_CONFIG, KG_TIME_DECAY


class Neo4jClient:
    _driver: Optional[Driver] = None

    @classmethod
    def get_driver(cls) -> Driver:
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                NEO4J_CONFIG["uri"],
                auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
            )
        return cls._driver

    @classmethod
    def close(cls):
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None

    @classmethod
    def get_session(cls) -> Session:
        return cls.get_driver().session(database=NEO4J_CONFIG["database"])

    @classmethod
    def run_query(cls, query: str, parameters: Dict[str, Any] = None) -> list:
        with cls.get_session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]


def _time_decay_factor(relation_type: str, created_date_str: str, reference_date: datetime = None) -> float:
    if not KG_TIME_DECAY.get("enabled", True):
        return 1.0

    if reference_date is None:
        reference_date = datetime.now()

    half_life = KG_TIME_DECAY["relation_types"].get(
        relation_type, KG_TIME_DECAY.get("half_life_days", 365)
    )
    max_decay_days = KG_TIME_DECAY.get("max_decay_days", 3650)
    min_weight = KG_TIME_DECAY.get("min_weight", 0.1)

    try:
        if isinstance(created_date_str, str):
            created = datetime.strptime(created_date_str, "%Y-%m-%d")
        elif hasattr(created_date_str, "to_native"):
            created = created_date_str.to_native()
        elif isinstance(created_date_str, datetime):
            created = created_date_str
        else:
            return 1.0
    except (ValueError, TypeError):
        return 1.0

    days_elapsed = (reference_date - created).days

    if days_elapsed <= 0:
        return 1.0
    if days_elapsed >= max_decay_days:
        return min_weight

    decay = math.exp(-0.693 * days_elapsed / half_life)
    return max(min_weight, decay)


def _compute_decayed_sum(
    items: List[Dict[str, Any]],
    value_key: str,
    date_key: str,
    relation_type: str
) -> float:
    total = 0.0
    for item in items:
        value = float(item.get(value_key, 0))
        date_val = item.get(date_key)
        if date_val is None:
            total += value
        else:
            decay = _time_decay_factor(relation_type, date_val)
            total += value * decay
    return total


def create_company_graph(company_data, relation_date: str = None) -> None:
    if relation_date is None:
        relation_date = datetime.now().strftime("%Y-%m-%d")

    query = """
    MERGE (c:Company {company_id: $company_id})
    SET c.company_name = $company_name,
        c.industry = $industry,
        c.registered_capital = $registered_capital,
        c.established_date = $established_date,
        c.operating_status = $operating_status,
        c.created_at = datetime()
    """
    Neo4jClient.run_query(query, {
        "company_id": company_data.business_info.company_id,
        "company_name": company_data.business_info.company_name,
        "industry": company_data.business_info.industry,
        "registered_capital": company_data.business_info.registered_capital,
        "established_date": company_data.business_info.established_date,
        "operating_status": company_data.business_info.operating_status,
    })

    for shareholder in company_data.shareholders:
        sh_query = """
        MATCH (c:Company {company_id: $company_id})
        MERGE (s:Shareholder {name: $name, type: $type})
        MERGE (s)-[:OWNS {share_ratio: $share_ratio, company_id: $company_id,
                          created_date: $created_date}]->(c)
        """
        Neo4jClient.run_query(sh_query, {
            "company_id": company_data.business_info.company_id,
            "name": shareholder.shareholder_name,
            "type": shareholder.shareholder_type,
            "share_ratio": shareholder.share_ratio,
            "created_date": relation_date,
        })

    for executive in company_data.executives:
        ex_query = """
        MATCH (c:Company {company_id: $company_id})
        MERGE (p:Person {name: $name})
        MERGE (p)-[:MANAGES {position: $position, tenure_years: $tenure_years,
                             created_date: $created_date}]->(c)
        """
        Neo4jClient.run_query(ex_query, {
            "company_id": company_data.business_info.company_id,
            "name": executive.name,
            "position": executive.position,
            "tenure_years": executive.tenure_years,
            "created_date": relation_date,
        })

    industry_query = """
    MATCH (c:Company {company_id: $company_id})
    MERGE (i:Industry {name: $industry})
    MERGE (c)-[:BELONGS_TO {created_date: $created_date}]->(i)
    """
    Neo4jClient.run_query(industry_query, {
        "company_id": company_data.business_info.company_id,
        "industry": company_data.business_info.industry,
        "created_date": relation_date,
    })


def create_supply_chain_relation(company_id: str, related_company_id: str, relation_type: str,
                                  strength: float = 0.5, relation_date: str = None) -> None:
    if relation_date is None:
        relation_date = datetime.now().strftime("%Y-%m-%d")
    query = """
    MATCH (c1:Company {company_id: $company_id})
    MATCH (c2:Company {company_id: $related_company_id})
    MERGE (c1)-[:SUPPLIES_TO {type: $relation_type, strength: $strength,
                               created_date: $created_date}]->(c2)
    """
    Neo4jClient.run_query(query, {
        "company_id": company_id,
        "related_company_id": related_company_id,
        "relation_type": relation_type,
        "strength": strength,
        "created_date": relation_date,
    })


def create_legal_relation(company_id: str, related_company_id: str, lawsuit_count: int = 0,
                           relation_date: str = None) -> None:
    if relation_date is None:
        relation_date = datetime.now().strftime("%Y-%m-%d")
    query = """
    MATCH (c1:Company {company_id: $company_id})
    MATCH (c2:Company {company_id: $related_company_id})
    MERGE (c1)-[:HAS_LEGAL_RELATION {lawsuit_count: $lawsuit_count,
                                      created_date: $created_date}]->(c2)
    """
    Neo4jClient.run_query(query, {
        "company_id": company_id,
        "related_company_id": related_company_id,
        "lawsuit_count": lawsuit_count,
        "created_date": relation_date,
    })


def extract_kg_features(company_id: str) -> Dict[str, float]:
    features = {}

    shareholding_query = """
    MATCH (c:Company {company_id: $company_id})<-[r:OWNS]-(s:Shareholder)
    WITH s, c, r
    OPTIONAL MATCH (s)-[r2:OWNS]->(other:Company)
    WHERE other.company_id <> $company_id
    RETURN
        collect({name: s.name, type: s.type, share_ratio: r.share_ratio,
                 created_date: r.created_date, company_id: r.company_id}) AS shareholders,
        count(DISTINCT other) AS shareholder_other_companies
    """
    result = Neo4jClient.run_query(shareholding_query, {"company_id": company_id})
    if result and result[0].get("shareholders"):
        r = result[0]
        shareholders = r["shareholders"]
        decayed_share_ratios = []
        corporate_count = 0.0
        for sh in shareholders:
            date_val = sh.get("created_date")
            decay = _time_decay_factor("OWNS", date_val) if date_val else 1.0
            decayed_share_ratios.append(float(sh["share_ratio"]) * decay)
            if sh["type"] == "法人股东":
                corporate_count += decay

        features["shareholder_count"] = float(len(shareholders))
        features["avg_share_ratio"] = sum(decayed_share_ratios) / len(decayed_share_ratios)
        features["shareholder_other_companies"] = float(r.get("shareholder_other_companies", 0))
        features["corporate_shareholder_count"] = corporate_count
        features["shareholder_quality_score"] = _calc_shareholder_quality(features)
    else:
        features.update({
            "shareholder_count": 0.0,
            "avg_share_ratio": 0.0,
            "shareholder_other_companies": 0.0,
            "corporate_shareholder_count": 0.0,
            "shareholder_quality_score": 50.0,
        })

    executive_query = """
    MATCH (c:Company {company_id: $company_id})<-[r:MANAGES]-(p:Person)
    RETURN collect({name: p.name, tenure_years: r.tenure_years,
                     created_date: r.created_date}) AS executives
    """
    result = Neo4jClient.run_query(executive_query, {"company_id": company_id})
    if result and result[0].get("executives"):
        executives = result[0]["executives"]
        decayed_tenures = []
        for ex in executives:
            date_val = ex.get("created_date")
            decay = _time_decay_factor("MANAGES", date_val) if date_val else 1.0
            decayed_tenures.append(float(ex["tenure_years"]) * decay)

        features["executive_count"] = float(len(executives))
        features["avg_executive_tenure"] = sum(decayed_tenures) / len(decayed_tenures)
    else:
        features["executive_count"] = 0.0
        features["avg_executive_tenure"] = 0.0

    industry_query = """
    MATCH (c:Company {company_id: $company_id})-[r:BELONGS_TO]->(i:Industry)
    OPTIONAL MATCH (peer:Company)-[:BELONGS_TO]->(i)
    WHERE peer.company_id <> $company_id
    RETURN
        count(DISTINCT peer) AS industry_peer_count,
        avg(DISTINCT peer.registered_capital) AS avg_peer_capital,
        r.created_date AS relation_date
    """
    result = Neo4jClient.run_query(industry_query, {"company_id": company_id})
    if result:
        r = result[0]
        peer_count = float(r.get("industry_peer_count", 0))
        date_val = r.get("relation_date")
        decay = _time_decay_factor("BELONGS_TO", date_val) if date_val else 1.0
        features["industry_peer_count"] = peer_count
        features["industry_peer_score"] = _calc_industry_peer_score(peer_count, decay)
    else:
        features["industry_peer_count"] = 0.0
        features["industry_peer_score"] = 50.0

    supply_query = """
    MATCH (c:Company {company_id: $company_id})-[r:SUPPLIES_TO]-(other:Company)
    RETURN collect({strength: r.strength, created_date: r.created_date}) AS supplies
    """
    result = Neo4jClient.run_query(supply_query, {"company_id": company_id})
    if result and result[0].get("supplies"):
        supplies = result[0]["supplies"]
        decayed_strengths = []
        partner_count = 0
        for sup in supplies:
            date_val = sup.get("created_date")
            decay = _time_decay_factor("SUPPLIES_TO", date_val) if date_val else 1.0
            if decay > 0.3:
                partner_count += 1
            decayed_strengths.append(float(sup["strength"]) * decay)

        features["supply_chain_partners"] = float(partner_count)
        features["avg_supply_strength"] = sum(decayed_strengths) / len(decayed_strengths)
        features["supply_chain_stability_score"] = _calc_supply_chain_score(
            features["supply_chain_partners"], features["avg_supply_strength"]
        )
    else:
        features["supply_chain_partners"] = 0.0
        features["avg_supply_strength"] = 0.0
        features["supply_chain_stability_score"] = 50.0

    legal_query = """
    MATCH (c:Company {company_id: $company_id})-[r:HAS_LEGAL_RELATION]-(other:Company)
    RETURN collect({lawsuit_count: r.lawsuit_count, created_date: r.created_date}) AS legal_rels
    """
    result = Neo4jClient.run_query(legal_query, {"company_id": company_id})
    if result and result[0].get("legal_rels"):
        legal_rels = result[0]["legal_rels"]
        decayed_legal_count = 0.0
        decayed_total_lawsuits = 0.0
        for lr in legal_rels:
            date_val = lr.get("created_date")
            decay = _time_decay_factor("HAS_LEGAL_RELATION", date_val) if date_val else 1.0
            decayed_legal_count += decay
            decayed_total_lawsuits += float(lr["lawsuit_count"]) * decay

        features["legal_relation_count"] = decayed_legal_count
        features["total_legal_lawsuits"] = decayed_total_lawsuits
        features["legal_relation_score"] = _calc_legal_relation_score(
            decayed_legal_count, decayed_total_lawsuits
        )
    else:
        features["legal_relation_count"] = 0.0
        features["total_legal_lawsuits"] = 0.0
        features["legal_relation_score"] = 80.0

    association_risk_query = """
    MATCH (c:Company {company_id: $company_id})<-[:OWNS]-(s:Shareholder)
    MATCH (s)-[:OWNS]->(other:Company)
    WHERE other.company_id <> $company_id
    MATCH (other)<-[:MANAGES]-(p:Person)
    RETURN
        count(DISTINCT other) AS associated_companies,
        count(DISTINCT p) AS associated_executives
    """
    result = Neo4jClient.run_query(association_risk_query, {"company_id": company_id})
    if result:
        r = result[0]
        assoc_companies = float(r.get("associated_companies", 0))
        assoc_execs = float(r.get("associated_executives", 0))
        features["associated_companies"] = assoc_companies
        features["associated_executives"] = assoc_execs
        features["association_risk_score"] = _calc_association_risk_score(assoc_companies, assoc_execs)
    else:
        features["associated_companies"] = 0.0
        features["associated_executives"] = 0.0
        features["association_risk_score"] = 60.0

    return features


def get_time_decay_info() -> Dict[str, Any]:
    return {
        "enabled": KG_TIME_DECAY.get("enabled", True),
        "half_life_days": KG_TIME_DECAY.get("half_life_days", 365),
        "max_decay_days": KG_TIME_DECAY.get("max_decay_days", 3650),
        "min_weight": KG_TIME_DECAY.get("min_weight", 0.1),
        "relation_types": KG_TIME_DECAY.get("relation_types", {}),
    }


def _calc_shareholder_quality(features: Dict[str, float]) -> float:
    score = 50.0
    score += min(features.get("shareholder_count", 0) * 5, 20)
    score += min(features.get("corporate_shareholder_count", 0) * 10, 20)
    if features.get("avg_share_ratio", 0) > 0.7:
        score -= 10
    elif features.get("avg_share_ratio", 0) < 0.3:
        score += 5
    return max(0, min(100, score))


def _calc_industry_peer_score(peer_count: float, decay: float = 1.0) -> float:
    base = 50.0
    if peer_count == 0:
        return base
    if peer_count > 100:
        base = 70.0
    else:
        base = 50.0 + peer_count * 0.2
    return base * max(0.5, decay)


def _calc_supply_chain_score(partners: float, avg_strength: float) -> float:
    score = 50.0
    score += min(partners * 3, 30)
    score += min(avg_strength * 20, 20)
    return max(0, min(100, score))


def _calc_legal_relation_score(legal_count: float, total_lawsuits: float) -> float:
    score = 80.0
    score -= min(legal_count * 5, 30)
    score -= min(total_lawsuits * 3, 40)
    return max(0, min(100, score))


def _calc_association_risk_score(assoc_companies: float, assoc_execs: float) -> float:
    score = 60.0
    score -= min(assoc_companies * 3, 30)
    return max(0, min(100, score))
