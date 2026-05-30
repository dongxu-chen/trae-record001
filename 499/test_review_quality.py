import sys
import io
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import settings
from schemas import (
    ReviewItem, UserProfile, PurchaseBehavior,
    ReputationEvent, ReputationEventType,
    PurchaseVerificationStatus, VoteRecord,
    MerchantReply, ReviewInteraction
)
from modules import (
    AuthenticityAnalyzer,
    UserReputationModel,
    RuleEngine,
    ScoringEngine,
    GangDetector,
    AdoptionAnalyzer,
    MerchantReplyAnalyzer
)

NOW = datetime.now()


def make_user(uid, age=365, reviews=50, verified=45, helpful=200, removals=0, avg=4.2):
    return UserProfile(
        user_id=uid, account_age_days=age,
        total_reviews=reviews, verified_purchases=verified,
        helpful_votes_received=helpful, review_removal_count=removals,
        average_rating=avg
    )


def make_purchase(verified=True, days_ago=28, returned=False, fast=False):
    days = 0.08 if fast else days_ago
    return PurchaseBehavior(
        has_purchased=True, purchase_verified=verified,
        purchase_time=NOW - timedelta(days=days_ago + days),
        review_after_purchase=True,
        days_between_purchase_and_review=days,
        return_requested=returned, return_completed=False
    )


def make_review(rid, uid, pid, content, rating=5, days_ago=7, verified=True,
                images=True, videos=False, user=None, purchase=None,
                merchant_reply=None, interaction=None):
    return ReviewItem(
        review_id=rid, user_id=uid, product_id=pid,
        content=content, rating=rating,
        helpful_votes=0, create_time=NOW - timedelta(days=days_ago),
        is_verified_purchase=verified, has_images=images, has_videos=videos,
        user_profile=user, purchase_behavior=purchase,
        merchant_reply=merchant_reply, interaction=interaction
    )


def test_gang_detection():
    print("=" * 70)
    print("TEST 1: Gang Detection (Fake Review Ring)")
    print("=" * 70)

    detector = GangDetector()

    gang_users = [
        make_user("gang_a", age=5, reviews=3, verified=0, helpful=0, avg=5.0),
        make_user("gang_b", age=8, reviews=4, verified=0, helpful=0, avg=5.0),
        make_user("gang_c", age=3, reviews=2, verified=0, helpful=0, avg=5.0),
    ]
    normal_user = make_user("normal_x", age=300, reviews=80, verified=70, helpful=300, avg=4.0)

    reviews = [
        make_review("gr1", "gang_a", "p1", "非常好！完美！超级推荐！五星好评！", rating=5, days_ago=1, verified=False, images=False, user=gang_users[0]),
        make_review("gr2", "gang_b", "p1", "太棒了！质量非常好！强烈推荐！", rating=5, days_ago=1, verified=False, images=False, user=gang_users[1]),
        make_review("gr3", "gang_c", "p1", "非常好！满意！推荐购买！", rating=5, days_ago=2, verified=False, images=False, user=gang_users[2]),
        make_review("gr4", "gang_a", "p2", "非常好！完美产品！", rating=5, days_ago=3, verified=False, images=False, user=gang_users[0]),
        make_review("gr5", "gang_b", "p2", "超级好！强烈推荐！", rating=5, days_ago=3, verified=False, images=False, user=gang_users[1]),
        make_review("gr6", "normal_x", "p1", "质量不错，物流快，但包装一般。性价比还可以。", rating=4, days_ago=10, verified=True, images=True, user=normal_user),
    ]

    vote_records = [
        VoteRecord(voter_id="gang_a", target_user_id="gang_b", target_review_id="gr2", vote_time=NOW - timedelta(hours=2)),
        VoteRecord(voter_id="gang_a", target_user_id="gang_c", target_review_id="gr3", vote_time=NOW - timedelta(hours=2)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_a", target_review_id="gr1", vote_time=NOW - timedelta(hours=1)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_c", target_review_id="gr3", vote_time=NOW - timedelta(hours=1)),
        VoteRecord(voter_id="gang_c", target_user_id="gang_a", target_review_id="gr1", vote_time=NOW - timedelta(hours=3)),
        VoteRecord(voter_id="gang_c", target_user_id="gang_b", target_review_id="gr2", vote_time=NOW - timedelta(hours=3)),
        VoteRecord(voter_id="gang_a", target_user_id="gang_b", target_review_id="gr5", vote_time=NOW - timedelta(hours=2)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_a", target_review_id="gr4", vote_time=NOW - timedelta(hours=1)),
        VoteRecord(voter_id="normal_x", target_user_id="gang_a", target_review_id="gr1", vote_time=NOW - timedelta(days=5)),
    ]

    gangs = detector.detect_gangs(reviews, vote_records)

    print(f"\nDetected {len(gangs)} gang(s):")
    for g in gangs:
        print(f"\n  Gang ID: {g.gang_id}")
        print(f"  Members: {g.members}")
        print(f"  Member Count: {g.member_count}")
        print(f"  Mutual Votes: {g.mutual_vote_count}")
        print(f"  Suspicious Score: {g.suspicious_score:.1f}/100")
        print(f"  Is Suspicious: {g.is_suspicious}")
        if g.warnings:
            for w in g.warnings:
                print(f"    [!] {w}")

    print("\n--- Gang Penalty for individual users ---")
    for uid in ["gang_a", "gang_b", "gang_c", "normal_x"]:
        penalty, warnings = detector.calculate_gang_penalty(uid, gangs)
        print(f"  User {uid}: penalty={penalty:.1f}, warnings={warnings[:1]}")


def test_adoption_analysis():
    print("\n" + "=" * 70)
    print("TEST 2: Adoption Analysis (Purchase Decision Helpfulness)")
    print("=" * 70)

    analyzer = AdoptionAnalyzer()

    user = make_user("u1")

    reviews_with_interactions = [
        make_review("ar1", "u1", "p1",
            "这款手机使用了一个月，屏幕清晰，电池续航一天没问题。拍照白天细节丰富，夜景噪点控制好。缺点是充电稍慢。性价比高，推荐购买。",
            rating=5, days_ago=7, user=user, purchase=make_purchase(),
            interaction=ReviewInteraction(
                review_id="ar1", view_count=500,
                helpful_votes=120, unhelpful_votes=5,
                share_count=30, collect_count=80,
                comment_count=15, purchase_after_view_count=60,
                add_to_cart_after_view_count=90
            )
        ),
        make_review("ar2", "u1", "p1",
            "好",
            rating=5, days_ago=3, verified=False, images=False,
            interaction=ReviewInteraction(
                review_id="ar2", view_count=100,
                helpful_votes=2, unhelpful_votes=10,
                share_count=0, collect_count=0,
                comment_count=0, purchase_after_view_count=1,
                add_to_cart_after_view_count=2
            )
        ),
        make_review("ar3", "u1", "p2",
            "质量一般，做工有点粗糙。材质和描述不一样，尺寸偏小。颜色还可以。物流快，包装完整。使用效果一般。优点是便宜，缺点是质量有待提高。",
            rating=3, days_ago=14, user=user, purchase=make_purchase(),
            interaction=ReviewInteraction(
                review_id="ar3", view_count=300,
                helpful_votes=85, unhelpful_votes=3,
                share_count=15, collect_count=40,
                comment_count=8, purchase_after_view_count=25,
                add_to_cart_after_view_count=35
            )
        ),
        make_review("ar4", "u1", "p2",
            "对比了三款同类产品，这款性价比最高。之前用的XX品牌容易坏，这款用了两个月很稳定。建议买大一号的，尺码偏小。",
            rating=4, days_ago=5, user=user, purchase=make_purchase(),
            interaction=ReviewInteraction(
                review_id="ar4", view_count=800,
                helpful_votes=200, unhelpful_votes=2,
                share_count=50, collect_count=120,
                comment_count=25, purchase_after_view_count=100,
                add_to_cart_after_view_count=150
            )
        ),
    ]

    print("\n--- Individual Adoption Analysis ---")
    for review in reviews_with_interactions:
        result = analyzer.analyze_adoption(review)
        print(f"\n  Review {review.review_id}: \"{review.content[:30]}...\"")
        print(f"    Adoption Score:      {result.adoption_score:.1f}/100")
        print(f"    Purchase Influence:  {result.purchase_influence:.1f}/100")
        print(f"    Engagement Quality:  {result.engagement_quality:.1f}/100")
        print(f"    Decision Helpfulness:{result.decision_helpfulness:.1f}/100")

    print("\n--- Top Adopted Reviews Ranking ---")
    ranked = analyzer.rank_by_adoption(reviews_with_interactions)
    for r in ranked:
        review = next(rv for rv in reviews_with_interactions if rv.review_id == r.review_id)
        print(f"  Rank {r.adoption_rank}: {r.review_id} - Score:{r.adoption_score:.1f} (Purchase:{r.purchase_influence:.1f}, Engage:{r.engagement_quality:.1f}, Decision:{r.decision_helpfulness:.1f})")

    print("\n--- Top Decision-Helpful Reviews ---")
    top_decision = analyzer.find_top_decision_reviews(reviews_with_interactions, top_k=3)
    for r in top_decision:
        print(f"  {r.review_id} - Decision Helpfulness: {r.decision_helpfulness:.1f}")


def test_merchant_reply():
    print("\n" + "=" * 70)
    print("TEST 3: Merchant Reply Impact Assessment")
    print("=" * 70)

    analyzer = MerchantReplyAnalyzer()

    user = make_user("u1")

    print("\n--- Scenario A: Negative review + quick apologetic reply with solution ---")
    review_neg = make_review("mr1", "u1", "p1",
        "太差了！质量非常不好，做工粗糙，刚收到就有破损。",
        rating=1, days_ago=5, user=user, purchase=make_purchase(),
        merchant_reply=MerchantReply(
            reply_id="rep1",
            reply_content="非常抱歉给您带来不好的体验！我们已安排补发新商品，同时对质量问题进行整改。请联系客服获取赔偿方案。",
            reply_time=NOW - timedelta(days=4, hours=20),
            is_official=True, mentions_solution=True,
            mentions_compensation=True, is_apologetic=True
        )
    )
    impact_a = analyzer.analyze_reply_impact(review_neg)
    print(f"  Impact Level: {impact_a.impact_level}")
    print(f"  Quality Delta: +{impact_a.quality_delta:.1f}")
    print(f"  Trust Boost: {impact_a.trust_boost:.1f}")
    print(f"  Satisfaction Improvement: {impact_a.satisfaction_improvement:.1f}%")
    if impact_a.warnings:
        for w in impact_a.warnings:
            print(f"    [!] {w}")

    print("\n--- Scenario B: Negative review + late generic reply ---")
    review_neg_late = make_review("mr2", "u1", "p1",
        "太差了！质量非常不好，做工粗糙。",
        rating=1, days_ago=15, user=user, purchase=make_purchase(),
        merchant_reply=MerchantReply(
            reply_id="rep2",
            reply_content="感谢您的反馈。",
            reply_time=NOW - timedelta(days=3),
            is_official=True
        )
    )
    impact_b = analyzer.analyze_reply_impact(review_neg_late)
    print(f"  Impact Level: {impact_b.impact_level}")
    print(f"  Quality Delta: {impact_b.quality_delta:.1f}")
    print(f"  Trust Boost: {impact_b.trust_boost:.1f}")
    print(f"  Satisfaction Improvement: {impact_b.satisfaction_improvement:.1f}%")

    print("\n--- Scenario C: Positive review + merchant reply ---")
    review_pos = make_review("mr3", "u1", "p1",
        "质量很好，使用体验不错，推荐购买。",
        rating=5, days_ago=3, user=user, purchase=make_purchase(),
        merchant_reply=MerchantReply(
            reply_id="rep3",
            reply_content="感谢您的好评！欢迎再次光临。",
            reply_time=NOW - timedelta(days=2),
            is_official=True
        )
    )
    impact_c = analyzer.analyze_reply_impact(review_pos)
    print(f"  Impact Level: {impact_c.impact_level}")
    print(f"  Quality Delta: +{impact_c.quality_delta:.1f}")
    print(f"  Trust Boost: {impact_c.trust_boost:.1f}")

    print("\n--- Scenario D: No merchant reply ---")
    review_no_reply = make_review("mr4", "u1", "p2",
        "一般般，没什么特别的。",
        rating=3, days_ago=10, user=user
    )
    impact_d = analyzer.analyze_reply_impact(review_no_reply)
    print(f"  Impact Level: {impact_d.impact_level}")
    print(f"  Quality Delta: {impact_d.quality_delta:.1f}")

    print("\n--- Score Adjustment Comparison ---")
    base_score = 55.0
    for label, review in [("A:Neg+GoodReply", review_neg), ("B:Neg+LateReply", review_neg_late), ("C:Pos+Reply", review_pos), ("D:NoReply", review_no_reply)]:
        adjusted, impact = analyzer.apply_reply_to_score(review, base_score)
        print(f"  {label}: {base_score:.1f} -> {adjusted:.1f} (delta: +{impact.quality_delta:.1f})")


def test_full_integration():
    print("\n" + "=" * 70)
    print("TEST 4: Full Integration Scoring (All Features)")
    print("=" * 70)

    analyzer = AuthenticityAnalyzer()
    rep_model = UserReputationModel()
    rule_engine = RuleEngine()
    gang_detector = GangDetector()
    adoption_analyzer = AdoptionAnalyzer()
    merchant_analyzer = MerchantReplyAnalyzer()

    scoring = ScoringEngine(
        analyzer, rep_model, rule_engine,
        gang_detector, adoption_analyzer, merchant_analyzer
    )

    gang_users = [
        make_user("gang_a", age=5, reviews=3, verified=0, helpful=0, avg=5.0),
        make_user("gang_b", age=8, reviews=4, verified=0, helpful=0, avg=5.0),
    ]
    good_user = make_user("good_u")

    reviews = [
        make_review("r1", "good_u", "p1",
            "这款手机使用了一个月，整体体验非常好。屏幕显示效果清晰，色彩还原准确，电池续航不错。缺点是充电稍慢。推荐购买。",
            rating=5, days_ago=1, user=good_user, purchase=make_purchase(),
            interaction=ReviewInteraction(review_id="r1", view_count=500,
                helpful_votes=120, unhelpful_votes=3, share_count=20,
                collect_count=60, comment_count=10, purchase_after_view_count=50,
                add_to_cart_after_view_count=80),
            merchant_reply=MerchantReply(
                reply_id="mr1", reply_content="感谢好评！充电速度我们正在优化中。",
                reply_time=NOW - timedelta(hours=12), is_official=True
            )
        ),
        make_review("r2", "gang_a", "p1",
            "非常好！完美！超级推荐！",
            rating=5, days_ago=1, verified=False, images=False, user=gang_users[0],
            interaction=ReviewInteraction(review_id="r2", view_count=50,
                helpful_votes=5, unhelpful_votes=2, purchase_after_view_count=1)
        ),
        make_review("r3", "gang_b", "p1",
            "太棒了！质量非常好！强烈推荐！",
            rating=5, days_ago=1, verified=False, images=False, user=gang_users[1],
            interaction=ReviewInteraction(review_id="r3", view_count=45,
                helpful_votes=4, unhelpful_votes=1, purchase_after_view_count=0)
        ),
        make_review("r4", "good_u", "p1",
            "质量一般，做工粗糙。物流快但包装简陋。联系客服后给退换了。",
            rating=2, days_ago=10, user=good_user, purchase=make_purchase(returned=True),
            merchant_reply=MerchantReply(
                reply_id="mr4",
                reply_content="非常抱歉给您带来不好的体验！我们已为您办理退换货，并对包装问题进行整改。请联系客服获取补偿。",
                reply_time=NOW - timedelta(days=9), is_official=True,
                mentions_solution=True, mentions_compensation=True, is_apologetic=True
            )
        ),
    ]

    vote_records = [
        VoteRecord(voter_id="gang_a", target_user_id="gang_b", target_review_id="r3", vote_time=NOW - timedelta(hours=1)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_a", target_review_id="r2", vote_time=NOW - timedelta(hours=1)),
        VoteRecord(voter_id="gang_a", target_user_id="gang_b", target_review_id="r3", vote_time=NOW - timedelta(hours=2)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_a", target_review_id="r2", vote_time=NOW - timedelta(hours=2)),
        VoteRecord(voter_id="gang_a", target_user_id="gang_b", target_review_id="r3", vote_time=NOW - timedelta(hours=3)),
        VoteRecord(voter_id="gang_b", target_user_id="gang_a", target_review_id="r2", vote_time=NOW - timedelta(hours=3)),
        VoteRecord(voter_id="good_u", target_user_id="good_u", target_review_id="r1", vote_time=NOW - timedelta(days=5)),
    ]

    results, total, low_q, collapsed, gangs, top_adopted = scoring.score_batch(reviews, vote_records)

    print(f"\nProcessed: {total}, Low Quality: {low_q}, Collapsed: {collapsed}")
    print(f"Gangs Detected: {len(gangs)}")

    print(f"\n{'ID':<5} {'User':<8} {'Score':<7} {'Auth':<7} {'Gang':<6} {'Adoption':<9} {'Reply':<7} {'LowQ':<5} {'Fold':<5}")
    print("-" * 70)
    for r in results:
        has_gang = "Y" if r.gang_detection else "-"
        adoption = f"{r.adoption_analysis.adoption_score:.0f}" if r.adoption_analysis else "-"
        reply = f"+{r.merchant_reply_impact.quality_delta:.0f}" if r.merchant_reply_impact and r.merchant_reply_impact.quality_delta > 0 else "-"
        print(f"{r.review_id:<5} {reviews[0].user_id if r.review_id == 'r1' else '':<8}{r.review_id:<0}"
              f"  {r.overall_score:<7.1f} {r.dimension_scores.authenticity:<7.1f} {has_gang:<6} {adoption:<9} {reply:<7} {str(r.is_low_quality):<5} {str(r.should_collapse):<5}")

    for r in results:
        print(f"\n  Review {r.review_id}:")
        print(f"    Overall: {r.overall_score:.1f}")
        if r.gang_detection:
            print(f"    Gang: {r.gang_detection.gang_id} (score:{r.gang_detection.suspicious_score:.1f})")
        if r.adoption_analysis:
            a = r.adoption_analysis
            print(f"    Adoption: {a.adoption_score:.1f} (Purchase:{a.purchase_influence:.0f} Engage:{a.engagement_quality:.0f} Decision:{a.decision_helpfulness:.0f})")
        if r.merchant_reply_impact and r.merchant_reply_impact.impact_level != "none":
            m = r.merchant_reply_impact
            print(f"    Merchant Reply: delta=+{m.quality_delta:.1f}, trust=+{m.trust_boost:.1f}, level={m.impact_level}")

    if gangs:
        print(f"\n  Gang Details:")
        for g in gangs:
            print(f"    {g.gang_id}: members={g.members}, score={g.suspicious_score:.1f}, suspicious={g.is_suspicious}")

    if top_adopted:
        print(f"\n  Top Adopted Reviews:")
        for a in top_adopted:
            print(f"    Rank {a.adoption_rank}: {a.review_id} - Score:{a.adoption_score:.1f}")


def test_config_summary():
    print("\n" + "=" * 70)
    print("TEST 5: Configuration Summary (v3.0)")
    print("=" * 70)

    print(f"\nGang Detection:")
    print(f"  Min Members: {settings.GANG_MIN_MEMBERS}")
    print(f"  Mutual Vote Threshold: {settings.GANG_MUTUAL_VOTE_THRESHOLD}")
    print(f"  Suspicious Threshold: {settings.GANG_SUSPICIOUS_SCORE_THRESHOLD}")
    print(f"  Auth Penalty: {settings.GANG_DETECTION_AUTHENTICITY_PENALTY}")

    print(f"\nAdoption Analysis:")
    print(f"  Weights: Purchase={settings.ADOPTION_PURCHASE_INFLUENCE_WEIGHT}, "
          f"Engagement={settings.ADOPTION_ENGAGEMENT_WEIGHT}, "
          f"Decision={settings.ADOPTION_DECISION_WEIGHT}")
    print(f"  Purchase Rate Thresholds: Excellent>={settings.ADOPTION_PURCHASE_RATE_EXCELLENT}, "
          f"Good>={settings.ADOPTION_PURCHASE_RATE_GOOD}, "
          f"Avg>={settings.ADOPTION_PURCHASE_RATE_AVERAGE}")
    print(f"  Top K: {settings.ADOPTION_TOP_K}")

    print(f"\nMerchant Reply:")
    print(f"  Trust Boost: {settings.MERCHANT_REPLY_TRUST_BOOST}")
    print(f"  Solution Bonus: {settings.MERCHANT_REPLY_SOLUTION_BONUS}")
    print(f"  Apology Bonus: {settings.MERCHANT_REPLY_APOLOGY_BONUS}")
    print(f"  Compensation Bonus: {settings.MERCHANT_REPLY_COMPENSATION_BONUS}")
    print(f"  Quality Delta Max: {settings.MERCHANT_REPLY_QUALITY_DELTA_MAX}")
    print(f"  Negative Review Multiplier: {settings.MERCHANT_REPLY_NEGATIVE_REVIEW_MULTIPLIER}x")
    print(f"  Late Threshold: {settings.MERCHANT_REPLY_LATE_DAYS_THRESHOLD} days")

    print(f"\nReputation (with gang event):")
    print(f"  gang_member_detected weight: {settings.REPUTATION_EVENT_WEIGHTS.get('gang_member_detected', 'N/A')}")


def main():
    print("Review Quality Scoring System v3.0 - Test Suite")
    print("=" * 70)

    try:
        test_gang_detection()
        test_adoption_analysis()
        test_merchant_reply()
        test_full_integration()
        test_config_summary()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)

    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
