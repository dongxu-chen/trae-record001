"""
Playwright中间件 - 处理动态渲染页面
"""
from scrapy import signals
from scrapy.http import HtmlResponse, Response
from loguru import logger


class PlaywrightMiddleware:
    def __init__(self):
        self.browser = None
        self.context = None

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ],
            )
            logger.info("Playwright浏览器已启动")
        except ImportError:
            logger.warning("Playwright未安装，动态页面渲染将被跳过")
            self.browser = None
        except Exception as e:
            logger.error(f"Playwright启动失败: {e}")
            self.browser = None

    def spider_closed(self, spider):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            self.playwright.stop()
        logger.info("Playwright浏览器已关闭")

    def process_request(self, request, spider):
        if not request.meta.get('use_playwright'):
            return None

        if not self.browser:
            logger.warning("Playwright不可用，跳过动态渲染")
            return None

        try:
            if not self.context:
                self.context = self.browser.new_context(
                    user_agent=request.headers.get('User-Agent', b'').decode('utf-8'),
                    viewport={'width': 1920, 'height': 1080},
                )

            page = self.context.new_page()
            proxy_url = request.meta.get('proxy')
            if proxy_url:
                page.set_extra_http_headers({'X-Proxy': proxy_url})

            page.goto(
                request.url,
                wait_until='networkidle',
                timeout=30000,
            )

            wait_for = request.meta.get('playwright_wait_for')
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    pass

            auto_scroll = request.meta.get('playwright_auto_scroll', False)
            if auto_scroll:
                self._auto_scroll(page)

            body = page.content()
            current_url = page.url

            page.close()

            return HtmlResponse(
                url=current_url,
                body=body.encode('utf-8'),
                encoding='utf-8',
                request=request,
            )

        except Exception as e:
            logger.error(f"Playwright渲染失败: {request.url} - {e}")
            if 'page' in locals():
                try:
                    page.close()
                except Exception:
                    pass
            return None

    def _auto_scroll(self, page, scroll_pause_time=0.5, max_scrolls=5):
        for i in range(max_scrolls):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            import time
            time.sleep(scroll_pause_time)

    def process_response(self, request, response, spider):
        return response