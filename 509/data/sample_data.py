from typing import Dict, List
from models.schemas import (
    User, Dish, Order, Season, Allergen, UserPreference, NutritionInfo, 
    OrderItem, HealthData, ActivityLevel, Coupon, CouponType
)
from datetime import datetime, timedelta
import random


def create_sample_users() -> Dict[str, User]:
    users = {}
    
    users["u001"] = User(
        user_id="u001",
        name="张三",
        age=28,
        gender="male",
        allergens=[Allergen.PEANUT],
        preferences=UserPreference(
            taste_preferences=["辣", "麻辣"],
            cuisine_preferences=["川菜", "湘菜"],
            disliked_ingredients=["苦瓜", "芹菜"],
            diet_restrictions=[]
        ),
        order_history=["d001", "d003", "d005", "d007", "d010"],
        health_data=HealthData(
            height=175,
            weight=72,
            bmi=23.5,
            activity_level=ActivityLevel.MODERATE,
            health_conditions=[]
        )
    )
    
    users["u002"] = User(
        user_id="u002",
        name="李四",
        age=35,
        gender="female",
        allergens=[Allergen.SHELLFISH],
        preferences=UserPreference(
            taste_preferences=["清淡", "甜"],
            cuisine_preferences=["粤菜", "江浙菜"],
            disliked_ingredients=["辣椒"],
            diet_restrictions=["低糖"]
        ),
        order_history=["d002", "d004", "d006", "d008", "d012"],
        health_data=HealthData(
            height=162,
            weight=58,
            bmi=22.1,
            activity_level=ActivityLevel.LIGHT,
            target_weight=55,
            health_conditions=[]
        )
    )
    
    users["u003"] = User(
        user_id="u003",
        name="王五",
        age=22,
        gender="male",
        allergens=[],
        preferences=UserPreference(
            taste_preferences=["酸辣", "香"],
            cuisine_preferences=["川菜", "东北菜"],
            disliked_ingredients=[],
            diet_restrictions=[]
        ),
        order_history=["d001", "d002", "d005", "d009", "d011", "d015"],
        health_data=HealthData(
            height=180,
            weight=68,
            bmi=21.0,
            activity_level=ActivityLevel.ACTIVE,
            health_conditions=[]
        )
    )
    
    users["u004"] = User(
        user_id="u004",
        name="赵六",
        age=45,
        gender="male",
        allergens=[Allergen.MILK],
        preferences=UserPreference(
            taste_preferences=["咸鲜", "清淡"],
            cuisine_preferences=["鲁菜", "粤菜"],
            disliked_ingredients=["芥末"],
            diet_restrictions=["低卡"]
        ),
        order_history=["d004", "d006", "d008", "d013", "d014"],
        health_data=HealthData(
            height=172,
            weight=85,
            bmi=28.7,
            activity_level=ActivityLevel.SEDENTARY,
            target_weight=75,
            health_conditions=["高血压"]
        )
    )
    
    users["u005"] = User(
        user_id="u005",
        name="陈七",
        age=30,
        gender="female",
        allergens=[Allergen.EGG, Allergen.WHEAT],
        preferences=UserPreference(
            taste_preferences=["麻辣", "蒜香"],
            cuisine_preferences=["川菜", "云贵菜"],
            disliked_ingredients=["香菜"],
            diet_restrictions=[]
        ),
        order_history=["d003", "d005", "d007", "d010", "d016"],
        health_data=HealthData(
            height=165,
            weight=52,
            bmi=19.1,
            activity_level=ActivityLevel.VERY_ACTIVE,
            target_weight=55,
            health_conditions=[]
        )
    )
    
    return users


def create_sample_dishes() -> Dict[str, Dish]:
    dishes = {}
    
    dishes["d001"] = Dish(
        dish_id="d001",
        name="麻婆豆腐",
        description="经典川菜，麻辣鲜香，豆腐嫩滑",
        price=28.0,
        cuisine="川菜",
        taste_tags=["辣", "麻辣", "咸鲜"],
        ingredients=["豆腐", "牛肉末", "豆瓣酱", "花椒", "辣椒"],
        season=None,
        nutrition=NutritionInfo(calories=220, protein=15, fat=14, carbohydrates=8, fiber=2),
        allergens=[],
        popularity_score=9.2
    )
    
    dishes["d002"] = Dish(
        dish_id="d002",
        name="白切鸡",
        description="粤菜经典，皮爽肉滑，原汁原味",
        price=58.0,
        cuisine="粤菜",
        taste_tags=["清淡", "咸鲜"],
        ingredients=["土鸡", "姜", "葱", "料酒"],
        season=None,
        nutrition=NutritionInfo(calories=280, protein=35, fat=15, carbohydrates=2, fiber=0.5),
        allergens=[],
        popularity_score=8.5
    )
    
    dishes["d003"] = Dish(
        dish_id="d003",
        name="水煮鱼",
        description="川菜代表作，鱼肉鲜嫩，麻辣过瘾",
        price=88.0,
        cuisine="川菜",
        taste_tags=["辣", "麻辣", "香"],
        ingredients=["草鱼", "豆芽", "干辣椒", "花椒", "郫县豆瓣"],
        season=None,
        nutrition=NutritionInfo(calories=380, protein=45, fat=20, carbohydrates=10, fiber=3),
        allergens=[Allergen.FISH],
        popularity_score=9.5
    )
    
    dishes["d004"] = Dish(
        dish_id="d004",
        name="清蒸鲈鱼",
        description="粤菜清蒸，鲜嫩可口，营养丰富",
        price=98.0,
        cuisine="粤菜",
        taste_tags=["清淡", "咸鲜"],
        ingredients=["鲈鱼", "葱", "姜", "蒸鱼豉油"],
        season=Season.SUMMER,
        nutrition=NutritionInfo(calories=260, protein=42, fat=8, carbohydrates=3, fiber=0.5),
        allergens=[Allergen.FISH],
        popularity_score=8.8
    )
    
    dishes["d005"] = Dish(
        dish_id="d005",
        name="宫保鸡丁",
        description="川菜经典，鸡肉嫩滑，花生香脆",
        price=42.0,
        cuisine="川菜",
        taste_tags=["辣", "酸甜", "香"],
        ingredients=["鸡胸肉", "花生米", "干辣椒", "黄瓜", "胡萝卜"],
        season=None,
        nutrition=NutritionInfo(calories=320, protein=28, fat=18, carbohydrates=15, fiber=2),
        allergens=[Allergen.PEANUT],
        popularity_score=9.0
    )
    
    dishes["d006"] = Dish(
        dish_id="d006",
        name="虾饺皇",
        description="粤式点心，皮薄馅多，虾肉鲜美",
        price=38.0,
        cuisine="粤菜",
        taste_tags=["清淡", "鲜"],
        ingredients=["虾仁", "澄粉", "猪肉", "竹笋"],
        season=None,
        nutrition=NutritionInfo(calories=180, protein=12, fat=8, carbohydrates=18, fiber=1),
        allergens=[Allergen.SHELLFISH],
        popularity_score=8.7
    )
    
    dishes["d007"] = Dish(
        dish_id="d007",
        name="重庆火锅",
        description="麻辣鲜香，食材丰富，聚餐首选",
        price=168.0,
        cuisine="川菜",
        taste_tags=["辣", "麻辣", "重口味"],
        ingredients=["牛油锅底", "各种肉类", "蔬菜", "豆制品"],
        season=Season.WINTER,
        nutrition=NutritionInfo(calories=800, protein=60, fat=50, carbohydrates=40, fiber=8),
        allergens=[],
        popularity_score=9.8
    )
    
    dishes["d008"] = Dish(
        dish_id="d008",
        name="龙井虾仁",
        description="杭州名菜，茶香虾鲜，清口开胃",
        price=128.0,
        cuisine="江浙菜",
        taste_tags=["清淡", "茶香", "鲜"],
        ingredients=["河虾", "龙井茶叶", "蛋清", "料酒"],
        season=Season.SPRING,
        nutrition=NutritionInfo(calories=220, protein=30, fat=10, carbohydrates=5, fiber=1),
        allergens=[Allergen.EGG, Allergen.SHELLFISH],
        popularity_score=8.3
    )
    
    dishes["d009"] = Dish(
        dish_id="d009",
        name="酸菜鱼",
        description="酸辣开胃，鱼肉嫩滑，汤鲜味美",
        price=78.0,
        cuisine="川菜",
        taste_tags=["酸辣", "酸", "辣"],
        ingredients=["黑鱼", "酸菜", "泡椒", "姜蒜"],
        season=Season.AUTUMN,
        nutrition=NutritionInfo(calories=340, protein=40, fat=16, carbohydrates=12, fiber=4),
        allergens=[Allergen.FISH],
        popularity_score=9.1
    )
    
    dishes["d010"] = Dish(
        dish_id="d010",
        name="口水鸡",
        description="川菜凉菜，麻辣鲜香，鸡肉嫩滑",
        price=48.0,
        cuisine="川菜",
        taste_tags=["辣", "麻辣", "蒜香"],
        ingredients=["三黄鸡", "红油", "花椒", "蒜末", "芝麻"],
        season=Season.SUMMER,
        nutrition=NutritionInfo(calories=300, protein=28, fat=20, carbohydrates=5, fiber=1),
        allergens=[Allergen.SOY],
        popularity_score=8.9
    )
    
    dishes["d011"] = Dish(
        dish_id="d011",
        name="锅包肉",
        description="东北名菜，外酥里嫩，酸甜可口",
        price=52.0,
        cuisine="东北菜",
        taste_tags=["酸甜", "香", "酥脆"],
        ingredients=["猪里脊肉", "淀粉", "糖", "醋", "胡萝卜"],
        season=None,
        nutrition=NutritionInfo(calories=450, protein=25, fat=25, carbohydrates=35, fiber=1),
        allergens=[Allergen.WHEAT],
        popularity_score=8.6
    )
    
    dishes["d012"] = Dish(
        dish_id="d012",
        name="蜜汁叉烧",
        description="粤式烧腊，色泽红亮，甜香入味",
        price=68.0,
        cuisine="粤菜",
        taste_tags=["甜", "香", "咸鲜"],
        ingredients=["梅花肉", "叉烧酱", "蜂蜜", "料酒"],
        season=None,
        nutrition=NutritionInfo(calories=380, protein=32, fat=22, carbohydrates=15, fiber=0),
        allergens=[Allergen.SOY],
        popularity_score=8.4
    )
    
    dishes["d013"] = Dish(
        dish_id="d013",
        name="糖醋鲤鱼",
        description="鲁菜经典，外焦里嫩，酸甜适口",
        price=88.0,
        cuisine="鲁菜",
        taste_tags=["酸甜", "香", "酥脆"],
        ingredients=["黄河鲤鱼", "糖", "醋", "番茄酱", "葱姜"],
        season=None,
        nutrition=NutritionInfo(calories=420, protein=38, fat=18, carbohydrates=28, fiber=2),
        allergens=[Allergen.FISH, Allergen.WHEAT],
        popularity_score=8.2
    )
    
    dishes["d014"] = Dish(
        dish_id="d014",
        name="葱烧海参",
        description="鲁菜名品，海参软糯，葱香浓郁",
        price=298.0,
        cuisine="鲁菜",
        taste_tags=["咸鲜", "葱香", "醇厚"],
        ingredients=["海参", "大葱", "蚝油", "酱油", "料酒"],
        season=Season.WINTER,
        nutrition=NutritionInfo(calories=180, protein=28, fat=6, carbohydrates=12, fiber=1),
        allergens=[Allergen.SHELLFISH],
        popularity_score=7.8
    )
    
    dishes["d015"] = Dish(
        dish_id="d015",
        name="地三鲜",
        description="东北家常菜，鲜香下饭",
        price=32.0,
        cuisine="东北菜",
        taste_tags=["咸鲜", "香"],
        ingredients=["茄子", "土豆", "青椒", "蒜"],
        season=Season.SUMMER,
        nutrition=NutritionInfo(calories=280, protein=5, fat=18, carbohydrates=25, fiber=4),
        allergens=[],
        popularity_score=8.0
    )
    
    dishes["d016"] = Dish(
        dish_id="d016",
        name="云南过桥米线",
        description="云南特色，汤鲜味美，配料丰富",
        price=45.0,
        cuisine="云贵菜",
        taste_tags=["鲜", "清淡", "香"],
        ingredients=["米线", "鸡汤", "火腿", "蔬菜", "鹌鹑蛋"],
        season=None,
        nutrition=NutritionInfo(calories=420, protein=18, fat=15, carbohydrates=55, fiber=3),
        allergens=[Allergen.EGG],
        popularity_score=8.5
    )
    
    return dishes


def create_sample_orders(users: Dict[str, User], dishes: Dict[str, Dish]) -> List[Order]:
    orders = []
    order_id = 1
    
    user_ids = list(users.keys())
    dish_ids = list(dishes.keys())
    
    base_time = datetime.now() - timedelta(days=90)
    
    for day in range(30):
        num_orders = random.randint(3, 8)
        for _ in range(num_orders):
            user_id = random.choice(user_ids)
            num_items = random.randint(2, 5)
            selected_dishes = random.sample(dish_ids, num_items)
            
            items = []
            total = 0
            for dish_id in selected_dishes:
                qty = random.randint(1, 2)
                items.append(OrderItem(
                    dish_id=dish_id,
                    quantity=qty,
                    rating=round(random.uniform(3.0, 5.0), 1)
                ))
                total += dishes[dish_id].price * qty
            
            is_group = random.random() < 0.2
            group_members = []
            if is_group:
                other_users = [u for u in user_ids if u != user_id]
                group_members = random.sample(other_users, min(2, len(other_users)))
            
            orders.append(Order(
                order_id=f"o{order_id:03d}",
                user_id=user_id,
                items=items,
                order_time=base_time + timedelta(days=day, hours=random.randint(11, 20)),
                total_amount=round(total, 2),
                is_group_order=is_group,
                group_members=group_members
            ))
            order_id += 1
    
    return orders


def create_sample_coupons() -> List[Coupon]:
    now = datetime.now()
    coupons = []
    
    coupons.append(Coupon(
        coupon_id="c001",
        name="新用户专享8折",
        coupon_type=CouponType.PERCENTAGE,
        discount_value=20,
        min_order_amount=0,
        max_discount=50,
        valid_from=now - timedelta(days=30),
        valid_until=now + timedelta(days=60),
        description="新用户首单立享8折优惠，最高减50元",
        applicable_cuisines=[],
        is_active=True
    ))
    
    coupons.append(Coupon(
        coupon_id="c002",
        name="满100减20",
        coupon_type=CouponType.FIXED_AMOUNT,
        discount_value=20,
        min_order_amount=100,
        valid_from=now - timedelta(days=15),
        valid_until=now + timedelta(days=45),
        description="满100元立减20元",
        applicable_cuisines=[],
        is_active=True
    ))
    
    coupons.append(Coupon(
        coupon_id="c003",
        name="满200减50",
        coupon_type=CouponType.FIXED_AMOUNT,
        discount_value=50,
        min_order_amount=200,
        valid_from=now - timedelta(days=15),
        valid_until=now + timedelta(days=45),
        description="满200元立减50元",
        applicable_cuisines=[],
        is_active=True
    ))
    
    coupons.append(Coupon(
        coupon_id="c004",
        name="川菜专属7折",
        coupon_type=CouponType.PERCENTAGE,
        discount_value=30,
        min_order_amount=80,
        max_discount=60,
        valid_from=now - timedelta(days=7),
        valid_until=now + timedelta(days=30),
        description="川菜菜品专享7折，最高减60元",
        applicable_cuisines=["川菜"],
        is_active=True
    ))
    
    coupons.append(Coupon(
        coupon_id="c005",
        name="工作日午市券",
        coupon_type=CouponType.FIXED_AMOUNT,
        discount_value=15,
        min_order_amount=50,
        valid_from=now - timedelta(days=10),
        valid_until=now + timedelta(days=50),
        description="工作日午市（11:00-14:00）满50减15",
        applicable_cuisines=[],
        is_active=True
    ))
    
    coupons.append(Coupon(
        coupon_id="c006",
        name="满300减80",
        coupon_type=CouponType.FIXED_AMOUNT,
        discount_value=80,
        min_order_amount=300,
        valid_from=now - timedelta(days=5),
        valid_until=now + timedelta(days=25),
        description="多人聚餐专享，满300减80",
        applicable_cuisines=[],
        is_active=True
    ))
    
    return coupons


def mark_some_dishes_sold_out(dishes: Dict[str, Dish]) -> Dict[str, Dish]:
    sold_out_dishes = ["d003", "d007"]
    for dish_id in sold_out_dishes:
        if dish_id in dishes:
            dishes[dish_id].is_available = False
            dishes[dish_id].stock_quantity = 0
    return dishes
