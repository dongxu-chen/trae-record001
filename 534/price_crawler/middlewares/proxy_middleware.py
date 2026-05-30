from scrapy import signals
from price_crawler.middlewares.proxy_pool import ProxyPool
import logging
import random

logger = logging.getLogger(__name__)


class DynamicProxyMiddleware:
    def __init__(self, proxy_enabled=True, proxy_rotation_interval=5):
        self.proxy_enabled = proxy_enabled
        self.proxy_rotation_interval = proxy_rotation_interval
        self.proxy_pool = ProxyPool()
        self.request_count = 0
        self.current_proxy = None

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(
            proxy_enabled=crawler.settings.getbool('PROXY_ENABLED', True),
            proxy_rotation_interval=crawler.settings.getint('PROXY_ROTATION_INTERVAL', 5),
        )
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        spider.logger.info('DynamicProxyMiddleware initialized')

    def process_request(self, request, spider):
        if not self.proxy_enabled:
            return None
        if 'dont_proxy' in request.meta and request.meta['dont_proxy']:
            return None

        self.request_count += 1

        if self.request_count % self.proxy_rotation_interval == 0 or self.current_proxy is None:
            self.current_proxy = self.proxy_pool.get_elite_proxy()
            logger.debug(f"Rotating to new proxy: {self.current_proxy}")

        request.meta['proxy'] = self.current_proxy
        request.meta['proxy_used'] = self.current_proxy

        return None

    def process_response(self, request, response, spider):
        if response.status >= 400 and 'proxy_used' in request.meta:
            self.proxy_pool.mark_proxy_failed(request.meta['proxy_used'])
            logger.warning(f"Proxy failed with status {response.status}: {request.meta['proxy_used']}")
            new_request = request.copy()
            new_request.meta['proxy'] = self.proxy_pool.get_elite_proxy()
            new_request.dont_filter = True
            return new_request

        return response

    def process_exception(self, request, exception, spider):
        if 'proxy_used' in request.meta:
            self.proxy_pool.mark_proxy_failed(request.meta['proxy_used'])
            logger.error(f"Proxy exception: {exception}, proxy: {request.meta['proxy_used']}")

        new_request = request.copy()
        new_request.meta['proxy'] = self.proxy_pool.get_elite_proxy()
        new_request.dont_filter = True
        return new_request

    def get_proxy_stats(self):
        return self.proxy_pool.get_proxy_stats()
