"""
Scrapy项目设置
"""
BOT_NAME = 'price_monitor'
SPIDER_MODULES = ['spider.spiders']
NEWSPIDER_MODULE = 'spider.spiders'

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
COOKIES_ENABLED = False

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

DOWNLOADER_MIDDLEWARES = {
    'spider.middlewares.ProxyMiddleware': 350,
    'spider.middlewares.UserAgentMiddleware': 400,
    'spider.hybrid_middleware.HybridMiddleware': 500,
    'spider.playwright_middleware.PlaywrightMiddleware': 543,
}

ITEM_PIPELINES = {
    'spider.pipelines.ProductPipeline': 300,
    'spider.pipelines.PriceHistoryPipeline': 400,
    'spider.pipelines.AlertPipeline': 500,
    'spider.analysis_pipeline.AnalysisPipeline': 600,
}

PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
    'args': [
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--no-sandbox',
    ],
}

PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_FILE = 'logs/spider.log'