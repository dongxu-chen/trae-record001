import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_health():
    print('=== 1. 健康检查 ===')
    r = requests.get(f'{BASE_URL}/api/health')
    print(f'状态: {r.json()["status"]}')
    print()

def test_generate_data():
    print('=== 2. 生成测试数据 ===')
    r = requests.post(f'{BASE_URL}/api/generate-data', 
                      json={'days': 7, 'freq': '5min', 'inject_anomalies': True})
    result = r.json()
    print(f'成功: {result["success"]}')
    print(f'消息: {result["message"]}')
    print()
    return result["success"]

def test_full_detection():
    print('=== 3. 完整异常检测 ===')
    r = requests.post(f'{BASE_URL}/api/detect/full', json={'store_results': True})
    result = r.json()
    print(f'成功: {result["success"]}')
    print(f'异常数: {result["anomalies_count"]}')
    if result["anomalies"]:
        first = result["anomalies"][0]
        print(f'第一个异常 - 时间: {first["timestamp"]}, 分数: {first["total_score"]:.2f}')
        print(f'  影响指标: {list(first["metrics"].keys())}')
        if first.get("most_probable_root_cause"):
            cause = first["most_probable_root_cause"]
            print(f'  最可能根因: {cause.get("cause", "未知")} (概率: {cause.get("posterior_probability", 0):.2%})')
    print()
    return result["anomalies"]

def test_prediction():
    print('=== 4. 异常预测预警 ===')
    r = requests.post(f'{BASE_URL}/api/predict/anomalies', 
                      json={'threshold_hours': 6, 'min_score': 0.5})
    result = r.json()
    print(f'成功: {result["success"]}')
    print(f'预警数量: {result["combined_alerts_count"]}')
    if result["combined_alerts"]:
        first = result["combined_alerts"][0]
        print(f'第一个预警 - {first["combined_risk"]}级, 预计{first["time_window_hours"]:.1f}小时后')
        print(f'  影响指标: {first["metrics_affected"]}')
        print(f'  联合预警: {"是" if first["is_joint_alert"] else "否"}')
    print()
    return result["combined_alerts"]

def test_correlation():
    print('=== 5. 异常事件关联 ===')
    r = requests.post(f'{BASE_URL}/api/events/correlate',
                      json={'time_window_minutes': 30})
    result = r.json()
    print(f'成功: {result["success"]}')
    print(f'关联事件数: {result["events_count"]}')
    print(f'合并后事件数: {result["merged_events_count"]}')
    if result["events"]:
        first = result["events"][0]
        print(f'第一个事件 - ID: {first["event_id"]}')
        print(f'  时间范围: {first["start_time"]} ~ {first["end_time"]}')
        print(f'  影响指标: {first["affected_metrics"]}')
        print(f'  异常数量: {first["anomaly_count"]}')
        print(f'  关联分数: {first["correlation_score"]:.2%}')
        if first.get("root_cause_hypothesis"):
            print(f'  疑似根因: {first["root_cause_hypothesis"].get("most_likely_cause", "未知")}')
    print()
    return result["events"]

def test_incident_management(events):
    print('=== 6. 事件管理（处置闭环） ===')
    
    if not events:
        print('没有事件可用于测试')
        return
    
    first_event_time = events[0]['start_time']
    
    # 6.1 创建事件
    print('6.1 创建事件')
    r = requests.post(f'{BASE_URL}/api/incidents',
                      json={'timestamp': first_event_time})
    result = r.json()
    print(f'创建成功: {result["success"]}')
    if not result["success"]:
        print(f'错误: {result.get("error")}')
        return
    
    incident_id = result['incident']['incident_id']
    print(f'事件ID: {incident_id}')
    print(f'状态: {result["incident"]["status"]}')
    print(f'优先级: {result["incident"]["priority"]}')
    print()
    
    # 6.2 确认事件
    print('6.2 确认事件')
    r = requests.post(f'{BASE_URL}/api/incidents/{incident_id}/acknowledge',
                      json={'user': '测试员'})
    result = r.json()
    print(f'确认成功: {result["success"]}')
    print(f'新状态: {result["incident"]["status"]}')
    print(f'处理人: {result["incident"]["assignee"]}')
    print()
    
    # 6.3 开始处置
    print('6.3 开始处置')
    r = requests.post(f'{BASE_URL}/api/incidents/{incident_id}/start-treatment',
                      json={'user': '测试员', 'description': '正在排查根因，准备扩容'})
    result = r.json()
    print(f'开始处置成功: {result["success"]}')
    print(f'新状态: {result["incident"]["status"]}')
    print(f'操作日志数: {len(result["incident"]["action_logs"])}')
    print()
    
    # 6.4 添加效果反馈
    print('6.4 添加效果反馈')
    r = requests.post(f'{BASE_URL}/api/incidents/{incident_id}/feedback',
                      json={'metric': 'qps', 'before_value': 1500, 'after_value': 800, 'user': '测试员'})
    result = r.json()
    print(f'反馈成功: {result["success"]}')
    if result["success"]:
        fb = result["feedback"]
        print(f'  指标: {fb["metric"]}')
        print(f'  处理前: {fb["before_value"]} → 处理后: {fb["after_value"]}')
        print(f'  改善率: {fb["improvement_pct"]:.1f}%')
        print(f'  是否有效: {"是" if fb["is_effective"] else "否"}')
    print()
    
    # 6.5 解决事件
    print('6.5 解决事件')
    r = requests.post(f'{BASE_URL}/api/incidents/{incident_id}/resolve',
                      json={'resolution_notes': '扩容了2台服务器，QPS恢复正常', 'user': '测试员'})
    result = r.json()
    print(f'解决成功: {result["success"]}')
    print(f'新状态: {result["incident"]["status"]}')
    print()
    
    # 6.6 关闭事件
    print('6.6 关闭事件')
    r = requests.post(f'{BASE_URL}/api/incidents/{incident_id}/close',
                      json={'user': '测试员'})
    result = r.json()
    print(f'关闭成功: {result["success"]}')
    print(f'新状态: {result["incident"]["status"]}')
    print()
    
    # 6.7 获取事件列表和统计
    print('6.7 获取事件统计')
    r = requests.get(f'{BASE_URL}/api/incidents')
    result = r.json()
    print(f'事件总数: {result["count"]}')
    print(f'统计信息: {json.dumps(result["summary"], indent=2, ensure_ascii=False)}')
    print()
    
    # 6.8 获取事件详情
    print('6.8 事件详情（含完整操作日志和反馈）')
    r = requests.get(f'{BASE_URL}/api/incidents/{incident_id}')
    result = r.json()
    if result["success"]:
        inc = result["incident"]
        print(f'事件ID: {inc["incident_id"]}')
        print(f'状态: {inc["status"]}')
        print(f'操作日志 ({len(inc["action_logs"])}条):')
        for log in inc["action_logs"]:
            print(f'  [{log["timestamp"]}] {log["user"]} - {log["action_type"]}: {log["description"]}')
        print(f'效果反馈 ({len(inc["effect_feedbacks"])}条):')
        for fb in inc["effect_feedbacks"]:
            print(f'  [{fb["timestamp"]}] {fb["metric"]}: {fb["before_value"]}→{fb["after_value"]} (改善{fb["improvement_pct"]:.1f}%)')
    print()

def test_incident_summary():
    print('=== 7. 事件管理汇总统计 ===')
    r = requests.get(f'{BASE_URL}/api/incidents/summary')
    result = r.json()
    print(f'成功: {result["success"]}')
    print(f'事件汇总: {json.dumps(result["summary"], indent=2, ensure_ascii=False)}')
    print(f'效果统计: {json.dumps(result["effectiveness"], indent=2, ensure_ascii=False)}')
    print()

if __name__ == '__main__':
    try:
        test_health()
        if test_generate_data():
            anomalies = test_full_detection()
            alerts = test_prediction()
            events = test_correlation()
            test_incident_management(events)
            test_incident_summary()
        print('✅ 所有API测试完成！')
    except Exception as e:
        print(f'❌ 测试出错: {e}')
        import traceback
        traceback.print_exc()
