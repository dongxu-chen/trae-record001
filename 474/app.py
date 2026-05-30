import streamlit as st
import pandas as pd
import numpy as np
import time
import random
import plotly.graph_objects as go
from warehouse import (Warehouse, generate_sample_products, generate_sample_orders,
                      SeasonalityAnalyzer, SeasonalityType, ABCClass, ZoneType)
from ga_optimizer import WarehouseOptimizer
from path_simulator import PathSimulator, PeakHourSimulator
from visualizer_3d import WarehouseVisualizer, LODSettings
from animation import PickingPathAnimator, ComparisonAnimator

st.set_page_config(
    page_title="仓库货位分配优化系统 - 智能版",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    if 'warehouse' not in st.session_state:
        st.session_state.warehouse = None
    if 'optimizer' not in st.session_state:
        st.session_state.optimizer = None
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = None
    if 'path_simulator' not in st.session_state:
        st.session_state.path_simulator = None
    if 'peak_simulator' not in st.session_state:
        st.session_state.peak_simulator = None
    if 'seasonality_analyzer' not in st.session_state:
        st.session_state.seasonality_analyzer = None
    if 'products_df' not in st.session_state:
        st.session_state.products_df = None
    if 'orders_df' not in st.session_state:
        st.session_state.orders_df = None
    if 'assignments' not in st.session_state:
        st.session_state.assignments = {}
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    if 'peak_comparison_results' not in st.session_state:
        st.session_state.peak_comparison_results = None
    if 'logbook' not in st.session_state:
        st.session_state.logbook = None
    if 'optimization_done' not in st.session_state:
        st.session_state.optimization_done = False
    if 'seasonality_analyzed' not in st.session_state:
        st.session_state.seasonality_analyzed = False
    if 'current_month' not in st.session_state:
        st.session_state.current_month = 1
    if 'abc_analyzed' not in st.session_state:
        st.session_state.abc_analyzed = False
    if 'animation_result' not in st.session_state:
        st.session_state.animation_result = None
    if 'comparison_animation_result' not in st.session_state:
        st.session_state.comparison_animation_result = None
    if 'last_reoptimization_time' not in st.session_state:
        st.session_state.last_reoptimization_time = None

def main():
    init_session_state()

    st.title("📦 仓库货位分配优化系统 - 高级版")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ 系统设置")

        st.subheader("仓库配置")
        num_aisles = st.slider("通道数量", 2, 8, 4)
        bays_per_aisle = st.slider("每通道货位数", 5, 20, 10)
        levels = st.slider("层数", 2, 5, 3)

        st.subheader("商品配置")
        num_products = st.slider("商品数量", 10, 100, 50)
        num_orders = st.slider("订单数量", 50, 500, 200)

        st.subheader("季节性设置")
        current_month = st.select_slider(
            "当前月份",
            options=list(range(1, 13)),
            format_func=lambda x: f"{x}月",
            value=st.session_state.current_month
        )
        st.session_state.current_month = current_month

        st.subheader("遗传算法参数")
        population_size = st.slider("种群大小", 20, 200, 50)
        generations = st.slider("迭代次数", 20, 300, 100)
        cxpb = st.slider("交叉概率", 0.1, 1.0, 0.7)
        mutpb = st.slider("变异概率", 0.01, 0.5, 0.2)

        st.subheader("优化权重")
        weight_turnover = st.slider("周转率权重", 0.0, 1.0, 0.3)
        weight_correlation = st.slider("相关性权重", 0.0, 1.0, 0.2)
        weight_distance = st.slider("距离权重", 0.0, 1.0, 0.2)
        weight_seasonality = st.slider("季节性权重", 0.0, 1.0, 0.15)
        weight_abc_zone = st.slider("ABC区域权重", 0.0, 1.0, 0.15)

        total_weight = weight_turnover + weight_correlation + weight_distance + weight_seasonality + weight_abc_zone
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"权重总和为 {total_weight:.2f}，建议总和为 1.0")

        enforce_abc = st.checkbox("强制ABC分类约束", value=True)

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("初始化数据", use_container_width=True):
                initialize_data(num_aisles, bays_per_aisle, levels, num_products, num_orders, current_month)
        with col2:
            if st.button("运行优化", use_container_width=True, type="primary"):
                if st.session_state.optimizer is None:
                    st.error("请先初始化数据！")
                else:
                    run_optimization(population_size, generations, cxpb, mutpb,
                                   weight_turnover, weight_correlation, weight_distance, weight_seasonality, weight_abc_zone,
                                   current_month, enforce_abc)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 数据概览",
        "🏷️ ABC分类",
        "📈 季节性分析",
        "🏗️ 货位布局",
        "🧬 优化结果",
        "🚚 拣货路径",
        "⏰ 高峰时段模拟",
        "� 动态调整",
        "🎬 仿真动画",
        "� 效果对比"
    ])

    with tab1:
        show_data_overview()
    with tab2:
        show_abc_analysis()
    with tab3:
        show_seasonality_analysis()
    with tab4:
        show_warehouse_layout()
    with tab5:
        show_optimization_results()
    with tab6:
        show_picking_path()
    with tab7:
        show_peak_hour_simulation()
    with tab8:
        show_dynamic_adjustment()
    with tab9:
        show_animation()
    with tab10:
        show_comparison()

def initialize_data(num_aisles, bays_per_aisle, levels, num_products, num_orders, current_month):
    with st.spinner("正在生成数据..."):
        warehouse = Warehouse(num_aisles, bays_per_aisle, levels)
        products_df = generate_sample_products(num_products)
        warehouse.add_products_from_dataframe(products_df)

        orders_df = generate_sample_orders(num_orders, list(products_df['product_id']))
        warehouse.generate_correlation_matrix(orders_df)

        seasonality_analyzer = SeasonalityAnalyzer(warehouse)
        seasonality_analyzer.analyze_all_products(num_days=365)

        warehouse.abc_analyzer.perform_abc_analysis()

        optimizer = WarehouseOptimizer(warehouse, current_season=current_month)
        visualizer = WarehouseVisualizer(warehouse)
        path_simulator = PathSimulator(warehouse)
        peak_simulator = PeakHourSimulator(warehouse)

        random_assignment = optimizer.generate_random_assignment()
        turnover_assignment = optimizer.generate_turnover_based_assignment()

        st.session_state.warehouse = warehouse
        st.session_state.optimizer = optimizer
        st.session_state.visualizer = visualizer
        st.session_state.path_simulator = path_simulator
        st.session_state.peak_simulator = peak_simulator
        st.session_state.seasonality_analyzer = seasonality_analyzer
        st.session_state.products_df = products_df
        st.session_state.orders_df = orders_df
        st.session_state.assignments = {
            '随机分配': random_assignment,
            '周转率优先': turnover_assignment
        }
        st.session_state.optimization_done = False
        st.session_state.seasonality_analyzed = True
        st.session_state.abc_analyzed = True
        st.session_state.animation_result = None
        st.session_state.comparison_animation_result = None
        st.session_state.last_reoptimization_time = pd.Timestamp.now()

        st.success("数据初始化成功！已完成季节性分析和ABC分类。")
        st.balloons()

def run_optimization(population_size, generations, cxpb, mutpb,
                     weight_turnover, weight_correlation, weight_distance, weight_seasonality, weight_abc_zone,
                     current_month, enforce_abc):
    with st.spinner("遗传算法优化中..."):
        optimizer = st.session_state.optimizer
        optimizer.weight_turnover = weight_turnover
        optimizer.weight_correlation = weight_correlation
        optimizer.weight_distance = weight_distance
        optimizer.weight_seasonality = weight_seasonality
        optimizer.weight_abc_zone = weight_abc_zone
        optimizer.current_season = current_month
        optimizer.enforce_abc_constraints = enforce_abc

        best_assignment, logbook, pop = optimizer.optimize(
            population_size=population_size,
            generations=generations,
            cxpb=cxpb,
            mutpb=mutpb,
            verbose=False
        )

        st.session_state.assignments['遗传算法优化'] = best_assignment
        st.session_state.logbook = logbook
        st.session_state.optimization_done = True
        st.session_state.comparison_results = None
        st.session_state.peak_comparison_results = None
        st.session_state.last_reoptimization_time = pd.Timestamp.now()

        st.success("优化完成！")

def show_data_overview():
    st.header("📊 数据概览")

    if st.session_state.products_df is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("仓库货位数", len(st.session_state.warehouse.locations))
    with col2:
        st.metric("商品数量", len(st.session_state.products_df))
    with col3:
        st.metric("订单数量", st.session_state.orders_df['order_id'].nunique())
    with col4:
        st.metric("平均订单商品数",
                 f"{st.session_state.orders_df.groupby('order_id').size().mean():.1f}")

    st.subheader("商品数据")
    products_display = st.session_state.products_df.copy()
    if st.session_state.seasonality_analyzed:
        seasonal_info = []
        for prod_id in products_display['product_id']:
            pattern = st.session_state.seasonality_analyzer.product_seasonality.get(prod_id)
            if pattern:
                seasonal_info.append({
                    'product_id': prod_id,
                    '季节性类型': pattern.seasonality_type.value,
                    '季节强度': f"{pattern.seasonality_strength:.2f}",
                    '峰值月份': ','.join(map(str, pattern.peak_seasons))
                })
        seasonal_df = pd.DataFrame(seasonal_info)
        products_display = pd.merge(products_display, seasonal_df, on='product_id', how='left')

    st.dataframe(
        products_display.style.format({
            'width': '{:.2f}',
            'depth': '{:.2f}',
            'height': '{:.2f}',
            'weight': '{:.2f}',
            'turnover_rate': '{:.2f}'
        }),
        use_container_width=True,
        height=300
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("商品分类分布")
        category_counts = st.session_state.products_df['category'].value_counts()
        st.bar_chart(category_counts)

    with col2:
        st.subheader("季节性类型分布")
        if st.session_state.seasonality_analyzed:
            fig = st.session_state.visualizer.create_seasonality_distribution_chart(
                st.session_state.assignments.get('随机分配', {})
            )
            st.plotly_chart(fig, use_container_width=True)

def show_seasonality_analysis():
    st.header("📈 季节性分析")

    if not st.session_state.seasonality_analyzed:
        st.info("请先在侧边栏点击「初始化数据」进行季节性分析")
        return

    st.subheader(f"当前月份: {st.session_state.current_month}月")

    recommendations = st.session_state.seasonality_analyzer.get_seasonal_recommendations(
        st.session_state.current_month
    )

    if recommendations:
        st.warning(f"⚠️ 发现 {len(recommendations)} 个商品需要根据季节性调整货位")
        rec_df = pd.DataFrame(recommendations, columns=['商品ID', '建议动作', '季节权重'])
        st.dataframe(rec_df, use_container_width=True)
    else:
        st.success("✅ 当前月份无需调整货位")

    st.subheader("时间序列分解示例")
    sample_product = random.choice(list(st.session_state.warehouse.products.keys()))
    prod = st.session_state.warehouse.products[sample_product]

    daily_sales = st.session_state.seasonality_analyzer._generate_synthetic_sales(sample_product, 365)
    decomposition = st.session_state.seasonality_analyzer.decomposer.decompose(daily_sales)

    fig_decomp = st.session_state.visualizer.create_time_series_decomposition_plot(
        daily_sales.values,
        decomposition['trend'],
        decomposition['seasonal'],
        title=f"商品 {prod.name} - 销售时间序列分解"
    )
    st.plotly_chart(fig_decomp, use_container_width=True)

    pattern = st.session_state.seasonality_analyzer.product_seasonality.get(sample_product)
    if pattern:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("季节性类型", pattern.seasonality_type.value)
        with col2:
            st.metric("季节强度", f"{pattern.seasonality_strength:.2f}")
        with col3:
            st.metric("峰值月份", ','.join(map(str, pattern.peak_seasons)))
        with col4:
            st.metric("置信度", f"{pattern.confidence_score:.2f}")

    st.subheader("季节性商品分布3D视图")
    assignment = st.session_state.assignments.get('遗传算法优化',
                              st.session_state.assignments.get('随机分配', {}))
    fig_seasonal = st.session_state.visualizer.create_seasonality_3d_plot(
        assignment,
        current_month=st.session_state.current_month,
        title="季节性商品分布"
    )
    st.plotly_chart(fig_seasonal, use_container_width=True)

def show_warehouse_layout():
    st.header("🏗️ 仓库货位布局")

    if st.session_state.visualizer is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.subheader("选择分配策略")
        strategy = st.radio(
            "货位分配策略",
            list(st.session_state.assignments.keys())
        )

    with col2:
        st.subheader("渲染模式")
        render_mode = st.radio(
            "渲染模式",
            ['标准渲染', 'LOD层级渲染']
        )

    assignment = st.session_state.assignments.get(strategy, {})

    with col3:
        if render_mode == 'LOD层级渲染':
            st.subheader("LOD设置")
            near_threshold = st.slider("近距离阈值", 5.0, 20.0, 10.0)
            medium_threshold = st.slider("中距离阈值", 15.0, 40.0, 25.0)
            st.session_state.visualizer.lod_renderer.settings.distance_threshold_near = near_threshold
            st.session_state.visualizer.lod_renderer.settings.distance_threshold_medium = medium_threshold

    if render_mode == 'LOD层级渲染':
        fig = st.session_state.visualizer.create_3d_warehouse_lod_plot(
            assignment,
            title=f"仓库货位布局 (LOD) - {strategy}"
        )
        st.info("💡 LOD渲染: 近处显示详细立方体，中距离显示圆形，远处显示简化方框")
    else:
        fig = st.session_state.visualizer.create_3d_warehouse_plot(
            assignment,
            title=f"仓库货位布局 - {strategy}"
        )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("周转率热力图")
    fig_heatmap = st.session_state.visualizer.create_turnover_heatmap(
        assignment,
        title=f"货位周转率热力图 - {strategy}"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.subheader("货位分配详情")
    if assignment:
        assignment_data = []
        for prod_id, loc_id in assignment.items():
            prod = st.session_state.warehouse.products[prod_id]
            loc = st.session_state.warehouse.locations[loc_id]
            seasonal_type = prod.seasonal_pattern.seasonality_type.value if prod.seasonal_pattern else "无"
            assignment_data.append({
                '商品ID': prod_id,
                '商品名称': prod.name,
                '分类': prod.category,
                '季节性': seasonal_type,
                '周转率': prod.turnover_rate,
                '货位ID': loc_id,
                '通道': loc.aisle,
                '货位': loc.bay,
                '层': loc.level
            })

        df = pd.DataFrame(assignment_data)
        st.dataframe(
            df.sort_values('周转率', ascending=False).style.format({'周转率': '{:.2f}'}),
            use_container_width=True,
            height=400
        )

def show_optimization_results():
    st.header("🧬 遗传算法优化结果")

    if not st.session_state.optimization_done:
        st.info("请先在侧边栏点击「运行优化」")
        return

    st.subheader("算法收敛曲线")
    fig_convergence = st.session_state.visualizer.create_ga_convergence_plot(
        st.session_state.logbook
    )
    st.plotly_chart(fig_convergence, use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        final_fitness = st.session_state.logbook.select("max")[-1]
        st.metric("最终适应度", f"{final_fitness:.4f}")

    with col2:
        initial_fitness = st.session_state.logbook.select("max")[0]
        improvement = (final_fitness - initial_fitness) / initial_fitness * 100
        st.metric("适应度提升", f"{improvement:.1f}%")

    with col3:
        generations = len(st.session_state.logbook)
        st.metric("迭代次数", generations)

    st.subheader("优化后货位布局 (LOD渲染)")
    optimized_assignment = st.session_state.assignments.get('遗传算法优化', {})
    fig_opt = st.session_state.visualizer.create_3d_warehouse_lod_plot(
        optimized_assignment,
        title="遗传算法优化后的货位布局 (LOD)"
    )
    st.plotly_chart(fig_opt, use_container_width=True)

    st.subheader("进化统计信息")
    stats_df = pd.DataFrame(st.session_state.logbook)
    st.dataframe(
        stats_df.style.format({
            'avg': '{:.4f}',
            'std': '{:.4f}',
            'min': '{:.4f}',
            'max': '{:.4f}'
        }),
        use_container_width=True,
        height=300
    )

def show_picking_path():
    st.header("🚚 拣货路径模拟")

    if st.session_state.path_simulator is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        strategy = st.selectbox(
            "选择货位分配策略",
            list(st.session_state.assignments.keys())
        )

    with col2:
        path_method = st.selectbox(
            "选择路径规划算法",
            ['nearest_neighbor', 'tsp_2opt', 's_shape'],
            format_func=lambda x: {
                'nearest_neighbor': '最近邻居法',
                'tsp_2opt': 'TSP 2-opt 优化',
                's_shape': 'S型路径'
            }[x]
        )

    with col3:
        num_items = st.slider("订单商品数量", 3, 15, 8)

    assignment = st.session_state.assignments.get(strategy, {})

    product_ids = list(assignment.keys())
    if product_ids:
        order_items = random.sample(product_ids, min(num_items, len(product_ids)))

        picking_path = st.session_state.path_simulator.get_picking_path(
            assignment, order_items, method=path_method
        )

        col1, col2 = st.columns([3, 1])

        with col1:
            fig_path = st.session_state.visualizer.create_picking_path_plot(
                picking_path,
                title=f"拣货路径 - {strategy} - {path_method}"
            )
            st.plotly_chart(fig_path, use_container_width=True)

        with col2:
            st.subheader("路径详情")
            st.metric("总距离", f"{picking_path.total_distance:.2f} m")
            st.metric("商品数量", len(picking_path.items))

            st.write("拣货顺序:")
            for i, item in enumerate(picking_path.item_sequence, 1):
                prod = st.session_state.warehouse.products[item]
                seasonal = prod.seasonal_pattern.seasonality_type.value if prod.seasonal_pattern else ""
                st.write(f"{i}. {prod.name} ({seasonal})")

        if st.button("生成新订单", use_container_width=True):
            st.rerun()

def show_peak_hour_simulation():
    st.header("⏰ 高峰时段模拟")

    if st.session_state.peak_simulator is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    st.subheader("24小时订单强度模式")
    hourly_pattern = pd.DataFrame([
        {'hour': h,
         'is_peak': ts.is_peak,
         'intensity': ts.order_intensity,
         'avg_items': ts.avg_items_per_order,
         'congestion': ts.congestion_factor}
        for h, ts in st.session_state.peak_simulator.hourly_pattern.items()
    ])

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=[hourly_pattern['intensity']],
        x=hourly_pattern['hour'],
        y=['订单强度'],
        colorscale='Reds',
        showscale=True
    ))
    fig_heatmap.update_layout(
        title="24小时订单强度热力图",
        xaxis_title="小时",
        height=200
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.subheader("策略对比")
    strategy = st.selectbox(
        "选择货位分配策略进行高峰时段测试",
        list(st.session_state.assignments.keys()),
        key="peak_strategy"
    )

    assignment = st.session_state.assignments.get(strategy, {})

    if st.button("运行高峰时段模拟", use_container_width=True, type="primary"):
        with st.spinner("模拟中..."):
            hourly_results = st.session_state.peak_simulator.simulate_day_simulation(
                assignment, orders_per_hour=50
            )
            st.session_state.hourly_results = hourly_results

    if 'hourly_results' in st.session_state:
        hourly_data = pd.DataFrame([
            {
                'hour': h,
                'is_peak': '高峰' if r['is_peak'] else '平峰',
                'mean_distance': r['mean_distance'],
                'total_distance': r['total_distance'],
                'congestion_factor': r['congestion_factor']
            }
            for h, r in st.session_state.hourly_results.items()
        ])

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("各时段平均拣货距离")
            fig_bar = go.Figure()
            colors = ['red' if peak else 'blue' for peak in hourly_data['is_peak'] == '高峰']
            fig_bar.add_trace(go.Bar(
                x=hourly_data['hour'],
                y=hourly_data['mean_distance'],
                marker_color=colors,
                name='平均距离'
            ))
            fig_bar.update_layout(
                xaxis_title="小时",
                yaxis_title="平均距离 (m)",
                height=400
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.subheader("高峰 vs 平峰对比")
            peak_compare = st.session_state.peak_simulator.compare_peak_vs_normal(
                assignment, orders_per_hour=100
            )

            comparison_df = pd.DataFrame({
                '指标': ['平均距离(m)', '总距离(m)', '订单数'],
                '高峰时段': [
                    f"{peak_compare['peak']['mean']:.2f}",
                    f"{peak_compare['peak']['total']:.1f}",
                    peak_compare['peak']['count']
                ],
                '平峰时段': [
                    f"{peak_compare['normal']['mean']:.2f}",
                    f"{peak_compare['normal']['total']:.1f}",
                    peak_compare['normal']['count']
                ]
            })
            st.table(comparison_df.set_index('指标'))

            peak_increase = (peak_compare['peak']['mean'] - peak_compare['normal']['mean']) / peak_compare['normal']['mean'] * 100
            st.metric(
                "高峰时段距离增加",
                f"{peak_increase:.1f}%"
            )

    st.subheader("多策略高峰时段对比")
    if len(st.session_state.assignments) >= 2:
        if st.button("计算所有策略的高峰表现", use_container_width=True):
            with st.spinner("计算中..."):
                peak_results = st.session_state.peak_simulator.compare_assignments_peak_hours(
                    st.session_state.assignments, orders_per_hour=100
                )
                st.session_state.peak_comparison_results = peak_results

        if st.session_state.peak_comparison_results:
            peak_data = []
            for name, result in st.session_state.peak_comparison_results.items():
                peak_data.append({
                    '策略': name,
                    '高峰平均距离(m)': f"{result['peak']['mean']:.2f}",
                    '平峰平均距离(m)': f"{result['normal']['mean']:.2f}",
                    '高峰增长%': f"{(result['peak']['mean']/result['normal']['mean']-1)*100:.1f}%"
                })

            st.table(pd.DataFrame(peak_data).set_index('策略'))

def show_comparison():
    st.header("📈 优化效果对比")

    if st.session_state.path_simulator is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    if len(st.session_state.assignments) < 2:
        st.info("请运行优化以生成对比数据")
        return

    if st.session_state.comparison_results is None:
        with st.spinner("计算对比结果..."):
            comparison_results = st.session_state.path_simulator.compare_assignments(
                st.session_state.assignments,
                num_orders=100,
                strategy='nearest_neighbor'
            )
            st.session_state.comparison_results = comparison_results

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("平均拣货距离对比")
        fig_bar = st.session_state.visualizer.create_comparison_bar_chart(
            st.session_state.comparison_results
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("拣货距离分布")
        fig_box = st.session_state.visualizer.create_boxplot_comparison(
            st.session_state.comparison_results
        )
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("详细统计对比")

    comparison_data = []
    for name, data in st.session_state.comparison_results.items():
        comparison_data.append({
            '分配策略': name,
            '平均距离 (m)': f"{data['mean_distance']:.2f}",
            '标准差 (m)': f"{data['std_distance']:.2f}",
            '最短距离 (m)': f"{data['min_distance']:.2f}",
            '最长距离 (m)': f"{data['max_distance']:.2f}",
            '总距离 (m)': f"{data['total_distance']:.2f}"
        })

    st.table(pd.DataFrame(comparison_data).set_index('分配策略'))

    if st.session_state.optimization_done:
        st.subheader("优化效果分析")

        baseline = st.session_state.comparison_results.get('随机分配', {})
        optimized = st.session_state.comparison_results.get('遗传算法优化', {})
        turnover = st.session_state.comparison_results.get('周转率优先', {})

        if baseline and optimized:
            metrics = st.session_state.path_simulator.get_comparison_metrics(
                baseline, optimized
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "相比随机分配",
                    f"{metrics['mean_distance']['reduction_percent']:.1f}%",
                    delta=f"减少 {metrics['mean_distance']['reduction']:.2f}m"
                )

            with col2:
                if turnover:
                    metrics_turnover = st.session_state.path_simulator.get_comparison_metrics(
                        turnover, optimized
                    )
                    st.metric(
                        "相比周转率优先",
                        f"{metrics_turnover['mean_distance']['reduction_percent']:.1f}%",
                        delta=f"减少 {metrics_turnover['mean_distance']['reduction']:.2f}m"
                    )

            with col3:
                total_saving = baseline.get('total_distance', 0) - optimized.get('total_distance', 0)
                st.metric(
                    "100单总节省距离",
                    f"{total_saving:.1f}m",
                    delta="效率提升"
                )

    if st.button("重新计算对比", use_container_width=True):
        st.session_state.comparison_results = None
        st.session_state.peak_comparison_results = None

def show_abc_analysis():
    st.header("🏷️ ABC分类分析")

    if not st.session_state.abc_analyzed:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    abc_results = st.session_state.warehouse.abc_analyzer.abc_results
    abc_stats = st.session_state.warehouse.abc_analyzer.get_class_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        a_stats = abc_stats.get('A类 (高周转)', {})
        st.metric(
            "A类商品 (高周转)",
            f"{a_stats.get('count', 0)} 个",
            f"{a_stats.get('percent', 0):.1f}%"
        )

    with col2:
        b_stats = abc_stats.get('B类 (中周转)', {})
        st.metric(
            "B类商品 (中周转)",
            f"{b_stats.get('count', 0)} 个",
            f"{b_stats.get('percent', 0):.1f}%"
        )

    with col3:
        c_stats = abc_stats.get('C类 (低周转)', {})
        st.metric(
            "C类商品 (低周转)",
            f"{c_stats.get('count', 0)} 个",
            f"{c_stats.get('percent', 0):.1f}%"
        )

    st.subheader("ABC帕累托分布")
    abc_df = pd.DataFrame([
        {
            'product_id': r.product_id,
            '周转频率': r.turnover_rate,
            '累计百分比': r.cumulative_percent,
            '年需求量': int(r.annual_demand),
            'ABC分类': r.abc_class.value
        }
        for r in abc_results.values()
    ])
    abc_df = abc_df.sort_values('周转频率', ascending=False).reset_index(drop=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=abc_df.index,
        y=abc_df['周转频率'],
        name='周转频率',
        marker_color=abc_df['ABC分类'].map({
            'A类 (高周转)': '#FF6B6B',
            'B类 (中周转)': '#FFD93D',
            'C类 (低周转)': '#6BCB77'
        })
    ))
    fig.add_trace(go.Scatter(
        x=abc_df.index,
        y=abc_df['累计百分比'],
        name='累计百分比',
        yaxis='y2',
        mode='lines',
        line=dict(color='#4D96FF', width=3)
    ))
    fig.update_layout(
        title='ABC分类帕累托图',
        xaxis_title='商品排序 (按周转频率)',
        yaxis_title='周转频率',
        yaxis2=dict(
            title='累计百分比 (%)',
            overlaying='y',
            side='right',
            range=[0, 105]
        ),
        height=500,
        barmode='group',
        bargap=0.1
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("货位区域分布")
    zone_counts = {}
    for zone in ZoneType:
        zone_counts[zone.value] = len(st.session_state.warehouse.get_locations_by_zone(zone))

    fig_zone = go.Figure(data=[go.Pie(
        labels=list(zone_counts.keys()),
        values=list(zone_counts.values()),
        hole=0.4,
        marker_colors=['#FFD700', '#C0C0C0', '#CD7F32', '#E8E8E8']
    )])
    fig_zone.update_layout(title='仓库区域分布')
    st.plotly_chart(fig_zone, use_container_width=True)

    st.subheader("ABC分类详情")
    st.dataframe(
        abc_df.style.format({
            '周转频率': '{:.3f}',
            '累计百分比': '{:.1f}%'
        }).background_gradient(subset=['周转频率'], cmap='Reds'),
        use_container_width=True
    )

def show_dynamic_adjustment():
    st.header("🔄 动态货位调整")

    if st.session_state.warehouse is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    st.subheader("模式变化检测")

    col1, col2 = st.columns(2)
    with col1:
        current_intensity = st.slider("当前订单强度", 0.5, 3.0, 1.0, 0.1,
                                     help="1.0为正常强度，2.0为高峰强度")
        test_month = st.selectbox("模拟月份", list(range(1, 13)),
                                format_func=lambda x: f"{x}月")
    with col2:
        pattern_similarity = st.slider("订单模式相似度", 0.5, 1.0, 0.9, 0.05,
                                      help="1.0为完全相同，低于0.75视为模式变化")
        reopt_interval = st.number_input("重优化间隔 (小时)", 1, 168, 24)

    should_change, triggers = st.session_state.warehouse.dynamic_manager.detect_mode_change(
        current_intensity, test_month, pattern_similarity
    )

    st.markdown("---")

    if should_change:
        trigger_names = {
            'peak_demand': '🚨 高峰需求',
            'seasonal_change': '📅 季节变化',
            'pattern_shift': '🔄 模式偏移'
        }
        trigger_descs = [trigger_names.get(t, t) for t in triggers]
        st.warning(f"**检测到模式变化！** 触发原因: {', '.join(trigger_descs)}")
    else:
        st.success("✅ 当前模式稳定，无需紧急重优化")

    should_reopt = st.session_state.warehouse.dynamic_manager.should_reoptimize(reopt_interval)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.last_reoptimization_time:
            time_since = (pd.Timestamp.now() - st.session_state.last_reoptimization_time).total_seconds() / 3600
            st.metric("距上次优化", f"{time_since:.1f} 小时")
        else:
            st.metric("距上次优化", "-")
    with col2:
        st.metric("是否需要重优化", "是" if should_reopt else "否")
    with col3:
        st.metric("历史模式记录", f"{len(st.session_state.warehouse.dynamic_manager.mode_history)} 条")

    st.markdown("---")
    st.subheader("货位调整建议")

    if st.session_state.seasonality_analyzed and st.session_state.abc_analyzed:
        recommendations = st.session_state.seasonality_analyzer.get_seasonal_recommendations(
            test_month
        )

        if recommendations:
            rec_df = pd.DataFrame(recommendations[:10], columns=['商品ID', '调整建议', '权重变化'])
            rec_df['权重变化'] = rec_df['权重变化'].apply(lambda x: f"{x:+.1%}")
            st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("当前月份无需特别调整")

    st.markdown("---")
    if st.button("执行动态重优化", type="primary", use_container_width=True):
        with st.spinner("执行动态优化..."):
            st.session_state.warehouse.dynamic_manager.record_optimization()
            best_assignment, logbook, pop = st.session_state.optimizer.optimize(
                population_size=50,
                generations=80,
                cxpb=0.7,
                mutpb=0.2,
                verbose=False
            )
            st.session_state.assignments['动态优化'] = best_assignment
            st.session_state.last_reoptimization_time = pd.Timestamp.now()
            st.success("动态优化完成！")

def show_animation():
    st.header("🎬 拣货路径仿真动画")

    if st.session_state.warehouse is None:
        st.info("请先在侧边栏点击「初始化数据」")
        return

    st.subheader("动画生成设置")

    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox(
            "选择分配策略",
            list(st.session_state.assignments.keys())
        )
        num_items = st.slider("订单商品数量", 3, 15, 8)
    with col2:
        fps = st.slider("动画帧率", 5, 20, 10)
        show_comparison = st.checkbox("生成优化对比动画", value=True)

    product_ids = list(st.session_state.warehouse.products.keys())
    if st.button("随机选择商品", use_container_width=True):
        st.session_state.selected_animation_items = random.sample(product_ids, num_items)

    if 'selected_animation_items' not in st.session_state:
        st.session_state.selected_animation_items = random.sample(product_ids, num_items)

    selected_items = st.multiselect(
        "选择订单商品",
        product_ids,
        default=st.session_state.selected_animation_items[:num_items]
    )

    if len(selected_items) < 3:
        st.warning("请至少选择3个商品")
        return

    if st.button("生成仿真动画", type="primary", use_container_width=True):
        with st.spinner("正在生成动画..."):
            animator = PickingPathAnimator(st.session_state.warehouse)
            result = animator.create_picking_animation(
                selected_items,
                st.session_state.assignments[strategy],
                title=f"{strategy} - 拣货路径仿真",
                output_path=f"picking_{strategy.lower().replace(' ', '_')}.gif",
                fps=fps
            )
            st.session_state.animation_result = result

            if show_comparison and '随机分配' in st.session_state.assignments and '遗传算法优化' in st.session_state.assignments:
                comp_animator = ComparisonAnimator(st.session_state.warehouse)
                comp_result = comp_animator.create_comparison_animation(
                    selected_items,
                    st.session_state.assignments['随机分配'],
                    st.session_state.assignments['遗传算法优化'],
                    output_path="comparison_animation.gif",
                    fps=fps
                )
                st.session_state.comparison_animation_result = comp_result

    if st.session_state.animation_result:
        st.markdown("---")
        st.subheader("📹 拣货路径仿真")
        st.markdown(st.session_state.animation_result.html_video, unsafe_allow_html=True)

    if st.session_state.comparison_animation_result:
        st.markdown("---")
        st.subheader("🎯 优化前后对比")
        st.markdown(st.session_state.comparison_animation_result.html_video, unsafe_allow_html=True)

    st.markdown("---")
    st.info("💡 **动画说明**: 红色圆点表示待拣货商品，绿色圆点表示已完成，蓝色圆点表示拣货员当前位置")

if __name__ == "__main__":
    main()
