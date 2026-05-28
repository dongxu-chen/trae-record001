"""
混合抓取模式中间件
根据页面类型智能路由：静态页面用Requests，动态页面用Playwright
"""
import re
import time
from typing import Optional

import requests
from scrapy import signals
from scrapy.http import HtmlResponse, Request, TextResponse
from loguru import logger

from proxy_pool.pool import get_proxy_pool


STATIC_URL_PATTERNS = [
    r'\.html?$',
    r'/product/\d+',
    r'/goods/\d+',
    r'/item/\d+',
    r'/category/',
    r'/list/',
    r'/search\?',
]

DYNAMIC_INDICATORS = [
    'spa', 'app', 'dynamic', 'infinite', 'scroll',
    'ajax', 'api', 'react', 'vue', 'angular',
]


class HybridMiddleware:
    def __init__(self, settings):
        self.settings = settings
        self.proxy_pool = get_proxy_pool()
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.request_timeout = 15
        self.static_cache = {}
        self._stats = {'static_count': 0, 'dynamic_count': 0, 'fallback_count': 0}

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        logger.info(f"混合抓取中间件已启动: {spider.name}")

    def spider_closed(self, spider):
        if self.session:
            self.session.close()
        logger.info(
            f"混合抓取统计: 静态={self._stats['static_count']}, "
            f"动态={self._stats['dynamic_count']}, "
            f"降级={self._stats['fallback_count']}"
        )

    def _detect_mode(self, request) -> str:
        fetch_mode = request.meta.get('fetch_mode')
        if fetch_mode in ('static', 'dynamic'):
            return fetch_mode

        if request.meta.get('use_playwright'):
            return 'dynamic'

        url = request.url.lower()

        for pattern in STATIC_URL_PATTERNS:
            if re.search(pattern, url):
                return 'static'

        for indicator in DYNAMIC_INDICATORS:
            if indicator in url:
                return 'dynamic'

        competitor_config = request.meta.get('competitor_config', {})
        if competitor_config.get('use_playwright'):
            return 'dynamic'

        return 'static'

    def process_request(self, request, spider):
        mode = self._detect_mode(request)
        request.meta['_detected_mode'] = mode

        if mode == 'dynamic':
            request.meta['use_playwright'] = True
            self._stats['dynamic_count'] += 1
            logger.debug(f"[动态] {request.url}")
            return None

        self._stats['static_count'] += 1
        logger.debug(f"[静态] {request.url}")

        try:
            return self._fetch_with_requests(request)
        except Exception as e:
            logger.warning(f"Requests抓取失败，降级到Scrapy默认: {request.url} - {e}")
            self._stats['fallback_count'] += 1
            return None

    def _fetch_with_requests(self, request) -> Optional[HtmlResponse]:
        proxy_url = None
        proxies = None

        if self.proxy_pool and self.proxy_pool.enabled and not request.meta.get('dont_use_proxy'):
            proxy_url = self.proxy_pool.get_proxy()
            if proxy_url:
                proxies = {'http': proxy_url, 'https': proxy_url}

        headers = self._build_headers(request)

        try:
            resp = self.session.get(
                request.url,
                headers=headers,
                proxies=proxies,
                timeout=self.request_timeout,
                allow_redirects=True,
            )

            if proxy_url:
                self.proxy_pool.mark_valid(proxy_url)

            content_type = resp.headers.get('Content-Type', '')
            body = resp.content
            encoding = resp.encoding or 'utf-8'

            if 'text/html' in content_type or 'application/xhtml' in content_type:
                return HtmlResponse(
                    url=resp.url,
                    status=resp.status_code,
                    headers=dict(resp.headers),
                    body=body,
                    encoding=encoding,
                    request=request,
                )
            else:
                return TextResponse(
                    url=resp.url,
                    status=resp.status_code,
                    headers=dict(resp.headers),
                    body=body,
                    encoding=encoding,
                    request=request,
                )

        except requests.exceptions.Timeout:
            if proxy_url:
                self.proxy_pool.mark_invalid(proxy_url)
            raise
        except requests.exceptions.ConnectionError:
            if proxy_url:
                self.proxy_pool.mark_invalid(proxy_url)
            raise
        except requests.exceptions.ProxyError:
            if proxy_url:
                self.proxy_pool.mark_invalid(proxy_url)
            raise

    def _build_headers(self, request) -> dict:
        headers = dict(self.session.headers)

        ua = request.headers.get('User-Agent', b'').decode('utf-8') if request.headers.get('User-Agent') else None
        if ua:
            headers['User-Agent'] = ua

        for key, value in request.headers.items():
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            if key_str.lower() not in ('user-agent',):
                val_str = value[0].decode('utf-8') if isinstance(value, list) and value else ''
                headers[key_str] = val_str

        return headers

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None