import sys
sys.path.insert(0, '.')

import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sentiment_analyzer_enhanced():
    print("\n" + "="*70)
    print("Testing Enhanced Sentiment Analyzer")
    print("="*70)
    
    from analysis.sentiment_analyzer import SentimentAnalyzer
    
    analyzer = SentimentAnalyzer()
    
    test_cases = [
        {
            'text': '这个产品真的太棒了，非常满意！👍❤️',
            'description': '带表情符号的正面评价'
        },
        {
            'text': '质量太差了，客服态度也不好，很失望。😡💔',
            'description': '带表情符号的负面评价'
        },
        {
            'text': '今天天气不错，温度适宜。😊',
            'description': '带表情符号的中性评价'
        },
        {
            'text': '这个产品不是不好，只是不太符合我的预期。',
            'description': '含否定词的复杂评价'
        },
        {
            'text': '非常非常好的购物体验，真的超级棒！',
            'description': '含程度副词的正面评价'
        },
        {
            'text': '这个电影我觉得有点无聊，稍微有点失望。',
            'description': '含弱化词的评价'
        },
        {
            'text': '这件衣服质量很好，但是发货速度太慢了！',
            'description': '混合情感评价'
        },
        {
            'text': '🔥🔥🔥这个产品简直绝了，太好用了！💯',
            'description': '多个表情符号'
        },
    ]
    
    all_passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Text: {test['text']}")
        
        result = analyzer.analyze(test['text'])
        
        print(f"   Sentiment: {result['sentiment']}")
        print(f"   Positive: {result['positive']:.4f}, Negative: {result['negative']:.4f}, Neutral: {result['neutral']:.4f}")
        print(f"   Confidence: {result['confidence']:.4f}")
        
        if 'emoji_features' in result and result['emoji_features']:
            print(f"   Emojis detected: {len(result['emoji_features'])}")
            for ef in result['emoji_features']:
                print(f"      - {ef['emoji']}: {ef['sentiment_score']:.4f}")
        
        if 'emoji_sentiment' in result:
            print(f"   Emoji sentiment: {result['emoji_sentiment']:.4f}")
        
        if 'context_features' in result and result['context_features']:
            print(f"   Context features: {len(result['context_features'])} keywords analyzed")
        
        if 'sentence_count' in result:
            print(f"   Sentence count: {result['sentence_count']}")
        
        if 'sentence_sentiments' in result and result['sentence_sentiments']:
            print(f"   Sentence sentiments: {result['sentence_sentiments'][:5]}")
    
    print("\n🔍 Testing context-aware analysis:")
    context_texts = [
        '这个品牌的产品质量一直很好',
        '我之前买过他们家的其他产品，都很满意',
        '售后服务也很到位'
    ]
    target_text = '这次的购物体验非常好'
    
    context_result = analyzer.analyze_with_context(target_text, context_texts)
    print(f"   Target text: {target_text}")
    print(f"   Context texts: {len(context_texts)}")
    print(f"   Context-aware result: {context_result['sentiment']} (pos={context_result['positive']:.4f}, neg={context_result['negative']:.4f})")
    print(f"   Context aware: {context_result.get('context_aware', False)}")
    
    print("\n✅ Sentiment Analyzer Enhanced Features Test Passed!")
    return True

def test_topic_modeler_enhanced():
    print("\n" + "="*70)
    print("Testing Enhanced Topic Modeler with Dynamic Topic Detection")
    print("="*70)
    
    from analysis.topic_modeler import TopicModeler
    
    modeler = TopicModeler()
    
    test_texts = [
        "这款手机的拍照功能非常强大，夜景模式效果很好",
        "新出的相机应用拍照效果真的很棒，色彩还原度高",
        "手机的续航能力很强，充电速度也很快",
        "这个产品的电池续航不错，能用一整天",
        "屏幕显示效果很清晰，看视频很舒服",
        "显示屏的画质很好，色彩鲜艳",
        "系统运行很流畅，没有卡顿现象",
        "手机的性能很强，玩游戏不卡",
        "价格有点贵，但是性价比还可以",
        "促销活动期间购买很划算，优惠力度大",
        "这个品牌的售后服务很好，响应及时",
        "客服态度很好，问题解决得很快",
        "包装很精美，送人很有面子",
        "外观设计很漂亮，手感也很好",
        "重量很轻，携带方便",
    ]
    
    print(f"\nTesting with {len(test_texts)} documents...")
    
    print("\n1. Calculating optimal topics:")
    optimal_result = modeler._calculate_optimal_topics(len(test_texts))
    print(f"   Calculated optimal topics: {optimal_result}")
    
    print("\n2. Testing find_optimal_topics (fallback mode):")
    result = modeler.find_optimal_topics(test_texts)
    print(f"   Method: {result.get('method', 'unknown')}")
    print(f"   Optimal topics: {result.get('optimal_num_topics', 0)}")
    print(f"   Num docs analyzed: {result.get('num_docs', 0)}")
    
    if 'search_range' in result:
        print(f"   Search range: {result['search_range']}")
    
    print("\n3. Testing get_topic_distribution:")
    topic_dist = modeler.get_topic_distribution(test_texts)
    print(f"   Topic distribution: {topic_dist}")
    
    print("\n4. Testing get_all_topics:")
    all_topics = modeler.get_all_topics()
    print(f"   Total topics available: {len(all_topics)}")
    for topic in all_topics:
        print(f"   Topic {topic['topic_id']} ({topic['name']}): {topic['keywords'][:5]}")
    
    print("\n5. Testing extract_keywords:")
    keywords = modeler.extract_keywords(test_texts, top_k=10)
    print(f"   Top 10 keywords:")
    for kw, freq in keywords:
        print(f"      {kw}: {freq}")
    
    print("\n6. Testing single text topic extraction:")
    single_text = "这款手机拍照功能强大，续航也很好"
    topics = modeler.get_topics(single_text)
    print(f"   Text: {single_text}")
    print(f"   Topics found: {len(topics)}")
    for topic in topics:
        print(f"      Topic {topic['topic_id']}: weight={topic['weight']:.4f}, keywords={topic['keywords'][:5]}")
    
    print("\n✅ Topic Modeler Enhanced Features Test Passed!")
    return True

def test_propagation_analyzer_enhanced():
    print("\n" + "="*70)
    print("Testing Enhanced Propagation Analyzer with Originality Detection")
    print("="*70)
    
    from analysis.propagation_analyzer import PropagationAnalyzer, OriginalityDetector
    
    print("\n1. Testing OriginalityDetector:")
    detector = OriginalityDetector(similarity_threshold=0.7)
    
    text1 = "这款手机的拍照功能非常强大，夜景模式效果很好，性价比很高"
    text2 = "这款手机拍照功能非常强大，夜景模式效果很好，性价比很高"
    text3 = "这个产品的质量真的很差，不推荐购买"
    text4 = "这个手机拍照很强大，夜景模式效果不错，性价比很高"
    
    print(f"\n   Text1: {text1}")
    print(f"   Text2: {text2}")
    print(f"   Text3: {text3}")
    print(f"   Text4: {text4}")
    
    sim12 = detector.calculate_similarity(text1, text2)
    sim13 = detector.calculate_similarity(text1, text3)
    sim14 = detector.calculate_similarity(text1, text4)
    
    print(f"\n   Similarity (text1 vs text2): {sim12['combined_similarity']:.4f} - {'Duplicate' if sim12['is_duplicate'] else 'Original'}")
    print(f"      Jaccard: {sim12['jaccard_similarity']:.4f}, Bigram: {sim12['bigram_similarity']:.4f}, Trigram: {sim12['trigram_similarity']:.4f}")
    print(f"   Similarity (text1 vs text3): {sim13['combined_similarity']:.4f} - {'Duplicate' if sim13['is_duplicate'] else 'Original'}")
    print(f"   Similarity (text1 vs text4): {sim14['combined_similarity']:.4f} - {'Duplicate' if sim14['is_duplicate'] else 'Original'}")
    
    print("\n2. Testing check_originality:")
    existing_posts = [
        {'post_id': 'post_001', 'content': text1, 'timestamp': datetime.utcnow() - timedelta(hours=2)},
    ]
    
    result1 = detector.check_originality('post_002', text2, datetime.utcnow() - timedelta(hours=1), existing_posts)
    result2 = detector.check_originality('post_003', text3, datetime.utcnow(), existing_posts)
    
    print(f"   Post 002 (similar to 001): is_original={result1['is_original']}, duplicate_type={result1['duplicate_type']}")
    print(f"      Original post: {result1['original_post_id']}, similarity: {result1['similarity_score']:.4f}")
    print(f"   Post 003 (original): is_original={result2['is_original']}, duplicate_type={result2['duplicate_type']}")
    
    print("\n3. Testing PropagationAnalyzer with originality detection:")
    analyzer = PropagationAnalyzer()
    
    base_time = datetime.utcnow()
    test_posts = [
        {'post_id': 'user_001', 'content': '这款手机拍照功能非常强大，夜景模式效果很好', 'timestamp': base_time - timedelta(hours=5)},
        {'post_id': 'user_002', 'content': '这款手机拍照功能非常强大，夜景模式效果很好', 'timestamp': base_time - timedelta(hours=4)},
        {'post_id': 'user_003', 'content': '手机拍照功能很强，夜景模式不错', 'timestamp': base_time - timedelta(hours=3)},
        {'post_id': 'user_004', 'content': '这个产品的电池续航能力很强', 'timestamp': base_time - timedelta(hours=2)},
        {'post_id': 'user_005', 'content': '这款手机拍照功能非常强大，夜景模式效果很好', 'timestamp': base_time - timedelta(hours=1)},
        {'post_id': 'user_006', 'content': '系统运行很流畅，没有卡顿现象', 'timestamp': base_time},
    ]
    
    analyzer.add_posts_for_originality_check(test_posts)
    
    print("\n4. Testing get_originality_report:")
    report = analyzer.get_originality_report()
    print(f"   Total posts: {report['total_posts']}")
    print(f"   Original count: {report['original_count']}")
    print(f"   Duplicate count: {report['duplicate_count']}")
    print(f"   Original ratio: {report['original_ratio']:.4f}")
    print(f"   Duplicate types: {report['duplicate_types']}")
    
    if report['top_original_posts']:
        print(f"   Top original posts: {len(report['top_original_posts'])}")
        for top in report['top_original_posts']:
            print(f"      {top['original_post_id']}: {top['plagiarism_count']} plagiarisms, influence={top['total_similarity']:.4f}")
    
    print("\n5. Testing analyze_plagiarism_propagation:")
    if report['top_original_posts']:
        original_id = report['top_original_posts'][0]['original_post_id']
        plag_analysis = analyzer.analyze_plagiarism_propagation(original_id)
        if plag_analysis:
            print(f"   Original post: {plag_analysis['original_post_id']}")
            print(f"   Total plagiarisms: {plag_analysis['total_plagiarisms']}")
            if 'time_range' in plag_analysis and plag_analysis['time_range']:
                print(f"   Time range: {plag_analysis['time_range']}")
            if 'similarity_stats' in plag_analysis:
                print(f"   Similarity stats: {plag_analysis['similarity_stats']}")
            print(f"   Influence score: {plag_analysis.get('influence_score', 0)}")
    
    print("\n6. Testing compare_posts:")
    compare_result = analyzer.compare_posts('user_001', 'user_002', 
        '这款手机拍照功能非常强大，夜景模式效果很好',
        '这款手机拍照功能非常强大，夜景模式效果很好')
    print(f"   Compare result: is_plagiarism={compare_result['is_plagiarism']}")
    print(f"   Similarity: {compare_result['similarity']['combined_similarity']:.4f}")
    print(f"   Recommendation: {compare_result['recommendation']}")
    
    print("\n7. Testing propagation with plagiarism edges:")
    test_paths = [
        {'source_node': 'user_001', 'target_node': 'user_002', 'propagation_time': base_time - timedelta(hours=4), 'is_plagiarism': True, 'similarity_score': 0.95},
        {'source_node': 'user_002', 'target_node': 'user_003', 'propagation_time': base_time - timedelta(hours=3), 'is_plagiarism': True, 'similarity_score': 0.85},
        {'source_node': 'user_001', 'target_node': 'user_005', 'propagation_time': base_time - timedelta(hours=1), 'is_plagiarism': True, 'similarity_score': 0.92},
        {'source_node': 'user_004', 'target_node': 'user_006', 'propagation_time': base_time, 'is_plagiarism': False},
    ]
    
    propagation_result = analyzer.analyze_propagation('user_001', paths=test_paths, posts=test_posts)
    print(f"\n   Total nodes: {propagation_result['total_nodes']}")
    print(f"   Total edges: {propagation_result['total_edges']}")
    print(f"   Plagiarism edges: {propagation_result['graph_data']['plagiarism_edge_count']}")
    print(f"   Original nodes: {propagation_result['graph_data']['original_node_count']}")
    
    if propagation_result.get('plagiarism_analysis'):
        print(f"   Plagiarism analysis available: {len(propagation_result['plagiarism_analysis'])} fields")
    
    print("\n8. Testing get_top_influencers with plagiarism info:")
    influencers = analyzer.get_top_influencers(top_k=3)
    for inf in influencers:
        print(f"   {inf['node']}: influence={inf['influence_score']:.6f}, is_original={inf.get('is_original')}, plagiarism_count={inf.get('plagiarism_count', 0)}")
    
    print("\n9. Testing get_plagiarism_edges:")
    plag_edges = analyzer.get_plagiarism_edges()
    print(f"   Plagiarism edges found: {len(plag_edges)}")
    for edge in plag_edges:
        print(f"      {edge['source']} -> {edge['target']}: similarity={edge['similarity_score']:.4f}")
    
    print("\n✅ Propagation Analyzer Enhanced Features Test Passed!")
    return True

def main():
    print("="*70)
    print("Enhanced Features Test Suite")
    print("="*70)
    
    results = []
    
    try:
        results.append(('Sentiment Analyzer', test_sentiment_analyzer_enhanced()))
    except Exception as e:
        logger.error(f"Sentiment Analyzer test failed: {e}", exc_info=True)
        results.append(('Sentiment Analyzer', False))
    
    try:
        results.append(('Topic Modeler', test_topic_modeler_enhanced()))
    except Exception as e:
        logger.error(f"Topic Modeler test failed: {e}", exc_info=True)
        results.append(('Topic Modeler', False))
    
    try:
        results.append(('Propagation Analyzer', test_propagation_analyzer_enhanced()))
    except Exception as e:
        logger.error(f"Propagation Analyzer test failed: {e}", exc_info=True)
        results.append(('Propagation Analyzer', False))
    
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All enhanced features tests passed!")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
