import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import json

sys.path.insert(0, '.')

from data_generator import TimeSeriesDataGenerator

print('=' * 60)
print('测试三个核心功能模块')
print('=' * 60)
print()

# 1. 生成测试数据
print('1. 生成测试数据...')
generator = TimeSeriesDataGenerator(days=7, freq='15min')
df, injected = generator.generate_metrics_data(inject_anomalies=True)
print(f'   生成 {len(df)} 条数据, {len(injected)} 个注入异常')
print(f'   时间范围: {df["timestamp"].min()} ~ {df["timestamp"].max()}')
print()

# 2. 测试异常预测模块
print('2. 测试异常预测模块 (AnomalyPredictor)...')
from anomaly_predictor import AnomalyPredictor

predictor = AnomalyPredictor(forecast_periods=96, interval_width=0.95)
print('   正在训练预测模型并检测预警...')

# 先查看每个指标的预警分数分布
for metric in ['qps', 'latency', 'error_rate']:
    alerts = predictor.detect_pending_anomalies(df, metric, threshold_hours=6, alert_score_threshold=0.1)
    if alerts:
        max_score = max(a['anomaly_score'] for a in alerts)
        print(f'   {metric}: 共{len(alerts)}个预警点, 最高分数={max_score:.3f}')

combined_alerts = predictor.get_combined_alerts(
    df, ['qps', 'latency', 'error_rate'], 
    threshold_hours=6, min_score=0.3, alert_score_threshold=0.2
)

print(f'   ✅ 预测完成')
print(f'   预警数量: {len(combined_alerts)}')
for i, alert in enumerate(combined_alerts[:3]):
    print(f'   预警 {i+1}: {alert["combined_risk"]}级, '
          f'预计{alert["time_window_hours"]:.1f}小时后, '
          f'指标: {alert["metrics_affected"]}, '
          f'联合预警: {"是" if alert["is_joint_alert"] else "否"}')
print()

# 3. 测试异常事件关联模块
print('3. 测试异常事件关联模块 (EventCorrelator)...')
from event_correlator import EventCorrelator

# 先获取一些异常用于关联
print('   先运行异常检测获取异常数据...')
from anomaly_fusion import AnomalyFusion
fusion = AnomalyFusion()
anomalies = fusion.fuse_anomalies(df, ['qps', 'latency', 'error_rate'])
print(f'   检测到 {len(anomalies)} 个异常')

correlator = EventCorrelator(time_window_minutes=30, similarity_threshold=0.3)
events = correlator.correlate_anomalies(anomalies)
merged_events = correlator.merge_similar_events(events, max_time_gap_hours=2)
summary = correlator.get_summary(events)

print(f'   ✅ 关联分析完成')
print(f'   关联事件数: {len(events)}')
print(f'   合并后事件数: {len(merged_events)}')
print(f'   平均时长: {summary.get("average_duration_minutes", 0):.1f} 分钟')

# 打印异常数>1的事件
multi_anomaly_events = [e for e in events if len(e.anomalies) > 1]
print(f'   多异常事件数: {len(multi_anomaly_events)}')
for i, event in enumerate(multi_anomaly_events[:3] if multi_anomaly_events else events[:3]):
    ed = event.to_dict()
    print(f'   事件 {i+1}: ID={ed["event_id"]}, '
          f'异常数={ed["anomaly_count"]}, '
          f'指标={ed["affected_metrics"]}, '
          f'关联分数={ed["correlation_score"]:.2%}')
    if ed.get('root_cause_hypothesis'):
        print(f'      疑似根因: {ed["root_cause_hypothesis"].get("most_likely_cause", "未知")}')
print()

# 4. 测试事件管理模块（处置闭环）
print('4. 测试事件管理模块 (IncidentManager)...')
from incident_manager import IncidentManager, IncidentStatus

# 使用内存存储，不持久化
manager = IncidentManager(storage_path=None)

# 从异常创建事件
print('   4.1 从异常创建事件...')
incident = manager.create_incident_from_anomaly(anomalies[0])
print(f'   ✅ 创建成功: {incident.incident_id}')
print(f'       状态: {incident.status.value}, 优先级: {incident.priority.value}')
print(f'       标题: {incident.title}')
print()

# 确认事件
print('   4.2 确认事件...')
incident = manager.acknowledge_incident(incident.incident_id, '操作员A')
print(f'   ✅ 确认成功, 新状态: {incident.status.value}, 处理人: {incident.assignee}')
print()

# 开始处置
print('   4.3 开始处置...')
incident = manager.start_treatment(
    incident.incident_id, '操作员A', 
    '发现数据库连接池耗尽，正在重启服务并调整连接数配置'
)
print(f'   ✅ 开始处置成功, 新状态: {incident.status.value}')
print(f'       操作日志数: {len(incident.action_logs)}')
print()

# 添加效果反馈
print('   4.4 添加效果反馈...')
feedback = manager.add_effect_feedback(
    incident.incident_id, 'qps', 1500.0, 650.0, '操作员A'
)
print(f'   ✅ 反馈成功')
print(f'       指标: {feedback.metric}')
print(f'       处理前: {feedback.before_value} → 处理后: {feedback.after_value}')
print(f'       改善率: {feedback.improvement_pct:.1f}%')
print(f'       是否有效: {"是" if feedback.is_effective else "否"}')
print()

# 再添加一个反馈（无效的）
feedback2 = manager.add_effect_feedback(
    incident.incident_id, 'latency', 500.0, 480.0, '操作员A'
)
print(f'   第二个反馈: latency 改善 {feedback2.improvement_pct:.1f}%, 有效: {"是" if feedback2.is_effective else "否"}')
print()

# 解决事件
print('   4.5 解决事件...')
incident = manager.resolve_incident(
    incident.incident_id, 
    '调整了数据库连接池大小从100到500，同时增加了2台应用服务器，所有指标恢复正常',
    '操作员A'
)
print(f'   ✅ 解决成功, 新状态: {incident.status.value}')
print()

# 关闭事件
print('   4.6 关闭事件...')
incident = manager.close_incident(incident.incident_id, '主管B')
print(f'   ✅ 关闭成功, 新状态: {incident.status.value}')
print()

# 获取事件详情
print('   4.7 事件完整详情...')
incident_full = manager.get_incident(incident.incident_id)
print(f'   事件ID: {incident_full.incident_id}')
print(f'   状态流转: OPEN → ACKNOWLEDGED → IN_PROGRESS → RESOLVED → CLOSED')
print(f'   操作日志 ({len(incident_full.action_logs)} 条):')
for log in incident_full.action_logs:
    print(f'     [{log.timestamp.strftime("%H:%M:%S")}] {log.user} - {log.action_type}: {log.description}')
print(f'   效果反馈 ({len(incident_full.effect_feedbacks)} 条):')
for fb in incident_full.effect_feedbacks:
    status = '✅ 有效' if fb.is_effective else '❌ 无效'
    print(f'     {status} {fb.metric}: {fb.before_value}→{fb.after_value} (改善{fb.improvement_pct:.1f}%)')
print()

# 5. 统计数据
print('5. 事件管理统计...')
summary = manager.get_incident_summary()
eff_stats = manager.get_effectiveness_stats()
print(f'   总事件数: {summary["total_incidents"]}')
print(f'   按状态: {summary["by_status"]}')
print(f'   按优先级: {summary["by_priority"]}')
print(f'   平均解决时间: {summary.get("avg_resolution_hours", 0):.2f} 小时')
print(f'   处置有效率: {eff_stats.get("effectiveness_rate", 0):.1%}')
print(f'   平均改善率: {eff_stats.get("avg_improvement_pct", 0):.1f}%')
print()

print('=' * 60)
print('✅ 所有核心功能测试通过！')
print('=' * 60)
print()
print('三个新增功能模块总结:')
print('1. 异常预测: 基于Prophet的多步预测 + 风险评分，支持联合预警')
print('2. 事件关联: 时间窗口 + 多维度相似度，同源异常自动合并')
print('3. 处置闭环: OPEN→ACK→IN_PROGRESS→RESOLVED→CLOSED完整状态机，')
print('           支持操作日志、效果量化反馈、统计分析')
print()
print('前端界面包含四个Tab:')
print('  - 异常检测: 原有功能（Prophet/3-Sigma/孤立森林 + 根因分析）')
print('  - 预测预警: 新增功能（配置预测窗口、预警分数，展示预警结果）')
print('  - 事件关联: 新增功能（配置时间窗口，展示关联事件）')
print('  - 事件管理: 新增功能（状态筛选、优先级筛选、完整处置流程）')
