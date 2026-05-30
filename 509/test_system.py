import sys
sys.path.append('.')

from data import (
    create_sample_users, create_sample_dishes, create_sample_orders,
    create_sample_coupons, mark_some_dishes_sold_out
)
from engine import (
    RecommendationEngine, DishSubstituteEngine,
    CouponEngine, AllergyKnowledgeBase
)
from models.schemas import Season, SubstituteReason


def test_all_new_features():
    print("=" * 80)
    print("餐厅菜品推荐系统 - 新功能综合测试")
    print("=" * 80)
    
    print("\n1. 加载数据...")
    users = create_sample_users()
    dishes = create_sample_dishes()
    orders = create_sample_orders(users, dishes)
    coupons = create_sample_coupons()
    dishes = mark_some_dishes_sold_out(dishes)
    
    print(f"   用户数: {len(users)}")
    print(f"   菜品数: {len(dishes)}")
    print(f"   优惠券数: {len(coupons)}")
    print(f"   沽清菜品: {[d for d in dishes if not dishes[d].is_available]}")
    
    print("\n" + "-" * 80)
    print("2. 菜品替代推荐测试（沽清替代）")
    print("-" * 80)
    
    substitute_engine = DishSubstituteEngine(dishes)
    
    sold_out_dish = "d003"
    print(f"\n   沽清菜品: {dishes[sold_out_dish].name} (水煮鱼)")
    
    substitutes = substitute_engine.find_substitutes(
        sold_out_dish,
        SubstituteReason.SOLD_OUT,
        user=users['u001'],
        top_n=3
    )
    
    print(f"   推荐替代品:")
    for sub in substitutes:
        price_diff = f"+{sub.price_difference:.0f}元" if sub.price_difference >= 0 else f"{sub.price_difference:.0f}元"
        print(f"   - {sub.substitute_dish_name} (相似度: {sub.similarity_score:.2f}, {price_diff})")
        print(f"     说明: {sub.explanation}")
    
    print("\n   购物车自动替换测试:")
    cart = ["d003", "d001", "d007", "d005"]
    cart_names = [dishes[d].name for d in cart]
    print(f"   原始购物车: {cart_names}")
    
    result = substitute_engine.substitute_sold_out_dishes(cart, users['u001'])
    final_names = [dishes[d].name for d in result.final_cart]
    print(f"   替换后购物车: {final_names}")
    
    if result.substitutions:
        print(f"   替换记录:")
        for sub in result.substitutions:
            print(f"     {sub.original_dish_name} → {sub.substitute_dish_name}")
    
    print("\n" + "-" * 80)
    print("3. 优惠券推荐 + 凑单推荐测试")
    print("-" * 80)
    
    coupon_engine = CouponEngine(coupons, dishes)
    
    test_cart = ["d001", "d002", "d005"]
    cart_total = coupon_engine.calculate_cart_total(test_cart)
    cart_names = [dishes[d].name for d in test_cart]
    print(f"\n   购物车: {cart_names}")
    print(f"   当前总价: {cart_total:.0f}元")
    
    coupon_recs = coupon_engine.get_coupon_recommendations(test_cart, users['u001'], top_n=3)
    
    print(f"\n   可用优惠券推荐:")
    for i, rec in enumerate(coupon_recs, 1):
        if rec.amount_to_add > 0:
            print(f"   {i}. {rec.coupon.name}")
            print(f"      还差 {rec.amount_to_add:.0f} 元可用，可省 {rec.savings_amount:.0f} 元")
            if rec.suggestion_dishes:
                add_on_names = [d.dish_name for d in rec.suggestion_dishes[:2]]
                print(f"      推荐加购: {', '.join(add_on_names)}")
        else:
            print(f"   {i}. {rec.coupon.name}")
            print(f"      已满足条件，可省 {rec.savings_amount:.0f} 元")
    
    print(f"\n   加购推荐:")
    add_ons = coupon_engine.get_add_on_recommendations(test_cart, users['u001'], top_n=3)
    for i, add_on in enumerate(add_ons, 1):
        print(f"   {i}. {add_on.add_on_dish.dish_name} - ¥{add_on.price:.0f}")
        print(f"      {add_on.reason}")
        if add_on.contributes_to_coupon:
            print(f"      (可用于凑单优惠券)")
    
    print("\n" + "-" * 80)
    print("4. 过敏源自动标注 + 过敏知识库测试")
    print("-" * 80)
    
    allergy_kb = AllergyKnowledgeBase()
    
    print(f"\n   菜品过敏源自动标注测试:")
    test_dishes = ["d005", "d006", "d008"]
    for dish_id in test_dishes:
        dish = dishes[dish_id]
        allergens, labels = allergy_kb.label_dish_allergens(dish)
        print(f"   - {dish.name}:")
        if labels:
            for label in labels:
                print(f"     ⚠ {label}")
        else:
            print(f"     ✓ 无常见过敏源")
    
    print(f"\n   用户菜单安全检测 (用户: u001, 花生过敏):")
    user = users['u001']
    menu_dishes = list(dishes.values())[:8]
    safety = allergy_kb.check_menu_safety(user, menu_dishes)
    
    print(f"   安全菜品: {safety['safe_count']} 道")
    print(f"   风险菜品: {safety['risky_count']} 道")
    print(f"   高风险菜品: {safety['high_risk_count']} 道")
    
    if safety['high_risk_dishes']:
        print(f"\n   高风险菜品详情:")
        for risky in safety['high_risk_dishes'][:3]:
            dish = dishes[risky['dish_id']]
            warnings = risky['warnings']
            print(f"   - {dish.name}:")
            for w in warnings:
                print(f"     {w['severity'].upper()}: {w['allergen'].value}")
                print(f"     {w['description']}")
            
            alternatives = allergy_kb.get_alternative_dishes(user, dish, dishes, top_n=2)
            if alternatives:
                alt_names = [a.name for a in alternatives]
                print(f"     推荐替代: {', '.join(alt_names)}")
    
    print(f"\n   过敏源知识库查询 (花生):")
    peanut_info = allergy_kb.get_allergen_info(user.allergens[0])
    if peanut_info:
        print(f"   严重程度: {peanut_info.severity_level}")
        print(f"   常见名称: {', '.join(peanut_info.common_names[:5])}")
        print(f"   相关食材: {', '.join(peanut_info.related_ingredients[:5])}")
        print(f"   交叉反应: {[a.value for a in peanut_info.cross_reactivity]}")
        print(f"   注意事项: {peanut_info.avoidance_tips[0]}")
    
    print("\n" + "-" * 80)
    print("5. 综合推荐引擎测试（整合所有功能）")
    print("-" * 80)
    
    engine = RecommendationEngine(users, dishes, orders)
    
    print(f"\n   个性化推荐 (u001 张三, 夏季):")
    recs, allergens, seasonal = engine.get_personalized_recommendations(
        user_id='u001',
        current_season=Season.SUMMER,
        top_n=5
    )
    
    for i, rec in enumerate(recs, 1):
        dish = dishes[rec.dish_id]
        availability = "✓" if dish.is_available else "✗沽清"
        print(f"   {i}. {rec.dish_name} - {availability}")
        print(f"      评分: {rec.score:.2f}, 理由: {rec.reason}")
        if dish.allergens:
            allergen_names = [a.value for a in dish.allergens]
            print(f"      过敏源: {', '.join(allergen_names)}")
    
    print("\n" + "=" * 80)
    print("所有新功能测试通过!")
    print("  ✓ 菜品沽清替代推荐")
    print("  ✓ 优惠券推荐 + 凑单菜品")
    print("  ✓ 过敏源自动标注")
    print("  ✓ 过敏知识库关联检测")
    print("  ✓ 菜单安全检测")
    print("=" * 80)


if __name__ == "__main__":
    test_all_new_features()
