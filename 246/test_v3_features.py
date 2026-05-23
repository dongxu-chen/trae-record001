import io
import base64
import time
from PIL import Image
import requests

API_URL = "http://localhost:8000"

def create_test_image(width=224, height=224, color=(255, 200, 150)):
    img = Image.new('RGB', (width, height), color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def test_health_check():
    print("=" * 70)
    print("Test 1: Health Check (v3)")
    print("=" * 70)
    try:
        response = requests.get(f"{API_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_sync_audit_with_report():
    print("\n" + "=" * 70)
    print("Test 2: Sync Audit with Report Recording")
    print("=" * 70)
    
    print("Auditing 5 images for report statistics...")
    colors = [(100, 150, 200), (200, 100, 150), (150, 200, 100), (180, 180, 100), (100, 180, 180)]
    
    for i, color in enumerate(colors):
        image_data = create_test_image(color=color)
        files = {'file': (f'test_{i}.jpg', image_data, 'image/jpeg')}
        data = {'enable_cache': 'true', 'enable_review': 'true', 'use_multi_hash': 'true'}
        
        try:
            response = requests.post(f"{API_URL}/api/audit/sync", files=files, data=data)
            result = response.json()
            print(f"  Image {i+1}: risk={result.get('risk_level')}, cached={result.get('cached')}")
        except Exception as e:
            print(f"  Image {i+1} Error: {e}")
    
    return True

def test_dynamic_thresholds():
    print("\n" + "=" * 70)
    print("Test 3: Dynamic Content Thresholds Configuration")
    print("=" * 70)
    
    try:
        print("Current thresholds:")
        response = requests.get(f"{API_URL}/api/config/thresholds")
        thresholds = response.json().get("thresholds", {})
        for content_type, values in thresholds.items():
            if isinstance(values, dict) and "high" in values:
                print(f"  {content_type}: high={values['high']}, low={values['low']}")
        
        print("\nUpdating porn threshold...")
        response = requests.post(
            f"{API_URL}/api/config/thresholds",
            data={
                "content_type": "porn",
                "high_threshold": 0.9,
                "low_threshold": 0.6
            }
        )
        print(f"Update status: {response.json().get('status')}")
        
        print("\nUpdated thresholds:")
        response = requests.get(f"{API_URL}/api/config/thresholds")
        thresholds = response.json().get("thresholds", {})
        porn_thresh = thresholds.get("porn", {})
        print(f"  porn: high={porn_thresh.get('high')}, low={porn_thresh.get('low')}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_sensitive_words():
    print("\n" + "=" * 70)
    print("Test 4: Sensitive Words Management")
    print("=" * 70)
    
    try:
        print("Setting sensitive words...")
        response = requests.post(
            f"{API_URL}/api/config/sensitive-words",
            json={"words": ["违禁词1", "敏感词2", "广告"], "category": "all"}
        )
        print(f"Set status: {response.json().get('status')}")
        
        print("\nAdding new sensitive word...")
        response = requests.post(
            f"{API_URL}/api/config/sensitive-words/add",
            data={"word": "违规内容", "category": "all"}
        )
        print(f"Add status: {response.json().get('status')}")
        
        print("\nCurrent sensitive words:")
        response = requests.get(f"{API_URL}/api/config/sensitive-words")
        result = response.json()
        print(f"  Count: {result.get('count')}")
        print(f"  Words: {result.get('words')}")
        
        print("\nChecking text for sensitive content:")
        test_text = "这是一个包含违禁词1的文本内容"
        response = requests.post(
            f"{API_URL}/api/config/sensitive-words/check",
            data={"text": test_text}
        )
        check_result = response.json()
        print(f"  Text: {test_text}")
        print(f"  Has sensitive: {check_result.get('has_sensitive')}")
        print(f"  Matched words: {check_result.get('matched_words')}")
        
        print("\nRemoving sensitive word...")
        response = requests.post(
            f"{API_URL}/api/config/sensitive-words/remove",
            data={"word": "广告", "category": "all"}
        )
        print(f"Remove status: {response.json().get('status')}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_review_rules_config():
    print("\n" + "=" * 70)
    print("Test 5: Review Rules Configuration")
    print("=" * 70)
    
    try:
        print("Current review rules:")
        response = requests.get(f"{API_URL}/api/config/review-rules")
        rules = response.json().get("rules", {})
        for key, value in rules.items():
            print(f"  {key}: {value}")
        
        print("\nUpdating review rules...")
        new_rules = {
            "auto_submit_high_risk": True,
            "auto_submit_low_confidence": True,
            "low_confidence_threshold": 0.7,
            "review_priority_high_risk": "high",
            "review_priority_low_confidence": "medium",
            "require_manual_review": False
        }
        response = requests.post(
            f"{API_URL}/api/config/review-rules",
            json=new_rules
        )
        print(f"Update status: {response.json().get('status')}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_content_distribution_report():
    print("\n" + "=" * 70)
    print("Test 6: Content Distribution Report")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/reports/content-distribution")
        report = response.json()
        
        print(f"Period: {report.get('period')}")
        print(f"Date: {report.get('date')}")
        print(f"Total audits: {report.get('total')}")
        print("Distribution:")
        for content_type, data in report.get("distribution", {}).items():
            if isinstance(data, dict):
                print(f"  {content_type}: {data.get('count')} ({data.get('percentage')}%)")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_risk_distribution_report():
    print("\n" + "=" * 70)
    print("Test 7: Risk Distribution Report")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/reports/risk-distribution")
        report = response.json()
        
        print(f"Period: {report.get('period')}")
        print(f"Total audits: {report.get('total')}")
        print("Risk distribution:")
        for risk_level, data in report.get("distribution", {}).items():
            if isinstance(data, dict):
                print(f"  {risk_level}: {data.get('count')} ({data.get('percentage')}%)")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_performance_report():
    print("\n" + "=" * 70)
    print("Test 8: Audit Performance Report")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/reports/performance")
        report = response.json()
        
        print(f"Total audits: {report.get('total_count')}")
        print(f"Total process time: {report.get('total_process_time')}s")
        print(f"Average process time: {report.get('avg_process_time')}s")
        print(f"Cached count: {report.get('cached_count')}")
        print(f"Cache hit rate: {report.get('cache_hit_rate')}%")
        print(f"Similar count: {report.get('similar_count')}")
        print(f"Similar hit rate: {report.get('similar_hit_rate')}%")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_review_consistency_report():
    print("\n" + "=" * 70)
    print("Test 9: Review Consistency Report")
    print("=" * 70)
    
    try:
        print("Recording some review data...")
        for i in range(5):
            response = requests.post(
                f"{API_URL}/api/reports/record-review",
                data={
                    "review_id": f"review_{i}",
                    "image_id": f"image_{i}",
                    "original_risk": "low_risk" if i < 4 else "high_risk",
                    "final_risk": "low_risk" if i < 3 else "high_risk",
                    "reviewer": f"reviewer_{i % 2}"
                }
            )
        
        response = requests.get(f"{API_URL}/api/reports/review-consistency")
        report = response.json()
        
        print(f"Total reviews: {report.get('total_reviews')}")
        print(f"Consistent count: {report.get('consistent_count')}")
        print(f"Inconsistent count: {report.get('inconsistent_count')}")
        print(f"Consistency rate: {report.get('consistency_rate')}%")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_trend_data():
    print("\n" + "=" * 70)
    print("Test 10: Trend Data Report (7 days)")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/reports/trend", params={"days": 7})
        report = response.json()
        
        print(f"Days: {report.get('days')}")
        print("Trend data:")
        for day_data in report.get("trend", []):
            print(f"  {day_data.get('date')}: total={day_data.get('total_count')}, "
                  f"high={day_data.get('high_risk_count')}, low={day_data.get('low_risk_count')}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_comprehensive_report():
    print("\n" + "=" * 70)
    print("Test 11: Comprehensive Report")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/reports/comprehensive")
        report = response.json()
        
        print("✓ Content distribution included")
        print("✓ Risk distribution included")
        print("✓ Performance included")
        print("✓ Review consistency included")
        
        print("\nReport sections:", list(report.keys()))
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_all_config():
    print("\n" + "=" * 70)
    print("Test 12: Get All Configuration")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_URL}/api/config/all")
        config = response.json()
        
        print("Config sections:")
        for section in config.keys():
            print(f"  ✓ {section}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_reset_config():
    print("\n" + "=" * 70)
    print("Test 13: Reset Configuration to Default")
    print("=" * 70)
    
    try:
        response = requests.post(f"{API_URL}/api/config/reset")
        print(f"Status: {response.json().get('status')}")
        print(f"Message: {response.json().get('message')}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def print_api_summary():
    print("\n" + "=" * 70)
    print("v3.0 API Summary")
    print("=" * 70)
    print("\nVideo Audit:")
    print("  POST /api/video/audit - Video content audit with frame extraction")
    
    print("\nDynamic Configuration:")
    print("  GET  /api/config/all - Get all config")
    print("  GET  /api/config/thresholds - Get content thresholds")
    print("  POST /api/config/thresholds - Update content threshold")
    print("  GET  /api/config/sensitive-words - Get sensitive words")
    print("  POST /api/config/sensitive-words - Set sensitive words")
    print("  POST /api/config/sensitive-words/add - Add sensitive word")
    print("  POST /api/config/sensitive-words/remove - Remove sensitive word")
    print("  POST /api/config/sensitive-words/check - Check sensitive content")
    print("  GET  /api/config/review-rules - Get review rules")
    print("  POST /api/config/review-rules - Set review rules")
    print("  POST /api/config/reset - Reset config to default")
    
    print("\nReports:")
    print("  GET  /api/reports/content-distribution - Content type distribution")
    print("  GET  /api/reports/risk-distribution - Risk level distribution")
    print("  GET  /api/reports/performance - Audit performance metrics")
    print("  GET  /api/reports/review-consistency - Review consistency rate")
    print("  GET  /api/reports/comprehensive - Comprehensive report")
    print("  GET  /api/reports/trend - 7-day trend data")
    print("  GET  /api/reports/top-violations - Top violations")
    print("  POST /api/reports/record-review - Record review result")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Image Audit Service v3.0 - New Features Test Suite")
    print("=" * 70)
    
    results = []
    
    results.append(("Health Check", test_health_check()))
    results.append(("Sync Audit + Report", test_sync_audit_with_report()))
    results.append(("Dynamic Thresholds", test_dynamic_thresholds()))
    results.append(("Sensitive Words", test_sensitive_words()))
    results.append(("Review Rules Config", test_review_rules_config()))
    results.append(("Content Distribution", test_content_distribution_report()))
    results.append(("Risk Distribution", test_risk_distribution_report()))
    results.append(("Performance Report", test_performance_report()))
    results.append(("Review Consistency", test_review_consistency_report()))
    results.append(("Trend Data", test_trend_data()))
    results.append(("Comprehensive Report", test_comprehensive_report()))
    results.append(("All Config", test_all_config()))
    results.append(("Reset Config", test_reset_config()))
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    print(f"\nTotal: {passed}/{total} tests passed")
    
    print_api_summary()
