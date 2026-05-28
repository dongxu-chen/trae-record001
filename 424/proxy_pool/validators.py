"""
代理验证模块
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
import requests


class ProxyValidator:
    def __init__(self, check_url='https://httpbin.org/ip', check_timeout=5):
        self.check_url = check_url
        self.check_timeout = check_timeout

    def validate_proxy(self, proxy_url):
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            start_time = time.time()
            resp = requests.get(
                self.check_url,
                proxies=proxies,
                timeout=self.check_timeout,
            )
            elapsed = time.time() - start_time
            if resp.status_code == 200:
                logger.debug(f"代理 {proxy_url} 验证成功, 延迟: {elapsed:.2f}s")
                return {
                    'proxy': proxy_url,
                    'valid': True,
                    'latency': elapsed,
                    'checked_at': time.time(),
                }
        except requests.exceptions.Timeout:
            logger.debug(f"代理 {proxy_url} 验证超时")
        except requests.exceptions.ConnectionError:
            logger.debug(f"代理 {proxy_url} 连接失败")
        except Exception as e:
            logger.debug(f"代理 {proxy_url} 验证异常: {e}")
        return {
            'proxy': proxy_url,
            'valid': False,
            'latency': None,
            'checked_at': time.time(),
        }

    def validate_batch(self, proxies, max_workers=20):
        valid_proxies = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {
                executor.submit(self.validate_proxy, proxy): proxy
                for proxy in proxies
            }
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result()
                    if result['valid']:
                        valid_proxies.append(result)
                except Exception as e:
                    logger.debug(f"验证任务异常: {e}")
        logger.info(f"代理验证完成: {len(valid_proxies)}/{len(proxies)} 有效")
        return valid_proxies