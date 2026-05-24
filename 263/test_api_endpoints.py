#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, '.')

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://127.0.0.1:5000'

def test_endpoint(name, method, path, data=None, params=None):
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    try:
        if method == 'GET':
            resp = requests.get(f'{BASE_URL}{path}', params=params, timeout=10)
        elif method == 'POST':
            resp = requests.post(f'{BASE_URL}{path}', json=data, params=params, timeout=10)
        
        print(f"URL: {BASE_URL}{path}")
        print(f"状态码: {resp.status_code}")
        
        try:
            result = resp.json()
            if 'success' in result:
                print(f"成功: {result.get('success')}")
            if 'message' in result:
                print(f"消息: {result.get('message')}")
            
            if 'status' in result:
                status = result['status']
                print(f"运行状态: {status.get('is_running')}")
                print(f"检查次数: {status.get('total_checks', status.get('check_count'))}")
            
            if name == '监控立即检查':
                print(f"告警数量: {len(result.get('alerts', []))}")
                print(f"锁等待数量: {len(result.get('lock_waits', []))}")
            
            if name == '获取调用链关联':
                print(f"关联数量: {len(result.get('correlations', []))}")
            
            return True
        except Exception as e:
            print(f"响应解析失败: {e}")
            print(f"响应内容: {resp.text[:200]}")
            return False
            
    except Exception as e:
        print(f"请求失败: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Flask API端点测试")
    print("="*60)

    tests = [
        ("获取MySQL示例日志", 'GET', '/api/sample/mysql'),
        ("获取PostgreSQL示例日志", 'GET', '/api/sample/postgresql'),
        ("获取监控状态", 'GET', '/api/monitor/status'),
        ("启动实时监控", 'POST', '/api/monitor/start', {'db_type': 'mysql'}),
        ("监控立即检查", 'POST', '/api/monitor/check'),
        ("获取监控告警", 'GET', '/api/monitor/alerts'),
        ("配置APM", 'POST', '/api/apm/configure', {
            'apm_type': 'mock',
            'config': {'base_url': 'http://localhost:8080', 'service_name': 'test'}
        }),
        ("获取APM traces", 'GET', '/api/apm/traces'),
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test_endpoint(*test):
            passed += 1
        else:
            failed += 1

    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {len(tests)}")

    print("\n✓ 基础API测试完成")
    return failed == 0

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
