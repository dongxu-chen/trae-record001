"""验证三项新功能：覆盖查询分析、趋势预测、Explain火焰图"""
import json
import sys
sys.path.insert(0, ".")

from mongo_slow_analyzer.log_parser import parse_file
from mongo_slow_analyzer.analyzer import (
    build_report,
    analyze_covered_queries,
    forecast_slow_query_trend,
    simulate_explain_for_entry,
    convert_explain_to_flamegraph,
)

print("=" * 70)
print("加载 sample_logs.txt 数据")
print("=" * 70)

entries = list(parse_file("sample_logs.txt"))
print(f"解析条目数: {len(entries)}")

# === 1. 覆盖查询分析 ===
print("\n" + "=" * 70)
print("1. 覆盖查询分析")
print("=" * 70)

# 构造一些模拟现有索引
mock_indexes = [
    {"ns": "test.orders", "name": "idx_userId", "key": {"userId": 1, "status": 1, "createdAt": 1}},
    {"ns": "test.products", "name": "idx_category", "key": {"category": 1, "price": 1}},
]

covered = analyze_covered_queries(entries, mock_indexes)
print(f"可覆盖查询模式数: {len(covered)}")
for c in covered:
    print(f"  ns={c['ns']}, count={c['count']}, "
          f"avg_coverage={c['avg_coverage_ratio']}, "
          f"fully_covered={c['is_fully_covered']}, "
          f"used_fields={c['used_fields']}")

# === 2. 趋势预测 ===
print("\n" + "=" * 70)
print("2. 趋势预测")
print("=" * 70)

trend = forecast_slow_query_trend(entries, periods=7)
print(f"历史数据点: {trend['metrics']['history_points']}")
print(f"趋势: {trend['metrics']['trend']}")
print(f"斜率: {trend['metrics']['slope']}")
print(f"截距: {trend['metrics']['intercept']}")
print(f"残差标准差: {trend['metrics']['residual_std']}")
print(f"\n历史数据:")
for h in trend["history"]:
    print(f"  {h['timestamp']}: count={h['count']}, total_ms={h['total_ms']}")
print(f"\n预测数据 (未来 {len(trend['forecast'])} 周期):")
for f in trend["forecast"]:
    print(f"  {f['timestamp']}: predicted={f['predicted_count']}, "
          f"smoothed={f['smoothed_count']}, trend={f['trend']}")

# === 3. Explain 火焰图 ===
print("\n" + "=" * 70)
print("3. Explain 火焰图")
print("=" * 70)

# 取一个 IXSCAN 样本
ixscan_entry = next(e for e in entries if "IXSCAN" in str(e.get("planSummary", "")))
print(f"选取样本: ns={ixscan_entry['ns']}, duration={ixscan_entry['duration']}ms, "
      f"plan={ixscan_entry['planSummary']}")

explain_result = simulate_explain_for_entry(ixscan_entry)
flame = convert_explain_to_flamegraph(explain_result)

print(f"\n总耗时: {flame['total_execution_time_ms']}ms")
print(f"返回文档: {flame['n_returned']}")
print(f"索引扫描: {flame['total_keys_examined']}")
print(f"文档扫描: {flame['total_docs_examined']}")
print(f"\n阶段树结构:")
def print_tree(node, indent=0):
    prefix = "  " * indent
    name = node.get("name")
    value = node.get("value", 0)
    pct = (value / max(1, flame['total_execution_time_ms'])) * 100
    print(f"{prefix}{name}: {value}ms ({pct:.1f}%)")
    for child in node.get("children", []):
        print_tree(child, indent + 1)

print_tree(flame["tree"])

print(f"\n扁平化节点列表 (共 {len(flame['nodes'])} 个节点):")
for n in flame["nodes"]:
    pct = (n["value"] / max(1, flame["total_execution_time_ms"])) * 100
    print(f"  [{n['id']}] {n['name']}: {n['value']}ms ({pct:.1f}%) "
          f"keys={n['details'].get('keysExamined', 0)} docs={n['details'].get('docsExamined', 0)}")

print(f"\n边列表 (共 {len(flame['edges'])} 条边):")
for e in flame["edges"]:
    print(f"  {e['source']} → {e['target']}: {e['value']}ms")

# === 4. 完整报告 ===
print("\n" + "=" * 70)
print("4. 完整报告汇总")
print("=" * 70)

report = build_report(entries, mock_indexes)
print(f"总条目: {report['total_entries']}")
print(f"唯一模式: {report['total_unique_patterns']}")
print(f"索引建议: {len(report['index_suggestions'])}")
print(f"覆盖查询: {len(report['covered_queries'])}")
print(f"Explain样本: {len(report['explain_samples'])}")
print(f"趋势预测历史点: {report['trend_forecast']['metrics']['history_points']}")
print(f"趋势: {report['trend_forecast']['metrics']['trend']}")
print(f"分片动态阈值: {report['shard_hotspots']['quantile_thresholds']}")

# 打印 Explain 样例的树
for i, s in enumerate(report["explain_samples"][:1]):
    print(f"\nExplain 样本 #{i+1}: {s['ns']} - {s['flamegraph']['total_execution_time_ms']}ms")
    print(f"  模拟数据: {s['simulated']}")
    print(f"  阶段数: {len(s['flamegraph']['nodes'])}")

print("\n✅ 全部新功能验证完成!")
