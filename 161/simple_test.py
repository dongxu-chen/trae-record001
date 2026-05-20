#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from nginx_log_analyzer import NginxLogAnalyzer, LogParser

print("="*60)
print("简单验证测试")
print("="*60)

# 测试1: 日志行解析
print("\n测试1: 日志解析")
line = '192.168.1.1 - - [18/May/2026:10:00:01 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0" 156.7'
parsed = LogParser.parse_log_line(line)
if parsed:
    print("  PASS: 解析成功")
    print(f"  时间: {parsed['time_str']}")
    print(f"  响应时间: {parsed['response_time']}")
else:
    print("  FAIL: 解析失败")

# 测试2: 实际日志文件
print("\n测试2: 实际日志文件分析")
analyzer = NginxLogAnalyzer('sample_access.log')
report = analyzer.analyze()
if 'error' in report:
    print(f"  FAIL: {report['error']}")
else:
    print("  PASS: 分析成功")
    print(f"  总请求数: {report['summary']['total_requests']}")
    print(f"  慢请求数: {len(report['top_slow_requests'])}")

# 测试3: 慢请求详情
print("\n测试3: 慢请求详情")
if 'top_slow_requests' in report and report['top_slow_requests']:
    print("  PASS: 慢请求数据存在")
    for req in report['top_slow_requests'][:3]:
        print(f"  - #{req['rank']}: {req['response_time_ms']}ms - {req['path']} at {req['time']}")
else:
    print("  INFO: 无慢请求或数据为空")

# 测试4: 时间格式一致性
print("\n测试4: 时间格式一致性")
if 'top_requests_per_second' in report and report['top_requests_per_second']:
    peak_time = report['top_requests_per_second'][0]['time']
    print(f"  高峰时间: {peak_time}")
    if '-' in peak_time and ':' in peak_time:
        print("  PASS: 高峰时间格式正确")
    else:
        print("  FAIL: 高峰时间格式异常")

if 'top_slow_requests' in report and report['top_slow_requests']:
    slow_time = report['top_slow_requests'][0]['time']
    print(f"  慢请求时间: {slow_time}")
    if '-' in slow_time and ':' in slow_time:
        print("  PASS: 慢请求时间格式正确")
    else:
        print("  FAIL: 慢请求时间格式异常")

# 测试5: 保存报告
print("\n测试5: 保存报告")
if analyzer.save_report(report, 'test_output.json'):
    print("  PASS: 报告保存成功")
    if os.path.exists('test_output.json'):
        print("  PASS: 报告文件已创建")
        os.remove('test_output.json')

print("\n" + "="*60)
print("测试完成")
print("="*60)
