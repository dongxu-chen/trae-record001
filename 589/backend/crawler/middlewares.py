import random
import time
from scrapy import signals
from scrapy.http import HtmlResponse
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import logging

logger = logging.getLogger(__name__)


class UserAgentMiddleware:
    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getlist('USER_AGENTS'))

    def process_request(self, request, spider):
        ua = random.choice(self.user_agents)
        request.headers.setdefault('User-Agent', ua)
        request.headers.setdefault('Referer', self._get_referer(request.url))

    def _get_referer(self, url):
        if 'taobao' in url:
            return 'https://www.taobao.com/'
        elif 'jd' in url:
            return 'https://www.jd.com/'
        elif 'yangkeduo' in url:
            return 'https://www.pinduoduo.com/'
        elif 'suning' in url:
            return 'https://www.suning.com/'
        return 'https://www.baidu.com/'


class ProxyMiddleware:
    def __init__(self):
        self.proxies = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if self.proxies and not request.meta.get('dont_proxy'):
            proxy = random.choice(self.proxies)
            request.meta['proxy'] = proxy


class RetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            logger.warning(f'Retrying {request.url} (status: {response.status})')
            time.sleep(random.uniform(1, 3))
            return self._retry(request, reason, spider) or response

        if 'anti' in response.url or 'verify' in response.url or response.status == 403:
            logger.warning(f'Anti-crawling detected for {request.url}')
            time.sleep(random.uniform(3, 5))
            return self._retry(request, 'anti-crawling', spider) or response

        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY) \
                and not request.meta.get('dont_retry', False):
            logger.warning(f'Exception while downloading {request.url}: {exception}')
            time.sleep(random.uniform(2, 4))
            return self._retry(request, exception, spider)


class JSRenderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        spider.logger.info('JSRenderMiddleware started')

    def spider_closed(self, spider):
        spider.logger.info('JSRenderMiddleware closed')

    def process_request(self, request, spider):
        if request.meta.get('render_js', False):
            return HtmlResponse(
                url=request.url,
                request=request,
                encoding='utf-8',
                body=b''
            )
        return None
