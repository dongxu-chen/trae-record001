import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.parsers.sql_lineage_parser import SQLLineageParser

TEST_SQL = """
WITH cte1 AS (
    SELECT 
        customer_id as c1_id,
        customer_name as c1_name
    FROM raw.customers
),
cte2 AS (
    SELECT 
        c1_id as c2_id,
        c1_name as c2_name,
        o.order_id
    FROM cte1 c1
    JOIN raw.orders o ON c1.c1_id = o.customer_id
)
INSERT INTO analytics.summary
SELECT 
    c2_id,
    c2_name,
    count(order_id) as total_orders
FROM cte2
GROUP BY c2_id, c2_name
"""

def test_parser():
    parser = SQLLineageParser()
    result = parser.parse(TEST_SQL)
    
    source_tables = [t.full_name for t in result.tables if t.node_type == 'source']
    target_tables = [t.full_name for t in result.tables if t.node_type == 'target']
    cte_tables = [t.full_name for t in result.tables if t.node_type == 'cte']
    
    print("Number of tables:", len(result.tables))
    print("Number of columns:", len(result.columns))
    print("Number of table lineages:", len(result.table_lineage))
    print("Number of column lineages:", len(result.column_lineage))
    print("Number of mapping chains:", len(result.mapping_chains))
    print("Source tables:", source_tables)
    print("Target tables:", target_tables)
    print("CTE tables:", cte_tables)
    
    print("\nTables:")
    for t in result.tables:
        print(f"  - {t.full_name} ({t.node_type})")
    
    print("\nMapping chains:")
    for mc in result.mapping_chains:
        print(f"  - {mc.full_chain}")
    
    with open('test_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
    print("\nResult saved to test_result.json")

if __name__ == "__main__":
    test_parser()
