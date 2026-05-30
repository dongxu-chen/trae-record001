BOT_NAME = 'price_crawler'

SPIDER_MODULES = ['price_crawler.spiders']
NEWSPIDER_MODULE = 'price_crawler.spiders'

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_DELAY_RANDOM_RANGE = (0.5, 2.0)

CONCURRENT_REQUESTS = 4

COOKIES_ENABLED = True
COOKIES_DEBUG = False

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]

PROXY_ENABLED = True
PROXY_ROTATION_INTERVAL = 5

DOWNLOADER_MIDDLEWARES = {
    'price_crawler.middlewares.fingerprint_middleware.FingerprintSimulatorMiddleware': 100,
    'price_crawler.middlewares.proxy_middleware.DynamicProxyMiddleware': 200,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

ITEM_PIPELINES = {
    'price_crawler.pipelines.PriceCrawlerPipeline': 300,
}

FEED_FORMAT = 'json'
FEED_URI = 'data/crawl_result.json'

LOG_LEVEL = 'INFO'
