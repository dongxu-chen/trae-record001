import sys
import os
import time
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def import_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

flink_pkg = importlib.util.module_from_spec(importlib.util.spec_from_loader('flink', None))
sys.modules['flink'] = flink_pkg

suggestion_pkg = importlib.util.module_from_spec(importlib.util.spec_from_loader('suggestion', None))
sys.modules['suggestion'] = suggestion_pkg

live_dict = import_module(os.path.join(BASE_DIR, 'flink', 'live_dictionary.py'), 'flink.live_dictionary')
flink_pkg.live_dictionary = live_dict
flink_pkg.LiveDictionary = live_dict.LiveDictionary
flink_pkg.LIVE_JARGON = live_dict.LIVE_JARGON
flink_pkg.EMOTICONS = live_dict.EMOTICONS

LiveDictionary = live_dict.LiveDictionary
LIVE_JARGON = live_dict.LIVE_JARGON
EMOTICONS = live_dict.EMOTICONS

sentiment_module = import_module(os.path.join(BASE_DIR, 'flink', 'sentiment.py'), 'flink.sentiment')
flink_pkg.sentiment = sentiment_module
flink_pkg.SentimentAnalyzer = sentiment_module.SentimentAnalyzer
SentimentAnalyzer = sentiment_module.SentimentAnalyzer

aggregation_module = import_module(os.path.join(BASE_DIR, 'flink', 'aggregation.py'), 'flink.aggregation')
flink_pkg.aggregation = aggregation_module
flink_pkg.MetricsAggregator = aggregation_module.MetricsAggregator
flink_pkg.EventTimeAggregator = aggregation_module.EventTimeAggregator
flink_pkg.EventTimeWindow = aggregation_module.EventTimeWindow
MetricsAggregator = aggregation_module.MetricsAggregator
EventTimeAggregator = aggregation_module.EventTimeAggregator
EventTimeWindow = aggregation_module.EventTimeWindow

advisor_module = import_module(os.path.join(BASE_DIR, 'suggestion', 'advisor.py'), 'suggestion.advisor')
suggestion_pkg.advisor = advisor_module
suggestion_pkg.LiveAdvisor = advisor_module.LiveAdvisor
suggestion_pkg.IncrementalState = advisor_module.IncrementalState
LiveAdvisor = advisor_module.LiveAdvisor
IncrementalState = advisor_module.IncrementalState


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", details: dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status} {self.name}: {self.message}"


class ImprovementTester:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def test_live_dictionary(self) -> TestResult:
        print("\n" + "=" * 60)
        print("测试1: 直播黑话词汇库")
        print("=" * 60)

        try:
            d = LiveDictionary()
            jargon_count = d.get_all_jargon_count()
            total_jargon = sum(jargon_count.values())
            emoticon_count = len(EMOTICONS['positive']) + len(EMOTICONS['negative']) + len(EMOTICONS['neutral'])

            print(f"  正面词汇: {jargon_count['positive']} 个")
            print(f"  中性词汇: {jargon_count['neutral']} 个")
            print(f"  负面词汇: {jargon_count['negative']} 个")
            print(f"  总词汇数: {total_jargon} 个")
            print(f"  表情符号: {emoticon_count} 个")

            if total_jargon < 100:
                return TestResult("直播黑话词汇库", False,
                    f"词汇数量不足: {total_jargon} (需要≥100)",
                    {"count": total_jargon})

            test_text = "这个产品yyds！太划算了，闭眼入！😍"
            jargon_score, jargon_count, matches = d.match_jargon(test_text)
            emoticon_score, emoticon_count, _ = d.match_emoticons(test_text)

            print(f"\n  测试文本: {test_text}")
            print(f"  黑话匹配: {jargon_count} 个, 得分: {jargon_score:.4f}")
            print(f"  表情匹配: {emoticon_count} 个, 得分: {emoticon_score:.4f}")
            print(f"  匹配词汇: {[m[0] for m in matches]}")

            if jargon_count < 2:
                return TestResult("直播黑话词汇库", False,
                    f"黑话匹配数量不足: {jargon_count} (需要≥2)")

            concerns = d.classify_concern("这个价格太贵了，能便宜点吗？")
            categories = d.classify_product_category("这款口红颜色很好看")
            print(f"\n  关注点分类: {concerns}")
            print(f"  商品分类: {categories}")

            if 'price' not in concerns:
                return TestResult("直播黑话词汇库", False,
                    f"关注点分类错误: {concerns} (应包含'price')")

            if 'beauty' not in categories:
                return TestResult("直播黑话词汇库", False,
                    f"商品分类错误: {categories} (应包含'beauty')")

            weight = d.get_word_weight('yyds')
            print(f"\n  'yyds' 权重: {weight}")
            if abs(weight - 0.3) > 0.001:
                return TestResult("直播黑话词汇库", False,
                    f"词汇权重错误: 'yyds'={weight} (应为0.3)")

            return TestResult("直播黑话词汇库", True,
                f"词汇库包含 {total_jargon} 个专业词汇，匹配和分类功能正常",
                {"total_jargon": total_jargon, "emoticons": emoticon_count})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return TestResult("直播黑话词汇库", False, f"异常: {e}")

    def test_sentiment_analysis(self) -> TestResult:
        print("\n" + "=" * 60)
        print("测试2: 情感分析模型（加权融合算法）")
        print("=" * 60)

        try:
            analyzer = SentimentAnalyzer()
            weights = analyzer.get_weights()

            print(f"  基础权重配置:")
            print(f"    - 基础模型: {weights['base_weight']}")
            print(f"    - 黑话词汇: {weights['jargon_weight']}")
            print(f"    - 关键词: {weights['keyword_weight']}")
            print(f"    - 表情符号: {weights['emoticon_weight']}")

            test_cases = [
                ("这个产品yyds！太划算了，闭眼入！😍", "positive", "高赞直播语料"),
                ("质量太差了，根本就是假货，垃圾！😡", "negative", "差评直播语料"),
                ("多少钱？有优惠吗？包邮吗？", "neutral", "咨询类直播语料"),
                ("主播讲得真好，买它买它！🔥", "positive", "购买意向语料"),
                ("有点贵，再考虑考虑", "negative", "价格敏感语料"),
                ("666，主播太给力了，冲冲冲！💪", "positive", "互动激励语料"),
                ("发货太慢了，等了好久还没到", "negative", "物流抱怨语料"),
                ("这款有什么颜色？尺码标准吗？", "neutral", "规格咨询语料"),
            ]

            correct_count = 0
            total_count = 0

            print(f"\n  情感分析测试:")
            for text, expected, desc in test_cases:
                result = analyzer.analyze(text, event_timestamp=time.time())
                is_correct = result['label'] == expected
                if is_correct:
                    correct_count += 1
                total_count += 1

                status = "✓" if is_correct else "✗"
                print(f"  {status} [{desc}]")
                print(f"      文本: {text}")
                print(f"      预测: {result['label']} ({result['score']:.4f})")
                print(f"      期望: {expected}")
                print(f"      黑话匹配: {result['jargon_matches']} 个, 表情匹配: {result['emoticon_matches']} 个")
                print(f"      组件得分: 基础={result['components']['base_score']:.4f}, "
                      f"黑话={result['components']['jargon_score']:.4f}, "
                      f"关键词={result['components']['keyword_score']:.4f}, "
                      f"表情={result['components']['emoticon_score']:.4f}")

            accuracy = correct_count / total_count if total_count > 0 else 0
            print(f"\n  准确率: {correct_count}/{total_count} = {accuracy:.2%}")

            if accuracy < 0.75:
                return TestResult("情感分析模型", False,
                    f"准确率过低: {accuracy:.2%} (需要≥75%)",
                    {"accuracy": accuracy, "correct": correct_count, "total": total_count})

            stats = analyzer.get_statistics(use_event_time=True)
            print(f"\n  统计信息:")
            print(f"    正面: {stats['positive_count']}, 中性: {stats['neutral_count']}, 负面: {stats['negative_count']}")
            print(f"    平均得分: {stats['avg_score']:.4f}")
            print(f"    正面率: {stats['positive_rate']:.2%}, 负面率: {stats['negative_rate']:.2%}")
            print(f"    处理延迟: {stats['avg_processing_latency']:.4f}s")

            return TestResult("情感分析模型", True,
                f"加权融合算法准确率 {accuracy:.2%}，集成{len(LIVE_JARGON['positive']) + len(LIVE_JARGON['negative']) + len(LIVE_JARGON['neutral'])}个直播黑话",
                {"accuracy": accuracy, "test_cases": total_count})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return TestResult("情感分析模型", False, f"异常: {e}")

    def test_event_time_processing(self) -> TestResult:
        print("\n" + "=" * 60)
        print("测试3: 事件时间处理与窗口边界对齐")
        print("=" * 60)

        try:
            aggregator = MetricsAggregator()
            base_time = time.time() - 60

            print(f"  基础时间戳: {base_time:.2f}")
            print(f"  窗口大小: {aggregator.window_size}s, 滑动: {aggregator.window_slide}s")
            print(f"  水位线延迟: {aggregator.watermark_delay}s")

            aligned_start = EventTimeAggregator.align_window_start(base_time, 1)
            aligned_end = EventTimeAggregator.align_window_end(base_time, 1)
            print(f"\n  窗口边界对齐测试:")
            print(f"    原始时间: {base_time:.2f}")
            print(f"    对齐起始: {aligned_start:.2f} (整除1s = {aligned_start % 1 == 0})")
            print(f"    对齐结束: {aligned_end:.2f} (边界正确 = {aligned_end - aligned_start == 1})")

            if aligned_start % 1 != 0 or aligned_end - aligned_start != 1:
                return TestResult("事件时间处理", False, "窗口边界对齐错误")

            print(f"\n  模拟事件时间交易数据:")
            for i in range(10):
                event_time = base_time + i * 0.5
                amount = 100.0 + i * 50
                aggregator.add_transaction({
                    'amount': amount,
                    'product_id': f'P{i % 3 + 1:03d}',
                    'event_timestamp': event_time,
                })
                print(f"    事件 {i+1}: 时间={event_time:.2f}, 金额=¥{amount:.0f}, "
                      f"窗口={EventTimeAggregator.align_window_start(event_time, 1):.0f}s")

            wm_info = aggregator.get_watermark_info()
            print(f"\n  水位线信息:")
            print(f"    最大事件时间: {wm_info['max_event_time']:.2f}")
            print(f"    当前水位线: {wm_info['current_watermark']:.2f}")
            print(f"    处理延迟: {wm_info['lag']:.2f}s")
            print(f"    活跃窗口数: {wm_info['active_windows']}")
            print(f"    过期窗口数: {wm_info['expired_windows']}")
            print(f"    延迟事件数: {wm_info['late_events']}")

            if wm_info['max_event_time'] == 0 or wm_info['current_watermark'] == 0:
                return TestResult("事件时间处理", False, "水位线计算错误")

            metrics = aggregator.get_metrics(use_event_time=True)
            print(f"\n  事件时间指标:")
            print(f"    总成交金额: ¥{metrics['total_amount']:.2f}")
            print(f"    总订单数: {metrics['total_transactions']}")
            print(f"    事件时间戳: {metrics['event_time']:.2f}")
            print(f"    水位线: {metrics['watermark']:.2f}")
            print(f"    活跃窗口数: {metrics['active_window_count']}")
            print(f"    每秒成交额: ¥{metrics['amount_per_second']:.2f}")
            print(f"    每秒订单数: {metrics['transactions_per_second']}")

            if metrics['total_transactions'] != 10:
                return TestResult("事件时间处理", False,
                    f"交易计数错误: {metrics['total_transactions']} (应为10)")

            print(f"\n  延迟事件测试（事件时间早于水位线）:")
            late_event_time = base_time - 10
            aggregator.add_transaction({
                'amount': 999.0,
                'product_id': 'P999',
                'event_timestamp': late_event_time,
            })

            wm_info2 = aggregator.get_watermark_info()
            if wm_info2['late_events'] != 1:
                return TestResult("事件时间处理", False,
                    f"延迟事件未正确识别: {wm_info2['late_events']} (应为1)")

            print(f"    ✓ 延迟事件已识别，当前延迟事件数: {wm_info2['late_events']}")

            windows = aggregator.get_all_windows()
            print(f"\n  活跃窗口列表:")
            for w in windows[:5]:
                print(f"    窗口 [{w['window_start']:.0f}s - {w['window_end']:.0f}s]: "
                      f"{w['transaction_count']}笔订单, ¥{w['total_amount']:.0f}, "
                      f"{'已关闭' if w['is_closed'] else '活跃'}")

            trend = aggregator.get_trend_data(points=5, use_event_time=True)
            print(f"\n  趋势数据（事件时间）:")
            print(f"    时间点: {[f'{t:.0f}' for t in trend['timestamps']]}")
            print(f"    订单数: {trend['transactions']}")
            print(f"    成交额: {[f'¥{a:.0f}' for a in trend['amount']]}")

            return TestResult("事件时间处理", True,
                f"事件时间处理正常，窗口边界对齐正确，水位线={wm_info['current_watermark']:.2f}，"
                f"延迟={wm_info['lag']:.2f}s",
                {"total_transactions": 10, "late_events": 1, "lag": wm_info['lag']})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return TestResult("事件时间处理", False, f"异常: {e}")

    def test_incremental_computation(self) -> TestResult:
        print("\n" + "=" * 60)
        print("测试4: 增量计算（话术建议模块）")
        print("=" * 60)

        try:
            advisor = LiveAdvisor()

            print(f"  增量状态初始化:")
            state = advisor.get_incremental_state()
            print(f"    已处理弹幕ID: {state['last_processed_danmu_id']}")
            print(f"    总弹幕数: {state['total_danmu']}")
            print(f"    窗口年龄: {state['window_age']:.2f}s")

            if state['last_processed_danmu_id'] != 0 or state['total_danmu'] != 0:
                return TestResult("增量计算", False, "初始状态错误")

            print(f"\n  第一批弹幕处理（ID 1-5）:")
            batch1 = {
                'metrics': {
                    'current_online': 5000,
                    'conversion_rate': 0.08,
                    'likes_per_minute': 200,
                    'viewers_per_minute': 50,
                },
                'hotwords': [{'word': '优惠', 'count': 10}],
                'top_products': [{'product_id': 'P001', 'conversion_rate': 0.15, 'amount': 35880}],
                'latest_danmu': [
                    {'danmu_id': 1, 'content': '主播好帅！', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.8, 'concerns': []}},
                    {'danmu_id': 2, 'content': '这个多少钱？', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'neutral', 'score': 0.5, 'concerns': ['price']}},
                    {'danmu_id': 3, 'content': '太划算了！', 'is_vip': True, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.9, 'concerns': []}},
                    {'danmu_id': 4, 'content': '有优惠吗？', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'neutral', 'score': 0.5, 'concerns': ['price']}},
                    {'danmu_id': 5, 'content': '买它！', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.85, 'concerns': []}},
                ],
                'incremental_info': {'last_processed_danmu_id': 5}
            }

            result1 = advisor.analyze(batch1)
            inc1 = result1['incremental']

            print(f"    处理弹幕数: {inc1['processed_danmu_count']}")
            print(f"    已处理总数: {inc1['total_danmu_processed']}")
            print(f"    最后弹幕ID: {inc1['last_processed_danmu_id']}")
            print(f"    统计信息: 正面={inc1['full_stats']['positive_count']}, "
                  f"中性={inc1['full_stats']['neutral_count']}, "
                  f"负面={inc1['full_stats']['negative_count']}")

            if inc1['total_danmu_processed'] != 5 or inc1['last_processed_danmu_id'] != 5:
                return TestResult("增量计算", False,
                    f"第一批处理错误: 总数={inc1['total_danmu_processed']}, "
                    f"最后ID={inc1['last_processed_danmu_id']}")

            print(f"\n  第二批弹幕处理（ID 6-10，含重复ID 3-5）:")
            batch2 = {
                'metrics': {
                    'current_online': 5200,
                    'conversion_rate': 0.09,
                    'likes_per_minute': 220,
                    'viewers_per_minute': 60,
                },
                'hotwords': [{'word': '优惠', 'count': 12}, {'word': '质量', 'count': 5}],
                'top_products': [{'product_id': 'P001', 'conversion_rate': 0.16, 'amount': 42000}],
                'latest_danmu': [
                    {'danmu_id': 3, 'content': '太划算了！', 'is_vip': True, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.9, 'concerns': []}},
                    {'danmu_id': 4, 'content': '有优惠吗？', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'neutral', 'score': 0.5, 'concerns': ['price']}},
                    {'danmu_id': 5, 'content': '买它！', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.85, 'concerns': []}},
                    {'danmu_id': 6, 'content': '质量好吗？', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'neutral', 'score': 0.5, 'concerns': ['quality']}},
                    {'danmu_id': 7, 'content': 'yyds！', 'is_vip': True, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.95, 'concerns': []}},
                    {'danmu_id': 8, 'content': '太贵了', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'negative', 'score': 0.3, 'concerns': ['price']}},
                    {'danmu_id': 9, 'content': '发货快吗？', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'neutral', 'score': 0.5, 'concerns': ['logistics']}},
                    {'danmu_id': 10, 'content': '已下单！😍', 'is_vip': True, 'timestamp': time.time(),
                     'sentiment': {'label': 'positive', 'score': 0.9, 'concerns': []}},
                ],
                'incremental_info': {'last_processed_danmu_id': 10}
            }

            result2 = advisor.analyze(batch2)
            inc2 = result2['incremental']

            print(f"    新增处理弹幕数: {inc2['processed_danmu_count']} (应为5，跳过重复ID 3-5)")
            print(f"    已处理总数: {inc2['total_danmu_processed']} (应为10)")
            print(f"    最后弹幕ID: {inc2['last_processed_danmu_id']} (应为10)")
            print(f"    统计信息: 正面={inc2['full_stats']['positive_count']}, "
                  f"中性={inc2['full_stats']['neutral_count']}, "
                  f"负面={inc2['full_stats']['negative_count']}")
            print(f"    热门关注点: {inc2['top_concerns']}")

            if inc2['processed_danmu_count'] != 5:
                return TestResult("增量计算", False,
                    f"去重处理错误: 新增{inc2['processed_danmu_count']} (应为5)")
            if inc2['total_danmu_processed'] != 10:
                return TestResult("增量计算", False,
                    f"累计计数错误: {inc2['total_danmu_processed']} (应为10)")
            if inc2['full_stats']['negative_count'] != 1:
                return TestResult("增量计算", False,
                    f"负面计数错误: {inc2['full_stats']['negative_count']} (应为1)")

            print(f"\n  话术建议测试:")
            time.sleep(16)
            batch3 = {
                'metrics': {
                    'current_online': 3000,
                    'conversion_rate': 0.03,
                    'likes_per_minute': 50,
                    'viewers_per_minute': -100,
                },
                'hotwords': [{'word': '便宜', 'count': 8}, {'word': '质量', 'count': 6}],
                'top_products': [{'product_id': 'P001', 'conversion_rate': 0.04, 'amount': 10000}],
                'latest_danmu': [
                    {'danmu_id': 11, 'content': '好贵啊', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'negative', 'score': 0.25, 'concerns': ['price']}},
                    {'danmu_id': 12, 'content': '不想要了', 'is_vip': False, 'timestamp': time.time(),
                     'sentiment': {'label': 'negative', 'score': 0.3, 'concerns': []}},
                ],
                'incremental_info': {'last_processed_danmu_id': 12}
            }

            result3 = advisor.analyze(batch3)
            inc3 = result3['incremental']

            print(f"    新增处理弹幕数: {inc3['processed_danmu_count']}")
            print(f"    已处理总数: {inc3['total_danmu_processed']}")

            if result3.get('current'):
                suggestion = result3['current']
                print(f"    触发音讯建议:")
                print(f"      等级: {suggestion['level']}")
                print(f"      类别: {suggestion['category']}")
                print(f"      消息: {suggestion['message']}")
                print(f"      建议: {suggestion['action']}")

            print(f"\n  窗口重置测试:")
            window_age = advisor.get_incremental_state()['window_age']
            print(f"    当前窗口年龄: {window_age:.2f}s")
            advisor.reset_state()
            state_after_reset = advisor.get_incremental_state()
            print(f"    重置后状态: 总数={state_after_reset['total_danmu']}, "
                  f"最后ID={state_after_reset['last_processed_danmu_id']}")

            if state_after_reset['total_danmu'] != 0 or state_after_reset['last_processed_danmu_id'] != 0:
                return TestResult("增量计算", False, "状态重置错误")

            return TestResult("增量计算", True,
                f"增量计算正常，去重处理正确，累计处理10条弹幕，"
                f"新增处理5条（去重跳过5条重复）",
                {"total_processed": 10, "incremental_processed": 5, "deduplicated": 5})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return TestResult("增量计算", False, f"异常: {e}")

    def run_all_tests(self):
        print("╔" + "=" * 70 + "╗")
        print("║" + " " * 15 + "电商直播数据大屏 - 改进功能验证" + " " * 18 + "║")
        print("╚" + "=" * 70 + "╝")

        self.results = [
            self.test_live_dictionary(),
            self.test_sentiment_analysis(),
            self.test_event_time_processing(),
            self.test_incremental_computation(),
        ]

        return self.print_summary()

    def print_summary(self):
        print("\n" + "╔" + "=" * 70 + "╗")
        print("║" + " " * 28 + "测试结果汇总" + " " * 28 + "║")
        print("╠" + "=" * 70 + "╣")

        passed = 0
        total = len(self.results)

        for result in self.results:
            print(f"║  {result}")
            if result.passed:
                passed += 1

        print("╠" + "=" * 70 + "╣")
        print(f"║  通过: {passed}/{total} 项" + " " * (53 - len(str(passed)) - len(str(total))) +
              f"耗时: {(time.time() - self.start_time):.2f}s  ║")

        if passed == total:
            print("║" + " " * 15 + "✓ 所有改进功能验证通过！" + " " * 25 + "║")
        else:
            print("║" + " " * 15 + f"✗ {total - passed} 项改进功能验证失败" + " " * 25 + "║")

        print("╚" + "=" * 70 + "╝\n")

        return passed == total


def main():
    tester = ImprovementTester()
    success = tester.run_all_tests()

    print("详细说明:")
    print("  1. 直播黑话词汇库: 包含300+电商直播专属词汇，分为正面/中性/负面三类")
    print("  2. 情感分析模型: 采用4维度加权融合算法，集成直播黑话和表情符号")
    print("  3. 事件时间处理: 基于事件时间的窗口聚合，水位线机制，乱序/延迟数据处理")
    print("  4. 增量计算: 话术建议模块只处理新增弹幕，按ID去重，累积统计\n")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
