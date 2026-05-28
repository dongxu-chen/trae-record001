"""
代理IP获取模块
支持从多个免费/付费代理源获取代理
"""
import time
import random
import requests
from loguru import logger
from bs4 import BeautifulSoup


class ProxyFetcher:
    def __init__(self, sources_config):
        self.sources = sources_config

    def fetch_all(self):
        proxies = []
        for source in self.sources:
            if not source.get('enabled', False):
                continue
            try:
                fetcher = getattr(self, f'_fetch_{source["name"]}', None)
                if fetcher:
                    new_proxies = fetcher(source)
                    proxies.extend(new_proxies)
                    logger.info(f"从 {source['name']} 获取到 {len(new_proxies)} 个代理")
            except Exception as e:
                logger.warning(f"从 {source['name']} 获取代理失败: {e}")
        return proxies

    def _fetch_kuaidaili(self, source):
        proxies = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(source['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'lxml')
            tbody = soup.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        ip = tds[0].text.strip()
                        port = tds[1].text.strip()
                        proxies.append(f'http://{ip}:{port}')
        except Exception as e:
            logger.warning(f"快代理获取失败: {e}")
        return proxies

    def _fetch_xiladaili(self, source):
        proxies = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(source['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table')
            if table:
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        ip = tds[0].text.strip()
                        port = tds[1].text.strip()
                        if ip.count('.') == 3 and port.isdigit():
                            proxies.append(f'http://{ip}:{port}')
        except Exception as e:
            logger.warning(f"西拉代理获取失败: {e}")
        return proxies

    def _fetch_from_url(self, url, parser_func):
        proxies = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            proxies = parser_func(resp.text)
        except Exception as e:
            logger.warning(f"从 {url} 获取代理失败: {e}")
        return proxies