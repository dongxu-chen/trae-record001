import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random


ABANDONMENT_REASONS = {
    "价格敏感": {
        "weight": 0.35,
        "sub_reasons": ["找到更低价格", "等待促销活动", "总价超出预算", "优惠券不可用"],
    },
    "运费问题": {
        "weight": 0.25,
        "sub_reasons": ["运费过高", "不满足免运费门槛", "配送时间过长", "不支持指定配送"],
    },
    "登录门槛": {
        "weight": 0.18,
        "sub_reasons": ["强制注册账号", "验证码收不到", "第三方登录失败", "忘记密码"],
    },
    "支付障碍": {
        "weight": 0.12,
        "sub_reasons": ["支付方式不支持", "支付页面加载慢", "支付安全担忧", "银行卡限额"],
    },
    "比较犹豫": {
        "weight": 0.10,
        "sub_reasons": ["需要对比其他商品", "等待家人确认", "收藏备用", "浏览后离开"],
    },
}

BEHAVIOR_EVENTS = ["浏览商品", "查看详情", "加入购物车", "查看购物车", "修改数量", "移除商品", "去结算", "填写地址", "选择支付", "确认支付", "支付成功"]

USER_SEGMENTS = ["新用户", "回访用户", "活跃用户", "沉睡用户", "VIP用户"]

PRODUCT_CATEGORIES = ["数码电子", "服饰鞋包", "家居日用", "美妆护肤", "食品饮料", "母婴用品", "运动户外", "图书文具"]


def _weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def _generate_abandonment_reason():
    reasons = list(ABANDONMENT_REASONS.keys())
    weights = [ABANDONMENT_REASONS[r]["weight"] for r in reasons]
    reason = _weighted_choice(reasons, weights)
    sub = random.choice(ABANDONMENT_REASONS[reason]["sub_reasons"])
    return reason, sub


def _generate_behavior_path(completed: bool, segment: str):
    path = ["浏览商品", "查看详情", "加入购物车"]

    if completed:
        path += ["查看购物车", "去结算", "填写地址", "选择支付", "确认支付", "支付成功"]
    else:
        extra = random.choices(
            ["查看购物车", "修改数量", "移除商品", "去结算", "填写地址", "选择支付"],
            weights=[0.35, 0.20, 0.10, 0.20, 0.10, 0.05],
            k=random.randint(1, 3),
        )
        path += extra

    if segment == "VIP用户" and not completed:
        if "去结算" not in path and random.random() < 0.4:
            path.append("去结算")

    return path


SURVEY_QUESTIONS = {
    "放弃主因": ["价格太贵", "运费不合理", "需要注册太麻烦", "支付方式不支持", "还在犹豫比较", "其他"],
    "价格感受": ["非常贵，超出预算", "偏贵，但可以接受", "价格合适", "很划算"],
    "回归意愿": ["有优惠就回来", "降运费就回来", "简化流程就回来", "可能不会回来", "肯定会回来"],
}

SURVEY_REASONS_MAP = {
    "价格敏感": "价格太贵",
    "运费问题": "运费不合理",
    "登录门槛": "需要注册太麻烦",
    "支付障碍": "支付方式不支持",
    "比较犹豫": "还在犹豫比较",
}


def _generate_survey_response(abandonment_reason: str, cart_value: float, shipping_fee: float, segment: str):
    if random.random() < 0.55:
        return None

    mapped = SURVEY_REASONS_MAP.get(abandonment_reason, "其他")
    if random.random() < 0.70:
        main_reason = mapped
    else:
        main_reason = random.choice(SURVEY_QUESTIONS["放弃主因"])

    if cart_value > 500:
        price_feel = random.choices(SURVEY_QUESTIONS["价格感受"], weights=[0.4, 0.35, 0.20, 0.05])[0]
    elif cart_value > 100:
        price_feel = random.choices(SURVEY_QUESTIONS["价格感受"], weights=[0.15, 0.35, 0.40, 0.10])[0]
    else:
        price_feel = random.choices(SURVEY_QUESTIONS["价格感受"], weights=[0.05, 0.20, 0.50, 0.25])[0]

    if shipping_fee > 15:
        return_will = random.choices(SURVEY_QUESTIONS["回归意愿"], weights=[0.30, 0.35, 0.15, 0.10, 0.10])[0]
    elif segment == "新用户":
        return_will = random.choices(SURVEY_QUESTIONS["回归意愿"], weights=[0.25, 0.15, 0.30, 0.20, 0.10])[0]
    else:
        return_will = random.choices(SURVEY_QUESTIONS["回归意愿"], weights=[0.20, 0.20, 0.25, 0.15, 0.20])[0]

    return {
        "survey_main_reason": main_reason,
        "survey_price_feel": price_feel,
        "survey_return_willingness": return_will,
    }


COMPETITOR_NAMES = ["京东", "天猫", "拼多多", "抖音商城"]

INTERVENTION_TYPES = {
    "价格敏感": ["限时8折弹窗", "满减即时生效", "价格保障标签"],
    "运费问题": ["免运费券即时发放", "凑单免运费提醒", "运费减半券"],
    "登录门槛": ["游客结算引导", "一键登录提示", "免验证直接下单"],
    "支付障碍": ["支付方式推荐", "分期免息提示", "安全认证展示"],
    "比较犹豫": ["库存紧迫提示", "评价背书弹窗", "价格锁定1小时"],
}


def _generate_competitor_prices(cart_value: float, category: str, price_sensitivity_score: float):
    n_competitors = random.randint(2, 4)
    selected = random.sample(COMPETITOR_NAMES, n_competitors)
    prices = {}
    for comp in selected:
        base_ratio = random.uniform(0.85, 1.15)
        if price_sensitivity_score > 0.5 and random.random() < 0.4:
            base_ratio = random.uniform(0.75, 0.95)
        prices[comp] = round(cart_value * base_ratio, 2)

    lowest_comp = min(prices, key=prices.get)
    lowest_price = prices[lowest_comp]
    price_diff = round(cart_value - lowest_price, 2)
    price_diff_pct = round(price_diff / cart_value * 100, 2) if cart_value > 0 else 0
    has_lower_competitor = any(v < cart_value for v in prices.values())

    return {
        "competitor_prices": str(prices),
        "lowest_competitor": lowest_comp,
        "lowest_competitor_price": lowest_price,
        "price_diff_vs_lowest": price_diff,
        "price_diff_pct_vs_lowest": price_diff_pct,
        "has_lower_competitor": has_lower_competitor,
        "n_competitors_checked": n_competitors,
    }


def _generate_behavioral_features(completed: bool, segment: str, cart_value: float):
    if completed:
        cart_page_time = random.randint(15, 120)
        scroll_depth = random.uniform(0.6, 1.0)
        mouse_leave_count = random.randint(0, 1)
        tab_switch_count = random.randint(0, 1)
        cart_page_visits = random.randint(1, 2)
        hover_checkout_btn = random.uniform(0, 2)
        price_page_dwell = random.randint(0, 5)
    else:
        cart_page_time = random.randint(30, 600)
        scroll_depth = random.uniform(0.2, 0.8)
        mouse_leave_count = random.randint(1, 5)
        tab_switch_count = random.randint(1, 4)
        cart_page_visits = random.randint(2, 6)
        hover_checkout_btn = random.uniform(2, 15)
        price_page_dwell = random.randint(10, 120)

    if segment == "新用户":
        cart_page_visits += random.randint(0, 2)
        mouse_leave_count += random.randint(0, 2)
    elif segment == "VIP用户":
        cart_page_visits = max(1, cart_page_visits - 1)
        mouse_leave_count = max(0, mouse_leave_count - 1)

    hesitation_score = (
        (1 if cart_page_time > 120 else 0)
        + (1 if scroll_depth < 0.5 else 0)
        + (1 if mouse_leave_count > 2 else 0)
        + (1 if tab_switch_count > 2 else 0)
        + (1 if cart_page_visits > 3 else 0)
        + (1 if hover_checkout_btn > 8 else 0)
        + (1 if price_page_dwell > 60 else 0)
    )

    return {
        "cart_page_time_sec": cart_page_time,
        "scroll_depth": round(scroll_depth, 3),
        "mouse_leave_count": mouse_leave_count,
        "tab_switch_count": tab_switch_count,
        "cart_page_visits": cart_page_visits,
        "hover_checkout_btn_sec": round(hover_checkout_btn, 1),
        "price_page_dwell_sec": price_page_dwell,
        "hesitation_score": hesitation_score,
    }


def _generate_intervention_event(completed: bool, abandonment_reason: str, price_sensitivity_score: float):
    if completed:
        return {
            "intervention_triggered": False,
            "intervention_type": None,
            "intervention_timing_sec": None,
            "intervention_accepted": None,
            "intervention_converted": None,
        }

    triggered = random.random() < 0.65
    if not triggered:
        return {
            "intervention_triggered": False,
            "intervention_type": None,
            "intervention_timing_sec": None,
            "intervention_accepted": None,
            "intervention_converted": None,
        }

    if abandonment_reason and abandonment_reason in INTERVENTION_TYPES:
        intervention_type = random.choice(INTERVENTION_TYPES[abandonment_reason])
    else:
        intervention_type = random.choice(["限时优惠弹窗", "免运费券", "客服介入"])

    timing = random.randint(3, 30)

    accept_rate = 0.35
    if price_sensitivity_score > 0.5:
        if "折" in intervention_type or "减" in intervention_type:
            accept_rate = 0.55
    if "免运费" in intervention_type or "运费" in intervention_type:
        accept_rate = 0.50

    accepted = random.random() < accept_rate

    convert_rate = 0.40 if accepted else 0.02
    converted = random.random() < convert_rate

    return {
        "intervention_triggered": triggered,
        "intervention_type": intervention_type,
        "intervention_timing_sec": timing,
        "intervention_accepted": accepted,
        "intervention_converted": converted,
    }


def generate_user_sessions(n_sessions=5000, start_date="2025-01-01", end_date="2025-06-30"):
    np.random.seed(42)
    random.seed(42)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_range_days = (end - start).days

    segment_weights = [0.25, 0.25, 0.20, 0.15, 0.15]

    base_completion_rates = {
        "新用户": 0.15,
        "回访用户": 0.30,
        "活跃用户": 0.45,
        "沉睡用户": 0.10,
        "VIP用户": 0.60,
    }

    user_price_sensitivity = {}

    sessions = []

    for i in range(n_sessions):
        session_id = f"S{i + 1:06d}"
        user_id = f"U{random.randint(1, n_sessions // 3):06d}"

        if user_id not in user_price_sensitivity:
            user_price_sensitivity[user_id] = round(np.random.beta(2, 5), 4)
        price_sensitivity_score = user_price_sensitivity[user_id]

        session_ts = start + timedelta(
            days=random.randint(0, date_range_days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        segment = _weighted_choice(USER_SEGMENTS, segment_weights)
        completion_rate = base_completion_rates[segment]

        month_progress = (session_ts - start).days / date_range_days
        completion_rate *= 1 + 0.1 * month_progress

        completed = random.random() < completion_rate

        behavior_path = _generate_behavior_path(completed, segment)

        abandonment_reason = None
        abandonment_sub_reason = None
        if not completed:
            abandonment_reason, abandonment_sub_reason = _generate_abandonment_reason()

        category = random.choice(PRODUCT_CATEGORIES)

        if category in ["数码电子"]:
            base_price = random.uniform(500, 8000)
        elif category in ["服饰鞋包", "美妆护肤"]:
            base_price = random.uniform(50, 1500)
        elif category in ["食品饮料", "图书文具"]:
            base_price = random.uniform(10, 200)
        else:
            base_price = random.uniform(30, 3000)

        cart_value = round(base_price * random.uniform(0.8, 3.5), 2)
        cart_items = random.randint(1, 8)

        shipping_fee = round(random.uniform(0, 30), 2) if cart_value < 99 else 0

        has_coupon = random.random() < 0.35
        coupon_value = round(random.uniform(5, 50), 2) if has_coupon else 0

        device = random.choices(["移动端", "PC端", "平板"], weights=[0.55, 0.35, 0.10])[0]

        ab_group = random.choice(["control", "variant_A", "variant_B"])

        session_duration = random.randint(30, 3600) if not completed else random.randint(120, 1800)

        pages_viewed = random.randint(2, 15) if not completed else random.randint(3, 20)

        survey_main_reason = None
        survey_price_feel = None
        survey_return_willingness = None
        if not completed:
            survey = _generate_survey_response(abandonment_reason, cart_value, shipping_fee, segment)
            if survey:
                survey_main_reason = survey["survey_main_reason"]
                survey_price_feel = survey["survey_price_feel"]
                survey_return_willingness = survey["survey_return_willingness"]

        comp = _generate_competitor_prices(cart_value, category, price_sensitivity_score)

        behav = _generate_behavioral_features(completed, segment, cart_value)

        interven = _generate_intervention_event(completed, abandonment_reason, price_sensitivity_score)

        sessions.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "session_timestamp": session_ts,
                "date": session_ts.strftime("%Y-%m-%d"),
                "week": session_ts.strftime("%Y-W%W"),
                "month": session_ts.strftime("%Y-%m"),
                "user_segment": segment,
                "behavior_path": " → ".join(behavior_path),
                "last_event": behavior_path[-1],
                "completed": completed,
                "abandonment_reason": abandonment_reason,
                "abandonment_sub_reason": abandonment_sub_reason,
                "product_category": category,
                "cart_value": cart_value,
                "cart_items": cart_items,
                "shipping_fee": shipping_fee,
                "has_coupon": has_coupon,
                "coupon_value": coupon_value,
                "device": device,
                "ab_group": ab_group,
                "session_duration_sec": session_duration,
                "pages_viewed": pages_viewed,
                "price_sensitivity_score": price_sensitivity_score,
                "survey_main_reason": survey_main_reason,
                "survey_price_feel": survey_price_feel,
                "survey_return_willingness": survey_return_willingness,
                "competitor_prices": comp["competitor_prices"],
                "lowest_competitor": comp["lowest_competitor"],
                "lowest_competitor_price": comp["lowest_competitor_price"],
                "price_diff_vs_lowest": comp["price_diff_vs_lowest"],
                "price_diff_pct_vs_lowest": comp["price_diff_pct_vs_lowest"],
                "has_lower_competitor": comp["has_lower_competitor"],
                "n_competitors_checked": comp["n_competitors_checked"],
                "cart_page_time_sec": behav["cart_page_time_sec"],
                "scroll_depth": behav["scroll_depth"],
                "mouse_leave_count": behav["mouse_leave_count"],
                "tab_switch_count": behav["tab_switch_count"],
                "cart_page_visits": behav["cart_page_visits"],
                "hover_checkout_btn_sec": behav["hover_checkout_btn_sec"],
                "price_page_dwell_sec": behav["price_page_dwell_sec"],
                "hesitation_score": behav["hesitation_score"],
                "intervention_triggered": interven["intervention_triggered"],
                "intervention_type": interven["intervention_type"],
                "intervention_timing_sec": interven["intervention_timing_sec"],
                "intervention_accepted": interven["intervention_accepted"],
                "intervention_converted": interven["intervention_converted"],
            }
        )

    return pd.DataFrame(sessions)


def generate_ab_test_data(sessions_df):
    ab_results = []

    for group in sessions_df["ab_group"].unique():
        group_df = sessions_df[sessions_df["ab_group"] == group]
        total = len(group_df)
        completed = group_df["completed"].sum()
        completion_rate = completed / total if total > 0 else 0
        avg_cart_value = group_df["cart_value"].mean()
        avg_session_duration = group_df["session_duration_sec"].mean()
        avg_pages = group_df["pages_viewed"].mean()

        reason_dist = group_df[group_df["completed"] == False]["abandonment_reason"].value_counts(normalize=True).to_dict() if not group_df["completed"].all() else {}

        ab_results.append(
            {
                "group": group,
                "total_sessions": total,
                "completed": completed,
                "completion_rate": round(completion_rate, 4),
                "abandonment_rate": round(1 - completion_rate, 4),
                "avg_cart_value": round(avg_cart_value, 2),
                "avg_session_duration": round(avg_session_duration, 1),
                "avg_pages_viewed": round(avg_pages, 1),
                "reason_distribution": reason_dist,
            }
        )

    return pd.DataFrame(ab_results)


def get_personalized_strategies(abandonment_reason: str, price_sensitivity_score: float):
    sensitivity_level = "高" if price_sensitivity_score > 0.5 else ("中" if price_sensitivity_score > 0.2 else "低")

    base_strategies = {
        "价格敏感": {
            "高": [
                {"strategy": "限时闪购弹窗", "description": f"针对价格敏感度{sensitivity_level}的用户，弹出限时5分钟8折优惠", "expected_impact": "高", "implementation_effort": "低", "personalized_discount": "8折", "sensitivity_level": sensitivity_level},
                {"strategy": "免息分期+立减", "description": "提供3期免息叠加50元立减，降低单次支付感知", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "3期免息+50减", "sensitivity_level": sensitivity_level},
                {"strategy": "全网比价结果展示", "description": "自动展示3家竞品价格对比，证明本平台最低", "expected_impact": "中", "implementation_effort": "高", "personalized_discount": "价格保障标签", "sensitivity_level": sensitivity_level},
                {"strategy": "阶梯满减即时生效", "description": "当前金额再买X元即可享满减，直接展示可凑单商品", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "满减即时生效", "sensitivity_level": sensitivity_level},
            ],
            "中": [
                {"strategy": "限时优惠倒计时", "description": f"价格敏感度{sensitivity_level}用户，展示24小时专属优惠倒计时", "expected_impact": "高", "implementation_effort": "低", "personalized_discount": "9折限时", "sensitivity_level": sensitivity_level},
                {"strategy": "分期付款选项", "description": "提供6期免息分期降低单次支付压力", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "6期免息", "sensitivity_level": sensitivity_level},
                {"strategy": "价格匹配承诺", "description": "展示'全网最低价保障'标签降低价格顾虑", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "价保标签", "sensitivity_level": sensitivity_level},
            ],
            "低": [
                {"strategy": "会员专属价格", "description": "提示开通会员享专属价，顺带提升粘性", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "会员价", "sensitivity_level": sensitivity_level},
                {"strategy": "品质保障标签", "description": "突出正品保障和售后无忧，弱化价格聚焦价值", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "价值导向", "sensitivity_level": sensitivity_level},
            ],
        },
        "运费问题": {
            "高": [
                {"strategy": "满额免运费+凑单推荐", "description": f"价格敏感度{sensitivity_level}，展示距离免运费还差X元并推荐凑单品", "expected_impact": "高", "implementation_effort": "低", "personalized_discount": "免运费", "sensitivity_level": sensitivity_level},
                {"strategy": "运费补贴券即时发放", "description": "放弃时自动发放运费全额补贴券", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "全免运费券", "sensitivity_level": sensitivity_level},
            ],
            "中": [
                {"strategy": "运费减半券", "description": "发放运费减半优惠券", "expected_impact": "高", "implementation_effort": "低", "personalized_discount": "运费5折", "sensitivity_level": sensitivity_level},
                {"strategy": "多配送方式选择", "description": "提供经济/标准/加急配送，突出经济配送选项", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "经济配送", "sensitivity_level": sensitivity_level},
            ],
            "低": [
                {"strategy": "预估到货时间", "description": "结算页明确展示预计送达日期", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "时效保障", "sensitivity_level": sensitivity_level},
                {"strategy": "运费险赠送", "description": "赠送退换货运费险降低运费顾虑", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "运费险", "sensitivity_level": sensitivity_level},
            ],
        },
        "登录门槛": {
            "高": [
                {"strategy": "游客免登录结算", "description": "允许无需注册直接下单，后续再引导注册", "expected_impact": "高", "implementation_effort": "高", "personalized_discount": "免登录", "sensitivity_level": sensitivity_level},
                {"strategy": "一键微信登录", "description": "强化微信一键登录，减少输入步骤", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "一键登录", "sensitivity_level": sensitivity_level},
            ],
            "中": [
                {"strategy": "渐进式注册", "description": "先完成订单再引导注册，降低前置摩擦", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "渐进注册", "sensitivity_level": sensitivity_level},
                {"strategy": "手机号快捷验证", "description": "短信验证码替代密码登录", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "快捷验证", "sensitivity_level": sensitivity_level},
            ],
            "低": [
                {"strategy": "记住登录状态", "description": "延长登录态有效期，减少重复登录", "expected_impact": "低", "implementation_effort": "低", "personalized_discount": "免重复登录", "sensitivity_level": sensitivity_level},
            ],
        },
        "支付障碍": {
            "高": [
                {"strategy": "支付方式全扩展", "description": "增加花呗、白条、数字人民币等全部支付方式", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "全支付方式", "sensitivity_level": sensitivity_level},
                {"strategy": "支付页面极速预加载", "description": "优化支付页面加载速度到1秒以内", "expected_impact": "高", "implementation_effort": "中", "personalized_discount": "极速支付", "sensitivity_level": sensitivity_level},
            ],
            "中": [
                {"strategy": "信任标识强化", "description": "在支付页面展示安全认证标识和保障承诺", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "安全标识", "sensitivity_level": sensitivity_level},
                {"strategy": "指纹/面容支付", "description": "支持生物识别支付简化流程", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "生物支付", "sensitivity_level": sensitivity_level},
            ],
            "低": [
                {"strategy": "简化支付确认", "description": "减少支付确认步骤到1步", "expected_impact": "低", "implementation_effort": "低", "personalized_discount": "一键支付", "sensitivity_level": sensitivity_level},
            ],
        },
        "比较犹豫": {
            "高": [
                {"strategy": "库存紧迫+限时保留", "description": f"价格敏感度{sensitivity_level}，展示'仅剩X件'且保留购物车价格1小时", "expected_impact": "高", "implementation_effort": "低", "personalized_discount": "价格锁定1h", "sensitivity_level": sensitivity_level},
                {"strategy": "同类热门对比", "description": "内置同品类Top3商品对比，减少外部比价", "expected_impact": "高", "implementation_effort": "高", "personalized_discount": "内置比价", "sensitivity_level": sensitivity_level},
            ],
            "中": [
                {"strategy": "用户评价突出", "description": "在结算页展示优质评价和购买人数", "expected_impact": "中", "implementation_effort": "低", "personalized_discount": "评价背书", "sensitivity_level": sensitivity_level},
                {"strategy": "购物车保留提醒", "description": "24小时后发送'购物车商品还在'提醒", "expected_impact": "中", "implementation_effort": "中", "personalized_discount": "保留提醒", "sensitivity_level": sensitivity_level},
            ],
            "低": [
                {"strategy": "7天无理由退换", "description": "突出展示7天无理由退换降低决策风险", "expected_impact": "低", "implementation_effort": "低", "personalized_discount": "无忧退换", "sensitivity_level": sensitivity_level},
            ],
        },
    }

    return base_strategies.get(abandonment_reason, {}).get(sensitivity_level, [])


def get_intervention_strategies(abandonment_reason: str):
    strategies = {
        "价格敏感": [
            {"strategy": "动态定价策略", "description": "根据用户行为实时调整价格展示，突出优惠力度", "expected_impact": "高", "implementation_effort": "中"},
            {"strategy": "限时优惠弹窗", "description": "用户停留超过30秒未操作时弹出限时折扣", "expected_impact": "高", "implementation_effort": "低"},
            {"strategy": "价格匹配承诺", "description": "展示'全网最低价保障'标签降低价格顾虑", "expected_impact": "中", "implementation_effort": "低"},
            {"strategy": "分期付款选项", "description": "提供免息分期降低单次支付压力", "expected_impact": "高", "implementation_effort": "中"},
        ],
        "运费问题": [
            {"strategy": "满额免运费提醒", "description": "购物车页面实时展示距离免运费还差多少", "expected_impact": "高", "implementation_effort": "低"},
            {"strategy": "运费补贴券", "description": "放弃时自动发放运费补贴券", "expected_impact": "高", "implementation_effort": "中"},
            {"strategy": "多配送方式选择", "description": "提供经济配送/标准配送/加急配送多种选择", "expected_impact": "中", "implementation_effort": "中"},
            {"strategy": "预估到货时间", "description": "结算页明确展示预计送达日期", "expected_impact": "中", "implementation_effort": "低"},
        ],
        "登录门槛": [
            {"strategy": "游客结算", "description": "允许无需注册直接下单购买", "expected_impact": "高", "implementation_effort": "高"},
            {"strategy": "一键登录优化", "description": "强化微信/支付宝等一键登录体验", "expected_impact": "高", "implementation_effort": "中"},
            {"strategy": "渐进式注册", "description": "先完成订单再引导注册，降低前置摩擦", "expected_impact": "中", "implementation_effort": "中"},
            {"strategy": "手机号快捷验证", "description": "短信验证码替代密码登录，缩短登录流程", "expected_impact": "中", "implementation_effort": "低"},
        ],
        "支付障碍": [
            {"strategy": "支付方式扩展", "description": "增加花呗、白条、数字人民币等支付方式", "expected_impact": "中", "implementation_effort": "中"},
            {"strategy": "信任标识强化", "description": "在支付页面展示安全认证标识", "expected_impact": "中", "implementation_effort": "低"},
            {"strategy": "支付页面预加载", "description": "优化支付页面加载速度到2秒以内", "expected_impact": "高", "implementation_effort": "中"},
            {"strategy": "简化支付流程", "description": "减少支付确认步骤，支持指纹/面容支付", "expected_impact": "高", "implementation_effort": "中"},
        ],
        "比较犹豫": [
            {"strategy": "库存紧迫提示", "description": "展示'仅剩X件'营造紧迫感", "expected_impact": "高", "implementation_effort": "低"},
            {"strategy": "用户评价突出", "description": "在结算页展示优质评价和购买人数", "expected_impact": "中", "implementation_effort": "低"},
            {"strategy": "购物车保留提醒", "description": "24小时后发送'购物车商品还在'提醒", "expected_impact": "高", "implementation_effort": "中"},
            {"strategy": "对比功能内置", "description": "提供站内商品对比工具减少外部比价", "expected_impact": "中", "implementation_effort": "高"},
        ],
    }

    return strategies.get(abandonment_reason, [])
