import sys
from datetime import datetime, timedelta
import random

def test_merchant_db():
    print("=" * 60)
    print("测试商户库模块（含地理位置和父子类）...")
    try:
        from merchant_db import MerchantDatabase, CATEGORIES, CATEGORY_HIERARCHY
        
        db = MerchantDatabase()
        
        print(f"✓ 支持的类别: {CATEGORIES}")
        print(f"✓ 分类层级数: {len(CATEGORY_HIERARCHY)}")
        
        print("\n测试精确匹配（含地理位置）:")
        category, merchant = db.exact_match("肯德基", "北京")
        print(f"  - '肯德基' + '北京': {category}")
        
        category, merchant = db.exact_match("肯德基", "上海")
        print(f"  - '肯德基' + '上海': {category}")
        
        print("\n测试模糊匹配（含地理位置）:")
        category, score, merchant_info = db.fuzzy_match("肯德基餐厅", "北京")
        print(f"  - '肯德基餐厅' + '北京': {category} (置信度: {score}%)")
        if merchant_info:
            print(f"    匹配商户: {merchant_info.name}, 城市: {merchant_info.city}")
        
        print("\n测试父类分类兜底:")
        parent_cat = db.parent_category_fallback("某特色餐厅")
        print(f"  - '某特色餐厅': {parent_cat}")
        
        parent_cat = db.cold_start_classify("好吃的饭馆")
        print(f"  - '好吃的饭馆' 冷启动分类: {parent_cat}")
        
        print("\n测试搜索商户:")
        results = db.search_merchants("咖啡")
        print(f"  - '咖啡' 找到 {len(results)} 个结果")
        
        print("\n✓ 商户库模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 商户库模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_classifier():
    print("=" * 60)
    print("测试分类器模块（含地理位置和父类兜底）...")
    try:
        from classifier import TransactionClassifier
        
        classifier = TransactionClassifier()
        print(f"✓ 分类模型加载成功")
        print(f"  - 是否冷启动: {classifier.is_cold_start}")
        
        print("\n测试批量分类（含地理位置）:")
        test_transactions = [
            {'merchant': '肯德基', 'amount': 35, 'date': '2024-01-15', 'time': '09:00:00', 'location': '北京'},
            {'merchant': '星巴克咖啡', 'amount': 35, 'date': '2024-01-15', 'time': '09:00:00', 'location': '上海'},
            {'merchant': '滴滴快车', 'amount': 28, 'date': '2024-01-15', 'time': '08:30:00', 'location': '广州'},
            {'merchant': '淘宝购物', 'amount': 299, 'date': '2024-01-15', 'time': '14:00:00', 'location': ''},
            {'merchant': '电影院', 'amount': 88, 'date': '2024-01-15', 'time': '19:30:00', 'location': '深圳'},
            {'merchant': '医院挂号', 'amount': 50, 'date': '2024-01-15', 'time': '09:00:00', 'location': '北京'},
            {'merchant': '某特色餐厅', 'amount': 150, 'date': '2024-01-15', 'time': '12:00:00', 'location': '杭州'},
        ]
        
        results = classifier.classify_batch(test_transactions)
        print("  分类结果:")
        for r in results:
            city_info = f", 城市: {r.get('city', 'N/A')}" if r.get('city') else ""
            sub_cat_info = f", 子分类: {r.get('sub_category', 'N/A')}" if r.get('sub_category') else ""
            tags_info = f", 标签: {r.get('tags', [])}" if r.get('tags') else ""
            print(f"    - {r['merchant']}: {r['category']} ({r['method']}, 置信度: {r['confidence']:.2%}{city_info}{sub_cat_info}{tags_info})")
        
        print("\n✓ 分类器模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 分类器模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_anomaly_detection():
    print("=" * 60)
    print("测试异常检测模块（动态阈值-分位数方法）...")
    try:
        from anomaly_detection import AnomalyDetector
        import pandas as pd
        
        detector = AnomalyDetector(use_dynamic_threshold=True)
        print("✓ 异常检测器初始化成功（动态阈值模式）")
        
        print("\n生成测试数据...")
        transactions = []
        categories = ['餐饮', '购物', '交通', '娱乐', '医疗']
        for i in range(50):
            cat = categories[i % 5]
            base_amount = {'餐饮': 50, '购物': 200, '交通': 30, '娱乐': 100, '医疗': 150}[cat]
            amount = base_amount + (i * 2) % 100
            transactions.append({
                'merchant': f'商户{i}',
                'amount': amount,
                'date': f'2024-01-{i%28 + 1:02d}',
                'time': f'{12+i%8:02d}:00:00',
                'category': cat,
                'location': '北京' if i % 2 == 0 else '上海'
            })
        
        transactions.append({
            'merchant': '异常商户',
            'amount': 10000,
            'date': '2024-01-15',
            'time': '02:30:00',
            'category': '购物',
            'location': '深圳'
        })
        
        print(f"✓ 生成 {len(transactions)} 条测试数据")
        
        anomalies = detector.detect_anomalies(transactions)
        print(f"✓ 检测到 {len(anomalies)} 个异常")
        
        if anomalies:
            summary = detector.get_anomaly_summary(anomalies)
            print(f"\n异常统计:")
            print(f"  - 高风险: {summary['by_severity']['high']}")
            print(f"  - 中风险: {summary['by_severity']['medium']}")
            print(f"  - 低风险: {summary['by_severity']['low']}")
            
            print(f"\n动态阈值:")
            threshold_info = summary.get('threshold_used', {})
            print(f"  - 金额95分位数阈值: ¥{threshold_info.get('amount_quantile', 'N/A')}")
            print(f"  - 频次95分位数阈值: {threshold_info.get('frequency_quantile', 'N/A')}")
            print(f"  - 新商户75分位数阈值: ¥{threshold_info.get('new_merchant_quantile', 'N/A')}")
            print(f"  - 异常时段中位数阈值: ¥{threshold_info.get('unusual_hour_quantile', 'N/A')}")
            
            print(f"\n异常详情（前3条）:")
            for a in anomalies[:3]:
                print(f"  - [{a['severity']}] {a['type']}: {a['description'][:50]}...")
        
        print("\n✓ 异常检测模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 异常检测模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tax_calculator():
    print("=" * 60)
    print("测试税务计算模块（个人+企业）...")
    try:
        from tax_calculator import TaxCalculator, TaxConfig
        
        calc = TaxCalculator()
        print("✓ 税务计算器初始化成功")
        
        print("\n生成测试数据...")
        transactions = []
        categories = ['餐饮', '交通', '购物', '娱乐', '医疗']
        for i in range(100):
            cat = categories[i % 5]
            base_amount = {'餐饮': 50, '交通': 30, '购物': 200, '娱乐': 100, '医疗': 150}[cat]
            amount = base_amount + random.randint(-10, 50)
            transactions.append({
                'merchant': f'商户{i}',
                'amount': amount,
                'date': f'2026-{i%12 + 1:02d}-{i%28 + 1:02d}',
                'time': f'{12+i%8:02d}:00:00',
                'category': cat,
                'location': '北京'
            })
        
        print(f"✓ 生成 {len(transactions)} 条测试数据")
        
        print("\n测试个人所得税计算:")
        config = TaxConfig(
            tax_type="personal",
            annual_income=200000.0,
            tax_rate=0.25,
            special_deductions={
                "子女教育": 12000.0,
                "住房贷款利息": 12000.0
            },
            other_deductions=0.0
        )
        calc.update_config(config)
        
        result = calc.calculate_personal_deduction(transactions, 2026)
        if result:
            print(f"  - 年度收入: ¥{result.get('annual_income', 0):,.2f}")
            print(f"  - 总扣除额: ¥{result.get('total_deduction', 0):,.2f}")
            print(f"  - 应纳税所得额: ¥{result.get('taxable_income', 0):,.2f}")
            print(f"  - 应缴个税: ¥{result.get('tax_payable', 0):,.2f}")
            print(f"  - 节税金额: ¥{result.get('tax_saved', 0):,.2f}")
            print(f"  - 实际税率: {result.get('effective_tax_rate', 0):.2f}%")
            
            deductions = result.get('category_deductions', [])
            print(f"  - 各类别抵扣明细:")
            for d in deductions:
                status = "✅" if d.get('eligible') else "❌"
                print(f"    {status} {d['category']}: ¥{d['total_amount']:,.2f} → 可抵扣 ¥{d['deductible_amount']:,.2f}")
        
        print("\n测试企业所得税计算:")
        biz_result = calc.calculate_business_deduction(
            transactions,
            business_type="enterprise",
            annual_revenue=1000000.0
        )
        if biz_result:
            print(f"  - 年度营业收入: ¥{biz_result.get('annual_revenue', 0):,.2f}")
            print(f"  - 总可抵扣额: ¥{biz_result.get('total_deductible', 0):,.2f}")
            print(f"  - 预计节税: ¥{biz_result.get('tax_saved', 0):,.2f}")
        
        print("\n测试抵扣汇总表:")
        summary_df = calc.get_deduction_summary(transactions, "personal")
        if not summary_df.empty:
            print(f"  ✓ 生成 {len(summary_df)} 条抵扣记录")
        
        print("\n✓ 税务计算模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 税务计算模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_budget_manager():
    print("=" * 60)
    print("测试预算管理模块（预警+对比+建议）...")
    try:
        from budget_manager import BudgetManager
        
        bm = BudgetManager()
        print("✓ 预算管理器初始化成功")
        
        budgets = bm.get_all_budgets()
        print(f"✓ 加载 {len(budgets)} 个类别预算")
        for cat, budget in budgets.items():
            print(f"  - {cat}: ¥{budget.monthly_budget:,.2f}")
        
        print("\n生成测试数据...")
        transactions = []
        categories = ['餐饮', '交通', '购物', '娱乐', '医疗']
        today = datetime.now()
        for i in range(200):
            cat = categories[i % 5]
            base_amount = {'餐饮': 50, '交通': 30, '购物': 200, '娱乐': 100, '医疗': 150}[cat]
            amount = base_amount + random.randint(-20, 100)
            
            days_offset = random.randint(0, 90)
            trans_date = today - timedelta(days=days_offset)
            
            transactions.append({
                'merchant': f'商户{i}',
                'amount': amount,
                'date': trans_date.strftime('%Y-%m-%d'),
                'time': f'{12+i%8:02d}:00:00',
                'category': cat,
                'location': '北京'
            })
        
        print(f"✓ 生成 {len(transactions)} 条测试数据（近3个月）")
        
        print("\n测试预算执行汇总:")
        summary = bm.get_budget_summary(transactions)
        if not summary.empty:
            total_budget = summary['预算金额'].sum()
            total_spent = summary['已消费'].sum()
            print(f"  - 总预算: ¥{total_budget:,.2f}")
            print(f"  - 已消费: ¥{total_spent:,.2f}")
            print(f"  - 完成率: {total_spent/total_budget*100:.1f}%")
            
            for _, row in summary.iterrows():
                status_icon = "🔴" if '超支' in str(row['状态']) else "🟡" if '即将' in str(row['状态']) else "🟢"
                print(f"  {status_icon} {row['类别']}: ¥{row['已消费']:,.2f}/¥{row['预算金额']:,.2f} ({row['完成比例']:.1f}%) - {row['状态']}")
        
        print("\n测试预算预警:")
        alerts = bm.check_budget_alerts(transactions)
        print(f"  ✓ 检测到 {len(alerts)} 个预警")
        for alert in alerts:
            level_icon = "🔴" if alert.alert_level == "critical" else "🟡"
            print(f"  {level_icon} {alert.message}")
            print(f"     已消费: ¥{alert.current_spending:,.2f}, 预算: ¥{alert.budget:,.2f}, 剩余: ¥{alert.remaining_budget:,.2f}")
        
        print("\n测试预算vs实际对比:")
        comparison = bm.get_budget_vs_actual(transactions, months=3)
        if not comparison.empty:
            print(f"  ✓ 生成 {len(comparison)} 条对比记录")
            print(f"    包含 {comparison['月份'].nunique()} 个月的数据")
        
        print("\n测试预算调整建议:")
        suggestions = bm.suggest_budget_adjustment(transactions, months=3)
        print(f"  ✓ 生成 {len(suggestions)} 条调整建议")
        for s in suggestions:
            icon = "⬆️" if '上调' in s['suggestion'] else "⬇️"
            print(f"  {icon} {s['category']}: {s['suggestion']} (偏离 {s['deviation']:+.1f}%)")
            print(f"     当前: ¥{s['current_budget']:,.2f} → 建议: ¥{s['recommended_budget']:,.2f}")
        
        print("\n测试设置预算:")
        bm.set_budget("餐饮", 2500, warning_threshold=0.75, critical_threshold=0.90)
        updated = bm.get_budget("餐饮")
        print(f"  ✓ 餐饮预算更新为: ¥{updated.monthly_budget:,.2f}")
        print(f"    预警阈值: {updated.warning_threshold*100:.0f}%, 严重阈值: {updated.critical_threshold*100:.0f}%")
        
        print("\n✓ 预算管理模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 预算管理模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trend_analysis():
    print("=" * 60)
    print("测试趋势分析模块（对比+预测+规律）...")
    try:
        from trend_analysis import TrendAnalyzer
        
        ta = TrendAnalyzer()
        print("✓ 趋势分析器初始化成功")
        
        print("\n生成测试数据（近12个月）...")
        transactions = []
        categories = ['餐饮', '交通', '购物', '娱乐', '医疗']
        today = datetime.now()
        for i in range(500):
            cat = categories[i % 5]
            base_amount = {'餐饮': 50, '交通': 30, '购物': 200, '娱乐': 100, '医疗': 150}[cat]
            
            month_offset = random.randint(0, 11)
            day_offset = random.randint(0, 27)
            trans_date = today - timedelta(days=month_offset*30 + day_offset)
            
            trend_factor = 1 + (month_offset / 24)
            amount = (base_amount + random.randint(-20, 50)) * trend_factor
            
            transactions.append({
                'merchant': f'商户{i}',
                'amount': round(amount, 2),
                'date': trans_date.strftime('%Y-%m-%d'),
                'time': f'{random.randint(8, 22):02d}:{random.randint(0, 59):02d}:00',
                'category': cat,
                'location': '北京'
            })
        
        print(f"✓ 生成 {len(transactions)} 条测试数据（近12个月）")
        
        print("\n测试环比分析（上月）:")
        mom = ta.compare_month_over_month(transactions, "previous_month")
        print(f"  - {mom.current_period}: ¥{mom.current_total:,.2f}")
        print(f"  - {mom.previous_period}: ¥{mom.previous_total:,.2f}")
        change_icon = "📈" if mom.is_increase else "📉"
        print(f"  - 变动: {change_icon} ¥{mom.change_amount:+,.2f} ({mom.change_percent:+.1f}%)")
        print(f"  - 趋势: {mom.trend}")
        
        print("\n测试同比分析（去年同月）:")
        yoy = ta.compare_month_over_month(transactions, "same_month_last_year")
        print(f"  - {yoy.current_period}: ¥{yoy.current_total:,.2f}")
        print(f"  - {yoy.previous_period}: ¥{yoy.previous_total:,.2f}")
        change_icon = "📈" if yoy.is_increase else "📉"
        print(f"  - 变动: {change_icon} ¥{yoy.change_amount:+,.2f} ({yoy.change_percent:+.1f}%)")
        print(f"  - 趋势: {yoy.trend}")
        
        print("\n测试各类别涨跌:")
        cat_trends = ta.get_category_trend(transactions)
        print(f"  ✓ 分析 {len(cat_trends)} 个类别的涨跌")
        for t in cat_trends:
            icon = "📈" if t.is_increase else "📉"
            print(f"  {icon} {t.category}: {t.change_percent:+.1f}% (占比: {t.contribution:.1f}%) - {t.trend}")
        
        print("\n测试月度趋势:")
        monthly = ta.get_monthly_trend(transactions, months=6)
        if not monthly.empty:
            print(f"  ✓ 获取 {len(monthly)} 个月的数据")
            print(f"    月份范围: {monthly['月份'].min()} ~ {monthly['月份'].max()}")
        
        print("\n测试周内消费规律:")
        weekday = ta.get_weekday_pattern(transactions, weeks=12)
        if not weekday.empty:
            max_day = weekday.loc[weekday['总消费'].idxmax()]
            min_day = weekday.loc[weekday['总消费'].idxmin()]
            print(f"  - 消费最高: {max_day['星期']} (¥{max_day['总消费']:,.2f})")
            print(f"  - 消费最低: {min_day['星期']} (¥{min_day['总消费']:,.2f})")
        
        print("\n测试时段消费分析:")
        hourly = ta.get_hourly_pattern(transactions, weeks=4)
        if not hourly.empty:
            peak_hour = hourly.loc[hourly['总消费'].idxmax()]
            print(f"  - 消费高峰: {peak_hour['时段']} (¥{peak_hour['总消费']:,.2f})")
            print(f"  - 单笔最高: {hourly.loc[hourly['平均每笔'].idxmax(), '时段']}")
        
        print("\n测试消费预测:")
        forecast = ta.forecast_next_month(transactions, "moving_average")
        if forecast:
            print(f"  - 预测方法: {forecast['method']}")
            print(f"  - 下月预测: ¥{forecast['forecast']:,.2f}")
            print(f"  - 95%置信区间: ¥{forecast['lower']:,.2f} ~ ¥{forecast['upper']:,.2f}")
            print(f"  - 置信度: {forecast['confidence']*100:.0f}%")
            print(f"  - 历史数据: {forecast['historical_points']} 个月")
        
        print("\n测试涨跌TOP:")
        growing = ta.get_top_growing_categories(transactions, top_n=3)
        declining = ta.get_top_declining_categories(transactions, top_n=3)
        print(f"  - 涨幅TOP3: {[g['category'] for g in growing]}")
        print(f"  - 跌幅TOP3: {[d['category'] for d in declining]}")
        
        print("\n测试综合分析报告:")
        summary = ta.get_comparison_summary(transactions)
        if summary:
            print(f"  ✓ 分析日期: {summary['analysis_date']}")
            print(f"  - 包含环比、同比、预测、涨跌TOP")
        
        print("\n✓ 趋势分析模块测试通过!")
        return True
    except Exception as e:
        print(f"✗ 趋势分析模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("信用卡消费分类系统 - 模块测试（完整版）")
    print("=" * 60)
    print("\n核心功能:")
    print("  ✓ 地理位置辅助匹配")
    print("  ✓ 同名店区分（按城市）")
    print("  ✓ 冷启动父类兜底（餐饮父类优先）")
    print("  ✓ 动态阈值（基于用户历史消费分位数）")
    print("  ✓ 税务计算（个人/企业可抵扣支出）")
    print("  ✓ 预算预警（类别超支提醒）")
    print("  ✓ 趋势分析（同期对比、涨跌、预测）")
    print()
    
    results = []
    results.append(test_merchant_db())
    results.append(test_classifier())
    results.append(test_anomaly_detection())
    results.append(test_tax_calculator())
    results.append(test_budget_manager())
    results.append(test_trend_analysis())
    
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有测试通过!")
        print("\n启动应用命令: streamlit run app.py")
        print("示例数据: sample_transactions.csv（已包含location字段）")
        print("\n新功能模块:")
        print("  - tax_calculator.py: 税务计算（个人+企业）")
        print("  - budget_manager.py: 预算管理（预警+建议）")
        print("  - trend_analysis.py: 趋势分析（对比+预测）")
        return 0
    else:
        print("✗ 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
