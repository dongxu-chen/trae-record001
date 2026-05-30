import os
import sys
import random
import json
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from features.text_matching import (
    compute_all_features, tokenize, clear_cache,
    title_match_score, category_match, brand_match,
)
from models.lightgbm_model import LambdaMARTRanker
from evaluation.metrics import (
    evaluate_ranking, evaluate_ranking_by_group,
    print_evaluation_results, print_group_evaluation_results,
    get_query_types,
)
from config.config import FEATURE_COLUMNS, DATA_DIR, MULTI_OBJECTIVE_WEIGHTS
from data.annotation_consistency import build_consistent_dataset, print_consistency_stats
from personalization.user_profile import PersonalizationEngine
from online_learning.online_learner import OnlineLearner, FeedbackSimulator
from multi_objective.multi_objective_ranker import MultiObjectiveScorer, create_balanced_scorer


CATEGORIES = [
    "手机", "笔记本电脑", "平板电脑", "耳机", "智能手表",
    "数码相机", "游戏主机", "显示器", "键盘", "鼠标",
    "电视", "冰箱", "洗衣机", "空调", "吸尘器",
    "连衣裙", "运动鞋", "背包", "太阳镜", "护肤套装",
]

BRANDS = [
    "苹果", "华为", "小米", "三星", "索尼",
    "联想", "戴尔", "海尔", "美的", "格力",
    "耐克", "阿迪达斯", "优衣库", "兰蔻", "雅诗兰黛",
]

QUERIES = [
    "苹果手机", "华为笔记本", "小米耳机", "三星电视", "索尼相机",
    "游戏键盘", "机械键盘", "无线鼠标", "智能手表", "运动鞋",
    "连衣裙", "护肤套装", "吸尘器", "平板电脑", "游戏主机",
    "手机", "笔记本电脑", "耳机", "冰箱", "空调",
    "数码相机", "显示器", "洗衣机", "背包", "太阳镜",
    "高端旗舰手机", "轻薄便携笔记本", "降噪蓝牙耳机",
    "大存储平板电脑", "高清4K电视", "变频节能空调",
    "手持无线吸尘器", "机械键盘青轴", "跑步鞋男款",
]

TITLE_TEMPLATES = {
    "手机": ["{brand}手机{model}旗舰新品", "{brand}{model}智能手机5G", "{brand}手机{model}大内存版"],
    "笔记本电脑": ["{brand}笔记本电脑{model}轻薄本", "{brand}{model}游戏本高性能", "{brand}笔记本{model}商务办公"],
    "平板电脑": ["{brand}平板电脑{model}大屏", "{brand}{model}平板学习版", "{brand}平板{model}高配版"],
    "耳机": ["{brand}无线蓝牙耳机{model}", "{brand}{model}降噪耳机", "{brand}耳机{model}运动版"],
    "智能手表": ["{brand}智能手表{model}运动版", "{brand}{model}手表心率监测", "{brand}手表{model}GPS版"],
    "数码相机": ["{brand}数码相机{model}微单", "{brand}{model}单反相机", "{brand}相机{model}4K视频"],
    "游戏主机": ["{brand}游戏主机{model}次世代", "{brand}{model}掌机", "{brand}主机{model}限定版"],
    "显示器": ["{brand}显示器{model}4K高清", "{brand}{model}电竞显示器", "{brand}曲面屏{model}"],
    "键盘": ["{brand}机械键盘{model}青轴", "{brand}{model}游戏键盘RGB", "{brand}键盘{model}无线"],
    "鼠标": ["{brand}无线鼠标{model}静音", "{brand}{model}游戏鼠标电竞", "{brand}鼠标{model}人体工学"],
    "电视": ["{brand}智能电视{model}大屏", "{brand}{model}4K电视", "{brand}电视{model}OLED"],
    "冰箱": ["{brand}冰箱{model}双开门", "{brand}{model}冰箱变频节能", "{brand}冰箱{model}小户型"],
    "洗衣机": ["{brand}洗衣机{model}滚筒", "{brand}{model}洗烘一体机", "{brand}洗衣机{model}迷你"],
    "空调": ["{brand}空调{model}变频", "{brand}{model}空调挂机", "{brand}空调{model}柜机"],
    "吸尘器": ["{brand}吸尘器{model}手持无线", "{brand}{model}扫地机器人", "{brand}吸尘器{model}大功率"],
    "连衣裙": ["{brand}连衣裙{model}夏季新款", "{brand}{model}碎花裙子", "{brand}连衣裙{model}长裙"],
    "运动鞋": ["{brand}运动鞋{model}跑步鞋", "{brand}{model}篮球鞋", "{brand}运动鞋{model}休闲"],
    "背包": ["{brand}背包{model}双肩包", "{brand}{model}旅行包大容量", "{brand}背包{model}商务"],
    "太阳镜": ["{brand}太阳镜{model}偏光", "{brand}{model}墨镜时尚", "{brand}太阳镜{model}男女同款"],
    "护肤套装": ["{brand}护肤套装{model}保湿", "{brand}{model}护肤品礼盒", "{brand}护肤套装{model}抗衰老"],
}


def generate_products(n=200):
    products = []
    for i in range(n):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)
        model = f"Pro{random.randint(1, 20)}"
        templates = TITLE_TEMPLATES.get(category, ["{brand}{category}{model}"])
        title = random.choice(templates).format(brand=brand, model=model, category=category)

        base_price = {
            "手机": 3000, "笔记本电脑": 5000, "平板电脑": 2000,
            "耳机": 300, "智能手表": 1000, "数码相机": 4000,
            "游戏主机": 3000, "显示器": 1500, "键盘": 200, "鼠标": 100,
            "电视": 3000, "冰箱": 2000, "洗衣机": 1500, "空调": 2500,
            "吸尘器": 800, "连衣裙": 200, "运动鞋": 400, "背包": 150,
            "太阳镜": 200, "护肤套装": 300,
        }
        bp = base_price.get(category, 500)
        price = round(bp * random.uniform(0.5, 2.5), 2)

        sales_volume = int(random.expovariate(1 / 5000))
        sales_7d = int(sales_volume * random.uniform(0.1, 0.3))

        base_ctr = random.betavariate(2, 8)
        ctr_1d = round(base_ctr * random.uniform(1.0, 1.5), 4)
        ctr_3d = round(base_ctr * random.uniform(0.9, 1.3), 4)
        ctr_7d = round(base_ctr, 4)
        ctr_14d = round(base_ctr * random.uniform(0.7, 1.0), 4)
        ctr_30d = round(base_ctr * random.uniform(0.5, 0.9), 4)

        click_rate = round(random.betavariate(2, 5), 4)
        cart_rate = round(click_rate * random.uniform(0.1, 0.5), 4)
        conversion_rate = round(cart_rate * random.uniform(0.1, 0.8), 4)
        conv_1d = round(conversion_rate * random.uniform(1.0, 1.3), 4)
        conv_3d = round(conversion_rate * random.uniform(0.9, 1.1), 4)

        return_rate = round(random.betavariate(1, 20), 4)
        review_score = round(random.uniform(3.0, 5.0), 1)

        current_days = time.time() / 86400
        launch_days = current_days - random.randint(1, 180)

        products.append({
            "product_id": f"P{i:05d}",
            "title": title,
            "category": category,
            "brand": brand,
            "price": price,
            "sales_volume": sales_volume,
            "sales_7d": sales_7d,
            "click_rate": click_rate,
            "cart_rate": cart_rate,
            "conversion_rate": conversion_rate,
            "conv_1d": conv_1d,
            "conv_3d": conv_3d,
            "ctr_1d": ctr_1d,
            "ctr_3d": ctr_3d,
            "ctr_7d": ctr_7d,
            "ctr_14d": ctr_14d,
            "ctr_30d": ctr_30d,
            "return_rate": return_rate,
            "review_score": review_score,
            "launch_days": launch_days,
        })
    return products


def pre_tokenize_products(products):
    for p in products:
        tokenize(p["title"])
        tokenize(p["category"])
    for q in QUERIES:
        tokenize(q)


def assign_relevance_labels(query, products):
    q_tokens = tokenize(query)
    labels = []
    for p in products:
        t_tokens = tokenize(p["title"])
        cat_tokens = tokenize(p["category"])
        text_sim = title_match_score(q_tokens, t_tokens)
        cat_sim = category_match(q_tokens, cat_tokens)
        brand_sim = brand_match(query, p["brand"])

        score = text_sim * 0.5 + cat_sim * 0.3 + brand_sim * 0.2
        score += p["conversion_rate"] * 0.3
        score += p["review_score"] / 5.0 * 0.1

        noise = random.gauss(0, 0.05)
        score = max(0, min(1, score + noise))

        if score > 0.7:
            label = 4
        elif score > 0.5:
            label = 3
        elif score > 0.3:
            label = 2
        elif score > 0.1:
            label = 1
        else:
            label = 0
        labels.append(label)
    return labels


def generate_synthetic_users(products, num_users=10):
    pers_engine = PersonalizationEngine()

    for user_id in range(num_users):
        uid = f"user_{user_id}"

        preferred_categories = random.sample(CATEGORIES, random.randint(2, 5))
        preferred_brands = random.sample(BRANDS, random.randint(2, 5))

        for _ in range(random.randint(5, 20)):
            category = random.choice(preferred_categories)
            brand = random.choice(preferred_brands)
            matching_products = [
                p for p in products
                if p["category"] == category and p["brand"] == brand
            ]
            if matching_products:
                product = random.choice(matching_products)
                action = random.choice(["click", "click", "click", "browse", "purchase"])

                if action == "click":
                    pers_engine.record_click(uid, product)
                elif action == "purchase":
                    pers_engine.record_purchase(uid, product)
                else:
                    pers_engine.record_browse(uid, product)

    return pers_engine


_log_file = None


def log(msg=""):
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()


def main():
    global _log_file
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_files")
    os.makedirs(log_dir, exist_ok=True)
    _log_file = open(os.path.join(log_dir, "training_log.txt"), "w", encoding="utf-8")

    log("=" * 80)
    log("  E-Commerce Search Relevance Ranking - Full Features")
    log("=" * 80)

    log("\n[1/9] Generating sample products with time-series and freshness data...")
    products = generate_products(n=200)
    log(f"  Generated {len(products)} products")

    log("  Pre-tokenizing product titles (caching jieba results)...")
    pre_tokenize_products(products)
    log("  Tokenization cache warmed up!")

    log("\n[2/9] Building training data with annotation consistency check...")
    feature_pairs, labels_list, groups, cons_stats = build_consistent_dataset(
        queries=QUERIES,
        products=products,
        label_fn=assign_relevance_labels,
        consistency_threshold=0.66,
        num_initial_annotations=2,
        max_relabel_attempts=3,
    )
    for k, v in cons_stats.items():
        log(f"    {k}: {v}")
    log(f"  Built {sum(groups)} query-product pairs, {len(groups)} groups")

    log("\n[3/9] Computing features (time-decay + user personalization)...")
    price_list = [p["price"] for p in products]

    log("  Generating synthetic user profiles for personalization demo...")
    pers_engine = generate_synthetic_users(products, num_users=10)
    sample_user = "user_0"
    user_profile = pers_engine.get_or_create_user(sample_user)
    log(f"  Sample user ({sample_user}) preferences:")
    log(f"    Top categories: {user_profile.get_top_categories(3)}")
    log(f"    Top brands: {user_profile.get_top_brands(3)}")

    all_features = []
    all_labels = []
    all_query_ids = []

    for q_idx, (original_q_idx, p_indices) in enumerate(feature_pairs):
        query = QUERIES[original_q_idx]
        q_labels = labels_list[q_idx]

        for j, p_idx in enumerate(p_indices):
            product = products[p_idx]
            feats = compute_all_features(query, product, price_list=price_list)

            pers_feats = pers_engine.compute_personalization_features(sample_user, product)
            feats.update(pers_feats)

            all_features.append(feats)
            all_labels.append(q_labels[j])
            all_query_ids.append(q_idx)

    X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in all_features])
    y = np.array(all_labels, dtype=np.float32)

    log(f"  Feature dimension: {X.shape[1]}")
    log(f"  Personalization features added: user_category_match, user_brand_match, ...")

    n_total = len(groups)
    n_train = int(n_total * 0.8)
    train_groups = groups[:n_train]
    val_groups = groups[n_train:]
    train_end = sum(train_groups)
    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:], y[train_end:]

    train_qids = []
    for i, g in enumerate(train_groups):
        train_qids.extend([i] * g)
    val_qids = []
    for i, g in enumerate(val_groups):
        val_qids.extend([n_train + i] * g)

    log(f"  Train: {X_train.shape[0]} samples, {len(train_groups)} groups")
    log(f"  Val:   {X_val.shape[0]} samples, {len(val_groups)} groups")

    log("\n[4/9] Training LambdaMART model (LightGBM)...")
    ranker = LambdaMARTRanker()
    model = ranker.train(
        X_train, y_train, train_groups,
        X_val, y_val, val_groups,
    )
    log("  Training complete!")

    model_path = ranker.save_model()
    log(f"  Model saved to: {model_path}")

    importance = ranker.get_feature_importance()
    log("\n  Feature Importance (top 20):")
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for fname, fval in sorted_imp[:20]:
        log(f"    {fname:30s}: {fval:.2f}")

    log("\n[5/9] Evaluating model (overall)...")
    train_preds = ranker.predict(X_train)
    val_preds = ranker.predict(X_val)
    all_preds = np.concatenate([train_preds, val_preds])
    all_labels_arr = np.concatenate([y_train, y_val])
    all_qids = np.array(train_qids + val_qids)

    results = evaluate_ranking(all_preds, all_labels_arr, all_qids, k_values=[1, 3, 5, 10])
    for metric, value in results.items():
        log(f"  {metric:12s}: {value:.4f}")

    val_results = evaluate_ranking(val_preds, y_val, np.array(val_qids), k_values=[1, 3, 5, 10])
    log("\n  Validation Set Evaluation:")
    for metric, value in val_results.items():
        log(f"  {metric:12s}: {value:.4f}")

    log("\n[6/9] Fine-grained evaluation by query type...")
    query_types = get_query_types(QUERIES)
    log(f"  Query type distribution: {query_types.count('popular')} popular, {query_types.count('longtail')} longtail")

    sample_query_types = []
    for q_idx in all_query_ids:
        original_q_idx = feature_pairs[q_idx][0] if q_idx < len(feature_pairs) else 0
        sample_query_types.append(query_types[original_q_idx])

    group_eval = evaluate_ranking_by_group(
        all_preds, all_labels_arr, all_qids,
        np.array(sample_query_types),
        k_values=[1, 3, 5, 10]
    )

    log("\n  Query Group Evaluation Results:")
    for group in ['popular', 'longtail', 'overall']:
        if group in group_eval:
            data = group_eval[group]
            metrics = data['metrics']
            log(f"\n  {group.upper()} ({data['num_queries']} queries):")
            for metric, value in metrics.items():
                log(f"    {metric:10s}: {value:.4f}")

    log("\n[7/9] Multi-Objective Ranking Demo...")
    log("  Objectives: Relevance (0.5) + Conversion (0.3) + Freshness (0.2)")

    demo_query = "苹果手机"
    demo_indices = random.sample(range(len(products)), 15)
    demo_products = [products[i] for i in demo_indices]

    demo_features = []
    for p in demo_products:
        feats = compute_all_features(demo_query, p, price_list=price_list)
        pers_feats = pers_engine.compute_personalization_features(sample_user, p)
        feats.update(pers_feats)
        demo_features.append(feats)

    X_demo = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in demo_features])
    base_scores = ranker.predict(X_demo)

    mo_ranker = MultiObjectiveScorer(weights=MULTI_OBJECTIVE_WEIGHTS)
    ranked_mo, final_scores, obj_scores = mo_ranker.rank_products(
        demo_products, base_scores, method="weighted"
    )

    log(f"\n  Query: '{demo_query}'")
    log(f"  User: {sample_user} (prefers {user_profile.get_top_categories(1)[0][0]})")
    log("\n  Multi-Objective Ranking (Top 10):")
    log(f"  {'Rank':<6} {'Product':<35} {'Rel':<8} {'Conv':<8} {'Fresh':<8} {'Final':<8}")
    log("  " + "-" * 80)
    for rank, p in enumerate(ranked_mo[:10], 1):
        obj = p["objective_scores"]
        log(f"  {rank:<6} {p.get('title', '')[:32]:<35} "
            f"{obj['relevance']:<8.3f} {obj['conversion']:<8.3f} "
            f"{obj['freshness']:<8.3f} {p['multi_objective_score']:<8.3f}")

    log("\n  Weighted vs Pareto comparison:")
    ranked_pareto, _, _ = mo_ranker.rank_products(demo_products, base_scores, method="pareto")
    log(f"    Weighted top: {ranked_mo[0]['title'][:30]}")
    log(f"    Pareto top:   {ranked_pareto[0]['title'][:30]}")

    log("\n[8/9] Online Learning with Click Feedback Simulation...")
    online_learner = OnlineLearner(feature_columns=FEATURE_COLUMNS)
    feedback_sim = FeedbackSimulator()

    log("  Simulating 100 search sessions with click feedback...")
    num_sessions = 100
    for session in range(num_sessions):
        query = random.choice(QUERIES)
        session_indices = random.sample(range(len(products)), 10)
        session_products = [products[i] for i in session_indices]

        session_features = []
        for p in session_products:
            feats = compute_all_features(query, p, price_list=price_list)
            session_features.append(feats)

        X_session = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in session_features])
        relevance_scores = ranker.predict(X_session)

        clicked_positions, dwell_times = feedback_sim.simulate_search_session(
            query, session_products, relevance_scores
        )

        for i, p in enumerate(session_products):
            clicked = i in clicked_positions
            dwell = dwell_times[i]
            online_learner.record_feedback(
                query, p, i, clicked, dwell,
                features=session_features[i]
            )

    stats = online_learner.get_stats()
    log(f"  Feedback stats: {stats['total_feedback']} total, "
        f"{stats['clicks']} clicks ({stats['click_rate']:.2%} CTR)")

    log("\n[9/9] Personalization Effect Demo...")
    log(f"  Comparing ranking for user_{sample_user} vs generic ranking...")

    generic_indices = np.argsort(-base_scores)
    pers_ranked, pers_scores = pers_engine.rerank_with_personalization(
        sample_user, demo_products, base_scores, personalization_weight=0.4
    )

    log(f"\n  {'Rank':<6} {'Generic':<30} {'Personalized':<30}")
    log("  " + "-" * 70)
    for i in range(min(10, len(demo_products))):
        generic_p = demo_products[generic_indices[i]]
        pers_p = pers_ranked[i]
        log(f"  {i + 1:<6} {generic_p.get('title', '')[:27]:<30} {pers_p.get('title', '')[:27]:<30}")

    log("\n" + "=" * 80)
    log("  FULL PIPELINE COMPLETED SUCCESSFULLY!")
    log("=" * 80)
    log("\n  Features Implemented:")
    log("    ✓ Annotation consistency check + re-labeling")
    log("    ✓ Time-decayed behavior features")
    log("    ✓ Query-type evaluation (popular vs longtail)")
    log("    ✓ Personalized ranking (user preferences)")
    log("    ✓ Online learning (click feedback)")
    log("    ✓ Multi-objective ranking (relevance + conversion + freshness)")
    log("\n  To start the Flask API, run: python api/app.py")
    log("=" * 80)

    _log_file.close()
    return results


if __name__ == "__main__":
    main()
