import random
import logging

logger = logging.getLogger(__name__)


class ProxyPool:
    def __init__(self):
        self.proxies = [
            {'ip': '103.10.63.135', 'port': '8080', 'type': 'http', 'anonymity': 'elite'},
            {'ip': '8.210.83.33', 'port': '80', 'type': 'http', 'anonymity': 'anonymous'},
            {'ip': '101.200.238.204', 'port': '3128', 'type': 'http', 'anonymity': 'elite'},
            {'ip': '117.74.65.201', 'port': '80', 'type': 'http', 'anonymity': 'anonymous'},
            {'ip': '106.54.128.253', 'port': '999', 'type': 'http', 'anonymity': 'elite'},
            {'ip': '183.236.238.25', 'port': '8080', 'type': 'http', 'anonymity': 'anonymous'},
            {'ip': '120.198.76.45', 'port': '8060', 'type': 'http', 'anonymity': 'elite'},
            {'ip': '222.74.73.202', 'port': '80', 'type': 'http', 'anonymity': 'anonymous'},
            {'ip': '113.121.36.170', 'port': '9999', 'type': 'http', 'anonymity': 'elite'},
            {'ip': '103.37.141.69', 'port': '80', 'type': 'http', 'anonymity': 'anonymous'},
            {'ip': '118.24.62.156', 'port': '1080', 'type': 'socks5', 'anonymity': 'elite'},
            {'ip': '120.234.13.220', 'port': '1080', 'type': 'socks5', 'anonymity': 'elite'},
        ]
        self.failed_proxies = []
        self.max_failures = 3

    def get_random_proxy(self):
        if not self.proxies:
            self._restore_proxies()
        proxy = random.choice(self.proxies)
        return self._format_proxy(proxy)

    def get_elite_proxy(self):
        elite_proxies = [p for p in self.proxies if p['anonymity'] == 'elite']
        if elite_proxies:
            proxy = random.choice(elite_proxies)
            return self._format_proxy(proxy)
        return self.get_random_proxy()

    def _format_proxy(self, proxy):
        if proxy['type'] == 'socks5':
            return f"socks5://{proxy['ip']}:{proxy['port']}"
        return f"http://{proxy['ip']}:{proxy['port']}"

    def mark_proxy_failed(self, proxy_url):
        proxy = self._parse_proxy_url(proxy_url)
        if proxy:
            self.failed_proxies.append(proxy)
            if proxy in self.proxies:
                self.proxies.remove(proxy)
            logger.warning(f"Proxy marked as failed: {proxy_url}")

    def _parse_proxy_url(self, proxy_url):
        for proxy in self.proxies + self.failed_proxies:
            formatted = self._format_proxy(proxy)
            if formatted == proxy_url:
                return proxy
        return None

    def _restore_proxies(self):
        if len(self.failed_proxies) > 0:
            self.proxies.extend(self.failed_proxies[:5])
            self.failed_proxies = self.failed_proxies[5:]
            logger.info("Restored some failed proxies to pool")

    def add_proxy(self, ip, port, proxy_type='http', anonymity='anonymous'):
        proxy = {'ip': ip, 'port': port, 'type': proxy_type, 'anonymity': anonymity}
        if proxy not in self.proxies and proxy not in self.failed_proxies:
            self.proxies.append(proxy)
            logger.info(f"Added new proxy: {ip}:{port}")
            return True
        return False

    def get_proxy_stats(self):
        return {
            'total_available': len(self.proxies),
            'total_failed': len(self.failed_proxies),
            'elite_count': len([p for p in self.proxies if p['anonymity'] == 'elite']),
            'socks5_count': len([p for p in self.proxies if p['type'] == 'socks5']),
        }
