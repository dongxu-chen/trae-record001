import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

from forecast_model import SalesForecaster, calculate_forecast_metrics, get_chinese_ecommerce_holidays
from inventory_optimization import (
    InventoryOptimizer, MultiEchelonInventoryOptimizer, 
    SupplierVariabilityAnalyzer, InventoryHealthScorer,
    LocationNode, SupplierDelivery
)
from simulation import (
    InventorySimulator, ScenarioConfig, ScenarioType,
    run_what_if_analysis, generate_scenario_comparison
)
from sample_data import get_full_sample_data
from utils import (
    format_number, format_currency, get_risk_color, get_risk_label,
    plot_forecast, plot_inventory_simulation, plot_stockout_risk,
    plot_newsvendor_curve, validate_dataframe, load_csv_upload,
    plot_scenario_comparison, plot_holiday_effects, plot_cost_optimization,
    plot_extreme_risk_analysis, plot_holiday_calendar,
    plot_multi_echelon_inventory, plot_supplier_variability,
    plot_safety_stock_adjustment, plot_inventory_health_gauge,
    plot_health_metrics, plot_transfer_plan
)

st.set_page_config(
    page_title="商品销量预测与库存优化系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 商品销量预测与库存优化系统")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 系统设置")
    
    st.subheader("📈 预测参数")
    forecast_days = st.slider("预测天数", 7, 365, 90, 7)
    changepoint_prior = st.slider("趋势敏感度", 0.01, 0.5, 0.05, 0.01)
    seasonality_prior = st.slider("季节敏感度", 1.0, 20.0, 10.0, 1.0)
    holidays_prior = st.slider("节假日敏感度", 1.0, 20.0, 10.0, 1.0)
    use_holidays = st.checkbox("启用自定义节假日", value=True)
    
    st.markdown("---")
    st.subheader("📦 库存参数")
    
    cost_price = st.number_input("成本价 (元)", 1.0, 1000.0, 50.0, 1.0)
    selling_price = st.number_input("销售价 (元)", 1.0, 2000.0, 120.0, 1.0)
    salvage_value = st.number_input("残值 (元)", 0.0, 500.0, 20.0, 1.0)
    service_level = st.slider("服务水平", 0.80, 0.99, 0.95, 0.01)
    lead_time_days = st.slider("供应链交期 (天)", 1, 30, 7, 1)
    initial_stock = st.number_input("当前库存", 0, 10000, 500, 10)
    
    st.markdown("---")
    st.subheader("🧪 仿真参数")
    num_simulations = st.slider("仿真次数", 50, 500, 100, 50)
    holding_cost = st.number_input("单位持有成本 (元/天)", 0.1, 10.0, 1.0, 0.1)
    stockout_cost = st.number_input("缺货成本 (元/次)", 1.0, 200.0, 50.0, 1.0)
    
    st.markdown("---")
    st.subheader("🔧 高级功能")
    auto_cost_estimation = st.checkbox("启用成本参数反推", value=False)
    enable_scenario_analysis = st.checkbox("启用多场景仿真", value=True)
    enable_extreme_test = st.checkbox("启用极端压力测试", value=False)
    enable_multi_echelon = st.checkbox("启用多级库存优化", value=True)
    enable_supplier_analysis = st.checkbox("启用供应商交期分析", value=True)
    enable_health_score = st.checkbox("启用库存健康度评分", value=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📁 数据输入", "📈 销量预测", "📦 库存优化", 
    "🧪 库存仿真", "🎭 场景分析", "🏪 多级库存",
    "📊 供应商分析", "⚠️ 风险预警"
])

with tab1:
    st.header("📁 数据输入")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("历史销量数据")
        use_sample_sales = st.checkbox("使用示例销量数据", value=True, key="sample_sales")
        sales_data = None
        
        if use_sample_sales:
            full_data = get_full_sample_data()
            sales_data = full_data['sales_data']
            promotions_data = full_data['promotions']
            future_promotions = full_data['future_promotions']
            inventory_data = full_data['inventory_data']
            orders_data = full_data['orders_data']
            holidays_data = full_data['holidays']
            supplier_deliveries = full_data['supplier_deliveries']
            multi_echelon_data = full_data['multi_echelon_data']
            st.success("✅ 已加载完整示例数据")
            st.dataframe(sales_data.head(10), use_container_width=True)
            st.info(f"共 {len(sales_data)} 条历史记录")
        else:
            sales_file = st.file_uploader("上传销量CSV文件 (date, sales)", type=["csv"])
            if sales_file:
                sales_data = load_csv_upload(sales_file)
                if sales_data is not None:
                    is_valid, msg = validate_dataframe(sales_data, ['date', 'sales'])
                    if is_valid:
                        st.success(msg)
                        st.dataframe(sales_data.head(10), use_container_width=True)
                    else:
                        st.error(msg)
    
    with col2:
        st.subheader("促销计划数据")
        use_sample_promo = st.checkbox("使用示例促销数据", value=True, key="sample_promo")
        promotions_data = None
        future_promotions = None
        
        if use_sample_promo and 'full_data' in locals():
            promotions_data = full_data['promotions']
            future_promotions = full_data['future_promotions']
            st.success("✅ 已加载示例促销数据")
            st.dataframe(promotions_data.head(10), use_container_width=True)
        else:
            promo_file = st.file_uploader("上传促销CSV文件 (date, promotion)", type=["csv"])
            if promo_file:
                promotions_data = load_csv_upload(promo_file)
                if promotions_data is not None:
                    is_valid, msg = validate_dataframe(promotions_data, ['date', 'promotion'])
                    if is_valid:
                        st.success(msg)
                        st.dataframe(promotions_data.head(10), use_container_width=True)
                    else:
                        st.error(msg)
            
            future_promo_file = st.file_uploader("上传未来促销CSV文件 (date, promotion)", type=["csv"])
            if future_promo_file:
                future_promotions = load_csv_upload(future_promo_file)
                if future_promotions is not None:
                    is_valid, msg = validate_dataframe(future_promotions, ['date', 'promotion'])
                    if is_valid:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🏪 历史库存数据 (可选)")
        use_sample_inv = st.checkbox("使用示例库存数据", value=True, key="sample_inv")
        inventory_data = None
        
        if use_sample_inv and 'full_data' in locals():
            inventory_data = full_data['inventory_data']
            st.success("✅ 已加载示例库存数据")
            st.dataframe(inventory_data.head(10), use_container_width=True)
        else:
            inv_file = st.file_uploader("上传库存CSV文件 (date, inventory)", type=["csv"])
            if inv_file:
                inventory_data = load_csv_upload(inv_file)
                if inventory_data is not None:
                    is_valid, msg = validate_dataframe(inventory_data, ['date', 'inventory'])
                    if is_valid:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    with col4:
        st.subheader("📋 历史订单数据 (可选)")
        use_sample_orders = st.checkbox("使用示例订单数据", value=True, key="sample_orders")
        orders_data = None
        
        if use_sample_orders and 'full_data' in locals():
            orders_data = full_data['orders_data']
            st.success("✅ 已加载示例订单数据")
            st.dataframe(orders_data.head(10), use_container_width=True)
        else:
            order_file = st.file_uploader("上传订单CSV文件 (date, quantity)", type=["csv"])
            if order_file:
                orders_data = load_csv_upload(order_file)
                if orders_data is not None:
                    is_valid, msg = validate_dataframe(orders_data, ['date', 'quantity'])
                    if is_valid:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    st.markdown("---")
    
    st.subheader("🎊 节假日设置")
    use_default_holidays = st.checkbox("使用默认电商大促节假日", value=True)
    
    if use_default_holidays:
        if 'full_data' in locals():
            holidays_data = full_data['holidays']
        else:
            holidays_data = get_chinese_ecommerce_holidays()
        
        st.dataframe(holidays_data, use_container_width=True)
        st.plotly_chart(plot_holiday_calendar(holidays_data), use_container_width=True)
    else:
        holiday_file = st.file_uploader("上传自定义节假日CSV", type=["csv"])
        if holiday_file:
            holidays_data = load_csv_upload(holiday_file)
            st.dataframe(holidays_data, use_container_width=True)

    if sales_data is not None:
        st.markdown("---")
        st.subheader("📊 数据预览")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(sales_data['date']),
            y=sales_data['sales'],
            mode='lines+markers',
            name='历史销量',
            marker=dict(size=4)
        ))
        fig.update_layout(
            title='历史销量趋势',
            xaxis_title='日期',
            yaxis_title='销量',
            template='plotly_white',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🏪 多级库存数据")
        use_sample_multi = st.checkbox("使用示例多级库存数据", value=True, key="sample_multi")
        
        if use_sample_multi and 'full_data' in locals():
            multi_echelon_data = full_data.get('multi_echelon_data', {})
            st.success("✅ 已加载示例多级库存数据")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("**仓库信息**")
                wh = multi_echelon_data.get('warehouse', {})
                st.write(f"• 仓库名称: {wh.get('name', '')}")
                st.write(f"• 当前库存: {format_number(wh.get('current_stock', 0))}")
                st.write(f"• 容量: {format_number(wh.get('capacity', 0))}")
                st.write(f"• 日均需求: {format_number(wh.get('demand_mean', 0))}")
            
            with col2:
                st.info("**门店列表**")
                stores = multi_echelon_data.get('stores', [])
                for store in stores:
                    st.write(f"• {store['name']}: 库存{format_number(store['current_stock'])}, 需求{format_number(store['demand_mean'])}/天")
        
        st.markdown("---")
        st.subheader("📦 供应商交期数据")
        use_sample_suppliers = st.checkbox("使用示例供应商数据", value=True, key="sample_suppliers")
        
        if use_sample_suppliers and 'full_data' in locals():
            supplier_deliveries = full_data.get('supplier_deliveries')
            if supplier_deliveries is not None and len(supplier_deliveries) > 0:
                st.success(f"✅ 已加载 {len(supplier_deliveries)} 条供应商交期记录")
                st.dataframe(supplier_deliveries.head(10), use_container_width=True)

if sales_data is not None:
    with tab2:
        st.header("📈 销量预测")
        
        with st.spinner("正在训练预测模型..."):
            try:
                forecaster = SalesForecaster(
                    changepoint_prior_scale=changepoint_prior,
                    seasonality_prior_scale=seasonality_prior,
                    holidays_prior_scale=holidays_prior,
                    use_default_holidays=use_holidays
                )
                
                custom_holidays = holidays_data if use_default_holidays else None
                
                forecaster.fit(sales_data, promotions_data, custom_holidays=custom_holidays)
                forecast, future_forecast = forecaster.predict(
                    periods=forecast_days,
                    future_promotions=future_promotions
                )
                
                st.success("✅ 模型训练完成")
                
                col1, col2, col3 = st.columns(3)
                
                historical_pred = forecast[forecast['ds'] <= forecaster.history['ds'].max()]
                metrics = calculate_forecast_metrics(
                    forecaster.history['y'],
                    historical_pred['yhat']
                )
                
                with col1:
                    st.metric("平均绝对误差 (MAE)", format_number(metrics['mae']))
                with col2:
                    st.metric("平均绝对百分比误差 (MAPE)", f"{format_number(metrics['mape'])}%")
                with col3:
                    st.metric("均方根误差 (RMSE)", format_number(metrics['rmse']))
                
                st.plotly_chart(
                    plot_forecast(forecaster.history, forecast, future_forecast),
                    use_container_width=True
                )
                
                st.subheader("🎊 节假日效应分析")
                holiday_effects = forecaster.get_holiday_effects(forecast)
                if len(holiday_effects) > 0 and holiday_effects['holidays'].abs().sum() > 0:
                    st.plotly_chart(plot_holiday_effects(holiday_effects), use_container_width=True)
                    
                    significant_holidays = holiday_effects[holiday_effects['holidays'].abs() > 5]
                    if len(significant_holidays) > 0:
                        st.info("显著节假日效应时间段:")
                        st.dataframe(significant_holidays, use_container_width=True)
                else:
                    st.info("未检测到显著的节假日效应")
                
                st.subheader("🔮 未来预测详情")
                forecast_display = future_forecast[[
                    'ds', 'yhat', 'yhat_lower', 'yhat_upper'
                ]].rename(columns={
                    'ds': '日期',
                    'yhat': '预测销量',
                    'yhat_lower': '预测下限',
                    'yhat_upper': '预测上限'
                })
                st.dataframe(forecast_display, use_container_width=True)
                
                st.subheader("📊 预测组件分解")
                components = forecaster.get_components(forecast)
                
                comp_fig = go.Figure()
                if components['trend'] is not None:
                    comp_fig.add_trace(go.Scatter(
                        x=components['trend']['ds'],
                        y=components['trend']['trend'],
                        name='趋势',
                        line=dict(color='#636efa')
                    ))
                if components['yearly'] is not None:
                    comp_fig.add_trace(go.Scatter(
                        x=components['yearly']['ds'],
                        y=components['yearly']['yearly'],
                        name='年度季节性',
                        line=dict(color='#00cc96')
                    ))
                if components['weekly'] is not None:
                    comp_fig.add_trace(go.Scatter(
                        x=components['weekly']['ds'],
                        y=components['weekly']['weekly'],
                        name='周度季节性',
                        line=dict(color='#ffa500')
                    ))
                if components['holidays'] is not None:
                    comp_fig.add_trace(go.Scatter(
                        x=components['holidays']['ds'],
                        y=components['holidays']['holidays'],
                        name='节假日效应',
                        line=dict(color='#ff4b4b')
                    ))
                
                comp_fig.update_layout(
                    title='预测组件分解',
                    xaxis_title='日期',
                    yaxis_title='贡献值',
                    template='plotly_white',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                st.plotly_chart(comp_fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"预测失败: {str(e)}")

    with tab3:
        st.header("📦 库存优化")
        
        try:
            optimizer = InventoryOptimizer(
                cost_price=cost_price,
                selling_price=selling_price,
                salvage_value=salvage_value,
                service_level=service_level,
                lead_time_days=lead_time_days
            )
            
            if auto_cost_estimation and inventory_data is not None:
                st.subheader("💰 成本参数自动反推")
                with st.spinner("正在进行成本参数优化..."):
                    cost_estimation = optimizer.estimate_costs(
                        sales_data, inventory_data, orders_data, optimize=True
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info("**🔍 预估参数**")
                        st.write(f"• 需求均值: {format_number(cost_estimation['demand_mean'])}")
                        st.write(f"• 需求标准差: {format_number(cost_estimation['demand_std'])}")
                        st.write(f"• 平均库存: {format_number(cost_estimation['avg_inventory'])}")
                        st.write(f"• 历史缺货率: {cost_estimation['stockout_rate']:.2%}")
                        st.write(f"• 隐含服务水平: {cost_estimation['implicit_service_level']:.2%}")
                    
                    with col2:
                        st.info("**📊 成本分析**")
                        if 'optimal_holding_cost' in cost_estimation:
                            st.write(f"• 最优持有成本: {format_currency(cost_estimation['optimal_holding_cost'])}/件/天")
                            st.write(f"• 最优缺货成本: {format_currency(cost_estimation['optimal_stockout_cost'])}/次")
                            st.write(f"• 最小化总成本: {format_currency(cost_estimation['minimized_total_cost'])}")
                            if cost_estimation.get('optimization_success'):
                                st.success("✅ 优化成功")
                        else:
                            st.write(f"• 预估持有成本: {format_currency(cost_estimation['estimated_holding_cost'])}/件/天")
                            st.write(f"• 预估缺货成本: {format_currency(cost_estimation['estimated_stockout_cost'])}/次")
                    
                    st.plotly_chart(plot_cost_optimization(cost_estimation), use_container_width=True)
                    
                    apply_optimized = st.button("应用优化后的成本参数")
                    if apply_optimized:
                        holding_cost = cost_estimation.get('optimal_holding_cost', cost_estimation['estimated_holding_cost'])
                        stockout_cost = cost_estimation.get('optimal_stockout_cost', cost_estimation['estimated_stockout_cost'])
                        st.success(f"已应用: 持有成本={format_currency(holding_cost)}, 缺货成本={format_currency(stockout_cost)}")
            
            opt_result = optimizer.optimize_inventory(future_forecast, current_stock=initial_stock)
            replenishment_plan = optimizer.generate_replenishment_plan(
                future_forecast, initial_stock, review_period_days=7
            )
            
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("安全库存", format_number(opt_result['safety_stock']))
            with col2:
                st.metric("补货点", format_number(opt_result['reorder_point']))
            with col3:
                st.metric("最优订货量", format_number(opt_result['optimal_order_quantity']))
            with col4:
                st.metric("净补货量", format_number(opt_result['net_order_quantity']))
            
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("日均需求", format_number(opt_result['avg_daily_demand']))
            with col2:
                st.metric("服务水平", f"{opt_result['service_level']:.2%}")
            with col3:
                st.metric("临界分位数", f"{opt_result['critical_fractile']:.2%}")
            with col4:
                st.metric("预期利润", format_currency(opt_result['expected_profit']))
            
            st.markdown("---")
            st.subheader("📊 报童模型分析")
            
            newsvendor_fig = plot_newsvendor_curve(
                opt_result['lead_time_demand'],
                opt_result['avg_daily_std'] * np.sqrt(lead_time_days),
                opt_result['optimal_order_quantity'],
                opt_result['critical_fractile']
            )
            st.plotly_chart(newsvendor_fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 补货计划")
            
            plan_display = replenishment_plan.copy()
            plan_display['action_label'] = plan_display['action'].map({
                'order': '🔴 需要补货',
                'hold': '🟢 无需补货'
            })
            plan_display = plan_display.rename(columns={
                'date': '日期',
                'action_label': '操作',
                'order_quantity': '补货数量',
                'projected_stock_before': '补货前库存',
                'projected_stock_after': '补货后库存',
                'expected_demand': '预期需求',
                'safety_stock': '安全库存',
                'reorder_point': '补货点'
            })
            
            st.dataframe(
                plan_display[['日期', '操作', '补货数量', '补货前库存', '补货后库存', 
                             '预期需求', '安全库存', '补货点']],
                use_container_width=True
            )
            
            if enable_health_score and inventory_data is not None:
                st.markdown("---")
                st.subheader("💊 库存健康度评分")
                
                with st.spinner("正在计算库存健康度..."):
                    health_scorer = InventoryHealthScorer()
                    health_result = health_scorer.from_inventory_data(
                        sales_data, inventory_data, orders_data, cost_price
                    )
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.plotly_chart(plot_inventory_health_gauge(health_result), use_container_width=True)
                        
                        st.info(f"**健康等级: {health_result['health_level']}**")
                        st.info(f"**综合得分: {health_result['overall_score']:.1f}**")
                    
                    with col2:
                        st.plotly_chart(plot_health_metrics(health_result), use_container_width=True)
                    
                    st.subheader("📋 详细指标分析")
                    metrics_df = pd.DataFrame(health_result['metrics'])
                    st.dataframe(
                        metrics_df[['name', 'value', 'score', 'weight', 'description']].rename(columns={
                            'name': '指标名称',
                            'value': '当前值',
                            'score': '得分',
                            'weight': '权重',
                            'description': '说明'
                        }),
                        use_container_width=True
                    )
                    
                    st.subheader("💡 优化建议")
                    for rec in health_result['recommendations']:
                        st.warning(f"• {rec}")
            
        except Exception as e:
            st.error(f"库存优化失败: {str(e)}")

    with tab4:
        st.header("🧪 库存仿真")
        
        try:
            simulator = InventorySimulator(
                forecast=future_forecast,
                initial_stock=initial_stock,
                lead_time_days=lead_time_days,
                order_quantity=opt_result['optimal_order_quantity'],
                reorder_point=opt_result['reorder_point'],
                safety_stock=opt_result['safety_stock'],
                holding_cost=holding_cost,
                stockout_cost=stockout_cost
            )
            
            with st.spinner(f"正在运行 {num_simulations} 次仿真..."):
                sim_result = simulator.run_simulations(num_simulations=num_simulations)
                risk_levels = simulator.calculate_risk_levels(sim_result)
                
                st.success("✅ 仿真完成")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("平均库存水平", format_number(sim_result.average_stock))
                with col2:
                    st.metric("缺货率", f"{sim_result.stockout_rate:.2%}")
                with col3:
                    st.metric("平均总成本", format_currency(sim_result.average_cost))
                with col4:
                    st.metric("仿真天数", f"{sim_result.days} 天")
                
                st.markdown("---")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("高风险天数", risk_levels['high_risk_days'], 
                             delta_color="inverse")
                with col2:
                    st.metric("中风险天数", risk_levels['medium_risk_days'],
                             delta_color="off")
                with col3:
                    st.metric("低风险天数", risk_levels['low_risk_days'],
                             delta_color="normal")
                
                st.plotly_chart(
                    plot_inventory_simulation(
                        sim_result.daily_metrics,
                        opt_result['reorder_point'],
                        opt_result['safety_stock']
                    ),
                    use_container_width=True
                )
                
                st.plotly_chart(
                    plot_stockout_risk(sim_result.daily_metrics),
                    use_container_width=True
                )
                
                if enable_extreme_test:
                    st.markdown("---")
                    st.subheader("🔥 极端压力测试")
                    with st.spinner("正在运行极端压力测试 (1000次仿真)..."):
                        extreme_result = simulator.calculate_extreme_stockout_probability(num_simulations=1000)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("平均缺货天数", format_number(extreme_result['avg_stockout_days']))
                        with col2:
                            st.metric("最大缺货天数", format_number(extreme_result['max_stockout_days']))
                        with col3:
                            st.metric("极端场景缺货率", f"{extreme_result['stockout_rate']:.2%}")
                        
                        st.plotly_chart(plot_extreme_risk_analysis(extreme_result), use_container_width=True)
                        
                        with st.expander("📊 详细压力测试结果"):
                            st.write(f"• 中位数缺货天数: {format_number(extreme_result['median_stockout_days'])}")
                            st.write(f"• 缺货超过5天概率: {extreme_result['prob_more_than_5_days']:.2%}")
                            st.write(f"• 缺货超过10天概率: {extreme_result['prob_more_than_10_days']:.2%}")
                            st.write(f"• 缺货超过20天概率: {extreme_result['prob_more_than_20_days']:.2%}")
                            st.write(f"• 平均库存: {format_number(extreme_result['average_stock'])}")
                            st.write(f"• 平均成本: {format_currency(extreme_result['average_cost'])}")
                
                st.subheader("📋 每日仿真详情")
                daily_display = sim_result.daily_metrics.copy()
                daily_display['risk_level'] = daily_display['stockout_prob'].apply(get_risk_label)
                daily_display = daily_display.rename(columns={
                    'date': '日期',
                    'avg_stock': '平均库存',
                    'std_stock': '库存标准差',
                    'p5_stock': '5%分位库存',
                    'p95_stock': '95%分位库存',
                    'p99_stock': '99%分位库存',
                    'p1_stock': '1%分位库存',
                    'stockout_prob': '缺货概率',
                    'forecast_demand': '预测需求',
                    'risk_level': '风险等级'
                })
                daily_display['缺货概率'] = (daily_display['缺货概率'] * 100).round(2).astype(str) + '%'
                
                st.dataframe(daily_display, use_container_width=True)
                
        except Exception as e:
            st.error(f"库存仿真失败: {str(e)}")

    with tab5:
        st.header("🎭 多场景仿真分析")
        
        if enable_scenario_analysis:
            try:
                scenarios = ScenarioConfig.get_default_scenarios()
                
                selected_scenarios = st.multiselect(
                    "选择要仿真的场景",
                    [s.name for s in scenarios],
                    default=[s.name for s in scenarios[:4]]
                )
                
                if st.button("运行多场景仿真"):
                    with st.spinner(f"正在运行 {len(selected_scenarios)} 个场景，每个场景 {num_simulations} 次仿真..."):
                        scenarios_to_run = [s for s in scenarios if s.name in selected_scenarios]
                        
                        scenario_results = simulator.run_multiple_scenarios(
                            scenarios=scenarios_to_run,
                            num_simulations=num_simulations
                        )
                        
                        st.success(f"✅ {len(scenario_results)} 个场景仿真完成")
                        
                        st.subheader("📊 场景对比")
                        comparison_df = generate_scenario_comparison(scenario_results)
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        st.plotly_chart(plot_scenario_comparison(scenario_results), use_container_width=True)
                        
                        for result in scenario_results:
                            with st.expander(f"📋 {result.scenario_name} - 详细分析"):
                                sim = result.simulation_result
                                risk = result.risk_assessment['risk_levels']
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("平均库存", format_number(sim.average_stock))
                                with col2:
                                    st.metric("缺货率", f"{sim.stockout_rate:.2%}")
                                with col3:
                                    st.metric("平均成本", format_currency(sim.average_cost))
                                with col4:
                                    st.metric("是否可接受", result.risk_assessment['is_acceptable'])
                                
                                st.write(f"**场景描述**: {result.scenario_config.description}")
                                st.write(f"**需求倍数**: {result.scenario_config.demand_multiplier}x")
                                st.write(f"**交期倍数**: {result.scenario_config.lead_time_multiplier}x")
                                
                                if not result.risk_assessment['is_acceptable']:
                                    rec_increase = result.risk_assessment['recommended_safety_stock_increase']
                                    if rec_increase > 0:
                                        st.warning(f"💡 建议增加安全库存 {format_number(rec_increase)} 件")
                
            except Exception as e:
                st.error(f"多场景仿真失败: {str(e)}")
        else:
            st.info("请在侧边栏启用多场景仿真功能")

    with tab6:
        st.header("🏪 多级库存优化")
        
        if enable_multi_echelon:
            try:
                if 'multi_echelon_data' in locals():
                    multi_data = multi_echelon_data
                    
                    warehouse_data = multi_data.get('warehouse', {})
                    stores_data = multi_data.get('stores', [])
                    
                    locations = []
                    
                    warehouse_node = LocationNode(
                        name=warehouse_data.get('name', '中心仓库'),
                        node_type='warehouse',
                        current_stock=warehouse_data.get('current_stock', 0),
                        capacity=warehouse_data.get('capacity', 10000),
                        demand_mean=warehouse_data.get('demand_mean', 500),
                        demand_std=warehouse_data.get('demand_std', 80)
                    )
                    locations.append(warehouse_node)
                    
                    store_names = []
                    for store in stores_data:
                        store_node = LocationNode(
                            name=store.get('name', ''),
                            node_type='store',
                            parent=warehouse_data.get('name', '中心仓库'),
                            current_stock=store.get('current_stock', 0),
                            capacity=store.get('capacity', 2000),
                            demand_mean=store.get('demand_mean', 100),
                            demand_std=store.get('demand_std', 20)
                        )
                        locations.append(store_node)
                        store_names.append(store.get('name', ''))
                    
                    multi_optimizer = MultiEchelonInventoryOptimizer(
                        locations=locations,
                        service_level=service_level
                    )
                    
                    if st.button("运行多级库存优化"):
                        with st.spinner("正在优化多级库存分配..."):
                            multi_plan = multi_optimizer.generate_multi_echelon_plan(
                                forecast=future_forecast,
                                warehouse_name=warehouse_data.get('name', '中心仓库'),
                                store_names=store_names
                            )
                            
                            st.success("✅ 多级库存优化完成")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📊 库存分布")
                                st.plotly_chart(
                                    plot_multi_echelon_inventory(multi_plan),
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.subheader("🏭 仓库状态")
                                wh = multi_plan.get('warehouse', {})
                                st.metric("仓库当前库存", format_number(wh.get('current_stock', 0)))
                                st.metric("仓库安全库存", format_number(wh.get('safety_stock', 0)))
                                st.metric("仓库补货点", format_number(wh.get('reorder_point', 0)))
                                if wh.get('needs_replenishment'):
                                    st.warning("⚠️ 仓库需要补货")
                                else:
                                    st.success("✅ 仓库库存充足")
                            
                            st.markdown("---")
                            st.subheader("🏪 门店状态")
                            
                            stores_info = multi_plan.get('stores', {})
                            stores_df = pd.DataFrame([
                                {
                                    '门店': name,
                                    '当前库存': format_number(info.get('current_stock', 0)),
                                    '安全库存': format_number(info.get('safety_stock', 0)),
                                    '补货点': format_number(info.get('reorder_point', 0)),
                                    '需要调拨': '✅' if info.get('needs_transfer') else '❌',
                                    '调拨数量': format_number(info.get('transfer_needed', 0))
                                }
                                for name, info in stores_info.items()
                            ])
                            st.dataframe(stores_df, use_container_width=True)
                            
                            transfers = multi_plan.get('transfers', [])
                            if transfers:
                                st.markdown("---")
                                st.subheader("🚚 调拨计划")
                                st.plotly_chart(plot_transfer_plan(transfers), use_container_width=True)
                                
                                transfer_cost = multi_plan.get('total_cost', 0)
                                st.info(f"**调拨总成本: {format_currency(transfer_cost)}**")
                                
                                for t in transfers:
                                    st.write(f"• {t['from']} → {t['to']}: {format_number(t['quantity'])}件, 成本: {format_currency(t['total_cost'])}")
                            
                            summary = multi_plan.get('summary', {})
                            st.markdown("---")
                            st.subheader("📋 优化摘要")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("需调拨门店数", summary.get('stores_needing_transfer', 0))
                            with col2:
                                st.metric("总调拨需求", format_number(summary.get('total_transfer_needed', 0)))
                            with col3:
                                st.metric("仓库覆盖率", f"{summary.get('warehouse_coverage', 0):.1%}")
                            with col4:
                                st.metric("调拨成本", format_currency(summary.get('total_transfer_cost', 0)))
                else:
                    st.info("请在数据输入页加载多级库存数据")
            except Exception as e:
                st.error(f"多级库存优化失败: {str(e)}")
        else:
            st.info("请在侧边栏启用多级库存优化功能")

    with tab7:
        st.header("📊 供应商交期分析")
        
        if enable_supplier_analysis:
            try:
                if 'supplier_deliveries' in locals() and supplier_deliveries is not None:
                    with st.spinner("正在分析供应商交期数据..."):
                        deliveries = []
                        for _, row in supplier_deliveries.iterrows():
                            delivery = SupplierDelivery(
                                supplier_id=row['supplier_id'],
                                supplier_name=row['supplier_name'],
                                order_date=pd.to_datetime(row['order_date']),
                                actual_delivery_date=pd.to_datetime(row['actual_delivery_date']),
                                promised_delivery_date=pd.to_datetime(row['promised_delivery_date']),
                                quantity=row['delivered_quantity'],
                                order_quantity=row['order_quantity']
                            )
                            deliveries.append(delivery)
                        
                        analyzer = SupplierVariabilityAnalyzer(deliveries)
                        
                        supplier_analysis = analyzer.get_all_suppliers_analysis()
                        
                        st.success(f"✅ 已分析 {len(supplier_analysis)} 个供应商")
                        
                        st.subheader("📊 供应商变异分析")
                        st.plotly_chart(
                            plot_supplier_variability(supplier_analysis),
                            use_container_width=True
                        )
                        
                        st.subheader("📋 供应商详情")
                        
                        display_df = supplier_analysis.copy()
                        display_df = display_df.rename(columns={
                            'supplier_name': '供应商名称',
                            'total_deliveries': '交货次数',
                            'avg_actual_lead_time': '平均实际交期(天)',
                            'avg_promised_lead_time': '平均承诺交期(天)',
                            'std_lead_time': '交期标准差',
                            'on_time_rate': '准时率',
                            'variability_score': '变异系数',
                            'risk_level': '风险等级'
                        })
                        display_df['准时率'] = (display_df['准时率'] * 100).round(2).astype(str) + '%'
                        display_df['变异系数'] = (display_df['变异系数'] * 100).round(2).astype(str) + '%'
                        display_df['风险等级'] = display_df['风险等级'].map({
                            'low': '🟢 低风险',
                            'medium': '🟡 中风险',
                            'high': '🔴 高风险'
                        })
                        
                        st.dataframe(
                            display_df[['供应商名称', '交货次数', '平均实际交期(天)', '平均承诺交期(天)', 
                                       '准时率', '变异系数', '风险等级']],
                            use_container_width=True
                        )
                        
                        st.markdown("---")
                        st.subheader("🔒 安全库存调整建议")
                        
                        selected_supplier = st.selectbox(
                            "选择供应商查看安全库存调整",
                            options=supplier_analysis['supplier_id'].tolist(),
                            format_func=lambda x: supplier_analysis[supplier_analysis['supplier_id'] == x]['supplier_name'].iloc[0]
                        )
                        
                        if selected_supplier:
                            adjustment = analyzer.calculate_adjusted_safety_stock(
                                supplier_id=selected_supplier,
                                base_safety_stock=opt_result['safety_stock'],
                                base_lead_time=lead_time_days
                            )
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("基础安全库存", format_number(adjustment.get('base_safety_stock', 0)))
                            with col2:
                                st.metric("调整后安全库存", format_number(adjustment.get('adjusted_safety_stock', 0)))
                            with col3:
                                st.metric("最终安全库存", format_number(adjustment.get('final_safety_stock', 0)))
                            
                            st.plotly_chart(
                                plot_safety_stock_adjustment(adjustment),
                                use_container_width=True
                            )
                            
                            if adjustment.get('increase_percentage', 0) > 0:
                                st.warning(f"⚠️ 建议增加安全库存 {adjustment['increase_percentage']:.1f}% 以应对供应商交期变异")
                            else:
                                st.success("✅ 当前安全库存已足够应对该供应商的交期变异")
                            
                            st.info(f"**风险等级**: {adjustment.get('risk_level', '未知').upper()}")
                            st.info(f"**供应商准时率**: {adjustment.get('on_time_rate', 0):.1%}")
                            st.info(f"**交期变异系数**: {adjustment.get('variability_score', 0):.1%}")
                else:
                    st.info("请在数据输入页加载供应商交期数据")
            except Exception as e:
                st.error(f"供应商分析失败: {str(e)}")
        else:
            st.info("请在侧边栏启用供应商交期分析功能")

    with tab8:
        st.header("⚠️ 风险预警与建议")
        
        try:
            daily_metrics = sim_result.daily_metrics
            high_risk = daily_metrics[daily_metrics['stockout_prob'] > 0.2]
            medium_risk = daily_metrics[(daily_metrics['stockout_prob'] > 0.05) & (daily_metrics['stockout_prob'] <= 0.2)]
            
            if len(high_risk) > 0:
                st.error(f"🚨 检测到 {len(high_risk)} 天高缺货风险！")
                
                for _, row in high_risk.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d')
                    prob = row['stockout_prob'] * 100
                    forecast_demand = row['forecast_demand']
                    
                    with st.expander(f"📅 {date_str} - 缺货概率: {prob:.1f}%", expanded=True):
                        st.warning(f"**预计需求: {forecast_demand:.1f} 件**")
                        st.warning("**建议措施:**")
                        st.warning("1. 提前安排补货，增加安全库存")
                        st.warning("2. 与供应商确认交期，优先处理该时间段订单")
                        st.warning("3. 可考虑适当提高售价或限制促销")
                        st.warning("4. 准备替代产品或紧急补货方案")
            
            if len(medium_risk) > 0:
                st.warning(f"⚠️ 检测到 {len(medium_risk)} 天中等缺货风险")
                
                for _, row in medium_risk.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d')
                    prob = row['stockout_prob'] * 100
                    forecast_demand = row['forecast_demand']
                    
                    with st.expander(f"📅 {date_str} - 缺货概率: {prob:.1f}%"):
                        st.info(f"**预计需求: {forecast_demand:.1f} 件**")
                        st.info("**建议措施:**")
                        st.info("1. 密切关注库存水平")
                        st.info("2. 提前安排补货计划")
                        st.info("3. 可适当增加补货数量")
            
            if len(high_risk) == 0 and len(medium_risk) == 0:
                st.success("✅ 未来时间段内缺货风险较低，库存水平健康")
            
            st.markdown("---")
            st.subheader("💡 综合优化建议")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("**📊 库存策略建议**")
                suggestions = [
                    f"建议保持安全库存: {format_number(opt_result['safety_stock'])} 件",
                    f"补货点设置为: {format_number(opt_result['reorder_point'])} 件",
                    f"每次最优补货量: {format_number(opt_result['optimal_order_quantity'])} 件",
                    f"预计服务水平可达: {opt_result['service_level']:.2%}",
                ]
                for s in suggestions:
                    st.write(f"• {s}")
            
            with col2:
                st.info("**💰 成本优化建议**")
                cost_suggestions = [
                    f"当前缺货成本较高 (¥{stockout_cost}/次)，建议增加安全库存降低缺货风险",
                    f"持有成本 ¥{holding_cost}/件/天，需平衡库存水平",
                    f"预计周期内预期利润: {format_currency(opt_result['expected_profit'])}",
                    f"交期 {lead_time_days} 天，考虑与供应商协商缩短交期以降低安全库存需求",
                ]
                for s in cost_suggestions:
                    st.write(f"• {s}")
            
            st.markdown("---")
            st.subheader("📥 补货建议汇总")
            
            order_plan = replenishment_plan[replenishment_plan['action'] == 'order'].copy()
            if len(order_plan) > 0:
                order_plan['date'] = pd.to_datetime(order_plan['date'])
                order_plan = order_plan.sort_values('date')
                
                for _, row in order_plan.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d')
                    qty = format_number(row['order_quantity'])
                    st.success(f"📦 建议在 {date_str} 补货 {qty} 件")
            else:
                st.info("根据当前预测和库存水平，未来时间段内暂无补货需求")
            
            if enable_scenario_analysis and 'scenario_results' in locals():
                st.markdown("---")
                st.subheader("🎭 场景风险总结")
                
                unacceptable_scenarios = [r for r in scenario_results if not r.risk_assessment['is_acceptable']]
                if unacceptable_scenarios:
                    st.error(f"⚠️ 有 {len(unacceptable_scenarios)} 个场景存在不可接受的缺货风险:")
                    for r in unacceptable_scenarios:
                        st.write(f"• **{r.scenario_name}**: 缺货率 {r.simulation_result.stockout_rate:.2%}")
                    
                    st.warning("💡 建议: 为应对极端场景，考虑额外增加安全库存或建立备用供应商")
            
        except Exception as e:
            st.error(f"风险分析失败: {str(e)}")

st.markdown("---")
st.caption("💡 商品销量预测与库存优化系统 | Prophet + 自定义节假日 + 报童模型 + 多场景仿真 + Streamlit")
