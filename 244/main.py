#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票因子回测平台 - 主程序入口
支持因子表达式输入、分层回测、绩效分析和可视化
"""

import argparse
import sys
from data_loader import DataLoader
from factor_engine import FactorEngine
from backtest import BacktestEngine
from performance import PerformanceAnalyzer
from visualization import Visualizer


def run_genetic_mining(n_stocks: int = 60,
                       population_size: int = 30,
                       max_generations: int = 5,
                       base_factors: list = None) -> dict:
    print("=" * 80)
    print("遗传编程因子挖掘")
    print("=" * 80)
    
    from genetic_factor_mining import GeneticFactorMiner
    
    print("\n[1/3] 加载数据...")
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=n_stocks, 
                                start_date='2021-01-01', 
                                end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    print("\n[2/3] 准备回测...")
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='M')
    
    print("\n[3/3] 开始遗传挖掘...")
    miner = GeneticFactorMiner(
        factors, returns, rebalance_dates,
        base_factors=base_factors or ['PE', 'PB', 'ROE'],
        population_size=population_size,
        max_generations=max_generations
    )
    
    best_factors = miner.mine_factors()
    
    print("\n" + "=" * 80)
    print("挖掘完成!")
    print("=" * 80)
    
    return {
        'best_factors': best_factors,
        'miner': miner
    }


def run_simulated_trading(factor_expression: str = '1 / PE',
                          factor_name: str = 'EP_Factor',
                          speed: float = 2.0) -> None:
    print("=" * 80)
    print("模拟交易系统 - WebSocket实时推送")
    print("=" * 80)
    
    from simulated_trading import TradingSimulator
    
    print("\n[1/3] 加载数据...")
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=50, 
                                start_date='2023-01-01', 
                                end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    print("\n[2/3] 计算因子和分组...")
    engine = FactorEngine(factors)
    factor = engine.calculate_factor(factor_expression)
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='W')
    groups = backtest.assign_groups(factor_ffill, rebalance_dates)
    
    print("\n[3/3] 启动模拟交易...")
    print("\nWebSocket服务器将在 ws://localhost:8765 启动")
    print("新开终端运行以下命令启动客户端监听:")
    print("  python simulated_trading.py --client")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 80)
    
    simulator = TradingSimulator(factor_ffill, price, groups)
    try:
        simulator.run_simulation_sync(factor_name=factor_name, speed=speed)
    except KeyboardInterrupt:
        print("\n模拟已停止")


def run_attribution_analysis(factor_expression: str = '1 / PE',
                             factor_name: str = 'EP_Factor') -> dict:
    print("=" * 80)
    print("归因分析 - 收益来源分解")
    print("=" * 80)
    
    from attribution_analysis import run_attribution_analysis
    
    print("\n[1/3] 加载数据...")
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=60, 
                                start_date='2022-01-01', 
                                end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    print("\n[2/3] 计算因子和分组...")
    engine = FactorEngine(factors)
    factor = engine.calculate_factor(factor_expression)
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='M')
    groups = backtest.assign_groups(factor_ffill, rebalance_dates)
    
    print("\n[3/3] 运行归因分析...")
    results = run_attribution_analysis(groups, returns, industry, factors, factor_name)
    
    return results


def run_factor_backtest(factor_expression: str,
                        factor_name: str = None,
                        rebalance_freq: str = 'M',
                        n_stocks: int = 100,
                        ascending: bool = False,
                        generate_plots: bool = True,
                        use_existing_data: bool = False,
                        neutralize: bool = True,
                        industry_neutral: bool = True,
                        forward_fill_factor: bool = True) -> dict:
    """
    运行因子回测
    
    Parameters:
    -----------
    factor_expression : str
        因子表达式，如 '1 / PE', 'ROE', 'rank(1 / PE)' 等
    factor_name : str, optional
        因子名称，用于保存结果
    rebalance_freq : str, default 'M'
        调仓频率 ('D', 'W', 'M', 'Q', 'Y')
    n_stocks : int, default 100
        模拟股票数量
    ascending : bool, default False
        因子排序方向 (True: 从小到大, False: 从大到小)
    generate_plots : bool, default True
        是否生成图表
    use_existing_data : bool, default False
        是否使用已存在的数据
    
    Returns:
    --------
    dict
        包含回测结果和分析报告的字典
    """
    if factor_name is None:
        factor_name = factor_expression.replace('/', '_').replace(' ', '')
    
    print("=" * 80)
    print(f"开始因子回测: {factor_expression}")
    print("=" * 80)
    
    print("\n[1/5] 加载数据...")
    loader = DataLoader()
    if not use_existing_data:
        loader.generate_sample_data(n_stocks=n_stocks)
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    print(f"数据加载完成: {price.shape[1]} 只股票, {price.shape[0]} 个交易日")
    if industry is not None:
        print(f"行业分布: {industry.nunique()} 个行业")
    
    print("\n[2/5] 计算因子值...")
    engine = FactorEngine(factors)
    try:
        factor_values = engine.calculate_factor(factor_expression)
        print(f"因子计算完成: {factor_expression}")
        print(f"  有效因子值比例: {(~factor_values.isnull()).mean().mean()*100:.2f}%")
        
        if forward_fill_factor:
            factor_values = loader.forward_fill_factor_for_suspend(factor_values)
            print(f"  停牌因子值向前填充完成")
    except Exception as e:
        print(f"因子计算失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    print("\n[3/5] 运行分层回测...")
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    backtest_results = backtest.run_backtest(
        factor_df=factor_values,
        rebalance_freq=rebalance_freq,
        ascending=ascending,
        weighting='equal',
        neutralize=neutralize,
        industry_neutral=industry_neutral
    )
    print("回测完成")
    
    print("\n[4/5] 绩效分析...")
    analyzer = PerformanceAnalyzer()
    report = analyzer.generate_report(backtest_results, factor_values, returns)
    analyzer.print_report(report, factor_name)
    
    print("\n[5/5] 生成可视化图表...")
    if generate_plots:
        visualizer = Visualizer()
        visualizer.generate_all_plots(backtest_results, report, factor_name)
    
    print("\n" + "=" * 80)
    print("回测完成!")
    print("=" * 80)
    
    return {
        'factor_expression': factor_expression,
        'factor_name': factor_name,
        'factor_values': factor_values,
        'backtest_results': backtest_results,
        'performance_report': report
    }


def run_multiple_factors(factor_configs: list, **kwargs) -> list:
    """
    批量运行多个因子回测
    
    Parameters:
    -----------
    factor_configs : list
        因子配置列表，每个元素是一个字典包含 'expression' 和 'name'
    **kwargs :
        传递给 run_factor_backtest 的其他参数
    
    Returns:
    --------
    list
        回测结果列表
    """
    results = []
    for i, config in enumerate(factor_configs):
        print(f"\n\n{'#' * 80}")
        print(f"# 因子 {i+1}/{len(factor_configs)}: {config['name']}")
        print(f"{'#' * 80}")
        
        result = run_factor_backtest(
            factor_expression=config['expression'],
            factor_name=config['name'],
            **kwargs
        )
        results.append(result)
    
    return results


def interactive_mode():
    """交互模式 - 用户输入因子表达式"""
    print("=" * 80)
    print("股票因子回测平台 - 交互模式")
    print("=" * 80)
    
    print("\n可用的基础因子:")
    print("  - PE: 市盈率")
    print("  - PB: 市净率")
    print("  - ROE: 净资产收益率")
    print("  - MKT_CAP: 市值")
    
    print("\n可用的因子函数:")
    print("  - rank(x): 排序(百分位)")
    print("  - zscore(x): 标准化")
    print("  - log(x): 取对数")
    print("  - abs(x): 绝对值")
    print("  - sqrt(x): 平方根")
    print("  - mean(x, window): 移动平均")
    print("  - std(x, window): 移动标准差")
    print("  - delta(x, period): 差分")
    print("  - pct_change(x, period): 变化率")
    
    print("\n表达式示例:")
    print("  - '1 / PE' (EP因子)")
    print("  - 'ROE'")
    print("  - 'rank(1 / PE)'")
    print("  - 'delta(ROE, 20)' (ROE变化率)")
    print("  - 'zscore(1 / PE) + zscore(ROE)' (复合因子)")
    
    while True:
        print("\n" + "-" * 80)
        expression = input("\n请输入因子表达式 (输入 'q' 退出): ").strip()
        
        if expression.lower() == 'q':
            print("退出程序")
            break
        
        if not expression:
            continue
        
        try:
            run_factor_backtest(
                factor_expression=expression,
                rebalance_freq='M',
                n_stocks=100,
                ascending=False,
                generate_plots=True,
                use_existing_data=True,
                neutralize=True,
                industry_neutral=True,
                forward_fill_factor=True
            )
        except Exception as e:
            print(f"回测出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        cont = input("\n是否继续测试其他因子? (y/n): ").strip().lower()
        if cont != 'y':
            break


def demo_mode():
    """演示模式 - 运行预定义的因子回测"""
    print("=" * 80)
    print("股票因子回测平台 - 演示模式")
    print("=" * 80)
    
    factor_configs = [
        {'expression': '1 / PE', 'name': 'EP'},
        {'expression': 'ROE', 'name': 'ROE'},
        {'expression': 'rank(1 / PE)', 'name': 'EP_Rank'},
        {'expression': 'delta(ROE, 20)', 'name': 'ROE_Change'},
        {'expression': '1 / PB', 'name': 'BP'},
    ]
    
    results = run_multiple_factors(
        factor_configs,
        rebalance_freq='M',
        n_stocks=100,
        ascending=False,
        generate_plots=True,
        use_existing_data=False
    )
    
    print("\n" + "=" * 80)
    print("所有因子回测完成!")
    print("结果保存在 results/ 目录下")
    print("=" * 80)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='股票因子回测平台 - 支持因子表达式输入、分层回测、绩效分析和可视化'
    )
    
    parser.add_argument(
        '--mode', '-m',
        type=str,
        choices=['interactive', 'demo', 'single', 'genetic', 'simtrade', 'attribution'],
        default='demo',
        help='运行模式: interactive(交互), demo(演示), single(单因子), genetic(遗传挖掘), simtrade(模拟交易), attribution(归因分析)'
    )
    
    parser.add_argument(
        '--factor', '-f',
        type=str,
        default='1 / PE',
        help='单因子模式下的因子表达式'
    )
    
    parser.add_argument(
        '--name', '-n',
        type=str,
        default=None,
        help='因子名称'
    )
    
    parser.add_argument(
        '--rebalance', '-r',
        type=str,
        default='M',
        help='调仓频率 (D, W, M, Q, Y)'
    )
    
    parser.add_argument(
        '--stocks', '-s',
        type=int,
        default=100,
        help='模拟股票数量'
    )
    
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='不生成图表'
    )
    
    parser.add_argument(
        '--no-neutralize',
        action='store_true',
        help='关闭行业市值中性化'
    )
    
    parser.add_argument(
        '--no-industry-neutral',
        action='store_true',
        help='关闭行业中性分组'
    )
    
    parser.add_argument(
        '--no-forward-fill',
        action='store_true',
        help='关闭停牌因子值向前填充'
    )
    
    parser.add_argument(
        '--population',
        type=int,
        default=30,
        help='遗传编程种群大小'
    )
    
    parser.add_argument(
        '--generations',
        type=int,
        default=5,
        help='遗传编程最大迭代次数'
    )
    
    parser.add_argument(
        '--speed',
        type=float,
        default=2.0,
        help='模拟交易速度倍率'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        interactive_mode()
    elif args.mode == 'demo':
        demo_mode()
    elif args.mode == 'single':
        run_factor_backtest(
            factor_expression=args.factor,
            factor_name=args.name,
            rebalance_freq=args.rebalance,
            n_stocks=args.stocks,
            ascending=False,
            generate_plots=not args.no_plots,
            use_existing_data=False,
            neutralize=not args.no_neutralize,
            industry_neutral=not args.no_industry_neutral,
            forward_fill_factor=not args.no_forward_fill
        )
    elif args.mode == 'genetic':
        run_genetic_mining(
            n_stocks=args.stocks,
            population_size=args.population,
            max_generations=args.generations
        )
    elif args.mode == 'simtrade':
        run_simulated_trading(
            factor_expression=args.factor,
            factor_name=args.name or 'Sim_Factor',
            speed=args.speed
        )
    elif args.mode == 'attribution':
        run_attribution_analysis(
            factor_expression=args.factor,
            factor_name=args.name or 'Attr_Factor'
        )


if __name__ == '__main__':
    main()
