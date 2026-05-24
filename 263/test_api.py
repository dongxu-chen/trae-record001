#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Flask API
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_sample_api():
    print("=" * 60)
    print("测试示例日志API")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/sample/mysql")
    data = response.json()

    if data.get('success'):
        print(f"✅ 成功获取MySQL示例日志，长度: {len(data['content'])}")
        return data['content']
    else:
        print(f"❌ 获取示例日志失败: {data.get('error')}")
        return None

def test_parse_api(log_content):
    print("\n" + "=" * 60)
    print("测试解析API")
    print("=" * 60)

    files = {
        'db_type': (None, 'mysql'),
        'log_content': (None, log_content)
    }

    response = requests.post(f"{BASE_URL}/api/parse", files=files)
    data = response.json()

    if data.get('success'):
        print(f"✅ 解析成功!")
        print(f"  消息: {data['message']}")
        print(f"  死锁数: {len(data['deadlocks'])}")
        print(f"  建议数: {len(data['suggestions'])}")
        print(f"  图节点数: {data['graph_stats'].get('nodes', 0)}")
        print(f"  图边数: {data['graph_stats'].get('edges', 0)}")

        if data.get('statistics'):
            stats = data['statistics']
            print(f"\n统计信息:")
            print(f"  总死锁数: {stats.get('total_deadlocks', 0)}")
            print(f"  涉及表: {stats.get('involved_tables', [])}")
            print(f"  平均等待时间: {stats.get('average_wait_time', 0)}秒")
            print(f"  时间段分布: {stats.get('time_distribution', {})}")

        if data.get('suggestions'):
            print(f"\n优化建议 (TOP 3):")
            for i, s in enumerate(data['suggestions'][:3], 1):
                priority = {"high": "高", "medium": "中", "low": "低"}.get(s['priority'], s['priority'])
                print(f"  {i}. [{priority}] {s['category']}: {s['title']}")

        if data.get('deadlocks'):
            print(f"\n死锁详情:")
            for i, d in enumerate(data['deadlocks'], 1):
                print(f"  死锁 #{i}: {len(d['transactions'])}个事务, 牺牲事务: {d.get('victim_txns', [])}")

        return True
    else:
        print(f"❌ 解析失败: {data.get('error')}")
        return False

if __name__ == '__main__':
    try:
        log_content = test_sample_api()
        if log_content:
            test_parse_api(log_content)
        print("\n" + "=" * 60)
        print("✅ API测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
