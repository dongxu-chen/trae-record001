#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nginx_log_analyzer import NginxLogAnalyzer, LogParser

print("="*60)
print("测试 Nginx 日志分析器修复")
print("="*60)

print("\n1. 测试日志解析功能...")
test_log_line = '192.168.1.1 - - [18/May/2026:10:00:01 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0" 45.2'
parsed = LogParser.parse_log_line(test_log_line)
if parsed:
    print(f"   ✓ 成功解析日志行")
    print(f"   - 时间格式: {parsed['time_str']}")
    print(f"   - 响应时间: {parsed['response_time']}ms")
else:
    print("   ✗ 解析失败")

print("\n2. 测试时间格式统一性...")
if parsed and parsed['time_str'] == '2026-05-18 10:00:01':
    print("   ✓ 时间格式正确统一 (YYYY-MM-DD HH:MM:SS)")
else:
    print(f"   ✗ 时间格式异常: {parsed['time_str'] if parsed else 'None'}")

print("\n3. 测试异常处理 - 不存在的文件...")
try:
    analyzer = NginxLogAnalyzer('nonexistent_file.log')
    report = analyzer.analyze()
    if 'error' in report:
        print(f"   ✓ 正确捕获文件不存在异常: {report['error']}")
    else:
        print("   ✗ 未能正确处理文件不存在")
except Exception as e:
    print(f"   ✓ 异常被抛出: {type(e).__name__}: {e}")

print("\n4. 测试现有日志文件分析...")
try:
    analyzer = NginxLogAnalyzer('sample_access.log')
    report = analyzer.analyze()
    
    if 'error' in report:
        print(f"   ✗ 分析失败: {report['error']}")
    else:
        print(f"   ✓ 成功分析 sample_access.log")
        print(f"   - 总请求数: {report['summary']['total_requests']}")
        print(f"   - 慢请求数量: {len(report['top_slow_requests'])}")
        
        print("\n5. 验证时间格式一致性...")
        time_formats = set()
        for item in report['top_requests_per_second']:
            time_formats.add(item['time'])
        for req in report['top_slow_requests']:
            time_formats.add(req['time'])
        
        all_iso = all('-' in t and ':' in t for t in time_formats)
        if all_iso:
            print("   ✓ 所有时间格式一致")
        else:
            print(f"   ✗ 时间格式不一致: {time_formats}")
        
        print("\n6. 验证慢请求功能...")
        if report['top_slow_requests']:
            print(f"   ✓ 找到 {len(report['top_slow_requests'])} 个慢请求")
            for req in report['top_slow_requests'][:3]:
                print(f"     - #{req['rank']}: {req['response_time_ms']}ms - {req['path']}")
        else:
            print("   ℹ 没有超过100ms的慢请求（这是正常的）")
        
        print("\n7. 保存报告测试...")
        if analyzer.save_report(report, 'test_report_output.json'):
            print("   ✓ 报告保存成功")
            if os.path.exists('test_report_output.json'):
                print("   ✓ 报告文件已创建")
        else:
            print("   ✗ 报告保存失败")
            
except Exception as e:
    print(f"   ✗ 测试失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("测试完成！")
print("="*60)
