import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = 'price_comparison_crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4

DOWNLOAD_DELAY = float(os.getenv("CRAWLER_DELAY", 2))
RANDOMIZE_DOWNLOAD_DELAY = True

COOKIES_ENABLED = True
COOKIES_DEBUG = False

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

DOWNLOADER_MIDDLEWARES = {
    'crawler.middlewares.UserAgentMiddleware': 400,
    'crawler.middlewares.ProxyMiddleware': 410,
    'crawler.middlewares.RetryMiddleware': 500,
}

ITEM_PIPELINES = {
    'crawler.pipelines.DataCleaningPipeline': 300,
    'crawler.pipelines.DatabasePipeline': 400,
    'crawler.pipelines.PriceHistoryPipeline': 500,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../price_comparison.db")
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///../price_history.db")

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
]

PLATFORMS = {
    'taobao': {
        'name': '淘宝',
        'search_url': 'https://s.taobao.com/search?q={keyword}',
        'price_selector': '.price--gHLPq0Kl',
        'name_selector': '.title--isvJA_zm',
    },
    'jd': {
        'name': '京东',
        'search_url': 'https://search.jd.com/Search?keyword={keyword}',
        'price_selector': '.p-price',
        'name_selector': '.p-name',
    },
    'pdd': {
        'name': '拼多多',
        'search_url': 'https://mobile.yangkeduo.com/search_result.html?search_key={keyword}',
        'price_selector': '.price',
        'name_selector': '.goods-name',
    },
    'suning': {
        'name': '苏宁',
        'search_url': 'https://search.suning.com/{keyword}/',
        'price_selector': '.def-price',
        'name_selector': '.title-selling-point',
    },
}
