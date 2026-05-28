import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    logger.info("Testing imports...")
    try:
        from config import Config
        logger.info("✓ config imported")
        
        from database import init_db, get_session
        logger.info("✓ database imported")
        
        from analysis import SentimentAnalyzer, TopicModeler, TextProcessor, PropagationAnalyzer
        logger.info("✓ analysis modules imported")
        
        from crawlers.data_generator import MockDataGenerator
        logger.info("✓ data_generator imported")
        
        from data_pipeline import DataPipeline
        logger.info("✓ data_pipeline imported")
        
        from alert_manager import AlertManager
        logger.info("✓ alert_manager imported")
        
        return True
    except Exception as e:
        logger.error(f"Import error: {e}")
        return False

def test_database():
    logger.info("\nTesting database...")
    try:
        from database import init_db, get_session
        engine = init_db()
        session = get_session()
        session.close()
        logger.info("✓ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False

def test_text_processor():
    logger.info("\nTesting text processor...")
    try:
        from analysis import TextProcessor
        
        processor = TextProcessor()
        
        text = "今天天气真好，心情也很好！"
        cleaned = processor.clean_text(text)
        tokens = processor.tokenize(text)
        keywords = processor.extract_keywords(text)
        
        logger.info(f"  Original: {text}")
        logger.info(f"  Cleaned: {cleaned}")
        logger.info(f"  Tokens: {tokens}")
        logger.info(f"  Keywords: {keywords}")
        logger.info("✓ Text processor works")
        return True
    except Exception as e:
        logger.error(f"Text processor error: {e}")
        return False

def test_sentiment_analyzer():
    logger.info("\nTesting sentiment analyzer...")
    try:
        from analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        test_cases = [
            "这个产品真的太棒了，非常满意！",
            "质量太差了，客服态度也不好，很失望。",
            "今天天气不错，温度适宜。"
        ]
        
        for text in test_cases:
            result = analyzer.analyze(text)
            logger.info(f"  Text: {text}")
            logger.info(f"  Result: {result['sentiment']} (pos={result['positive']:.3f}, neg={result['negative']:.3f}, neu={result['neutral']:.3f})")
        
        logger.info("✓ Sentiment analyzer works")
        return True
    except Exception as e:
        logger.error(f"Sentiment analyzer error: {e}")
        return False

def test_topic_modeler():
    logger.info("\nTesting topic modeler...")
    try:
        from analysis import TopicModeler
        
        modeler = TopicModeler()
        
        text = "这个产品的质量很好，服务也很到位，非常满意这次购物体验。"
        topics = modeler.get_topics(text)
        
        logger.info(f"  Text: {text}")
        for topic in topics:
            logger.info(f"  Topic {topic['topic_id']}: weight={topic['weight']:.3f}, keywords={topic['keywords']}")
        
        all_topics = modeler.get_all_topics()
        logger.info(f"  Total topics available: {len(all_topics)}")
        
        logger.info("✓ Topic modeler works")
        return True
    except Exception as e:
        logger.error(f"Topic modeler error: {e}")
        return False

def test_data_generator():
    logger.info("\nTesting data generator...")
    try:
        from crawlers.data_generator import MockDataGenerator
        
        generator = MockDataGenerator()
        posts = generator.generate_batch(count=10)
        
        logger.info(f"  Generated {len(posts)} posts")
        for i, post in enumerate(posts[:3]):
            logger.info(f"  Post {i+1}: platform={post['platform']}, content={post['content'][:30]}...")
        
        logger.info("✓ Data generator works")
        return True
    except Exception as e:
        logger.error(f"Data generator error: {e}")
        return False

def test_alert_manager():
    logger.info("\nTesting alert manager...")
    try:
        from alert_manager import AlertManager
        
        alert_manager = AlertManager()
        
        summary = alert_manager.get_alert_summary(hours=24)
        logger.info(f"  Alert summary: {summary}")
        
        recent_alerts = alert_manager.get_recent_alerts(limit=5)
        logger.info(f"  Recent alerts: {len(recent_alerts)}")
        
        logger.info("✓ Alert manager works")
        return True
    except Exception as e:
        logger.error(f"Alert manager error: {e}")
        return False

def test_data_pipeline():
    logger.info("\nTesting data pipeline...")
    try:
        from data_pipeline import DataPipeline
        from crawlers.data_generator import MockDataGenerator
        
        pipeline = DataPipeline(use_kafka=False)
        generator = MockDataGenerator()
        
        posts = generator.generate_batch(count=20)
        results = pipeline.process_batch(posts)
        
        logger.info(f"  Processed {len(results)} posts")
        
        dist = pipeline.get_sentiment_distribution(hours=24)
        logger.info(f"  Sentiment distribution: {dist}")
        
        keywords = pipeline.get_top_keywords(hours=24, top_k=10)
        logger.info(f"  Top keywords: {keywords[:5]}")
        
        logger.info("✓ Data pipeline works")
        return True
    except Exception as e:
        logger.error(f"Data pipeline error: {e}", exc_info=True)
        return False

def main():
    logger.info("=" * 60)
    logger.info("Social Media Sentiment Analysis System - System Test")
    logger.info("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Text Processor", test_text_processor),
        ("Sentiment Analyzer", test_sentiment_analyzer),
        ("Topic Modeler", test_topic_modeler),
        ("Data Generator", test_data_generator),
        ("Alert Manager", test_alert_manager),
        ("Data Pipeline", test_data_pipeline),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} failed with exception: {e}")
            results.append((name, False))
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready.")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
