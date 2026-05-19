#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nginx_log_analyzer import NginxLogAnalyzer, LogParser

def test_log_parser():
    print("测试1: 日志解析器")
    test_line = '192.168.1.1 - - [18/May/2026:10:00:01 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0" 156.7'
    result = LogParser.parse_log_line(test_line)
    if result:
        print(f"  ✓ 解析成功")
        print(f"    时间: {result['time_str']}")
        print(f"    响应时间: {result['response_time']}ms")
        return result
    else:
        print("  ✗ 解析失败")
        return None

def test_time_format():
    print("\n测试2: 时间格式一致性")
    result = test_log_parser()
    if result:
        expected = '2026-05-18 10:00:01'
        if result['time_str'] == expected:
            print(f"  ✓ 时间格式正确: {result['time_str']}")
            return True
        else:
            print(f"  ✗ 时间格式错误: {result['time_str']}, 期望: {expected}")
    return False

def test_slow_requests():
    print("\n测试3: 慢请求计算")
    analyzer = NginxLogAnalyzer('sample_access.log')
    report = analyzer.analyze()
    if 'error' in report:
        print(f"  ✗ 分析失败: {report['error']}")
        return False
    
    slow_requests = report['top_slow_requests']
    print(f"  ✓ 找到 {len(slow_requests)} 个慢请求")
    for req in slow_requests:
        if req['response_time_ms'] >= 100:
            print(f"    - {req['response_time_ms']}ms: {req['path']} ({req['time']})")
    return len(slow_requests) > 0

def test_exception_handling():
    print("\n测试4: 异常处理")
    analyzer = NginxLogAnalyzer('non_existent_file_1234.log')
    report = analyzer.analyze()
    if 'error' in report:
        print(f"  ✓ 正确处理文件不存在: {report['error']}")
        return True
    else:
        print("  ✗ 未能正确处理文件不存在")
        return False

def test_full_analysis():
    print("\n测试5: 完整分析功能")
    analyzer = NginxLogAnalyzer('sample_access.log')
    report = analyzer.analyze()
    
    if 'error' in report:
        print(f"  ✗ 分析失败: {report['error']}")
        return False
    
    print(f"  ✓ 分析成功")
    print(f"    总请求数: {report['summary']['total_requests']}")
    print(f"    状态码数: {len(report['status_code_statistics']['status_distribution'])}")
    print(f"    高峰时间点数: {len(report['top_requests_per_second'])}")
    print(f"    慢请求数: {len(report['top_slow_requests'])}")
    
    print("\n测试6: JSON报告验证")
    output_file = 'verification_report.json'
    if analyzer.save_report(report, output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  ✓ JSON报告保存成功")
        print(f"    分析时间: {data['analysis_time']}")
        print(f"    日志文件: {data['log_file']}")
        os.remove(output_file)
        return True
    return False

def main():
    print("="*60)
    print("Nginx 日志分析器 - 修复验证")
    print("="*60)
    
    results = []
    results.append(("日志解析", bool(test_log_parser())))
    results.append(("时间格式一致性", test_time_format()))
    results.append(("慢请求计算", test_slow_requests()))
    results.append(("异常处理", test_exception_handling()))
    results.append(("完整分析功能", test_full_analysis()))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有修复验证通过！")
    else:
        print("\n⚠ 部分测试需要关注")

if __name__ == '__main__':
    main()
