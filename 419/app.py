import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os

from model_training import AirlinePriceModel
from prediction import (
    generate_enhanced_booking_advice,
    predict_multi_city_itinerary,
    compare_direct_vs_connecting,
    predict_open_jaw,
    predict_price_range,
    generate_price_path
)
from airline_events import AIRLINE_SPECIFIC_DATES, get_event_calendar_summary
from oil_futures import get_current_futures_curve, get_oil_market_analysis
from risk_model import generate_risk_report
from price_alert import PriceAlertManager, get_price_drop_probability
from refund_cost import (
    compare_fare_options,
    simulate_refund_scenarios,
    calculate_refund_cost,
    calculate_change_cost,
    calculate_breakeven_point,
    FARE_TYPES
)
from multi_city import HUB_CITIES

st.set_page_config(
    page_title='航空票价预测系统 v3.0',
    page_icon='✈️',
    layout='wide',
    initial_sidebar_state='expanded'
)

@st.cache_resource
def load_model():
    model = AirlinePriceModel()
    if os.path.exists('models/xgb_model.pkl'):
        model.load_models()
        return model
    else:
        return None

@st.cache_resource
def get_alert_manager():
    return PriceAlertManager()

@st.cache_data
def get_routes():
    return [
        '北京-上海', '北京-广州', '上海-深圳',
        '北京-成都', '上海-广州', '深圳-成都',
        '北京-西安', '上海-重庆', '广州-成都',
        '北京-杭州', '广州-杭州', '深圳-西安'
    ]

@st.cache_data
def get_cities():
    return ['北京', '上海', '广州', '深圳', '成都', '西安', '重庆', '杭州', '南京', '武汉', '厦门', '青岛', '大连', '三亚', '昆明']

@st.cache_data
def get_airlines():
    return list(AIRLINE_SPECIFIC_DATES.keys())

def generate_data_and_train():
    with st.spinner('正在生成增强版数据并训练模型，这可能需要几分钟...'):
        from init_system import create_enhanced_data, train_enhanced_models
        df = create_enhanced_data()
        model = train_enhanced_models(df)
    return model

def main():
    st.title('✈️ 航空票价预测系统 v3.0')
    st.markdown('**增强版**: 多城市联运 + 价格警报 + 退改签成本模拟')

    model = load_model()

    if model is None:
        st.warning('⚠️ 未检测到已训练的增强版模型')
        if st.button('🔄 生成增强数据并训练模型', type='primary'):
            model = generate_data_and_train()
            st.success('✅ 增强版模型训练完成！')
            st.rerun()
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        '🎫 单程票价预测',
        '🌍 多城市联运',
        '🔔 价格警报',
        '💰 退改签成本'
    ])

    with tab1:
        single_city_prediction(model)

    with tab2:
        multi_city_prediction(model)

    with tab3:
        price_alert_panel(model)

    with tab4:
        refund_cost_panel(model)

def single_city_prediction(model):
    with st.sidebar:
        st.header('📝 输入信息')

        routes = get_routes()
        selected_route = st.selectbox('选择航线', routes, index=0, key='single_route')

        airlines = get_airlines()
        selected_airline = st.selectbox('选择航空公司', airlines, index=0, key='single_airline')

        min_date = datetime.now() + timedelta(days=1)
        max_date = datetime.now() + timedelta(days=180)
        default_date = datetime.now() + timedelta(days=30)

        departure_date = st.date_input(
            '出发日期',
            value=default_date,
            min_value=min_date,
            max_value=max_date,
            key='single_date'
        )

        st.markdown('---')
        st.subheader('⚙️ 高级设置')

        prediction_days = st.slider(
            '预测天数',
            min_value=7,
            max_value=90,
            value=60,
            step=7,
            key='single_pred_days'
        )

        confidence_level = st.slider(
            '置信区间 (%)',
            min_value=70,
            max_value=95,
            value=85,
            step=5,
            key='single_confidence'
        )

        show_risk_details = st.checkbox('显示风险分析详情', value=True, key='single_show_risk')
        show_oil_analysis = st.checkbox('显示油价分析', value=True, key='single_show_oil')
        show_events = st.checkbox('显示航司活动日历', value=True, key='single_show_events')

        predict_button = st.button('🔮 开始预测', type='primary', use_container_width=True, key='single_predict')

    if predict_button:
        with st.spinner('正在进行增强版票价预测与风险分析...'):
            try:
                result = generate_enhanced_booking_advice(
                    selected_route,
                    departure_date,
                    model,
                    airline=selected_airline
                )

                display_enhanced_results(result, confidence_level, show_risk_details, show_oil_analysis, show_events)

            except Exception as e:
                st.error(f'预测过程中出现错误: {str(e)}')
                import traceback
                st.code(traceback.format_exc())
    else:
        display_enhanced_welcome()

def multi_city_prediction(model):
    st.subheader('🌍 多城市联运推荐')

    col1, col2, col3 = st.columns(3)

    with col1:
        origin = st.selectbox('出发城市', get_cities(), index=0, key='mc_origin')

    with col2:
        destination = st.selectbox('目的城市', get_cities(), index=1, key='mc_dest')

    with col3:
        mc_date = st.date_input(
            '出发日期',
            value=datetime.now() + timedelta(days=30),
            min_value=datetime.now() + timedelta(days=1),
            key='mc_date'
        )

    col4, col5, col6 = st.columns(3)

    with col4:
        max_connections = st.slider('最大中转次数', 0, 2, 1, key='mc_connections')

    with col5:
        mc_airline = st.selectbox('偏好航空公司', ['不限'] + get_airlines(), index=0, key='mc_airline')

    with col6:
        top_n = st.slider('显示推荐数量', 3, 10, 5, key='mc_topn')

    if st.button('🔍 搜索多城市航线', type='primary', key='mc_search'):
        with st.spinner('正在搜索最优多城市航线...'):
            airline_param = None if mc_airline == '不限' else mc_airline

            itineraries = predict_multi_city_itinerary(
                origin, destination, mc_date, model,
                max_connections=max_connections,
                top_n=top_n,
                airline=airline_param
            )

            if itineraries:
                display_multi_city_results(itineraries, origin, destination, mc_date)

    st.markdown('---')

    with st.expander('🛫 开口程/多目的地查询'):
        st.markdown('**开口程查询** (A→B→C)')

        col_o1, col_o2, col_o3 = st.columns(3)
        with col_o1:
            city1 = st.selectbox('出发城市A', get_cities(), index=0, key='oj_city1')
        with col_o2:
            city2 = st.selectbox('中转城市B', get_cities(), index=1, key='oj_city2')
        with col_o3:
            city3 = st.selectbox('目的城市C', get_cities(), index=2, key='oj_city3')

        col_o4, col_o5 = st.columns(2)
        with col_o4:
            date1 = st.date_input('A→B日期', value=datetime.now() + timedelta(days=30), key='oj_date1')
        with col_o5:
            date2 = st.date_input('B→C日期', value=datetime.now() + timedelta(days=40), key='oj_date2')

        if st.button('🔎 查询开口程', key='oj_search'):
            with st.spinner('正在查询开口程价格...'):
                result = predict_open_jaw(city1, city2, city3, date1, date2, model)
                st.success('查询完成!')
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    st.metric('开口程总价', f'¥{result["total_price"]:.0f}')
                with col_r2:
                    if 'separate_booking_price' in result:
                        st.metric('分开预订价格', f'¥{result["separate_booking_price"]:.0f}')
                with col_r3:
                    if 'actual_savings' in result:
                        st.metric('预计节省', f'¥{result["actual_savings"]:.0f}',
                                  delta=f'{result["savings_percent"]}%')

def price_alert_panel(model):
    st.subheader('🔔 价格警报管理')

    alert_manager = get_alert_manager()

    tab_alert1, tab_alert2, tab_alert3 = st.tabs(['创建警报', '我的警报', '价格下跌概率分析'])

    with tab_alert1:
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            alert_route = st.selectbox('选择航线', get_routes(), key='alert_route')
            alert_target = st.number_input('目标价格 (¥)', min_value=100, value=500, step=50, key='alert_target')
            alert_date = st.date_input('出发日期', value=datetime.now() + timedelta(days=30), key='alert_date')

        with col_a2:
            alert_airline = st.selectbox('航空公司', ['不限'] + get_airlines(), key='alert_airline')
            alert_email = st.text_input('通知邮箱 (可选)', placeholder='your@email.com', key='alert_email')
            alert_phone = st.text_input('通知手机 (可选)', placeholder='138xxxxxxxxx', key='alert_phone')

        alert_note = st.text_input('备注 (可选)', placeholder='暑假旅行、出差等', key='alert_note')

        if st.button('➕ 创建价格警报', type='primary', key='create_alert'):
            airline_param = None if alert_airline == '不限' else alert_airline
            alert = alert_manager.create_alert(
                route=alert_route,
                target_price=alert_target,
                departure_date=alert_date.strftime('%Y-%m-%d'),
                email=alert_email if alert_email else None,
                phone=alert_phone if alert_phone else None,
                airline=airline_param,
                note=alert_note
            )
            st.success(f'✅ 价格警报创建成功! 警报ID: {alert["id"]}')

    with tab_alert2:
        alerts = alert_manager.get_all_alerts()

        if not alerts:
            st.info('暂无价格警报，点击"创建警报"添加新的价格提醒')
        else:
            stats = alert_manager.get_alert_statistics()
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric('总警报数', stats['total_alerts'])
            col_s2.metric('活动警报', stats['active_alerts'])
            col_s3.metric('已触发', stats['triggered_alerts'])
            col_s4.metric('触发率', f'{stats["trigger_rate"]}%')

            status_map = {
                'active': '🟢 活动中',
                'triggered': '🔔 已触发',
                'cancelled': '⚪ 已取消',
                'expired': '⚫ 已过期'
            }

            for alert in alerts:
                with st.expander(f"{status_map.get(alert['status'], alert['status'])} | {alert['route']} | ¥{alert['target_price']:.0f}"):
                    col_al1, col_al2, col_al3 = st.columns(3)
                    col_al1.write(f"**出发日期**: {alert['departure_date']}")
                    col_al2.write(f"**创建时间**: {alert['created_at']}")
                    col_al3.write(f"**航空公司**: {alert.get('airline', '不限')}")

                    if alert.get('current_lowest_price'):
                        st.metric('当前最低价格', f'¥{alert["current_lowest_price"]:.0f}')

                    if alert.get('note'):
                        st.info(f"📝 备注: {alert['note']}")

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if alert['status'] == 'active':
                            if st.button('❌ 取消警报', key=f'cancel_{alert["id"]}'):
                                alert_manager.cancel_alert(alert['id'])
                                st.rerun()
                    with col_btn2:
                        if st.button('🗑️ 删除', key=f'delete_{alert["id"]}'):
                            alert_manager.delete_alert(alert['id'])
                            st.rerun()

            if st.button('🧹 清除所有警报', type='secondary'):
                alert_manager.clear_all_alerts()
                st.success('已清除所有警报')
                st.rerun()

    with tab_alert3:
        st.markdown('### 价格下跌概率分析')

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            prob_route = st.selectbox('航线', get_routes(), key='prob_route')
        with col_p2:
            prob_target = st.number_input('目标价格', min_value=100, value=500, step=50, key='prob_target')
        with col_p3:
            prob_date = st.date_input('出发日期', value=datetime.now() + timedelta(days=30), key='prob_date')

        if st.button('📊 分析价格下跌概率', key='analyze_prob'):
            with st.spinner('正在进行蒙特卡洛模拟...'):
                result = get_price_drop_probability(prob_route, prob_target, prob_date.strftime('%Y-%m-%d'), model)

                col_pr1, col_pr2, col_pr3 = st.columns(3)
                col_pr1.metric('当前预测价格', f'¥{result["current_price"]:.0f}')
                col_pr2.metric('价格达到目标概率', f'{result["drop_probability"]}%')
                col_pr3.metric('预期最低价格', f'¥{result["expected_min_price"]:.0f}')

                st.info(f"📈 价格区间预测: ¥{result['price_range'][0]:.0f} - ¥{result['price_range'][1]:.0f}")

                if result['drop_probability'] >= 70:
                    st.success('✅ 价格达到目标的概率较高，建议设置价格警报等待')
                elif result['drop_probability'] >= 40:
                    st.warning('⚠️ 价格达到目标有一定概率，可以考虑设置警报或当前价格入手')
                else:
                    st.error('❌ 价格达到目标的概率较低，建议当前价格入手或调整目标价格')

def refund_cost_panel(model):
    st.subheader('💰 退改签成本模拟')

    tab_r1, tab_r2, tab_r3 = st.tabs(['舱位对比', '退票场景模拟', '盈亏平衡点分析'])

    with tab_r1:
        col_rf1, col_rf2, col_rf3 = st.columns(3)

        with col_rf1:
            refund_route = st.selectbox('选择航线', get_routes(), key='refund_route')
        with col_rf2:
            refund_date = st.date_input('出发日期', value=datetime.now() + timedelta(days=30), key='refund_date')
        with col_rf3:
            refund_airline = st.selectbox('航空公司', get_airlines(), index=0, key='refund_airline')

        if st.button('🔍 分析舱位选项', type='primary', key='analyze_fares'):
            from prediction import prepare_prediction_data_enhanced

            feature_data = prepare_prediction_data_enhanced(refund_route, refund_date, airline=refund_airline)
            base_price = model.predict_with_xgboost(feature_data)[0]
            lower, upper = predict_price_range(feature_data, model)

            fare_options = compare_fare_options(
                (lower, upper),
                pd.to_datetime(refund_date),
                airline=refund_airline
            )

            st.metric('当前预测经济舱价格', f'¥{base_price:.0f}',
                      delta=f'预测区间: ¥{lower:.0f} - ¥{upper:.0f}')

            for opt in fare_options:
                with st.expander(f"🎫 {opt['fare_name']} - ¥{opt['estimated_price']:.0f} | 灵活度: {opt['flexibility_score']}/100"):
                    col_fo1, col_fo2, col_fo3 = st.columns(3)

                    with col_fo1:
                        st.markdown('**退票费用 (出发前7天)**')
                        st.write(f"退款金额: ¥{opt['refund_info']['refund_amount']:.0f}")
                        st.write(f"手续费: ¥{opt['refund_info']['fee_amount']:.0f} ({opt['refund_info']['fee_rate']}%)")

                    with col_fo2:
                        st.markdown('**改期费用**')
                        st.write(f"改期手续费: ¥{opt['change_info']['change_fee']:.0f}")
                        if opt['change_info']['price_difference'] > 0:
                            st.write(f"补差价: ¥{opt['change_info']['price_difference']:.0f}")

                    with col_fo3:
                        st.markdown('**灵活度评分**')
                        st.progress(opt['flexibility_score'] / 100)
                        st.write(opt['recommendation'])

    with tab_r2:
        st.markdown('### 退票场景模拟')

        col_rs1, col_rs2, col_rs3 = st.columns(3)
        with col_rs1:
            sim_price = st.number_input('机票价格 (¥)', min_value=100, value=1000, step=100, key='sim_price')
        with col_rs2:
            sim_fare = st.selectbox('舱位类型', list(FARE_TYPES.keys()),
                                    format_func=lambda x: FARE_TYPES[x]['name'], key='sim_fare')
        with col_rs3:
            sim_date = st.date_input('出发日期', value=datetime.now() + timedelta(days=14), key='sim_date')

        if st.button('📊 模拟退票场景', key='simulate_refund'):
            scenarios = simulate_refund_scenarios(sim_price, sim_fare, pd.to_datetime(sim_date))

            fig = go.Figure()

            scenario_labels = [s['scenario'] for s in scenarios]
            refund_amounts = [s['refund_amount'] for s in scenarios]
            fee_amounts = [s['fee_amount'] for s in scenarios]

            fig.add_trace(go.Bar(
                x=scenario_labels,
                y=refund_amounts,
                name='退款金额',
                marker_color='green'
            ))

            fig.add_trace(go.Bar(
                x=scenario_labels,
                y=fee_amounts,
                name='手续费',
                marker_color='red'
            ))

            fig.update_layout(
                title='不同时间点退票金额对比',
                barmode='stack',
                yaxis_title='金额 (¥)',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            for sc in scenarios:
                st.write(f"**{sc['scenario']}**: 退款 ¥{sc['refund_amount']:.0f}, 手续费 ¥{sc['fee_amount']:.0f}")

    with tab_r3:
        st.markdown('### 盈亏平衡点分析')
        st.info('分析折扣票 vs 全价票的退票风险，帮助决策是否值得为灵活性支付溢价')

        col_be1, col_be2 = st.columns(2)
        with col_be1:
            be_discount_price = st.number_input('折扣票价格', min_value=100, value=800, step=50, key='be_discount')
            be_discount_type = st.selectbox('折扣票类型', ['economy_discount', 'economy_standard'],
                                            format_func=lambda x: FARE_TYPES[x]['name'], key='be_discount_type')
        with col_be2:
            be_full_price = st.number_input('全价票价格', min_value=100, value=1200, step=50, key='be_full')
            be_full_type = st.selectbox('全价票类型', ['economy_flexible', 'business_standard'],
                                        format_func=lambda x: FARE_TYPES[x]['name'], key='be_full_type')

        be_date = st.date_input('出发日期', value=datetime.now() + timedelta(days=14), key='be_date')

        if st.button('📈 计算盈亏平衡点', key='calc_breakeven'):
            result = calculate_breakeven_point(
                be_discount_price, be_full_price,
                be_discount_type, be_full_type,
                pd.to_datetime(be_date)
            )

            col_be_r1, col_be_r2, col_be_r3 = st.columns(3)
            col_be_r1.metric('价格差价', f'¥{result["price_savings"]:.0f}')
            col_be_r2.metric('退款差额', f'¥{result["refund_diff"]:.0f}')
            col_be_r3.metric('盈亏平衡概率', f'{result["breakeven_probability"]}%')

            st.warning(result['recommendation'])

            if result['breakeven_probability'] <= 50:
                st.success('✅ 如果退票概率较低，选择折扣票更划算')
            else:
                st.warning('⚠️ 如果退票概率较高，考虑选择全价票')

def display_enhanced_welcome():
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info('📅 **航司活动日历**\n\n会员日、周年庆、促销活动智能识别')

    with col2:
        st.info('📊 **风险价值模型**\n\nVaR量化等待风险与期望收益')

    with col3:
        st.info('🛢️ **油价期货曲线**\n\n预测燃油附加费趋势')

    with col4:
        st.info('🤝 **多城市联运**\n\n中转航线智能推荐，节省费用')

    st.markdown('---')

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.info('🔔 **价格警报**\n\n目标价格达到时自动通知')

    with col6:
        st.info('💰 **退改签成本**\n\n舱位对比，模拟退票损失')

    with col7:
        st.info('🌍 **开口程支持**\n\nA→B→C多目的地查询')

    with col8:
        st.info('📈 **双模型融合**\n\nXGBoost + Prophet增强预测')

    st.markdown('---')

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader('✨ v3.0 新增功能')
        st.markdown("""
        **v3.0 升级内容:**

        1. **多城市联运推荐**
           - 智能中转航线搜索（支持0-2次中转）
           - 开口程/多目的地查询 (A→B→C)
           - 价格-时间-中转次数综合评分排序
           - 直飞vs中转性价比对比

        2. **价格警报系统**
           - 自定义目标价格和航线
           - 价格达到阈值时自动通知
           - 价格下跌概率蒙特卡洛模拟
           - 警报状态管理（活动/触发/取消/过期）

        3. **退改签成本模拟**
           - 6种舱位类型对比（折扣经济舱到头等舱）
           - 退票场景模拟（不同时间点的损失对比）
           - 改期费用计算
           - 折扣票vs全价票盈亏平衡点分析
        """)

    with col2:
        st.subheader('🎯 快速开始')
        st.markdown("""
        **单程票价预测:**
        1. 左侧选择**航线**和**航空公司**
        2. 选择**出发日期**
        3. 点击**开始预测**

        **其他功能:**
        - 切换顶部标签页访问多城市联运、价格警报、退改签分析
        """)

def display_enhanced_results(result, confidence_level, show_risk_details, show_oil_analysis, show_events):
    best_time = result['best_time']
    trend = result['trend']
    risk_assessment = result['risk_assessment']
    oil_analysis = result['oil_analysis']
    upcoming_events = result['upcoming_events']

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader('📈 票价走势预测')

        price_preds = result['price_predictions']

        if len(price_preds) > 0:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=price_preds['search_date'],
                y=price_preds['predicted_price'],
                mode='lines+markers',
                name='预测价格',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=6)
            ))

            fig.add_trace(go.Scatter(
                x=price_preds['search_date'],
                y=price_preds['price_upper'],
                mode='lines',
                name=f'价格上限 ({confidence_level}%)',
                line=dict(color='rgba(31, 119, 180, 0.3)', width=1, dash='dash')
            ))

            fig.add_trace(go.Scatter(
                x=price_preds['search_date'],
                y=price_preds['price_lower'],
                mode='lines',
                name=f'价格下限 ({confidence_level}%)',
                line=dict(color='rgba(31, 119, 180, 0.3)', width=1, dash='dash'),
                fill='tonexty'
            ))

            best_point = price_preds.loc[price_preds['predicted_price'].idxmin()]
            fig.add_trace(go.Scatter(
                x=[best_point['search_date']],
                y=[best_point['predicted_price']],
                mode='markers',
                name='最佳购买点',
                marker=dict(color='red', size=15, symbol='star')
            ))

            fig.update_layout(
                title=f'{result["route"]} - {result["airline"]} 票价预测走势',
                xaxis_title='购票日期',
                yaxis_title='预测票价 (¥)',
                hovermode='x unified',
                height=450,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning('无法生成价格预测图表')

    with col2:
        st.subheader('🎯 购票建议')

        urgency_colors = {
            '高': '#ff4444',
            '中': '#ffbb33',
            '低': '#00C851'
        }

        risk_colors = {
            '低风险': '#00C851',
            '中低风险': '#00C851',
            '中等风险': '#ffbb33',
            '中高风险': '#ff8800',
            '高风险': '#ff4444'
        }

        urgency_color = urgency_colors.get(best_time['urgency'], '#333333')
        risk_color = risk_colors.get(risk_assessment['risk_level'], '#333333') if risk_assessment else '#333333'

        st.markdown(f"""
        <div style="padding: 20px; border-radius: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h3 style="margin-top: 0; color: white;">{best_time['recommendation']}</h3>
            <p style="font-size: 14px; opacity: 0.9;">紧急程度: <span style="color: {urgency_color}; font-weight: bold; background: white; padding: 2px 8px; border-radius: 4px;">{best_time['urgency']}</span></p>
            <p style="font-size: 13px; line-height: 1.5;">{best_time['reason']}</p>
        </div>
        """, unsafe_allow_html=True)

        if risk_assessment:
            st.markdown(f"""
            <div style="padding: 15px; border-radius: 10px; background-color: {risk_color}20; margin-top: 15px; border: 2px solid {risk_color};">
                <p style="margin: 0; color: {risk_color}; font-weight: bold;">⚠️ 风险等级: {risk_assessment['risk_level']}</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">风险收益比: {risk_assessment['risk_reward_ratio']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('---')

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(
                '当前预测价格',
                f'¥{best_time["current_price"]:.0f}',
                help=f'预测区间: ¥{best_time["current_price_lower"]:.0f} - ¥{best_time["current_price_upper"]:.0f}'
            )
        with col_m2:
            st.metric(
                '最佳预测价格',
                f'¥{best_time["best_price"]:.0f}',
                delta=f'-{best_time["potential_savings_percent"]:.1f}%',
                help=f'预测区间: ¥{best_time["best_price_lower"]:.0f} - ¥{best_time["best_price_upper"]:.0f}'
            )

        st.metric(
            '预计可节省',
            f'¥{best_time["potential_savings"]:.0f}',
            delta=f'潜在优惠'
        )

    st.markdown('---')

    if show_risk_details and risk_assessment:
        st.subheader('📊 风险价值 (VaR) 分析')

        risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)

        with risk_col1:
            st.metric(
                '95% VaR',
                f'{risk_assessment["var_95"]:.2f}%',
                help='95%置信度下的最大预期损失'
            )

        with risk_col2:
            st.metric(
                '99% VaR',
                f'{risk_assessment["var_99"]:.2f}%',
                help='99%置信度下的最大预期损失'
            )

        with risk_col3:
            st.metric(
                '日波动率',
                f'{risk_assessment["daily_volatility"]:.2f}%',
                help='价格日波动幅度'
            )

        with risk_col4:
            st.metric(
                '夏普比率',
                f'{risk_assessment["sharpe_ratio"]:.2f}',
                help='风险调整后收益指标'
            )

        risk_col5, risk_col6, risk_col7 = st.columns(3)

        with risk_col5:
            st.metric(
                '预期最大收益',
                f'¥{best_time["current_price"] * risk_assessment["potential_gain_percent"] / 100:.0f}',
                delta=f'{risk_assessment["potential_gain_percent"]:.1f}%'
            )

        with risk_col6:
            st.metric(
                '预期最大损失',
                f'¥{best_time["current_price"] * risk_assessment["potential_loss_percent"] / 100:.0f}',
                delta=f'-{risk_assessment["potential_loss_percent"]:.1f}%'
            )

        with risk_col7:
            st.metric(
                '风险收益比',
                f'{risk_assessment["risk_reward_ratio"]:.2f}',
                help='>1表示风险可控'
            )

        if result['risk_report'] and 'monte_carlo' in result['risk_report']:
            mc = result['risk_report']['monte_carlo']

            with st.expander('📈 蒙特卡洛模拟详情'):
                mc_col1, mc_col2, mc_col3 = st.columns(3)

                with mc_col1:
                    st.info(f"""
                    **价格分布**
                    • 均值: ¥{mc['mean_final_price']:.0f}
                    • 中位数: ¥{mc['median_final_price']:.0f}
                    • VaR 95%: ¥{mc['var_95']:.0f}
                    """)

                with mc_col2:
                    st.info(f"""
                    **概率分析**
                    • 价格下跌>10%: {mc['prob_price_lower_10']*100:.1f}%
                    • 价格上涨>10%: {mc['prob_price_higher_10']*100:.1f}%
                    • 期望损失: ¥{mc['expected_shortfall']:.0f}
                    """)

                with mc_col3:
                    sim_paths = mc['simulation_results']
                    fig_mc = go.Figure()
                    for i in range(min(100, sim_paths.shape[1])):
                        fig_mc.add_trace(go.Scatter(
                            x=list(range(sim_paths.shape[0])),
                            y=sim_paths[:, i],
                            mode='lines',
                            line=dict(width=0.5, color='rgba(31, 119, 180, 0.3)'),
                            showlegend=False
                        ))
                    fig_mc.update_layout(
                        title='价格模拟路径 (100条)',
                        height=200,
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig_mc, use_container_width=True)

    st.markdown('---')

    info_col1, info_col2, info_col3, info_col4 = st.columns(4)

    with info_col1:
        st.info(f"""
        **航线信息**

        {result['route']}

        航空公司: {result['airline']}

        出发日期: {result['departure_date'].strftime('%Y-%m-%d')}
        """)

    with info_col2:
        from prediction import is_holiday
        holiday_flag = is_holiday(result['departure_date'])
        holiday_text = '是' if holiday_flag >= 1 else ('周末' if holiday_flag >= 0.5 else '否')
        st.info(f"""
        **时间信息**

        距离出发: {result['days_to_departure']} 天

        节假日/周末: {holiday_text}

        价格趋势: {trend['trend']}
        """)

    with info_col3:
        if oil_analysis:
            st.info(f"""
            **油价信息**

            当前油价: ${oil_analysis['current_spot']:.1f}/桶

            市场状态: {oil_analysis['market_state']}

            预期变化: {oil_analysis['price_trend']}
            """)
        else:
            st.info('油价信息不可用')

    with info_col4:
        st.info(f"""
        **最佳购买日期**

        {best_time['best_date'].strftime('%Y-%m-%d')}

        提前 {(result['departure_date'] - best_time['best_date']).days} 天

        价格日变化: ¥{trend['daily_change']:.1f}
        """)

    if show_oil_analysis and oil_analysis:
        st.markdown('---')
        st.subheader('🛢️ 油价与燃油附加费分析')

        oil_col1, oil_col2 = st.columns([1, 2])

        with oil_col1:
            futures_curve = get_current_futures_curve()
            fig_oil = go.Figure()

            fig_oil.add_trace(go.Bar(
                x=futures_curve['months'].astype(str) + 'M',
                y=futures_curve['futures_price'],
                name='期货价格',
                marker_color='orange'
            ))

            fig_oil.update_layout(
                title='原油期货价格曲线',
                xaxis_title='合约月份',
                yaxis_title='价格 ($/桶)',
                height=300
            )

            st.plotly_chart(fig_oil, use_container_width=True)

        with oil_col2:
            fuel_trend = result['fuel_trend']
            if len(fuel_trend) > 0:
                fig_fuel = go.Figure()

                fig_fuel.add_trace(go.Scatter(
                    x=fuel_trend['date'],
                    y=fuel_trend['fuel_surcharge'],
                    mode='lines+markers',
                    name='预测燃油附加费',
                    line=dict(color='red', width=2),
                    marker=dict(size=8)
                ))

                fig_fuel.add_trace(go.Scatter(
                    x=fuel_trend['date'],
                    y=fuel_trend['oil_price'],
                    mode='lines',
                    name='原油价格 ($)',
                    line=dict(color='orange', width=2, dash='dash'),
                    yaxis='y2'
                ))

                fig_fuel.update_layout(
                    title='燃油附加费趋势预测',
                    xaxis_title='日期',
                    yaxis_title='燃油附加费 (¥)',
                    yaxis2=dict(
                        title='原油价格 ($/桶)',
                        overlaying='y',
                        side='right'
                    ),
                    height=300,
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )

                st.plotly_chart(fig_fuel, use_container_width=True)

        oil_details_col1, oil_details_col2, oil_details_col3 = st.columns(3)

        with oil_details_col1:
            st.metric(
                '当前现货价格',
                f'${oil_analysis["current_spot"]:.2f}',
                help='当前原油现货价格'
            )

        with oil_details_col2:
            st.metric(
                '12个月期货价格',
                f'${oil_analysis["twelve_month_future"]:.2f}',
                delta=f'{oil_analysis["expected_change_percent"]:.1f}%',
                help='市场预期12个月后油价'
            )

        with oil_details_col3:
            market_state_cn = '期货升水' if oil_analysis['market_state'] == 'contango' else '期货贴水'
            st.metric(
                '市场结构',
                market_state_cn,
                help='Contango=远期升水, Backwardation=远期贴水'
            )

    if show_events and upcoming_events:
        st.markdown('---')
        st.subheader('📅 航司活动日历')

        events_df = pd.DataFrame(upcoming_events)
        if len(events_df) > 0:
            events_df['date'] = events_df['date'].dt.strftime('%Y-%m-%d')
            events_df = events_df.rename(columns={
                'airline': '航空公司',
                'event': '活动类型',
                'date': '活动日期',
                'days_to_event': '距今天数'
            })

            st.dataframe(
                events_df[['航空公司', '活动类型', '活动日期', '距今天数']],
                use_container_width=True,
                hide_index=True
            )

        with st.expander('📆 查看完整航司活动日历'):
            calendar_summary = get_event_calendar_summary()
            calendar_pivot = calendar_summary.pivot(
                index='airline',
                columns='month',
                values='member_day'
            )
            calendar_pivot.columns = [f'{m}月' for m in calendar_pivot.columns]
            st.dataframe(calendar_pivot, use_container_width=True)

            st.markdown("""
            **说明:**
            - 表格显示各航空公司每月会员日
            - 会员日通常有专属折扣和积分加倍
            - 建议在会员日前后购票以获取最优价格
            """)

    st.markdown('---')

    with st.expander('📊 详细预测数据'):
        if len(result['price_predictions']) > 0:
            display_df = result['price_predictions'].copy()
            display_df['search_date'] = display_df['search_date'].dt.strftime('%Y-%m-%d')
            display_df = display_df.rename(columns={
                'search_date': '购票日期',
                'booking_days': '提前预订天数',
                'predicted_price': '预测价格',
                'price_lower': '价格下限',
                'price_upper': '价格上限'
            })
            st.dataframe(display_df, use_container_width=True)

    with st.expander('💡 购票小贴士'):
        st.markdown("""
        **增强版购票建议:**

        1. **关注航司会员日**
           - 中国国航: 每月12日
           - 东方航空: 每月18日
           - 南方航空: 每月28日
           - 会员日通常有专属折扣，建议在这些日期购票

        2. **风险收益评估**
           - 风险收益比 > 2: 强烈建议等待
           - 风险收益比 1-2: 可以谨慎等待
           - 风险收益比 < 1: 建议立即购买

        3. **油价趋势判断**
           - 期货升水(Contango): 市场预期油价上涨，建议尽早购票锁定价格
           - 期货贴水(Backwardation): 市场预期油价下跌，可以考虑等待

        4. **提前预订策略**
           - 国内航班: 提前30-45天通常价格最优
           - 节假日航班: 提前60天预订
           - 临近出发7天内: 价格通常快速上涨

        5. **多城市联运**
           - 热门航线直飞贵时，可考虑中转方案
           - 开口程(A→B→C)比分段预订更便宜
           - 权衡中转时间和价格节省

        6. **退改签成本**
           - 行程不确定时，考虑购买更灵活的舱位
           - 对比折扣票和全价票的盈亏平衡点
           - 使用退改签模拟功能评估不同方案

        **免责声明**: 本系统预测仅供参考，实际价格以航空公司官网为准。
        """)

def display_multi_city_results(itineraries, origin, destination, date):
    st.success(f'找到 {len(itineraries)} 条航线推荐')

    for idx, itin in enumerate(itineraries, 1):
        with st.container():
            col_mcr1, col_mcr2, col_mcr3, col_mcr4 = st.columns([3, 2, 2, 2])

            with col_mcr1:
                route_str = ' → '.join([f"{s[0]}-{s[1]}" for s in itin['segments']])
                st.markdown(f"**{idx}. {itin['type']}**")
                st.write(f"📍 {route_str}")
                if itin['transfer_count'] > 0:
                    st.write(f"🔄 中转: {itin['transfer_count']}次 | ⏱️ 总时长: {itin['estimated_duration']:.1f}h")
                    if 'transfer_time' in itin:
                        st.write(f"⏳ 中转时间: {itin['transfer_time']}分钟")

            with col_mcr2:
                price_html = f"<h3 style='color: #e74c3c; margin: 0;'>¥{itin['total_price']:.0f}</h3>"
                st.markdown(price_html, unsafe_allow_html=True)
                if 'savings_vs_direct' in itin and itin['savings_vs_direct'] > 0:
                    st.success(f"💰 比直飞省 {itin['savings_vs_direct']}%")

            with col_mcr3:
                score = itin.get('score', 0)
                st.write(f"📊 综合评分: {score:.0f}")
                st.write(f"📏 每公里价格: ¥{itin.get('price_per_km', 0):.2f}")

            with col_mcr4:
                if itin['type'] == '直飞':
                    st.info('✅ 直飞首选')
                elif itin['type'] == '中转':
                    st.warning('⏳ 中转换乘')
                else:
                    st.error('🔄 双中转')

            if 'segment_prices' in itin:
                with st.expander('查看航段详情'):
                    for seg in itin['segment_prices']:
                        st.write(f"  • {seg['segment']}: ¥{seg['price']:.0f}")

            st.markdown('---')

if __name__ == '__main__':
    main()
