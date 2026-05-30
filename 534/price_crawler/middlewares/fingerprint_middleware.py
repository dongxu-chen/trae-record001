from scrapy import signals
from price_crawler.middlewares.user_agent_pool import UserAgentPool
import random
import logging

logger = logging.getLogger(__name__)


class FingerprintSimulatorMiddleware:
    def __init__(self):
        self.ua_pool = UserAgentPool()
        self.accept_languages = [
            'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-HK,zh;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        ]
        self.accept_encodings = [
            'gzip, deflate, br',
            'gzip, deflate',
            'gzip, deflate, br, zstd',
        ]
        self.referers = [
            'https://www.baidu.com/',
            'https://www.google.com/',
            'https://www.sogou.com/',
            'https://www.bing.com/',
            'https://www.zhihu.com/',
            'https://www.weibo.com/',
            'https://www.taobao.com/',
            'https://www.jd.com/',
        ]
        self.cache_controls = [
            'max-age=0',
            'no-cache',
            'no-store',
            'max-age=300',
        ]

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        spider.logger.info('FingerprintSimulatorMiddleware initialized')

    def process_request(self, request, spider):
        if 'dont_simulate' in request.meta and request.meta['dont_simulate']:
            return None

        ua = self.ua_pool.get_random()
        is_mobile = 'iPhone' in ua or 'Android' in ua

        headers = {
            'User-Agent': ua,
            'Accept': self._generate_accept_header(is_mobile),
            'Accept-Language': random.choice(self.accept_languages),
            'Accept-Encoding': random.choice(self.accept_encodings),
            'Cache-Control': random.choice(self.cache_controls),
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if random.random() < 0.3 else 'cross-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        if is_mobile:
            headers['Sec-Ch-Ua-Mobile'] = '?1'
            headers['Sec-Ch-Ua-Platform'] = random.choice(['"Android"', '"iOS"'])
        else:
            headers['Sec-Ch-Ua-Mobile'] = '?0'
            headers['Sec-Ch-Ua-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])

        if random.random() < 0.7:
            headers['Referer'] = random.choice(self.referers)

        if random.random() < 0.3:
            headers['DNT'] = random.choice(['1', '0'])

        for key, value in headers.items():
            if key not in request.headers:
                request.headers[key] = value

        request.meta['fingerprint_ua'] = ua
        request.meta['is_mobile'] = is_mobile

        return None

    def _generate_accept_header(self, is_mobile):
        if is_mobile:
            return 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        else:
            variants = [
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            ]
            return random.choice(variants)
