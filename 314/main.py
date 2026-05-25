import sys
from datetime import datetime, timedelta
import random

from scoring_engine import CommentQualityScoringEngine
from user_reputation import UserHistory
from data_augmentation import TextDataAugmentor
from event_driven_reputation import EventType, EventSeverity
from fake_review_detector import FakeReviewDetector, ReviewForDetection
from review_ranking import ReviewForRanking, SortStrategy
from trend_monitor import AlertSeverity


def create_sample_user_histories() -> dict:
    histories = {}
    
    histories['trusted_user'] = UserHistory(
        user_id='U001',
        total_comments=156,
        total_likes=3240,
        total_reports=0,
        average_likes_per_comment=20.8,
        report_rate=0.0,
        account_age_days=730,
        is_verified=True,
        level=7,
        comment_history=[
            {'text': '非常好的产品，做工精良，推荐购买', 'rating': 5, 'timestamp': datetime.now() - timedelta(days=10)},
            {'text': '质量不错，物流也很快，客服态度很好', 'rating': 5, 'timestamp': datetime.now() - timedelta(days=20)},
            {'text': '性价比很高，使用体验不错', 'rating': 4, 'timestamp': datetime.now() - timedelta(days=30)},
        ]
    )
    
    histories['normal_user'] = UserHistory(
        user_id='U002',
        total_comments=45,
        total_likes=180,
        total_reports=1,
        average_likes_per_comment=4.0,
        report_rate=0.022,
        account_age_days=180,
        is_verified=False,
        level=3,
        comment_history=[
            {'text': '还不错，挺好用的', 'rating': 4, 'timestamp': datetime.now() - timedelta(days=5)},
            {'text': '一般般吧', 'rating': 3, 'timestamp': datetime.now() - timedelta(days=15)},
        ]
    )
    
    histories['new_user'] = UserHistory(
        user_id='U003',
        total_comments=3,
        total_likes=2,
        total_reports=0,
        average_likes_per_comment=0.7,
        report_rate=0.0,
        account_age_days=7,
        is_verified=False,
        level=1
    )
    
    histories['risky_user'] = UserHistory(
        user_id='U004',
        total_comments=28,
        total_likes=15,
        total_reports=5,
        average_likes_per_comment=0.5,
        report_rate=0.179,
        account_age_days=45,
        is_verified=False,
        level=2,
        comment_history=[
            {'text': '垃圾产品，千万别买！！！', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=5)},
            {'text': '骗人的，假货！！！', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=10)},
            {'text': '很差很差很差', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=15)},
        ]
    )
    
    histories['influential_user'] = UserHistory(
        user_id='U005',
        total_comments=230,
        total_likes=15600,
        total_reports=2,
        average_likes_per_comment=67.8,
        report_rate=0.009,
        account_age_days=1095,
        is_verified=True,
        level=10,
        comment_history=[
            {'text': '经过两周的详细测试，这款产品的性能超出预期。', 'rating': 5, 'timestamp': datetime.now() - timedelta(days=5)},
            {'text': '对比了同价位的三款产品，这款的性价比最高。', 'rating': 4, 'timestamp': datetime.now() - timedelta(days=15)},
        ]
    )
    
    return histories


def create_sample_comments() -> list:
    comments = [
        {
            'id': 'C001',
            'text': '这款手机我已经用了3个月了，整体来说非常满意。屏幕是6.7英寸的OLED屏，显示效果非常细腻，看视频玩游戏都很爽。处理器是最新的骁龙8 Gen3，日常使用完全不卡顿，玩大型游戏也能保持60帧以上。续航方面，4800mAh的电池中度使用可以用一天半，充电速度也很快，30分钟就能充到80%。拍照效果也不错，5000万像素的主摄像头拍照很清晰，夜景模式也很给力。唯一的小缺点是手机稍微有点重，210克的重量长时间握持有点累。总体来说，这款手机性价比很高，非常推荐购买！',
            'user_type': 'influential_user',
            'description': '优质评论 - 详细具体，多维度评价'
        },
        {
            'id': 'C002',
            'text': '很好，不错，推荐购买。',
            'user_type': 'normal_user',
            'description': '简短评论 - 信息含量低'
        },
        {
            'id': 'C003',
            'text': '垃圾！！！垃圾！！！垃圾！！！千万别买！！！骗人的！！！',
            'user_type': 'risky_user',
            'description': '差评刷屏 - 疑似恶意差评'
        },
        {
            'id': 'C004',
            'text': '五星好评！！！非常好！！！强烈推荐！！！太赞了！！！',
            'user_type': 'new_user',
            'description': '模板化好评 - 情感词过多'
        },
        {
            'id': 'C005',
            'text': '这款华为Mate 60 Pro我入手一周了，体验非常好。首先是外观设计，曲面屏手感很好，素皮背面不容易沾指纹。系统是鸿蒙4.0，流畅度没得说，各种APP秒开。拍照方面，可变光圈确实很实用，白天拍照色彩鲜艳，夜景模式噪点控制得很好。续航也不错，5000mAh电池用一天完全没问题。66W快充半小时能充到70%。对比我之前用的iPhone 14，信号强太多了，在地下车库也能满格。缺点就是价格有点贵，而且有点重，225克。但总体来说，支持华为，值得入手！',
            'user_type': 'trusted_user',
            'description': '优质评论 - 有对比，有具体参数'
        },
        {
            'id': 'C006',
            'text': '性价比很高，质量不错，物流也很快，客服态度很好，包装也很结实。',
            'user_type': 'normal_user',
            'description': '中等评论 - 泛泛而谈，缺乏细节'
        },
        {
            'id': 'C007',
            'text': '这款耳机的降噪效果真的让我惊艳！在地铁上开启降噪模式，几乎听不到外界的噪音，音质也很清晰，低音浑厚有力，高音清澈不刺耳。佩戴舒适度也不错，我戴了3个小时也没有感到不适。续航方面，官方说6小时，我实际用下来大概5个半小时，还可以接受。连接速度很快，开盖秒连。唯一的问题是触控操作有时候不太灵敏，经常误触。总体来说，在这个价位段，这款耳机的表现已经非常出色了，强烈推荐给需要降噪耳机的朋友们！',
            'user_type': 'influential_user',
            'description': '优质评论 - 详细使用体验'
        },
        {
            'id': 'C008',
            'text': '太差了，用了三天就坏了，已经申请退款了。',
            'user_type': 'risky_user',
            'description': '短差评 - 缺乏具体细节'
        },
        {
            'id': 'C009',
            'text': '5星好评，非常好的产品。',
            'user_type': 'new_user',
            'description': '超短评论 - 无参考价值'
        },
        {
            'id': 'C010',
            'text': '买给家里老人用的，老人说很好用，屏幕大字大，声音也大，操作简单。电池也很耐用，充一次电可以用3天。价格也很实惠，699元的价格能买到这样的手机真的很不错。小米的品牌还是值得信赖的，之前买过好几个小米的产品都没出过问题。物流也很快，当天下单第二天就到了。总的来说很满意，给个5星好评！',
            'user_type': 'trusted_user',
            'description': '良好评论 - 有具体使用场景'
        }
    ]
    
    return comments


def main():
    print("=" * 80)
    print("                    用户评论质量评分系统 v3.0")
    print("=" * 80)
    print()
    print("v3.0 新增功能:")
    print("  ✅ 虚假评论检测（刷单、水军、竞品恶意评论识别）")
    print("  ✅ 评论排序优化（7种策略，高质量评论优先展示）")
    print("  ✅ 评论趋势监控（7种异常检测，质量突降实时告警）")
    print()
    print("v2.0 核心功能:")
    print("  ✅ 短评数据增强（回译、随机删除、同义词替换等8种方法）")
    print("  ✅ 事件驱动的用户信誉实时更新（举报核实后实时扣分）")
    print("  ✅ 评分决策树路径解释（可视化展示各因素贡献权重）")
    print("  ✅ 事件日志和审计追踪系统")
    print()
    print("系统架构:")
    print("  ├── BERT文本分析模块 (有用性、真实性、完整性)")
    print("  ├── 知识图谱模块 (实体识别、关系抽取、事实验证)")
    print("  ├── 用户信誉统计模型 (可信度、影响力、一致性、风险)")
    print("  ├── 数据增强模块 (8种增强方法提升泛化能力)")
    print("  ├── 事件驱动信誉系统 (10种事件类型实时更新)")
    print("  ├── 决策树解释器 (贡献度可视化、规则生成)")
    print("  ├── 虚假评论检测器 (刷单/水军/竞品识别)")
    print("  ├── 评论排序引擎 (多策略融合、多样性重排)")
    print("  ├── 趋势监控告警器 (7种异常检测、实时告警)")
    print("  └── 综合评分引擎 (加权融合 + 完整可解释性输出)")
    print()
    
    print("初始化系统组件...")
    engine = CommentQualityScoringEngine(use_bert_pretrained=False, enable_event_driven=True, enable_fake_detection=True)
    augmentor = TextDataAugmentor(random_seed=42)
    fake_detector = FakeReviewDetector()
    user_histories = create_sample_user_histories()
    sample_comments = create_sample_comments()
    print("初始化完成！")
    print()
    
    while True:
        print("=" * 80)
        print("请选择操作:")
        print("=" * 80)
        print("【核心功能】")
        print("  1. 运行所有示例评论的评分演示")
        print("  2. 选择单个评论进行详细分析")
        print("  3. 输入自定义评论进行评分")
        print("  4. 调整评分权重")
        print()
        print("【v2.0新增功能】")
        print("  5. 短评数据增强演示")
        print("  6. 事件驱动信誉更新演示")
        print("  7. 决策树路径解释演示")
        print("  8. 查看用户审计追踪")
        print("  9. 模拟举报核实与信誉扣分")
        print()
        print("【v3.0新增功能】")
        print("  10. 虚假评论检测演示")
        print("  11. 评论排序优化演示")
        print("  12. 评论趋势监控与告警演示")
        print()
        print("【其他】")
        print("  13. 查看系统说明")
        print("  0. 退出程序")
        print("=" * 80)
        
        choice = input("请输入选项 (0-13): ").strip()
        
        if choice == '0':
            print("感谢使用，再见！")
            break
        
        elif choice == '1':
            run_all_demos(engine, user_histories, sample_comments)
        
        elif choice == '2':
            run_single_comment_demo(engine, user_histories, sample_comments)
        
        elif choice == '3':
            run_custom_comment(engine, user_histories)
        
        elif choice == '4':
            adjust_weights(engine)
        
        elif choice == '5':
            run_data_augmentation_demo(augmentor)
        
        elif choice == '6':
            run_event_driven_demo(engine, user_histories)
        
        elif choice == '7':
            run_decision_tree_demo(engine, user_histories, sample_comments)
        
        elif choice == '8':
            run_audit_trail_demo(engine, user_histories)
        
        elif choice == '9':
            run_report_verification_demo(engine, user_histories)
        
        elif choice == '10':
            run_fake_review_detection_demo(engine, fake_detector, user_histories)
        
        elif choice == '11':
            run_review_ranking_demo(engine, user_histories, sample_comments)
        
        elif choice == '12':
            run_trend_monitoring_demo(engine)
        
        elif choice == '13':
            show_system_info()
        
        else:
            print("无效选项，请重新输入！")
            print()


def run_all_demos(engine, user_histories, sample_comments):
    print("\n" + "=" * 80)
    print("运行所有示例评论评分演示")
    print("=" * 80)
    
    results = []
    for idx, comment in enumerate(sample_comments, 1):
        print(f"\n[{idx}/{len(sample_comments)}] 正在分析: {comment['description']}")
        print(f"评论ID: {comment['id']}")
        print(f"用户类型: {comment['user_type']}")
        
        user_history = user_histories[comment['user_type']]
        historical_scores = [0.75, 0.82, 0.78] if comment['user_type'] in ['trusted_user', 'influential_user'] else None
        
        result = engine.score_comment(
            comment_id=comment['id'],
            comment_text=comment['text'],
            user_history=user_history,
            historical_text_scores=historical_scores
        )
        
        results.append(result)
        engine.print_result_summary(result, show_details=False)
        print()
    
    print("\n" + "=" * 80)
    print("所有评论评分汇总")
    print("=" * 80)
    print(f"{'评论ID':<10} {'类型':<15} {'用户类型':<15} {'最终得分':<12} {'等级':<10}")
    print("-" * 65)
    
    results_sorted = sorted(results, key=lambda x: x.final_score, reverse=True)
    for result in results_sorted:
        comment = next(c for c in sample_comments if c['id'] == result.comment_id)
        print(f"{result.comment_id:<10} {comment['description'][:13]:<15} {result.user_id:<15} "
              f"{result.final_score:<12.4f} {result.score_grade:<10}")
    
    print()
    input("按回车键返回主菜单...")


def run_single_comment_demo(engine, user_histories, sample_comments):
    print("\n" + "=" * 80)
    print("选择单个评论进行详细分析")
    print("=" * 80)
    print("\n可用评论:")
    for idx, comment in enumerate(sample_comments, 1):
        print(f"  {idx}. [{comment['id']}] {comment['description']}")
    
    try:
        choice = int(input("\n请选择评论编号 (1-10): ")) - 1
        if 0 <= choice < len(sample_comments):
            comment = sample_comments[choice]
            print(f"\n评论内容:")
            print("-" * 80)
            print(comment['text'])
            print("-" * 80)
            
            user_history = user_histories[comment['user_type']]
            historical_scores = [0.75, 0.82, 0.78] if comment['user_type'] in ['trusted_user', 'influential_user'] else None
            
            print(f"\n用户类型: {comment['user_type']}")
            print(f"用户信息: ID={user_history.user_id}, "
                  f"评论数={user_history.total_comments}, "
                  f"获赞数={user_history.total_likes}, "
                  f"举报数={user_history.total_reports}, "
                  f"等级=Lv.{user_history.level}")
            
            print("\n开始分析...\n")
            result = engine.score_comment(
                comment_id=comment['id'],
                comment_text=comment['text'],
                user_history=user_history,
                historical_text_scores=historical_scores
            )
            
            engine.print_result_summary(
                result, 
                show_details=True,
                show_decision_tree=True,
                show_feature_contributions=True
            )
            
            export_choice = input("\n是否导出结果为JSON文件? (y/n): ").strip().lower()
            if export_choice == 'y':
                file_path = f"result_{comment['id']}.json"
                engine.export_result_to_json(result, file_path)
                print(f"结果已导出至: {file_path}")
        else:
            print("无效的编号！")
    except ValueError:
        print("请输入有效的数字！")
    
    print()
    input("按回车键返回主菜单...")


def run_custom_comment(engine, user_histories):
    print("\n" + "=" * 80)
    print("输入自定义评论进行评分")
    print("=" * 80)
    
    comment_text = input("请输入评论内容: ").strip()
    if not comment_text:
        print("评论内容不能为空！")
        input("按回车键返回主菜单...")
        return
    
    print("\n选择用户类型:")
    print("  1. 高信誉用户 (资深、实名认证、无举报)")
    print("  2. 普通用户 (有一定历史、少量举报)")
    print("  3. 新用户 (注册时间短、评论少)")
    print("  4. 高风险用户 (举报率高、评价极端)")
    print("  5. 有影响力用户 (大V、高赞、资深)")
    
    user_map = {
        '1': 'trusted_user',
        '2': 'normal_user',
        '3': 'new_user',
        '4': 'risky_user',
        '5': 'influential_user'
    }
    
    user_choice = input("请选择用户类型 (1-5): ").strip()
    if user_choice not in user_map:
        print("无效选择，默认使用普通用户！")
        user_choice = '2'
    
    user_type = user_map[user_choice]
    user_history = user_histories[user_type]
    
    comment_id = input("请输入评论ID (可选，默认CUSTOM): ").strip() or "CUSTOM"
    
    print("\n开始分析...\n")
    result = engine.score_comment(
        comment_id=comment_id,
        comment_text=comment_text,
        user_history=user_history
    )
    
    engine.print_result_summary(
        result, 
        show_details=True,
        show_decision_tree=True,
        show_feature_contributions=True,
        show_decision_paths=True
    )
    
    export_choice = input("\n是否导出结果为JSON文件? (y/n): ").strip().lower()
    if export_choice == 'y':
        file_path = f"result_{comment_id}.json"
        engine.export_result_to_json(result, file_path)
        print(f"结果已导出至: {file_path}")
    
    print()
    input("按回车键返回主菜单...")


def adjust_weights(engine):
    print("\n" + "=" * 80)
    print("调整评分权重")
    print("=" * 80)
    print("\n当前权重配置:")
    print(f"  文本质量: {engine.weights['text_quality']:.2%}")
    print(f"  知识图谱: {engine.weights['knowledge_graph']:.2%}")
    print(f"  用户信誉: {engine.weights['user_reputation']:.2%}")
    
    print("\n权重说明:")
    print("  文本质量 - 评论内容的有用性、真实性、完整性 (默认 45%)")
    print("  知识图谱 - 实体丰富度、关系质量、事实一致性 (默认 25%)")
    print("  用户信誉 - 发布用户的可信度、影响力、风险 (默认 30%)")
    
    print("\n请输入新的权重（三个权重之和应为100%）:")
    try:
        text_weight = float(input("  文本质量权重 (%): ")) / 100
        kg_weight = float(input("  知识图谱权重 (%): ")) / 100
        rep_weight = float(input("  用户信誉权重 (%): ")) / 100
        
        total = text_weight + kg_weight + rep_weight
        if abs(total - 1.0) > 0.01:
            print(f"\n警告: 权重之和为 {total*100:.1f}%，将自动归一化！")
        
        custom_weights = {
            'text_quality': text_weight,
            'knowledge_graph': kg_weight,
            'user_reputation': rep_weight
        }
        engine.update_weights(custom_weights)
        
        print("\n更新后的权重配置:")
        print(f"  文本质量: {engine.weights['text_quality']:.2%}")
        print(f"  知识图谱: {engine.weights['knowledge_graph']:.2%}")
        print(f"  用户信誉: {engine.weights['user_reputation']:.2%}")
        
        reset = input("\n是否重置为默认权重? (y/n): ").strip().lower()
        if reset == 'y':
            default_weights = {
                'text_quality': 0.45,
                'knowledge_graph': 0.25,
                'user_reputation': 0.30
            }
            engine.update_weights(default_weights)
            print("已重置为默认权重！")
        
    except ValueError:
        print("输入无效，权重未更改！")
    
    print()
    input("按回车键返回主菜单...")


def run_data_augmentation_demo(augmentor):
    print("\n" + "=" * 80)
    print("短评数据增强演示")
    print("=" * 80)
    
    print("\n可用的数据增强方法:")
    methods = augmentor.get_method_description()
    for idx, (key, desc) in enumerate(methods.items(), 1):
        print(f"  {idx:2d}. {desc}")
    
    print("\n选择要增强的短评示例:")
    sample_texts = [
        "很好，推荐购买",
        "质量不错，物流很快",
        "性价比很高，很满意",
        "太差了，不推荐",
        "一般般吧，还行"
    ]
    
    for idx, text in enumerate(sample_texts, 1):
        print(f"  {idx}. {text}")
    
    try:
        text_choice = int(input("\n请选择短评编号 (1-5): ")) - 1
        if 0 <= text_choice < len(sample_texts):
            original_text = sample_texts[text_choice]
            
            num_augments = input("请输入生成的增强样本数量 (默认5): ").strip()
            num_augments = int(num_augments) if num_augments.isdigit() else 5
            
            print(f"\n原始文本: {original_text}")
            print(f"\n正在生成 {num_augments} 个增强样本...")
            
            result = augmentor.augment(
                text=original_text,
                num_augments=num_augments
            )
            
            print(f"\n数据增强结果:")
            print("-" * 80)
            print(f"原始文本长度: {result.augmentation_stats['original_length']}")
            print(f"生成增强样本: {result.augmentation_stats['num_augments_generated']}/{result.augmentation_stats['num_augments_requested']}")
            print(f"增强成功率: {result.augmentation_stats['augmentation_ratio']:.1%}")
            print(f"使用的方法: {', '.join(result.methods_used)}")
            
            if result.augmentation_stats.get('method_distribution'):
                print(f"方法分布: {result.augmentation_stats['method_distribution']}")
            
            print("\n生成的增强样本:")
            for idx, aug_text in enumerate(result.augmented_texts, 1):
                print(f"  {idx:2d}. {aug_text}")
            
            print("\n" + "-" * 80)
            print("数据增强可以显著提升模型的泛化能力，特别适合短评、低资源场景。")
            print("通过同义词替换、回译、随机删除等方法，可以生成多样化的训练样本。")
            
        else:
            print("无效的编号！")
    except ValueError:
        print("请输入有效的数字！")
    
    print()
    input("按回车键返回主菜单...")


def run_event_driven_demo(engine, user_histories):
    print("\n" + "=" * 80)
    print("事件驱动的用户信誉更新演示")
    print("=" * 80)
    
    print("\n支持的事件类型:")
    event_types = [
        (EventType.COMMENT_POSTED, "发布评论", EventSeverity.LOW),
        (EventType.COMMENT_LIKED, "评论获赞", EventSeverity.LOW),
        (EventType.COMMENT_REPORTED, "评论被举报", EventSeverity.MEDIUM),
        (EventType.REPORT_VERIFIED, "举报核实", EventSeverity.HIGH),
        (EventType.REPORT_REJECTED, "举报被驳回", EventSeverity.LOW),
        (EventType.USER_VERIFIED, "用户实名认证", EventSeverity.MEDIUM),
        (EventType.LEVEL_UPGRADED, "用户等级提升", EventSeverity.LOW),
        (EventType.INFRACTION_ISSUED, "违规处罚", EventSeverity.CRITICAL),
    ]
    
    for idx, (etype, desc, severity) in enumerate(event_types, 1):
        print(f"  {idx:2d}. {desc:15s} (严重程度: {severity.value})")
    
    print("\n选择测试用户:")
    user_list = list(user_histories.keys())
    for idx, user_type in enumerate(user_list, 1):
        uh = user_histories[user_type]
        print(f"  {idx}. {user_type:15s} (ID:{uh.user_id}, 信誉分初始化中...)")
    
    try:
        user_choice = int(input("\n请选择用户编号 (1-5): ")) - 1
        if 0 <= user_choice < len(user_list):
            user_type = user_list[user_choice]
            user_history = user_histories[user_type]
            
            print(f"\n用户: {user_type}")
            print(f"初始信誉分: {user_history.total_reports / max(user_history.total_comments, 1):.4f} (模拟)")
            
            print("\n选择要触发的事件:")
            for idx, (etype, desc, severity) in enumerate(event_types, 1):
                print(f"  {idx:2d}. {desc}")
            
            event_choice = int(input("\n请选择事件编号 (1-8): ")) - 1
            if 0 <= event_choice < len(event_types):
                etype, desc, severity = event_types[event_choice]
                
                current_rep = max(0.3, 1.0 - user_history.total_reports / max(user_history.total_comments * 2, 10))
                
                print(f"\n触发事件: {desc}")
                print(f"严重程度: {severity.value}")
                print(f"当前信誉分: {current_rep:.4f}")
                
                metadata = {}
                if etype == EventType.COMMENT_LIKED:
                    metadata['like_count'] = 50
                    metadata['is_high_quality_content'] = True
                elif etype == EventType.REPORT_VERIFIED:
                    metadata['violation_type'] = 'fake_review'
                    metadata['is_first_offense'] = False
                    metadata['has_prior_records'] = True
                
                result = engine.handle_event(
                    event_type=etype,
                    user_id=user_history.user_id,
                    current_reputation=current_rep,
                    severity=severity,
                    metadata=metadata
                )
                
                print("\n" + "-" * 60)
                print(f"事件处理结果:")
                print(f"  处理状态: {'成功' if result.success else '失败'}")
                print(f"  原信誉分: {result.old_reputation:.4f}")
                print(f"  信誉变化: {result.change_amount:+.4f}")
                print(f"  新信誉分: {result.new_reputation:.4f}")
                print(f"  处理原因: {result.reason}")
                print(f"  事件ID: {result.event.event_id}")
                print("-" * 60)
                
                print("\n事件驱动系统特点:")
                print("  ✅ 实时更新 - 事件发生后立即更新信誉分")
                print("  ✅ 严重程度分级 - LOW/MEDIUM/HIGH/CRITICAL")
                print("  ✅ 边际递减 - 同类事件影响逐渐降低")
                print("  ✅ 冷却机制 - 防止恶意刷分")
                print("  ✅ 完整审计 - 所有事件可追溯")
                
        else:
            print("无效的编号！")
    except ValueError:
        print("请输入有效的数字！")
    
    print()
    input("按回车键返回主菜单...")


def run_decision_tree_demo(engine, user_histories, sample_comments):
    print("\n" + "=" * 80)
    print("评分决策树路径解释演示")
    print("=" * 80)
    
    print("\n选择评论进行决策树分析:")
    demo_comments = [
        sample_comments[0],
        sample_comments[4],
        sample_comments[6],
        sample_comments[2],
    ]
    
    for idx, comment in enumerate(demo_comments, 1):
        print(f"  {idx}. [{comment['id']}] {comment['description']}")
    
    try:
        choice = int(input("\n请选择评论编号 (1-4): ")) - 1
        if 0 <= choice < len(demo_comments):
            comment = demo_comments[choice]
            user_history = user_histories[comment['user_type']]
            
            print(f"\n正在分析评论 {comment['id']}...")
            print(f"评论内容: {comment['text'][:80]}...")
            
            result = engine.score_comment(
                comment_id=comment['id'],
                comment_text=comment['text'],
                user_history=user_history,
                generate_decision_tree=True
            )
            
            print("\n" + "=" * 80)
            print("1. 评分决策树")
            print("=" * 80)
            engine.print_decision_tree(result, max_depth=3)
            
            print("=" * 80)
            print("2. 特征贡献度排行")
            print("=" * 80)
            engine.print_feature_contributions(result, top_n=15)
            
            print("=" * 80)
            print("3. 主要决策路径")
            print("=" * 80)
            engine.print_decision_paths(result, top_n=5)
            
            print("=" * 80)
            print("4. 决策规则")
            print("=" * 80)
            engine.print_decision_rules(result)
            
            print("=" * 80)
            print("决策树解释说明:")
            print("  • 每个节点显示: 名称, 分数, 贡献度, 条件")
            print("  • 绿色表示得分较高(≥0.7), 黄色中等(≥0.5), 红色较低(<0.5)")
            print("  • 贡献度 = 分数 × 权重，表示该因素对最终评分的实际贡献")
            print("  • 决策路径展示了从根节点到叶子节点的完整推理过程")
            print("  • 特征贡献度排行帮助快速定位最关键的影响因素")
            
        else:
            print("无效的编号！")
    except ValueError:
        print("请输入有效的数字！")
    
    print()
    input("按回车键返回主菜单...")


def run_audit_trail_demo(engine, user_histories):
    print("\n" + "=" * 80)
    print("用户审计追踪演示")
    print("=" * 80)
    
    print("\n选择用户查看审计追踪:")
    user_list = list(user_histories.keys())
    for idx, user_type in enumerate(user_list, 1):
        uh = user_histories[user_type]
        summary = engine.get_user_event_summary(uh.user_id)
        event_count = summary.get('total_events', 0)
        print(f"  {idx}. {user_type:15s} (ID:{uh.user_id}, 历史事件数:{event_count})")
    
    try:
        user_choice = int(input("\n请选择用户编号 (1-5): ")) - 1
        if 0 <= user_choice < len(user_list):
            user_type = user_list[user_choice]
            user_history = user_histories[user_type]
            
            print(f"\n生成一些模拟事件用于演示...")
            
            current_rep = 0.75
            test_events = [
                (EventType.COMMENT_POSTED, EventSeverity.LOW, {'text_quality': 0.8}),
                (EventType.COMMENT_LIKED, EventSeverity.LOW, {'like_count': 30}),
                (EventType.COMMENT_REPORTED, EventSeverity.MEDIUM, {'report_reason': 'spam'}),
            ]
            
            for etype, severity, metadata in test_events:
                result = engine.handle_event(
                    event_type=etype,
                    user_id=user_history.user_id,
                    current_reputation=current_rep,
                    severity=severity,
                    metadata=metadata
                )
                if result.success:
                    current_rep = result.new_reputation
            
            print(f"\n用户 {user_type} 的审计追踪:")
            print("-" * 80)
            
            summary = engine.get_user_event_summary(user_history.user_id)
            print(f"总事件数: {summary.get('total_events', 0)}")
            print(f"当前信誉分: {summary.get('current_reputation', 0):.4f}")
            
            event_counts = summary.get('event_type_counts', {})
            if event_counts:
                print("事件类型统计:")
                for etype, count in event_counts.items():
                    print(f"  {etype}: {count}次")
            
            audit_trail = engine.get_user_audit_trail(user_history.user_id)
            
            if audit_trail:
                print(f"\n最近 {len(audit_trail)} 条记录:")
                print("-" * 80)
                print(f"{'时间':<25} {'事件类型':<18} {'变化':<10} {'新信誉分':<10}")
                print("-" * 80)
                
                for record in audit_trail[:10]:
                    timestamp = record['timestamp'].split('T')[1][:8] if 'T' in record['timestamp'] else record['timestamp']
                    change_color = '\033[92m' if record['change'] >= 0 else '\033[91m'
                    reset = '\033[0m'
                    print(f"{timestamp:<25} {record['event_type']:<18} "
                          f"{change_color}{record['change']:+.4f}{reset:<10} "
                          f"{record['new_reputation']:<10.4f}")
            else:
                print("\n暂无审计记录")
            
            print("\n" + "-" * 80)
            print("审计追踪系统特点:")
            print("  ✅ 完整记录所有影响信誉的事件")
            print("  ✅ 可追溯每一次信誉变化的原因")
            print("  ✅ 支持按时间范围筛选")
            print("  ✅ 可导出事件日志用于分析")
            
            export_choice = input("\n是否导出事件日志? (y/n): ").strip().lower()
            if export_choice == 'y':
                file_path = f"audit_log_{user_history.user_id}.json"
                engine.event_system.export_event_log(file_path, user_history.user_id)
                print(f"事件日志已导出至: {file_path}")
            
        else:
            print("无效的编号！")
    except ValueError:
        print("请输入有效的数字！")
    
    print()
    input("按回车键返回主菜单...")


def run_report_verification_demo(engine, user_histories):
    print("\n" + "=" * 80)
    print("模拟举报核实与信誉扣分演示")
    print("=" * 80)
    
    print("\n本演示模拟一个完整的举报流程:")
    print("  1. 用户发布评论")
    print("  2. 评论被其他用户举报")
    print("  3. 管理员审核并核实举报")
    print("  4. 用户信誉被实时扣分")
    print("  5. 用户申诉成功，信誉部分恢复")
    
    print("\n" + "-" * 60)
    print("场景: 用户 U004 (高风险用户) 发布了一条疑似虚假评论")
    print("-" * 60)
    
    risky_user = user_histories['risky_user']
    fake_comment = "这款产品简直完美！秒杀所有竞品！我已经买了100个送朋友！！！"
    
    print(f"\n【步骤1】用户 {risky_user.user_id} 发布评论:")
    print(f"     {fake_comment}")
    
    current_rep = 0.45
    print(f"     当前信誉分: {current_rep:.4f}")
    
    print(f"\n【步骤2】该评论被5个用户举报，原因: 虚假宣传")
    event_result = engine.handle_event(
        event_type=EventType.COMMENT_REPORTED,
        user_id=risky_user.user_id,
        current_reputation=current_rep,
        severity=EventSeverity.MEDIUM,
        metadata={
            'report_count': 5,
            'report_reason': 'fake',
            'comment_id': 'FAKE001'
        }
    )
    
    print(f"     举报后信誉分: {event_result.old_reputation:.4f} → {event_result.new_reputation:.4f}")
    print(f"     变化: {event_result.change_amount:+.4f}")
    print(f"     原因: {event_result.reason}")
    
    current_rep = event_result.new_reputation
    
    print(f"\n【步骤3】管理员人工审核，确认该评论为虚假评论")
    print("     违规类型: fake_review (虚假评论)")
    print("     该用户有历史违规记录，属于屡犯")
    
    event_result = engine.handle_event(
        event_type=EventType.REPORT_VERIFIED,
        user_id=risky_user.user_id,
        current_reputation=current_rep,
        severity=EventSeverity.HIGH,
        metadata={
            'violation_type': 'fake_review',
            'is_first_offense': False,
            'has_prior_records': True,
            'report_id': 'RPT001',
            'verifier': 'admin_01'
        }
    )
    
    print(f"\n【步骤4】举报核实，信誉实时扣分:")
    print(f"     原信誉分: {event_result.old_reputation:.4f}")
    print(f"     信誉变化: {event_result.change_amount:+.4f}")
    print(f"     新信誉分: {event_result.new_reputation:.4f}")
    print(f"     处理原因: {event_result.reason}")
    
    current_rep = event_result.new_reputation
    
    print(f"\n【步骤5】用户提交申诉，提供了购买凭证，申诉成功")
    print("     恢复50%的信誉损失")
    
    original_impact = abs(event_result.change_amount)
    event_result = engine.handle_event(
        event_type=EventType.APPEAL_GRANTED,
        user_id=risky_user.user_id,
        current_reputation=current_rep,
        severity=EventSeverity.LOW,
        metadata={
            'original_impact': original_impact,
            'restore_percentage': 0.5,
            'appeal_id': 'APL001'
        }
    )
    
    print(f"\n【步骤6】申诉成功，信誉部分恢复:")
    print(f"     原信誉分: {event_result.old_reputation:.4f}")
    print(f"     恢复变化: {event_result.change_amount:+.4f}")
    print(f"     新信誉分: {event_result.new_reputation:.4f}")
    print(f"     处理原因: {event_result.reason}")
    
    print("\n" + "=" * 80)
    print("事件处理完毕！完整审计记录:")
    print("=" * 80)
    
    audit_trail = engine.get_user_audit_trail(risky_user.user_id)
    for record in audit_trail:
        timestamp = record['timestamp'].split('T')[1][:8] if 'T' in record['timestamp'] else record['timestamp']
        change_color = '\033[92m' if record['change'] >= 0 else '\033[91m'
        reset = '\033[0m'
        print(f"  [{timestamp}] {record['event_type']:20s} "
              f"{change_color}{record['change']:+.4f}{reset} "
              f"→ {record['new_reputation']:.4f}")
    
    print("\n" + "-" * 80)
    print("举报核实机制特点:")
    print("  ✅ 实时扣分 - 核实后立即影响信誉")
    print("  ✅ 分级处理 - 根据违规类型和严重程度调整扣分幅度")
    print("  ✅ 累犯加重 - 有历史违规记录者扣分更重")
    print("  ✅ 申诉机制 - 支持申诉成功后部分恢复信誉")
    print("  ✅ 完整追溯 - 所有处理记录可审计")
    
    print()
    input("按回车键返回主菜单...")


def show_system_info():
    print("\n" + "=" * 80)
    print("系统说明 v3.0")
    print("=" * 80)
    
    print("""
【核心模块说明】

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【v1.0 基础模块】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. BERT文本分析模块 (bert_analyzer.py)
   分析评论文本的三个核心维度:
   • 有用性 - 信息含量、细节丰富度
   • 真实性 - 表达自然度、情感一致性
   • 完整性 - 维度覆盖、逻辑结构

2. 知识图谱模块 (knowledge_graph.py)
   基于知识图谱的可信度验证:
   • 实体识别 - 产品、品牌、属性等
   • 关系抽取 - 评价、对比、因果等
   • 事实验证 - 与知识库信息比对

3. 用户信誉模块 (user_reputation.py)
   四维用户信誉评估:
   • 可信度 - 历史真实性、认证状态
   • 影响力 - 获赞数、粉丝数、等级
   • 一致性 - 评分稳定性、历史波动
   • 风险 - 举报率、违规记录

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【v2.0 新增模块】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. 数据增强模块 (data_augmentation.py)
   8种增强方法提升模型泛化:
   • 同义词替换、随机删除、随机交换、随机插入
   • 伪回译、句子打乱、字符替换、上下文插入

5. 事件驱动信誉系统 (event_driven_reputation.py)
   10种事件类型实时更新信誉:
   • 发布评论、获赞、举报、举报核实、申诉等
   • 支持严重程度分级: LOW / MEDIUM / HIGH / CRITICAL

6. 决策树解释器 (decision_tree_explainer.py)
   完整评分可解释性:
   • 决策树可视化、特征贡献度排行
   • 决策路径提取、IF-THEN规则生成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【v3.0 新增模块】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. 虚假评论检测模块 (fake_review_detector.py)
   三类虚假评论识别:
   • 刷单评论 - 模板化、关键词堆砌、新账号特征
   • 水军评论 - IP聚类、内容相似度、时间突发
   • 竞品恶意 - 竞品提及、极端负面、定向攻击
   支持群组检测，识别规模化协同刷评

8. 评论排序优化模块 (review_ranking.py)
   7种排序策略 + 9维特征融合:
   • 质量优先、有用性优先、时间衰减、综合平衡等
   • 6大核心特征: 质量、有用性、时效性、信誉、互动、详细度
   • 支持多样性重排，避免内容同质化

9. 趋势监控模块 (trend_monitor.py)
   7种异常检测 + 实时告警:
   • 质量突降、虚假激增、评分操纵、量异常、情感突变
   • 竞品攻击、CUSUM统计过程控制
   • 支持趋势预测、告警管理、完整审计

【评分公式 v3.0】
最终得分 = 
    (有用性×0.35 + 真实性×0.35 + 完整性×0.30) × 0.45 +
    (事实验证×0.40 + 实体多样性×0.30 + 关系质量×0.30) × 0.25 +
    (可信度×0.40 + 影响力×0.30 + 一致性×0.20 + (1-风险)×0.10) × 0.30

【排序公式 v1.0】
排序分数 = Σ(特征归一化值 × 特征权重)
特征权重: 质量35% + 有用性25% + 时效性15% + 信誉10% + 互动10% + 详细5%

【功能使用建议】
1. 虚假评论检测: 评论发布时实时检测，高风险评论人工审核
2. 评论排序优化: 商品详情页高质量评论优先展示，提升转化
3. 趋势监控: 重点商品7×24小时监控，异常及时告警
4. 数据增强: 模型训练阶段使用，提升低资源场景性能
5. 事件驱动: 业务事件实时接入，信誉动态更新
6. 决策树解释: 评分结果页面展示依据，提升用户信任

【典型应用场景】
• 电商平台评论质量控制与排序
• 内容社区反作弊与内容治理
• 舆情分析可信度评估与预警
• 用户画像和信用评级体系
• 品牌口碑监控与竞品分析
    """)
    
    input("按回车键返回主菜单...")


def run_fake_review_detection_demo(engine, fake_detector, user_histories):
    print("\n" + "=" * 80)
    print("虚假评论检测演示 - 识别刷单、水军、竞品恶意评论")
    print("=" * 80)
    
    print("\n测试案例:")
    test_cases = [
        {
            'type': '正常评论',
            'text': '用了两周了，整体体验不错，屏幕显示细腻，电池续航也可以，轻度使用一天没问题。拍照中规中矩，满足日常需求。',
            'rating': 4,
            'user_type': 'trusted_user',
            'ip': '192.168.1.100',
            'expected': 'legitimate'
        },
        {
            'type': '刷单评论',
            'text': '好评好评好评！真的太赞了，超级喜欢，物美价廉，性价比很高，推荐购买，非常好，商家服务好，发货快，物流快，好评！',
            'rating': 5,
            'user_type': 'new_user',
            'ip': '192.168.1.200',
            'expected': 'brushing'
        },
        {
            'type': '竞品恶意差评',
            'text': '垃圾手机，千万不要买！用了三天就坏了，质量太差了，还是买苹果吧，苹果比这个好多了，三星也不错，华为就是垃圾，骗子公司！',
            'rating': 1,
            'user_type': 'risky_user',
            'ip': '192.168.1.300',
            'expected': 'competitor_malicious'
        },
        {
            'type': '超短刷单模板',
            'text': '很好，推荐购买',
            'rating': 5,
            'user_type': 'new_user',
            'ip': '192.168.1.201',
            'expected': 'brushing'
        },
        {
            'type': '专业差评师',
            'text': '这款手机真的太差了，完全比不上小米14。小米14的处理器更快，拍照更好，系统更流畅。而这款手机卡得要死，玩游戏掉帧严重，拍照模糊不清，系统广告一大堆。强烈建议大家去买小米，别买这个垃圾牌子。',
            'rating': 1,
            'user_type': 'risky_user',
            'ip': '192.168.1.400',
            'expected': 'competitor_malicious'
        },
        {
            'type': '刷好评模板',
            'text': '非常好，很满意，性价比高，值得购买',
            'rating': 5,
            'user_type': 'new_user',
            'ip': '192.168.1.202',
            'expected': 'brushing'
        }
    ]
    
    for idx, case in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"【测试 {idx}】{case['type']}")
        print(f"{'─' * 60}")
        print(f"评论内容: {case['text']}")
        print(f"评分: {case['rating']}星 | IP: {case['ip']}")
        
        user_history = user_histories[case['user_type']]
        user_history.metadata['product_id'] = 'PROD001'
        user_history.metadata['rating'] = case['rating']
        user_history.metadata['ip_address'] = case['ip']
        user_history.metadata['user_average_rating'] = 4.8 if case['type'] == '刷单评论' else None
        
        review_for_detection = ReviewForDetection(
            review_id=f'TEST_FAKE_{idx:03d}',
            user_id=user_history.user_id,
            product_id='PROD001',
            content=case['text'],
            rating=case['rating'],
            timestamp=datetime.now(),
            ip_address=case['ip'],
            device_id=f'DEVICE_{idx:03d}',
            user_account_age_days=user_history.account_age_days,
            user_total_reviews=user_history.total_comments,
            user_average_rating=user_history.metadata.get('user_average_rating')
        )
        
        result = fake_detector.detect(review_for_detection)
        
        status_icon = "⚠️ 虚假" if result.is_fake else "✅ 正常"
        type_names = {
            'legitimate': '正常评论',
            'brushing': '刷单评论',
            'water_army': '水军评论',
            'competitor_malicious': '竞品恶意评论'
        }
        level_names = {
            'none': '无', 'low': '低', 'medium': '中', 'high': '高', 'critical': '极高'
        }
        
        print(f"\n检测结果: {status_icon}")
        print(f"可疑类型: {type_names.get(result.fake_type.value, result.fake_type.value)}")
        print(f"可疑程度: {level_names.get(result.suspicion_level.value, result.suspicion_level.value)} ({result.suspicion_score:.2%})")
        print(f"分项得分: 刷单={result.brushing_score:.2%} | 水军={result.water_army_score:.2%} | 竞品恶意={result.competitor_score:.2%}")
        
        if result.evidence:
            print(f"检测证据:")
            for ev in result.evidence:
                impact_icon = "🔴" if ev.impact >= 0.2 else "🟡" if ev.impact >= 0.1 else "🟢"
                print(f"  {impact_icon} {ev.description} (权重: {ev.impact:.2%})")
        
        print(f"\n预期: {case['expected']} | 实际: {result.fake_type.value}")
        if result.fake_type.value == case['expected']:
            print("✅ 检测正确！")
        else:
            print(f"⚠️  检测与预期有差异（可能是多维度综合判断）")
    
    print("\n" + "=" * 80)
    print("📊 水军群组检测演示")
    print("=" * 80)
    
    print("\n模拟生成5条来自同一IP的相似评论（水军刷评）:")
    now = datetime.now()
    water_army_reviews = []
    base_texts = [
        "很好，很满意，值得购买",
        "非常好，很满意，推荐购买",
        "真的不错，很满意，好评",
        "很好，性价比高，推荐",
        "非常满意，值得购买，好评"
    ]
    
    for i in range(5):
        review = ReviewForDetection(
            review_id=f'WATER_{i+1:03d}',
            user_id=f'WATER_USER_{i+1:02d}',
            product_id='PROD002',
            content=base_texts[i],
            rating=5,
            timestamp=now + timedelta(minutes=i*2),
            ip_address='10.0.0.100',
            device_id=f'WATER_DEV_{i+1:02d}',
            user_account_age_days=random.randint(3, 15),
            user_total_reviews=random.randint(1, 4)
        )
        water_army_reviews.append(review)
        print(f"  {i+1}. [用户{review.user_id}] {review.content}")
    
    group_results = fake_detector.detect_group(water_army_reviews)
    
    if group_results:
        print(f"\n🚨 检测到 {len(group_results)} 个可疑群组!")
        for idx, group in enumerate(group_results, 1):
            print(f"\n  群组 {idx}: {group.group_id}")
            print(f"    可疑用户: {', '.join(group.suspicious_users)}")
            print(f"    可疑评论: {', '.join(group.suspicious_reviews)}")
            print(f"    群组可疑度: {group.suspicion_score:.2%}")
            print(f"    证据:")
            for ev in group.evidence:
                print(f"      • {ev}")
    else:
        print("\n未检测到可疑群组")
    
    print("\n" + "-" * 80)
    print("虚假评论检测能力总结:")
    print("  ✅ 刷单识别 - 检测模板化、关键词堆砌、新账号等特征")
    print("  ✅ 水军识别 - 基于IP聚类、内容相似度、时间突发等")
    print("  ✅ 竞品恶意识别 - 检测竞品提及、极端负面、定向攻击")
    print("  ✅ 群组检测 - 识别规模化协同刷评行为")
    
    print()
    input("按回车键返回主菜单...")


def run_review_ranking_demo(engine, user_histories, sample_comments):
    print("\n" + "=" * 80)
    print("评论排序优化演示 - 高质量评论优先展示")
    print("=" * 80)
    
    print("\n📝 生成测试评论数据（12条不同质量的评论）:")
    print("-" * 60)
    
    now = datetime.now()
    test_reviews_for_ranking = []
    
    review_data = [
        ("优质长评，有具体使用体验", 0.92, 0.85, 156, 12, 3, 1, True, 0.0),
        ("良好评论，多维度评价", 0.82, 0.78, 89, 45, 8, 2, True, 0.0),
        ("中等评论，内容一般", 0.62, 0.55, 35, 23, 5, 0, False, 0.0),
        ("短评，信息有限", 0.48, 0.60, 12, 8, 2, 1, True, 0.0),
        ("较差评论，内容简短", 0.35, 0.42, 8, 3, 1, 0, False, 0.0),
        ("优质老评论，高互动", 0.88, 0.90, 180, 234, 45, 12, True, 0.0),
        ("中等老评论", 0.58, 0.72, 45, 67, 12, 3, False, 0.0),
        ("新发布的优质评论", 0.85, 0.82, 120, 5, 1, 0, True, 0.0),
        ("新发布的中等评论", 0.60, 0.58, 42, 2, 0, 0, False, 0.0),
        ("疑似刷单评论", 0.55, 0.30, 15, 0, 0, 0, False, 0.75),
        ("高信誉用户新评论", 0.75, 0.95, 95, 3, 0, 1, True, 0.0),
        ("低质量差评", 0.28, 0.25, 20, 15, 8, 4, False, 0.15),
    ]
    
    for i, (desc, quality, reputation, length, helpful, unhelpful, replies, verified, fake_score) in enumerate(review_data, 1):
        days_ago = random.choice([0, 1, 3, 7, 15, 30, 60, 90])
        review = ReviewForRanking(
            review_id=f'RANK_{i:03d}',
            quality_score=quality,
            user_reputation=reputation,
            helpful_votes=helpful,
            unhelpful_votes=unhelpful,
            reply_count=replies,
            timestamp=now - timedelta(days=days_ago),
            content_length=length,
            is_verified_purchase=verified,
            fake_review_score=fake_score
        )
        test_reviews_for_ranking.append(review)
        print(f"  {i:2d}. {desc:25s} 质量={quality:.2f} 信誉={reputation:.2f} "
              f"有用={helpful:3d} 发布={days_ago:3d}天前"
              f"{' ✓验证' if verified else ''}"
              f"{' ⚠️虚假' if fake_score > 0.5 else ''}")
    
    print("\n" + "=" * 80)
    print("📊 不同排序策略对比 (Top 5)")
    print("=" * 80)
    engine.print_ranking_comparison(test_reviews_for_ranking, top_n=5)
    
    print("\n" + "=" * 80)
    print("🎯 综合平衡排序详细结果 (Top 10)")
    print("=" * 80)
    
    ranked = engine.rank_reviews(
        test_reviews_for_ranking,
        strategy=SortStrategy.BALANCED,
        enable_diversity=True
    )
    
    engine.print_ranking_details(ranked, top_n=10)
    
    print("\n" + "-" * 80)
    print("排序优化机制总结:")
    print("  ✅ 质量优先 - 高评论质量分数优先展示")
    print("  ✅ 有用性加权 - 贝叶斯平滑处理投票数据")
    print("  ✅ 时间衰减 - 新评论权重更高（半衰期可调）")
    print("  ✅ 信誉加成 - 高信誉用户评论权重更高")
    print("  ✅ 互动热度 - 回复多、讨论度高的评论优先")
    print("  ✅ 详细程度 - 内容充实的长评论优先")
    print("  ✅ 虚假惩罚 - 虚假评论嫌疑降低排序权重")
    print("  ✅ 验证购买 - 已验证购买评论获得额外加成")
    print("  ✅ 多样性重排 - 避免同一用户/相似内容集中展示")
    
    print()
    input("按回车键返回主菜单...")


def run_trend_monitoring_demo(engine):
    print("\n" + "=" * 80)
    print("评论趋势监控演示 - 质量突降时告警")
    print("=" * 80)
    
    product_id = 'DEMO_PROD_001'
    now = datetime.now()
    
    print("\n📊 模拟生成48小时的评论质量数据（每小时一个数据点）:")
    print("-" * 60)
    
    print("\n阶段1: 正常质量期 (前24小时，质量稳定在0.75-0.85)")
    for i in range(24):
        quality = 0.80 + random.uniform(-0.05, 0.05)
        fake_ratio = random.uniform(0.02, 0.08)
        review_count = random.randint(15, 30)
        avg_rating = 4.3 + random.uniform(-0.3, 0.3)
        
        engine.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=47 - i),
            avg_rating=avg_rating,
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.65 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count}
        )
        if i % 6 == 0:
            print(f"  小时 {47-i:2d}: 质量={quality:.3f} 虚假率={fake_ratio:.1%} 数量={review_count}")
    
    print("\n阶段2: 质量突降期 (中间12小时，质量骤降，虚假评论激增)")
    print("  ⚠️  模拟竞品恶意攻击/刷差评事件")
    for i in range(24, 36):
        hour = 47 - i
        quality = 0.80 - (i - 23) * 0.04 + random.uniform(-0.03, 0.03)
        quality = max(0.30, quality)
        fake_ratio = 0.25 + random.uniform(0, 0.15)
        review_count = random.randint(40, 60)
        avg_rating = 4.3 - (i - 23) * 0.15
        avg_rating = max(2.0, avg_rating)
        
        engine.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=hour),
            avg_rating=avg_rating,
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.40 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count, 'is_anomaly': True}
        )
        print(f"  小时 {hour:2d}: 质量={quality:.3f} 虚假率={fake_ratio:.1%} 数量={review_count} 评分={avg_rating:.1f}")
    
    print("\n阶段3: 恢复/处理期 (后12小时，质量逐步回升)")
    for i in range(36, 48):
        hour = 47 - i
        quality = 0.45 + (i - 35) * 0.03 + random.uniform(-0.03, 0.03)
        quality = min(0.85, quality)
        fake_ratio = 0.15 - (i - 35) * 0.01
        fake_ratio = max(0.05, fake_ratio)
        review_count = random.randint(20, 35)
        avg_rating = 3.5 + (i - 35) * 0.08
        
        engine.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=hour),
            avg_rating=avg_rating,
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.55 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count}
        )
        if i % 3 == 0:
            print(f"  小时 {hour:2d}: 质量={quality:.3f} 虚假率={fake_ratio:.1%} 数量={review_count}")
    
    print("\n" + "=" * 80)
    print("📈 趋势分析报告")
    print("=" * 80)
    
    analysis = engine.analyze_trends(product_id, time_window_hours=48)
    engine.print_trend_report(product_id, time_window_hours=48)
    
    print("\n" + "=" * 80)
    print("🔔 活跃告警列表")
    print("=" * 80)
    
    alerts = engine.get_active_alerts(product_id=product_id, only_unhandled=True)
    if alerts:
        for idx, alert in enumerate(alerts, 1):
            severity_icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.WARNING else "🔵"
            type_names = {
                'quality_drop': '质量突降',
                'spam_surge': '垃圾评论激增',
                'fake_review_surge': '虚假评论激增',
                'rating_manipulation': '评分操纵',
                'sentiment_shift': '情感突变',
                'volume_anomaly': '评论量异常',
                'competitor_attack': '竞品攻击'
            }
            print(f"\n{idx}. {severity_icon} [{alert.timestamp.strftime('%Y-%m-%d %H:%M')}] "
                  f"{type_names.get(alert.alert_type.value, alert.alert_type.value)}")
            print(f"   描述: {alert.description}")
            print(f"   指标: {alert.metric_name} = {alert.current_value:.4f} (预期: {alert.expected_value:.4f})")
            print(f"   变化: {alert.change_percent:+.1%} | 阈值: {alert.threshold:.4f}")
            
            handle = input("\n   是否标记为已处理? (y/n): ").strip().lower()
            if handle == 'y':
                engine.mark_alert_handled(alert.alert_id)
                print("   ✅ 已标记为已处理")
    else:
        print("暂无活跃告警")
    
    print("\n" + "-" * 80)
    print("趋势监控能力总结:")
    print("  ✅ 质量突降检测 - 前后半段对比，下降超阈值告警")
    print("  ✅ 虚假评论激增 - 虚假率突增2倍以上告警")
    print("  ✅ 评分操纵检测 - 平均分突变检测")
    print("  ✅ 评论量异常 - 评论量激增检测")
    print("  ✅ 情感突变检测 - 标准差变化检测")
    print("  ✅ 竞品攻击识别 - 低质量+高虚假率组合检测")
    print("  ✅ CUSUM累积和 - 统计过程控制算法")
    print("  ✅ 趋势预测 - 基于斜率预测下一期质量")
    print("  ✅ 告警冷却 - 防止重复告警")
    
    print()
    input("按回车键返回主菜单...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断，退出中...")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
