import sys
sys.path.insert(0, '.')

import logging
from datetime import datetime, timedelta
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_event_evolution():
    print("\n" + "="*70)
    print("Testing Event Evolution Analyzer")
    print("="*70)
    
    from analysis import EventEvolutionAnalyzer
    
    analyzer = EventEvolutionAnalyzer()
    
    base_time = datetime.utcnow()
    
    test_posts = []
    for i in range(30):
        hour_offset = i // 5
        content = ""
        
        if hour_offset < 3:
            content = f"新发布的手机拍照功能评测 {i} 这款手机的相机真的很不错"
        elif hour_offset < 6:
            content = f"手机续航测试 {i} 电池续航能力很强，充电速度快"
        else:
            content = f"手机价格讨论 {i} 性价比很高，值得购买"
        
        test_posts.append({
            'post_id': f'post_{i:03d}',
            'content': content,
            'timestamp': base_time - timedelta(hours=6 - hour_offset, minutes=i % 5 * 10),
            'likes': 100 + i * 10,
            'shares': 20 + i * 2,
            'comments': 50 + i * 5,
            'sentiment': {'sentiment': 'positive' if i % 3 != 0 else 'neutral'}
        })
    
    print(f"\n1. Testing detect_events with {len(test_posts)} posts...")
    events = analyzer.detect_events(test_posts, min_posts=3)
    print(f"   Events detected: {len(events)}")
    for event in events[:5]:
        print(f"   - {event['event_keyword']}: peak={event['peak_count']} at {event['peak_time']}, growth={event['growth_rate']:.2%}")
    
    print("\n2. Testing analyze_subtopic_evolution...")
    subtopic_result = analyzer.analyze_subtopic_evolution(test_posts, '手机')
    print(f"   Main keyword: {subtopic_result['main_keyword']}")
    print(f"   Total posts: {subtopic_result['total_posts']}")
    print(f"   Time windows: {subtopic_result['time_windows']}")
    
    if subtopic_result.get('subtopic_evolution'):
        print(f"\n   Subtopic evolution over time:")
        for window_data in subtopic_result['subtopic_evolution'][:3]:
            print(f"   {window_data['time_window']}: {window_data['post_count']} posts")
            if window_data['top_subtopics']:
                top3 = [t['keyword'] for t in window_data['top_subtopics'][:3]]
                print(f"      Top subtopics: {', '.join(top3)}")
    
    if subtopic_result.get('emerging_subtopics'):
        print(f"\n   Emerging subtopics:")
        for st in subtopic_result['emerging_subtopics'][:5]:
            print(f"      - {st['keyword']}: growth={st['growth_rate']:.2%}")
    
    if subtopic_result.get('declining_subtopics'):
        print(f"\n   Declining subtopics:")
        for st in subtopic_result['declining_subtopics'][:5]:
            print(f"      - {st['keyword']}: decline={st['decline_rate']:.2%}")
    
    print("\n3. Testing track_event_lifecycle...")
    lifecycle = analyzer.track_event_lifecycle(test_posts, '手机')
    print(f"   Event: {lifecycle['event_keyword']}")
    print(f"   Total posts: {lifecycle['total_posts']}")
    print(f"   Duration: {lifecycle['duration_hours']:.2f} hours")
    print(f"   Lifecycle stage: {lifecycle['lifecycle_stage']}")
    print(f"   Peak time: {lifecycle['peak_time']}")
    print(f"   Sentiment distribution: {lifecycle.get('sentiment_distribution', {})}")
    
    print("\n4. Testing generate_event_summary...")
    summary = analyzer.generate_event_summary(events)
    print(f"   Total events: {summary.get('total_events', 0)}")
    print(f"   Total mentions: {summary.get('total_mentions', 0)}")
    print(f"   Categories: {summary.get('categories', {})}")
    
    print("\n[OK] Event Evolution Analyzer Test Passed!")
    return True


def test_influence_analyzer():
    print("\n" + "="*70)
    print("Testing Influence Analyzer")
    print("="*70)
    
    from analysis import InfluenceAnalyzer
    
    analyzer = InfluenceAnalyzer()
    
    print("\n1. Testing classify_node_type...")
    test_authors = [
        ('人民日报', {'verified': True, 'followers_count': 10000000}),
        ('科技博主小明', {'verified': True, 'followers_count': 500000}),
        ('普通用户张三', {}),
        ('CNN Breaking News', {}),
        ('明星李华官方账号', {'verified': True, 'followers_count': 5000000}),
    ]
    
    for author, metadata in test_authors:
        node_type = analyzer.classify_node_type(author, metadata)
        print(f"   '{author}' -> {node_type}")
    
    print("\n2. Testing calculate_influence_score...")
    node_data = {
        'followers_count': 1000000,
        'following_count': 500,
        'total_posts': 500,
        'avg_likes': 5000,
        'avg_shares': 1000,
        'avg_comments': 2000,
        'verified': True,
        'node_type': 'celebrity'
    }
    score = analyzer.calculate_influence_score(node_data)
    print(f"   Celebrity node influence score: {score:.6f}")
    
    print("\n3. Testing identify_key_nodes...")
    base_time = datetime.utcnow()
    test_posts = []
    
    authors_config = [
        ('人民日报', 10, 10000, 5000, 2000, 'media'),
        ('科技博主小明', 8, 5000, 2000, 1000, 'influencer'),
        ('普通用户张三', 3, 100, 50, 20, 'normal'),
        ('明星李华', 15, 20000, 10000, 5000, 'celebrity'),
        ('新华网', 12, 8000, 4000, 1500, 'media'),
    ]
    
    for author, post_count, likes, shares, comments, _ in authors_config:
        for i in range(post_count):
            test_posts.append({
                'author': author,
                'content': f'测试内容 {i} 关于最新手机产品',
                'timestamp': base_time - timedelta(hours=i),
                'likes': likes + i * 10,
                'shares': shares + i * 5,
                'comments': comments + i * 2,
                'platform': 'weibo',
                'sentiment': {'sentiment': 'positive' if i % 3 != 0 else 'neutral'}
            })
    
    key_nodes = analyzer.identify_key_nodes(test_posts, top_k=10)
    print(f"   Top {len(key_nodes)} key nodes:")
    for node in key_nodes:
        print(f"   - {node['author']}: type={node['node_type']}, influence={node['influence_score']:.6f}, posts={node['post_count']}, engagement={node['total_engagement']}")
    
    print("\n4. Testing analyze_topic_influence...")
    topic_influence = analyzer.analyze_topic_influence(test_posts, '手机')
    if topic_influence:
        print(f"   Topic: {topic_influence['topic_keyword']}")
        print(f"   Related posts: {topic_influence['total_related_posts']}")
        print(f"   Top authors: {[a['author'] for a in topic_influence['top_authors_by_posts'][:3]]}")
        if topic_influence.get('sentiment_by_type'):
            print(f"   Sentiment by type: {list(topic_influence['sentiment_by_type'].keys())}")
    
    print("\n5. Testing generate_influence_report...")
    propagation_paths = [
        {'source_node': '人民日报', 'target_node': '科技博主小明', 'weight': 1.0},
        {'source_node': '科技博主小明', 'target_node': '普通用户张三', 'weight': 0.8},
        {'source_node': '明星李华', 'target_node': '普通用户张三', 'weight': 1.2},
        {'source_node': '新华网', 'target_node': '科技博主小明', 'weight': 0.9},
    ]
    
    report = analyzer.generate_influence_report(test_posts, propagation_paths)
    print(f"\n   Influence Report:")
    print(f"   Total nodes: {report['total_nodes_analyzed']}")
    print(f"   Total posts: {report['total_posts']}")
    print(f"   Estimated reach: {report['estimated_reach']:,}")
    print(f"   Summary: {report['summary']}")
    
    if report.get('node_types_distribution'):
        print(f"\n   Node type distribution:")
        for ntype, data in report['node_types_distribution'].items():
            print(f"      {ntype}: {data['count']} ({data['percentage']:.1%})")
    
    if report.get('top_influencers'):
        print(f"\n   Top influencers: {[n['author'] for n in report['top_influencers'][:3]]}")
    if report.get('top_media_outlets'):
        print(f"   Top media: {[n['author'] for n in report['top_media_outlets'][:3]]}")
    
    print("\n[OK] Influence Analyzer Test Passed!")
    return True


def test_multilingual_analyzer():
    print("\n" + "="*70)
    print("Testing Multilingual Analyzer")
    print("="*70)
    
    from analysis import MultilingualAnalyzer
    
    analyzer = MultilingualAnalyzer()
    
    print("\n1. Testing detect_language...")
    test_texts = [
        ('中文测试：这是一段中文文本，用于测试语言检测功能。', 'zh'),
        ('This is an English text for testing language detection.', 'en'),
        ('これは日本語のテキストです。', 'ja'),
        ('이것은 한국어 텍스트입니다.', 'ko'),
        ('This is a 混合 text with 中文 and English.', 'zh'),
    ]
    
    for text, expected_lang in test_texts:
        detected = analyzer.detect_language(text)
        status = "OK" if detected == expected_lang else "FAIL"
        print(f"   {status} Expected: {expected_lang}, Detected: {detected}")
        print(f"     Text: {text[:40]}...")
    
    print("\n2. Testing tokenize_multilingual...")
    zh_tokens = analyzer.tokenize_multilingual('这款手机的拍照功能非常强大', 'zh')
    en_tokens = analyzer.tokenize_multilingual('The camera quality of this phone is amazing', 'en')
    ja_tokens = analyzer.tokenize_multilingual('このスマートフォンのカメラはとても素晴らしいです', 'ja')
    print(f"   Chinese tokens: {zh_tokens}")
    print(f"   English tokens: {en_tokens}")
    print(f"   Japanese tokens: {ja_tokens}")
    
    print("\n3. Testing cross_language_keyword_mapping...")
    zh_mapping = analyzer.cross_language_keyword_mapping('产品', 'zh')
    print(f"   '产品' translations: {zh_mapping}")
    
    en_mapping = analyzer.cross_language_keyword_mapping('product', 'en')
    print(f"   'product' translations: {en_mapping}")
    
    print("\n4. Testing analyze_cross_language_sentiment...")
    sentiment_tests = [
        ('这个产品真的很棒，非常满意！', 'zh'),
        ('This product is amazing and I am very satisfied!', 'en'),
        ('この製品は素晴らしくて、とても満足しています！', 'ja'),
        ('이 제품은 정말 훌륭하고 매우 만족합니다!', 'ko'),
        ('这个产品质量很差，非常失望。', 'zh'),
        ('This product quality is terrible and I am very disappointed.', 'en'),
    ]
    
    for text, lang in sentiment_tests:
        result = analyzer.analyze_cross_language_sentiment(text, lang)
        print(f"\n   Text ({lang}): {text[:40]}...")
        print(f"      Sentiment: {result['sentiment']}")
        print(f"      Scores: pos={result['positive']:.4f}, neg={result['negative']:.4f}, neu={result['neutral']:.4f}")
        if result.get('matched_keywords'):
            pos_kws = result['matched_keywords'].get('positive', [])
            neg_kws = result['matched_keywords'].get('negative', [])
            if pos_kws:
                print(f"      Positive keywords: {pos_kws}")
            if neg_kws:
                print(f"      Negative keywords: {neg_kws}")
    
    print("\n5. Testing correlate_cross_language_posts...")
    multilingual_posts = [
        {'content': '这款手机拍照功能非常强大，值得推荐', 'timestamp': datetime.utcnow()},
        {'content': 'This smartphone has an amazing camera, highly recommended', 'timestamp': datetime.utcnow()},
        {'content': 'このスマートフォンのカメラは素晴らしい、強く推奨します', 'timestamp': datetime.utcnow()},
        {'content': '手机的续航能力很强，电池很耐用', 'timestamp': datetime.utcnow()},
        {'content': 'The battery life of this phone is excellent and very durable', 'timestamp': datetime.utcnow()},
        {'content': '이 스마트폰의 배터리 수명은 매우 우수합니다', 'timestamp': datetime.utcnow()},
        {'content': '产品质量很好，用户体验不错', 'timestamp': datetime.utcnow()},
        {'content': 'Product quality is very good, user experience is nice', 'timestamp': datetime.utcnow()},
        {'content': '製品の品質は非常に良く、ユーザー体験も素晴らしい', 'timestamp': datetime.utcnow()},
    ]
    
    correlation = analyzer.correlate_cross_language_posts(multilingual_posts)
    
    print(f"   Language distribution:")
    for lang, data in correlation.get('language_distribution', {}).items():
        print(f"      {lang}: {data['count']} posts")
    
    if correlation.get('top_keywords_by_language'):
        print(f"\n   Top keywords by language:")
        for lang, kws in correlation['top_keywords_by_language'].items():
            top3 = [kw['keyword'] for kw in kws[:3]]
            print(f"      {lang}: {', '.join(top3)}")
    
    if correlation.get('cross_language_matches'):
        print(f"\n   Cross-language matches found: {len(correlation['cross_language_matches'])}")
        for match in correlation['cross_language_matches'][:5]:
            print(f"      {match['source_keyword']}({match['source_language']}) <-> {match['target_keyword']}({match['target_language']}): {match['combined_volume']}")
    
    if correlation.get('sentiment_by_language'):
        print(f"\n   Sentiment by language:")
        for lang, data in correlation['sentiment_by_language'].items():
            print(f"      {lang}: {data['sentiment_percentages']}")
    
    print("\n6. Testing generate_multilingual_report...")
    report = analyzer.generate_multilingual_report(multilingual_posts)
    print(f"   Languages covered: {report['languages_covered']}")
    print(f"   Multilingual topics: {len(report['multilingual_trending_topics'])}")
    print(f"   Summary: {report['summary']}")
    
    if report.get('multilingual_trending_topics'):
        print(f"\n   Top multilingual topics:")
        for topic in report['multilingual_trending_topics'][:3]:
            print(f"      {topic['base_keyword']}({topic['base_language']}): volume={topic['total_volume']}")
            for lang, translations in topic['translations'].items():
                trans_kws = [t['keyword'] for t in translations]
                print(f"         {lang}: {', '.join(trans_kws)}")
    
    print("\n[OK] Multilingual Analyzer Test Passed!")
    return True


def main():
    print("="*70)
    print("New Features Test Suite")
    print("="*70)
    
    results = []
    
    try:
        results.append(('Event Evolution Analyzer', test_event_evolution()))
    except Exception as e:
        logger.error(f"Event Evolution Analyzer test failed: {e}", exc_info=True)
        results.append(('Event Evolution Analyzer', False))
    
    try:
        results.append(('Influence Analyzer', test_influence_analyzer()))
    except Exception as e:
        logger.error(f"Influence Analyzer test failed: {e}", exc_info=True)
        results.append(('Influence Analyzer', False))
    
    try:
        results.append(('Multilingual Analyzer', test_multilingual_analyzer()))
    except Exception as e:
        logger.error(f"Multilingual Analyzer test failed: {e}", exc_info=True)
        results.append(('Multilingual Analyzer', False))
    
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = 0
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n[OK] All new features tests passed!")
        return 0
    else:
        print(f"\n[WARN] {len(results) - passed} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
