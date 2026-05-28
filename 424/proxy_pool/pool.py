"""
代理IP池核心模块
管理代理的获取、验证、存储和轮换
支持主动健康检查和失效代理的二次验证
"""
import random
import time
import threading
from typing import Optional, Dict, List, Set
from loguru import logger

from proxy_pool.fetcher import ProxyFetcher
from proxy_pool.validators import ProxyValidator


class ProxyPool:
    _instance = None

    def __new__(cls, config=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config=None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        if config is None:
            from config import PROXY as config

        self.config = config
        self.proxies: Dict[str, dict] = {}
        self.probation: Set[str] = set()
        self.failure_counts: Dict[str, int] = {}

        self.fetcher = ProxyFetcher(config.get('sources', []))
        self.validator = ProxyValidator(
            check_url=config.get('check_url', 'https://httpbin.org/ip'),
            check_timeout=config.get('check_timeout', 5),
        )
        self.enabled = config.get('enable', True)
        self.min_pool_size = config.get('min_pool_size', 20)
        self.max_failures = config.get('max_failures', 3)
        self.probation_timeout = config.get('probation_timeout', 300)

        self._last_refresh = 0
        self._last_health_check = 0
        self._refresh_interval = config.get('refresh_interval', 300)
        self._health_check_interval = config.get('health_check_interval', 60)

        self._lock = threading.Lock()
        self._health_thread = None
        self._health_running = False

    def start_health_check(self):
        if self._health_thread and self._health_thread.is_alive():
            return

        self._health_running = True
        self._health_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self._health_thread.start()
        logger.info("代理池健康检查线程已启动")

    def stop_health_check(self):
        self._health_running = False
        if self._health_thread:
            self._health_thread.join(timeout=5)
        logger.info("代理池健康检查线程已停止")

    def _health_check_loop(self):
        while self._health_running:
            try:
                time.sleep(self._health_check_interval)
                if not self._health_running:
                    break
                self.active_health_check()
            except Exception as e:
                logger.error(f"健康检查线程异常: {e}")

    def refresh(self, force=False):
        now = time.time()
        if not force and (now - self._last_refresh) < self._refresh_interval:
            return

        if len(self.proxies) >= self.min_pool_size and not force:
            return

        logger.info("开始刷新代理池...")
        raw_proxies = self.fetcher.fetch_all()

        if not raw_proxies:
            logger.warning("未获取到新代理，尝试验证现有代理")
            self._revalidate_existing()
            return

        valid_proxies = self.validator.validate_batch(raw_proxies)
        with self._lock:
            for vp in valid_proxies:
                self.proxies[vp['proxy']] = vp
                self.failure_counts[vp['proxy']] = 0
                self.probation.discard(vp['proxy'])

        self._last_refresh = now
        logger.info(f"代理池刷新完成，当前可用代理: {len(self.proxies)}")

    def _revalidate_existing(self):
        if not self.proxies:
            return
        proxy_list = list(self.proxies.keys())
        valid_results = self.validator.validate_batch(proxy_list)
        with self._lock:
            self.proxies.clear()
            for vp in valid_results:
                self.proxies[vp['proxy']] = vp
                self.failure_counts[vp['proxy']] = 0
                self.probation.discard(vp['proxy'])

    def active_health_check(self):
        now = time.time()
        if not self.proxies:
            return

        logger.debug(f"开始主动健康检查，当前代理数: {len(self.proxies)}")

        proxy_list = list(self.proxies.keys())
        valid_results = self.validator.validate_batch(proxy_list)

        valid_set = {vp['proxy'] for vp in valid_results}
        invalid_proxies = []

        with self._lock:
            for proxy_url in proxy_list:
                if proxy_url in valid_set:
                    self.failure_counts[proxy_url] = 0
                    self.probation.discard(proxy_url)
                else:
                    self.failure_counts[proxy_url] = self.failure_counts.get(proxy_url, 0) + 1
                    if self.failure_counts[proxy_url] >= self.max_failures:
                        invalid_proxies.append(proxy_url)
                    else:
                        self.probation.add(proxy_url)

            for proxy_url in invalid_proxies:
                del self.proxies[proxy_url]
                self.failure_counts.pop(proxy_url, None)
                self.probation.discard(proxy_url)
                logger.debug(f"健康检查移除无效代理: {proxy_url}")

        self._last_health_check = now
        if invalid_proxies:
            logger.info(
                f"健康检查完成: 移除 {len(invalid_proxies)} 个无效代理, "
                f"剩余 {len(self.proxies)} 个"
            )

        if len(self.proxies) < self.min_pool_size:
            self.refresh(force=True)

    def get_proxy(self) -> Optional[str]:
        if not self.enabled:
            return None

        self.refresh()

        if not self.proxies:
            logger.warning("代理池为空，无法获取代理")
            return None

        with self._lock:
            available = [p for p in self.proxies if p not in self.probation]
            if not available:
                available = list(self.proxies.keys())
            if not available:
                return None

            proxy_url = random.choice(available)

        logger.debug(f"选取代理: {proxy_url}")
        return proxy_url

    def get_proxy_list(self, count: int = 1) -> List[str]:
        if not self.enabled:
            return []

        self.refresh()

        if not self.proxies:
            return []

        with self._lock:
            available = [p for p in self.proxies if p not in self.probation]
            if not available:
                available = list(self.proxies.keys())

        count = min(count, len(available))
        return random.sample(available, count)

    def mark_invalid(self, proxy_url: str):
        if proxy_url not in self.proxies:
            return

        with self._lock:
            self.failure_counts[proxy_url] = self.failure_counts.get(proxy_url, 0) + 1
            self.probation.add(proxy_url)

            if self.failure_counts[proxy_url] >= self.max_failures:
                del self.proxies[proxy_url]
                self.failure_counts.pop(proxy_url, None)
                self.probation.discard(proxy_url)
                logger.debug(f"代理连续失败，已移除: {proxy_url}, 剩余: {len(self.proxies)}")
            else:
                logger.debug(
                    f"代理标记待查: {proxy_url}, "
                    f"失败次数: {self.failure_counts[proxy_url]}/{self.max_failures}"
                )

    def mark_valid(self, proxy_url: str, latency: float = None):
        if proxy_url in self.proxies:
            with self._lock:
                self.proxies[proxy_url]['latency'] = latency
                self.proxies[proxy_url]['checked_at'] = time.time()
                self.failure_counts[proxy_url] = 0
                self.probation.discard(proxy_url)

    def revalidate_proxy(self, proxy_url: str) -> bool:
        if proxy_url not in self.proxies:
            return False

        result = self.validator.validate_proxy(proxy_url)
        if result['valid']:
            with self._lock:
                self.proxies[proxy_url] = result
                self.failure_counts[proxy_url] = 0
                self.probation.discard(proxy_url)
            return True
        else:
            with self._lock:
                del self.proxies[proxy_url]
                self.failure_counts.pop(proxy_url, None)
                self.probation.discard(proxy_url)
            return False

    def get_healthy_proxies(self) -> List[str]:
        with self._lock:
            return [p for p in self.proxies if p not in self.probation]

    @property
    def size(self):
        return len(self.proxies)

    @property
    def healthy_size(self):
        return len([p for p in self.proxies if p not in self.probation])

    @property
    def probation_size(self):
        return len(self.probation)

    @property
    def is_empty(self):
        return len(self.proxies) == 0

    def status(self):
        return {
            'enabled': self.enabled,
            'size': len(self.proxies),
            'healthy_size': self.healthy_size,
            'probation_size': self.probation_size,
            'min_size': self.min_pool_size,
            'last_refresh': self._last_refresh,
            'last_health_check': self._last_health_check,
            'health_check_running': self._health_running,
        }


proxy_pool: Optional[ProxyPool] = None


def init_proxy_pool(config=None):
    global proxy_pool
    proxy_pool = ProxyPool(config)
    if proxy_pool.enabled:
        proxy_pool.start_health_check()
    return proxy_pool


def get_proxy_pool():
    global proxy_pool
    if proxy_pool is None:
        proxy_pool = ProxyPool()
    return proxy_pool