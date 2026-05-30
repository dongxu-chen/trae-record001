from data_store import DataStore
from hybrid_recommender import HybridRecommender
from cold_start_and_diversity import DiversityController, ExplorationExploitation
from models import ReadingProgress
from datetime import datetime
from sample_data import create_sample_data


def test_recommender():
    print("=" * 60)
    print("图书推荐系统测试 - 完整版")
    print("=" * 60)
    
    data_store = DataStore()
    create_sample_data(data_store)
    
    recommender = HybridRecommender(data_store)
    recommender.train()

    print("\n" + "=" * 60)
    print("测试1: 系列丛书推荐 (用户3: 小刚，已读三体1-2)")
    print("=" * 60)
    series_progress = recommender.series_recommender.get_user_series_progress(3)
    for series_id, progress in series_progress.items():
        if progress['read_count'] > 0:
            series = progress['series']
            print(f"\n系列: {series.series_name} (已读 {progress['read_count']}/{progress['total_books']})")
            for book in progress['read_books']:
                print(f"  [X] {book.series_order}. {book.title}")
            for book in progress['unread_books']:
                mark = "[>] 推荐下一本" if book.book_id == progress['next_book'].book_id else "[ ]"
                print(f"  {mark} {book.series_order}. {book.title}")

    print("\n系列推荐结果:")
    series_recs = recommender.series_recommender.recommend_next_in_series(3, 5)
    for i, (book_id, score, reason) in enumerate(series_recs, 1):
        book = data_store.get_book(book_id)
        if book:
            print(f"{i}. {book.title} (评分: {score:.3f}) - {reason}")

    print("\n" + "=" * 60)
    print("测试2: 阅读进度追踪与时间预测 (用户1阅读三体3)")
    print("=" * 60)
    
    progress1 = recommender.reading_predictor.update_progress(user_id=1, book_id=3, current_page=100)
    print(f"首次更新进度: 第{progress1.current_page}页, 日均{progress1.pages_per_day_avg:.1f}页, 状态:{progress1.status}")
    
    progress2 = recommender.reading_predictor.update_progress(user_id=1, book_id=3, current_page=250)
    print(f"再次更新进度: 第{progress2.current_page}页, 日均{progress2.pages_per_day_avg:.1f}页, 状态:{progress2.status}")
    
    pred = recommender.reading_predictor.predict_finish_time(1, 3)
    print(f"\n阅读预测:")
    print(f"  当前进度: {pred.current_page}/{pred.total_pages}页 ({pred.progress_percent}%)")
    print(f"  阅读速度: {pred.pages_per_day}页/天")
    print(f"  预计剩余: {pred.estimated_days_left}天")
    print(f"  预计读完: {pred.estimated_finish_date.strftime('%Y-%m-%d %H:%M')}")

    print("\n" + "=" * 60)
    print("测试3: 用户阅读统计")
    print("=" * 60)
    stats = recommender.reading_predictor.get_user_reading_stats(1)
    print(f"总读书数: {stats['total_books_read']}")
    print(f"已读完: {stats['finished_books']}本")
    print(f"在读中: {stats['currently_reading_count']}本")
    print(f"总阅读页数: {stats['total_pages_read']}")
    print(f"日均阅读: {stats['avg_pages_per_day']}页")

    print("\n" + "=" * 60)
    print("测试4: 阅读计划安排 (每日目标30页)")
    print("=" * 60)
    schedule = recommender.reading_predictor.recommend_reading_schedule(1, 30)
    for s in schedule['schedules']:
        print(f"\n《{s['title']}》:")
        print(f"  当前: {s['current_page']}/{s['total_pages']}页, 剩余{s['pages_left']}页")
        print(f"  每日目标: {s['daily_goal_pages']}页")
        print(f"  预计天数: {s['estimated_days']}天")
        print(f"  预计完成: {s['estimated_finish'].strftime('%Y-%m-%d')}")

    print("\n" + "=" * 60)
    print("测试5: 书评摘要生成 - 《三体》")
    print("=" * 60)
    summary = recommender.review_summarizer.generate_summary(1)
    print(f"书名: {data_store.get_book(1).title}")
    print(f"\n概述: {summary.summary}")
    print(f"\n优点:")
    for p in summary.pros:
        print(f"  + {p}")
    print(f"\n缺点:")
    for c in summary.cons:
        print(f"  - {c}")
    print(f"\n核心主题: {', '.join(summary.key_themes)}")
    print(f"适合人群: {', '.join(summary.target_audience)}")

    print("\n" + "=" * 60)
    print("测试6: 阅读指南 - 《三体》")
    print("=" * 60)
    guide = recommender.review_summarizer.get_reading_guide(1)
    print(f"阅读难度: {'*' * guide['reading_difficulty']}{'.' * (5 - guide['reading_difficulty'])} ({guide['reading_difficulty']}/5)")
    print(f"预计阅读时间: {guide['estimated_reading_time']}")
    print(f"\n阅读建议:")
    for tip in guide['reading_tips']:
        print(f"  * {tip}")

    print("\n" + "=" * 60)
    print("测试7: 书籍对比 - 《三体》vs《黑暗森林》")
    print("=" * 60)
    comparison = recommender.review_summarizer.get_comparative_summary([1, 2])
    print(f"共同优点: {', '.join(comparison['common_pros'][:3])}")
    print(f"共同主题: {', '.join(comparison['common_themes'][:3])}")
    for up in comparison['unique_points']:
        book = data_store.get_book(up['book_id'])
        print(f"\n《{book.title}》独特之处:")
        for p in up['unique_pros'][:2]:
            print(f"  + {p}")

    print("\n" + "=" * 60)
    print("测试8: 完整推荐流程 (用户1，含系列推荐)")
    print("=" * 60)
    recs = recommender.recommend(user_id=1, top_n=10, diversity_weight=0.3)
    print(f"为用户'小明'推荐的书籍:")
    for i, (book_id, score, reason) in enumerate(recs, 1):
        book = data_store.get_book(book_id)
        if book:
            genres = ", ".join(book.genres)
            series_info = ""
            if book.series_id:
                series = data_store.get_book_series(book.series_id)
                if series:
                    series_info = f" [《{series.series_name}》#{book.series_order}]"
            print(f"{i}. {book.title}{series_info} [{genres}] (评分: {score:.3f})")
            print(f"   原因: {reason}")

    print("\n" + "=" * 60)
    print("测试9: 冷启动 - 流行度+热门类 (用户9)")
    print("=" * 60)
    recs = recommender.recommend(user_id=9, top_n=10)
    for i, (book_id, score, reason) in enumerate(recs, 1):
        book = data_store.get_book(book_id)
        if book:
            genres = ", ".join(book.genres)
            print(f"{i}. {book.title} [{genres}] (评分: {score:.3f}) - {reason}")

    print("\n" + "=" * 60)
    print("测试10: MMR多样性重排 (用户1)")
    print("=" * 60)
    diversity = DiversityController(data_store)
    cf_recs = recommender.collaborative_filtering.recommend(1, 20)
    mf_recs = recommender.matrix_factorization.recommend(1, 20)
    social_recs = recommender.social_recommender.recommend(1, 20)
    series_recs = recommender.series_recommender.recommend_next_in_series(1, 20)
    
    combined = {}
    for book_id, score, reason in cf_recs:
        combined[book_id] = {'score': score * 0.30, 'reasons': [reason]}
    for book_id, score, reason in mf_recs:
        if book_id not in combined:
            combined[book_id] = {'score': 0, 'reasons': []}
        combined[book_id]['score'] += score * 0.35
        combined[book_id]['reasons'].append(reason)
    for book_id, score, reason in social_recs:
        if book_id not in combined:
            combined[book_id] = {'score': 0, 'reasons': []}
        combined[book_id]['score'] += score * 0.20
        combined[book_id]['reasons'].append(reason)
    for book_id, score, reason in series_recs:
        if book_id not in combined:
            combined[book_id] = {'score': 0, 'reasons': []}
        combined[book_id]['score'] += score * 0.15
        combined[book_id]['reasons'].append(reason)
    
    raw_recs = [(bid, d['score'], " + ".join(set(d['reasons']))[:50]) for bid, d in combined.items()]
    raw_recs.sort(key=lambda x: x[1], reverse=True)
    
    mmr_result = diversity.mmr_rerank(raw_recs, top_n=10, lambda_param=0.5)
    print("MMR重排结果 (lambda=0.5, 均衡相关性与多样性):")
    for i, (book_id, score, reason) in enumerate(mmr_result, 1):
        book = data_store.get_book(book_id)
        if book:
            genres = ", ".join(book.genres)
            print(f"{i}. {book.title} [{genres}] (评分: {score:.3f})")

    div_before = diversity.compute_genre_diversity([r[0] for r in raw_recs[:10]])
    div_after = diversity.compute_genre_diversity([r[0] for r in mmr_result])
    print(f"\n重排前类型多样性: {div_before:.4f}")
    print(f"重排后类型多样性: {div_after:.4f}")

    print("\n" + "=" * 60)
    print("测试11: Epsilon时间衰减探索率")
    print("=" * 60)
    ee = ExplorationExploitation(data_store)
    test_users = [1, 2, 3, 9, 10]
    print("用户ID | 用户名   | 评分数 | epsilon | 说明")
    print("-" * 55)
    for uid in test_users:
        eps = ee.get_exploration_rate(uid)
        n_ratings = len(data_store.get_user_ratings(uid))
        user = data_store.get_user(uid)
        desc = "新用户,高探索" if n_ratings < 3 else "老用户,低探索"
        print(f"  {uid}    | {user.username:6s}  | {n_ratings:5d}  | {eps:.4f}  | {desc}")

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_recommender()
