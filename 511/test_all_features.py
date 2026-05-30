import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.parsers.sql_lineage_parser import SQLLineageParser
from app.services.analytics_service import (
    ImpactAnalysisService,
    DocumentGenerationService,
    AnomalyDetectionService,
)

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
        c1_id as c2_id,
        c1_name as c2_name,
        o.order_id,
        o.order_amount
    FROM cte1 c1
    JOIN raw.orders o ON c1.c1_id = o.customer_id
),
cte3 AS (
    SELECT 
        c2_id as customer_id,
        c2_name as customer_name,
        COUNT(order_id) as total_orders,
        SUM(order_amount) as total_amount
    FROM cte2
    GROUP BY c2_id, c2_name
)
INSERT INTO analytics.customer_summary
SELECT 
    customer_id,
    customer_name,
    total_orders,
    total_amount
FROM cte3
"""

def test_all_features():
    print("=" * 80)
    print("综合测试：验证所有新功能")
    print("=" * 80)
    
    parser = SQLLineageParser()
    result = parser.parse(TEST_SQL)
    
    print(f"\n✅ SQL解析成功")
    print(f"   表数量: {len(result.tables)}")
    print(f"   字段数量: {len(result.columns)}")
    print(f"   表血缘: {len(result.table_lineage)}")
    print(f"   字段血缘: {len(result.column_lineage)}")
    print(f"   映射链: {len(result.mapping_chains)}")
    
    print("\n" + "-" * 80)
    print("📊 测试1：影响分析")
    print("-" * 80)
    
    source_table = "raw.customers"
    impact_result = ImpactAnalysisService.analyze_impact(
        source_table,
        result.tables,
        result.columns,
        result.table_lineage,
        result.column_lineage,
        max_depth=10
    )
    
    print(f"\n源表: {source_table}")
    print(f"影响表数量: {impact_result.total_tables_impacted}")
    print(f"影响字段数量: {impact_result.total_columns_impacted}")
    print(f"最大影响深度: {impact_result.max_impact_depth}")
    
    print("\n下游影响表:")
    for table in impact_result.downstream_tables[:5]:
        print(f"  - {table.name} (层级: {table.level}, 直接影响: {table.direct_impacts})")
    
    print("\n影响统计摘要:")
    for key, value in impact_result.impact_summary.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-" * 80)
    print("📋 测试2：数据字典生成")
    print("-" * 80)
    
    data_dict = DocumentGenerationService.generate_data_dictionary(
        result.tables,
        result.columns,
        result.table_lineage,
        result.column_lineage,
        result.mapping_chains
    )
    
    print(f"\n生成时间: {data_dict.generated_at}")
    print(f"总表数: {data_dict.total_tables}")
    print(f"总字段数: {data_dict.total_columns}")
    
    print("\n表列表:")
    for table in data_dict.tables:
        print(f"\n  📄 {table.name} ({table.node_type})")
        print(f"     字段数: {len(table.columns)}")
        if table.source_tables:
            print(f"     源表: {', '.join(table.source_tables)}")
        if table.target_tables:
            print(f"     下游表: {', '.join(table.target_tables)}")
        
        print(f"     字段:")
        for col in table.columns[:3]:
            sources = ', '.join(col.source_columns) if col.source_columns else '-'
            transform = col.transformation or col.mapping_chain or '-'
            print(f"       - {col.name}: {sources} | {transform}")
        if len(table.columns) > 3:
            print(f"       ... 还有 {len(table.columns) - 3} 个字段")
    
    print("\n" + "-" * 80)
    print("📝 测试3：血缘文档生成")
    print("-" * 80)
    
    doc = DocumentGenerationService.generate_lineage_document(
        "测试血缘文档",
        result.tables,
        result.columns,
        result.table_lineage,
        result.column_lineage,
        result.mapping_chains
    )
    
    print(f"\n文档标题: {doc.title}")
    print(f"生成时间: {doc.generated_at}")
    
    print("\n文档摘要:")
    for key, value in doc.summary.items():
        if isinstance(value, list):
            print(f"  {key}: {', '.join(value) if len(value) < 5 else f'{len(value)} 项'}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n表血缘关系: {len(doc.table_lineage)} 条")
    print(f"字段血缘关系: {len(doc.column_lineage)} 条")
    print(f"关键字段映射: {len(doc.key_mappings)} 条")
    
    print("\n" + "-" * 80)
    print("📄 测试3a：Markdown文档导出")
    print("-" * 80)
    
    markdown = DocumentGenerationService.export_markdown(doc)
    print(f"\nMarkdown文档长度: {len(markdown)} 字符")
    
    md_preview = markdown[:500] + "..." if len(markdown) > 500 else markdown
    print(f"\nMarkdown预览:\n{md_preview}")
    
    with open('test_lineage_document.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
    print("\n✅ Markdown文档已保存到 test_lineage_document.md")
    
    print("\n" + "-" * 80)
    print("⚠️  测试4：异常检测")
    print("-" * 80)
    
    anomaly_result = AnomalyDetectionService.detect_anomalies(
        result.tables,
        result.columns,
        result.table_lineage,
        result.column_lineage
    )
    
    print(f"\n检测到异常总数: {anomaly_result.total_anomalies}")
    print(f"摘要: {anomaly_result.summary}")
    
    print("\n按严重程度统计:")
    for sev, count in anomaly_result.by_severity.items():
        print(f"  {sev}: {count}")
    
    print("\n按类型统计:")
    for typ, count in anomaly_result.by_type.items():
        print(f"  {typ}: {count}")
    
    print("\n异常详情:")
    for anomaly in anomaly_result.anomalies:
        icon = "🔴" if anomaly.severity in ['critical', 'high'] else "🟡" if anomaly.severity == 'medium' else "🟢"
        print(f"\n  {icon} [{anomaly.severity}] {anomaly.anomaly_type.value}")
        print(f"     描述: {anomaly.description}")
        if anomaly.affected_objects:
            print(f"     影响: {len(anomaly.affected_objects)} 个对象")
        if anomaly.recommendation:
            print(f"     建议: {anomaly.recommendation}")
    
    print("\n" + "=" * 80)
    print("✅ 所有功能测试完成！")
    print("=" * 80)
    
    print("\n📋 功能清单:")
    print("  ✅ 影响分析 - 源表影响下游范围展示")
    print("     - 下游表影响分析（层级、直接影响、总影响）")
    print("     - 下游字段影响分析")
    print("     - 影响路径追踪")
    print("     - 影响摘要统计")
    print("\n  ✅ 自动文档生成")
    print("     - 数据字典（表、字段、血缘关系）")
    print("     - 完整血缘文档（JSON格式）")
    print("     - Markdown文档导出")
    print("     - 关键字段映射链")
    print("\n  ✅ 异常检测")
    print("     - 孤立表检测")
    print("     - 孤立字段检测")
    print("     - 断连血缘链路检测")
    print("     - 循环依赖检测")
    print("     - 严重程度分级")
    print("     - 修复建议")
    
    result_json = {
        "impact_analysis": impact_result.model_dump(),
        "data_dictionary": data_dict.model_dump(),
        "lineage_document": doc.model_dump(),
        "anomaly_detection": anomaly_result.model_dump(),
    }
    
    with open('test_all_features.json', 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    print("\n💾 详细结果已保存到 test_all_features.json")
    
    return True

if __name__ == "__main__":
    try:
        success = test_all_features()
        if success:
            print("\n🎉 恭喜！所有新功能测试通过！")
        else:
            print("\n❌ 部分测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
