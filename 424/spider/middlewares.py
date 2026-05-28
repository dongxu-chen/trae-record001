"""
Scrapy中间件
包含代理中间件和User-Agent中间件
"""
import random
from scrapy import signals
from loguru import logger
from fake_useragent import UserAgent

from proxy_pool.pool import get_proxy_pool


class ProxyMiddleware:
    def __init__(self):
        self.proxy_pool = get_proxy_pool()

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        logger.info(f"代理中间件已启动，代理池大小: {self.proxy_pool.size}")

    def process_request(self, request, spider):
        if request.meta.get('dont_use_proxy'):
            return

        if self.proxy_pool and self.proxy_pool.enabled:
            proxy_url = self.proxy_pool.get_proxy()
            if proxy_url:
                request.meta['proxy'] = proxy_url
                request.meta['_proxy_url'] = proxy_url
                logger.debug(f"使用代理: {proxy_url} -> {request.url}")

    def process_response(self, request, response, spider):
        if response.status >= 400:
            proxy_url = request.meta.get('_proxy_url')
            if proxy_url:
                self.proxy_pool.mark_invalid(proxy_url)
                logger.debug(f"代理失效: {proxy_url} (状态码: {response.status})")
        return response

    def process_exception(self, request, exception, spider):
        proxy_url = request.meta.get('_proxy_url')
        if proxy_url:
            self.proxy_pool.mark_invalid(proxy_url)
            logger.debug(f"代理异常: {proxy_url} - {exception}")


class UserAgentMiddleware:
    def __init__(self):
        try:
            self.ua = UserAgent()
        except Exception:
            self.ua = None
        self.fallback_uas = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]

    def process_request(self, request, spider):
        if self.ua:
            try:
                ua = self.ua.random
            except Exception:
                ua = random.choice(self.fallback_uas)
        else:
            ua = random.choice(self.fallback_uas)

        request.headers['User-Agent'] = ua