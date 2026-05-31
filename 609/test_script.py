from scoring_model import ComprehensiveScorer
from training_recommender import PersonalizedTrainingRecommender
from sample_data import sample_conversations
from realtime_quality_monitor import RealtimeQualityMonitor
from excellent_script_miner import ExcellentScriptMiner
from agent_ranking_system import AgentRankingSystem

print("="*70)
print("客服对话质量评分系统 v3.0 - 全面测试")
print("="*70)

scorer = ComprehensiveScorer()
recommender = PersonalizedTrainingRecommender()
monitor = RealtimeQualityMonitor()
miner = ExcellentScriptMiner()
ranker = AgentRankingSystem()

print(f"\n测试对话数量: {len(sample_conversations)}")
print("\n" + "-"*70)

all_results = []
for i, conv in enumerate(sample_conversations):
    print(f"\n对话 {i+1}: {conv['id']} ({conv['agent_id']})")
    result = scorer.score_conversation(conv)
    all_results.append(result)

    print(f"  综合评分: {result['comprehensive_score']}")
    print(f"  等级: {result['grade']}")
    print(f"  响应速度: {result['dimension_scores']['response_speed']['score']}")
    print(f"  用户满意度: {result['dimension_scores']['customer_satisfaction']['score']}")
    print(f"  客服情绪归因: {result['dimension_scores']['service_emotion']['score']}")
    print(f"  扣分项: {len(result['deductions'])} 个")

print("\n" + "-"*70)
print("\n📊 1. 实时质检功能测试:")
test_messages = [
    {"role": "customer", "content": "你好，我想查询订单", "timestamp": "2024-01-01T10:00:00"},
    {"role": "service", "content": "您好，请提供您的订单号", "timestamp": "2024-01-01T10:00:25"}
]
realtime_result = monitor.analyze_realtime_message(test_messages[:-1], test_messages[-1])
print(f"  当前质量评分: {realtime_result['current_quality_score']}")
print(f"  预警数量: {realtime_result['warning_count']}")
print(f"  改进建议: {len(realtime_result['suggestions'])} 条")

print("\n" + "-"*70)
print("\n💬 2. 优秀话术推荐测试:")
script_analysis = miner.mine_excellent_scripts(all_results)
print(f"  高评分对话数: {script_analysis['total_high_score']}")
print(f"  高评分占比: {script_analysis['high_score_ratio']}%")
print(f"  推荐话术分类: {len(script_analysis['recommended_scripts'])} 类")
for rec in script_analysis['recommended_scripts'][:3]:
    print(f"    - {rec['category']}: {rec['example_count']} 条例子")

print("\n" + "-"*70)
print("\n🏆 3. 客服排名测试:")
ranking_data = ranker.calculate_agent_rankings(all_results)
print(f"  客服总数: {ranking_data['total_agents']}")
print(f"  团队平均分: {ranking_data['avg_team_score']}")
print(f"  徽章分布: 金牌{ranking_data['badge_distribution']['gold']}人, 银牌{ranking_data['badge_distribution']['silver']}人, 铜牌{ranking_data['badge_distribution']['bronze']}人")
print(f"\n  排名前3:")
for r in ranking_data['rankings'][:3]:
    print(f"    #{r['rank']} {r['agent_id']}: {r['final_score']}分 ({r['badge']['name']})")

print("\n" + "-"*70)
print("\n🎯 4. 个性化培训测试 (agent_002):")
weakness_analysis = recommender.analyze_personal_weaknesses(all_results, "agent_002")
print(f"  对话数量: {weakness_analysis['conversation_count']}")
print(f"  平均综合评分: {weakness_analysis['avg_comprehensive_score']}")
print(f"  整体评估: {weakness_analysis['overall_assessment']}")
print(f"  待改进项目: {len(weakness_analysis['weaknesses'])} 个")

training_plan = recommender.generate_personalized_training_plan(weakness_analysis)
print(f"  推荐培训模块: {len(training_plan['recommended_modules'])} 个")
if training_plan['recommended_modules']:
    for m in training_plan['recommended_modules']:
        print(f"    - {m['title']} ({m['duration']})")

print("\n" + "="*70)
print("✅ 所有测试完成! 系统v3.0功能正常")
print("="*70)
