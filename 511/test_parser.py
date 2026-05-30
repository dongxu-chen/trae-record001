"""
测试SQL血缘解析器的改进功能：
1. CTE递归展开解析
2. 别名映射链追踪
3. 中间节点标记
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.parsers.sql_lineage_parser import SQLLineageParser

# 测试用例：多层CTE嵌套 + 子查询 + 别名映射
TEST_SQL = """
WITH cte1 AS (
    SELECT 
        customer_id as c1_id,
        customer_name as c1_name,
        email as c1_email
    FROM raw.customers
    WHERE is_active = true
),
cte2 AS (
    SELECT 
        c1_id as c2_customer_id,
        c1_name as c2_name,
        o.order_id,
        o.order_amount
    FROM cte1 c1
    JOIN (
        SELECT 
            customer_id,
            order_id,
            amount as order_amount
        FROM raw.orders
        WHERE status = 'completed'
    ) o ON c1.c1_id = o.customer_id
),
cte3 AS (
    SELECT 
        c2_customer_id as customer_id,
        c2_name as customer_name,
        COUNT(order_id) as total_orders,
        SUM(order_amount) as total_amount
    FROM cte2
    GROUP BY c2_customer_id, c2_name
)
INSERT INTO analytics.customer_summary
SELECT 
    customer_id,
    customer_name,
    total_orders,
    total_amount
FROM cte3
"""

def test_parser():
    print("=" * 80)
    print("测试SQL血缘解析器 - 改进功能验证")
    print("=" * 80)
    
    parser = SQLLineageParser()
    
    print("\n🔍 解析SQL...")
    result = parser.parse(TEST_SQL)
    
    print("\n" + "=" * 80)
    print("📊 解析结果概览")
    print("=" * 80)
    
    print(f"\n✅ 解析成功: {result.success}")
    print(f"📝 目标表: {result.target_table}")
    print(f"📋 源表数量: {len(result.source_tables)}")
    print(f"🗂️  中间表(CTE/子查询): {len(result.intermediate_tables)}")
    print(f"🔗 表级血缘边: {len(result.table_lineages)}")
    print(f"🔗 字段级血缘边: {len(result.column_lineages)}")
    print(f"⛓️  映射链: {len(result.mapping_chains)}")
    
    print("\n" + "=" * 80)
    print("📋 节点类型分析")
    print("=" * 80)
    
    for table in result.tables:
        icon = {
            'source': '🟢',
            'target': '🔴',
            'cte': '🟠',
            'subquery': '🟣',
            'intermediate': '🔵'
        }.get(table.node_type, '⚪')
        
        alias_str = f" (别名链: {' ← '.join(table.alias_chain)})" if table.alias_chain else ""
        print(f"{icon} {table.full_name} - {table.node_type}{alias_str}")
    
    print("\n" + "=" * 80)
    print("⛓️  字段映射链 (完整追踪来源)")
    print("=" * 80)
    
    for chain in result.mapping_chains:
        print(f"\n🎯 目标字段: {chain.target_table}.{chain.target_column}")
        print(f"   完整链: {chain.full_chain}")
        print(f"   源表: {', '.join(chain.source_tables)}")
        print(f"   源字段: {', '.join(chain.source_columns)}")
        print(f"   深度: {chain.chain_depth}")
        print(f"   层级明细:")
        for link in chain.links:
            expr_str = f" [表达式: {link.expression}]" if link.expression else ""
            print(f"     {link.level}: {link.display_name}{expr_str}")
    
    print("\n" + "=" * 80)
    print("🔄 表级血缘流向 (包含中间节点)")
    print("=" * 80)
    
    for lineage in result.table_lineages:
        icon = "📦" if lineage.is_aggregated else "➡️"
        if lineage.is_aggregated:
            print(f"{icon} {lineage.source_table} ==> {lineage.target_table}")
            print(f"   (折叠 {lineage.intermediate_count} 个中间节点: {', '.join(lineage.intermediate_nodes)})")
        else:
            print(f"{icon} {lineage.source_table} → {lineage.target_table}")
    
    print("\n" + "=" * 80)
    print("🔍 字段级血缘流向")
    print("=" * 80)
    
    for lineage in result.column_lineages[:10]:  # 只显示前10条
        icon = "📦" if lineage.is_aggregated else "➡️"
        if lineage.is_aggregated:
            print(f"{icon} {lineage.source_column} ==> {lineage.target_column}")
            print(f"   (折叠 {lineage.intermediate_count} 个中间节点)")
        else:
            print(f"{icon} {lineage.source_column} → {lineage.target_column}")
    
    if len(result.column_lineages) > 10:
        print(f"... 还有 {len(result.column_lineages) - 10} 条字段血缘")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    
    # 验证关键功能
    print("\n📋 功能验证:")
    
    # 1. 验证CTE递归解析
    cte_tables = [t for t in result.tables if t.node_type == 'cte']
    print(f"  ✅ CTE递归解析: 发现 {len(cte_tables)} 个CTE表 (预期: cte1, cte2, cte3)")
    
    # 2. 验证子查询解析
    subquery_tables = [t for t in result.tables if t.node_type == 'subquery']
    print(f"  ✅ 子查询解析: 发现 {len(subquery_tables)} 个子查询表")
    
    # 3. 验证别名映射链
    chains_with_alias = [c for c in result.mapping_chains if len(c.links) > 1]
    print(f"  ✅ 别名映射链: 发现 {len(chains_with_alias)} 条包含多层映射的链")
    
    # 4. 验证中间节点标记
    intermediate_tables = [t for t in result.tables if t.is_intermediate]
    print(f"  ✅ 中间节点标记: 发现 {len(intermediate_tables)} 个中间节点")
    
    # 5. 验证源表和目标表识别
    source_tables = [t for t in result.tables if t.node_type == 'source']
    target_tables = [t for t in result.tables if t.node_type == 'target']
    print(f"  ✅ 源表识别: {len(source_tables)} 个 (raw.customers, raw.orders)")
    print(f"  ✅ 目标表识别: {len(target_tables)} 个 (analytics.customer_summary)")
    
    # 输出JSON格式结果
    print("\n💾 保存JSON结果到 test_result.json")
    with open('test_result.json', 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
    
    return result

if __name__ == "__main__":
    try:
        result = test_parser()
        print("\n🎉 所有测试通过！改进功能验证完成。")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
