import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from crawler.spiders import TaobaoSpider, JDSpider, PDDSpider, SuningSpider


def run_all_spiders(keyword=None, max_pages=3):
    settings = get_project_settings()
    settings.set('PROJECT_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    process = CrawlerProcess(settings)

    spiders = [
        (TaobaoSpider, {'keyword'}),
        (JDSpider, {'keyword'}),
        (PDDSpider, {'keyword'}),
        (SuningSpider, {'keyword'}),
    ]

    for spider_cls, params in spiders:
        spider_kwargs = {'max_pages': max_pages}
        if keyword:
            spider_kwargs['keyword'] = keyword
        process.crawl(spider_cls, **spider_kwargs)

    print(f"Starting crawlers for keyword: {keyword or 'default keywords'}...")
    process.start()
    print("Crawling completed!")


def run_single_spider(platform, keyword=None, max_pages=3):
    spider_map = {
        'taobao': TaobaoSpider,
        'jd': JDSpider,
        'pdd': PDDSpider,
        'suning': SuningSpider,
    }

    if platform not in spider_map:
        print(f"Unknown platform: {platform}")
        return

    settings = get_project_settings()
    settings.set('PROJECT_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    process = CrawlerProcess(settings)

    spider_cls = spider_map[platform]
    spider_kwargs = {'max_pages': max_pages}
    if keyword:
        spider_kwargs['keyword'] = keyword

    print(f"Starting {platform} spider...")
    process.crawl(spider_cls, **spider_kwargs)
    process.start()
    print(f"{platform} crawling completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run ecommerce price crawler')
    parser.add_argument('--platform', type=str, help='Platform to crawl (taobao, jd, pdd, suning, or all)')
    parser.add_argument('--keyword', type=str, help='Search keyword')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to crawl')

    args = parser.parse_args()

    if args.platform == 'all':
        run_all_spiders(args.keyword, args.pages)
    else:
        run_single_spider(args.platform, args.keyword, args.pages)
