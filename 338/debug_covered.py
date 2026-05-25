"""调试覆盖查询"""
import sys
sys.path.insert(0, ".")

from mongo_slow_analyzer.log_parser import parse_file
from mongo_slow_analyzer.analyzer import analyze_covered_queries

entries = list(parse_file("sample_logs.txt"))

# 打印所有 IXSCAN 的条目
print("IXSCAN 条目:")
for i, e in enumerate(entries):
    if "IXSCAN" in str(e.get("planSummary", "")):
        print(f"  [{i}] ns={e['ns']}, plan={e['planSummary']}, "
              f"keys={e.get('keysExamined')}, docs={e.get('docsExamined')}, "
              f"filter={e.get('filter')}, sort={e.get('sort')}, projection={e.get('projection')}")

mock_indexes = [
    {"ns": "test.orders", "name": "idx_userId", "key": {"userId": 1, "status": 1, "createdAt": 1}},
    {"ns": "test.products", "name": "idx_category", "key": {"category": 1, "price": 1}},
]

covered = analyze_covered_queries(entries, mock_indexes)
print(f"\n覆盖查询数量: {len(covered)}")
