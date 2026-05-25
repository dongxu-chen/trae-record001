import sys
sys.path.insert(0, '.')
from git_commit_checker.checker import CommitQualityChecker

print("Testing integration...")
checker = CommitQualityChecker()
print("Checker created")
report = checker.check_commit('a1fa73a')
print("Report generated")
data = report.to_dict()
print(f"Total score: {data['total_score']}/{data['max_score']}")
print(f"Percentage: {data['percentage']}%")
print(f"Grade: {data['grade']}")
print(f"Passed: {data['passed']}")

print("\n--- Consistency Check ---")
if 'consistency' in data:
    c = data['consistency']
    print(f"  Score: {c['score']}/{c['max_score']}")
    print(f"  Valid: {c.get('valid', 'N/A')}")
    if c.get('issues'):
        print(f"  Issues: {len(c['issues'])} issue(s)")
        for issue in c['issues'][:2]:
            print(f"    - {issue}")

print("\n--- History Analysis ---")
if 'history' in data:
    h = data['history']
    print(f"  Score: {h['score']}/{h['max_score']}")
    print(f"  Valid: {h.get('valid', 'N/A')}")
    if h.get('issues'):
        print(f"  Issues: {len(h['issues'])} issue(s)")
        for issue in h['issues'][:2]:
            print(f"    - {issue}")

print("\n--- Template Recommendation ---")
if 'template' in data:
    t = data['template']
    print(f"  Score: {t['score']}/{t['max_score']}")
    print(f"  Valid: {t.get('valid', 'N/A')}")
    recs = data.get('recommendations', [])
    print(f"  Recommendations: {len(recs)}")
    for rec in recs[:2]:
        print(f"    [{rec['type']}] {rec['confidence']:.0%}: {rec['template'][:50]}...")

print("\n--- All Issues ---")
for s in data['suggestions'][:5]:
    print(f"  - {s}")
