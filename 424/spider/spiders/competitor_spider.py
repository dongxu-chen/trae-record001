"""
竞品价格监控爬虫
支持配置多个竞品源，自动抓取价格、库存、促销信息
"""
import re
import hashlib
from urllib.parse import urljoin
from datetime import datetime

import scrapy
from loguru import logger

from spider.items import ProductItem
from config import SPIDER_CONFIG


class CompetitorSpider(scrapy.Spider):
    name = 'competitor'
    allowed_domains = []
    custom_settings = {
        'ITEM_PIPELINES': {
            'spider.pipelines.ProductPipeline': 300,
            'spider.pipelines.PriceHistoryPipeline': 400,
            'spider.pipelines.AlertPipeline': 500,
        }
    }

    def __init__(self, source=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_filter = source
        self.category_filter = category
        self.competitors = []
        self._load_competitors()

    def _load_competitors(self):
        for comp in SPIDER_CONFIG.get('competitors', []):
            if not comp.get('enabled', True):
                continue
            if self.source_filter and comp['name'] != self.source_filter:
                continue
            self.competitors.append(comp)
            self.allowed_domains.append(comp.get('domain', ''))

    def start_requests(self):
        for comp in self.competitors:
            use_playwright = comp.get('use_playwright', False)
            for url in comp.get('start_urls', []):
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_list_page,
                    meta={
                        'source': comp['name'],
                        'domain': comp.get('domain', ''),
                        'use_playwright': use_playwright,
                        'competitor_config': comp,
                    },
                    dont_filter=True,
                )

    def parse_list_page(self, response):
        source = response.meta.get('source', '')
        use_playwright = response.meta.get('use_playwright', False)
        competitor_config = response.meta.get('competitor_config', {})

        product_links = self._extract_product_links(response, competitor_config)
        logger.info(
            f"[{source}] 列表页发现 {len(product_links)} 个商品链接"
        )

        for link in product_links:
            yield response.follow(
                url=link,
                callback=self.parse_product_page,
                meta={
                    'source': source,
                    'use_playwright': use_playwright,
                    'competitor_config': competitor_config,
                },
            )

        next_page = self._extract_next_page(response, competitor_config)
        if next_page:
            yield response.follow(
                url=next_page,
                callback=self.parse_list_page,
                meta={
                    'source': source,
                    'use_playwright': use_playwright,
                    'competitor_config': competitor_config,
                },
            )

    def parse_product_page(self, response):
        source = response.meta.get('source', '')
        competitor_config = response.meta.get('competitor_config', {})

        item = self._extract_product_info(response, source, competitor_config)
        if item:
            yield item

    def _extract_product_links(self, response, config):
        links = []

        selectors = [
            'a[href*="/product"]',
            'a[href*="/goods"]',
            'a[href*="/item"]',
            'a.product-link',
            'a.goods-link',
            '.product-item a',
            '.goods-item a',
            '.item a',
        ]

        for sel in selectors:
            elements = response.css(sel)
            for el in elements:
                href = el.attrib.get('href', '')
                if href:
                    full_url = urljoin(response.url, href)
                    if self._is_product_url(full_url, config):
                        links.append(full_url)

        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        return unique_links

    def _is_product_url(self, url, config):
        patterns = [
            r'/product/\d+',
            r'/goods/\d+',
            r'/item/\d+',
            r'\.html?',
            r'/p/\d+',
            r'/detail/',
        ]
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _extract_next_page(self, response, config):
        next_selectors = [
            'a.next::attr(href)',
            'a.next-page::attr(href)',
            'a.pagination-next::attr(href)',
            '.next a::attr(href)',
            'li.next a::attr(href)',
        ]

        for sel in next_selectors:
            next_url = response.css(sel).get()
            if next_url:
                return urljoin(response.url, next_url)

        return None

    def _extract_product_info(self, response, source, config):
        item = ProductItem()

        item['url'] = response.url
        item['source'] = source

        product_id = self._extract_product_id(response, config)
        if not product_id:
            raw_id = f"{source}:{response.url}"
            product_id = hashlib.md5(raw_id.encode()).hexdigest()
        item['product_id'] = product_id

        item['name'] = self._extract_text(response, [
            'h1::text',
            '.product-title::text',
            '.goods-title::text',
            '.item-title::text',
            '[class*="title"]::text',
        ])

        item['brand'] = self._extract_text(response, [
            '.brand::text',
            '.product-brand::text',
            '[class*="brand"]::text',
            'meta[property="product:brand"]::attr(content)',
        ])

        item['category'] = self._extract_text(response, [
            '.category::text',
            '.product-category::text',
            '[class*="category"]::text',
        ])

        item['image_url'] = self._extract_image(response)

        item['current_price'] = self._extract_price(response, [
            '.price::text',
            '.current-price::text',
            '.sale-price::text',
            '[class*="price"]::text',
            'meta[property="product:price:amount"]::attr(content)',
        ])

        item['original_price'] = self._extract_price(response, [
            '.original-price::text',
            '.market-price::text',
            '.old-price::text',
            '[class*="original"] [class*="price"]::text',
            '[class*="market"] [class*="price"]::text',
        ])

        item['currency'] = self._extract_currency(response)

        item['in_stock'] = self._extract_stock_status(response)

        item['is_on_promotion'] = self._detect_promotion(response)
        item['promotion_info'] = self._extract_promotion_info(response)
        item['promotion_type'] = self._classify_promotion_type(
            item['promotion_info']
        )

        item['rating'] = self._extract_rating(response)
        item['review_count'] = self._extract_review_count(response)
        item['seller'] = self._extract_text(response, [
            '.seller::text',
            '.shop-name::text',
            '[class*="seller"]::text',
            '[class*="shop"]::text',
        ])

        item['sku'] = self._extract_text(response, [
            '.sku::text',
            '[class*="sku"]::text',
            'meta[property="product:sku"]::attr(content)',
        ])

        return item

    def _extract_product_id(self, response, config):
        patterns = [
            r'/product/(\d+)',
            r'/goods/(\d+)',
            r'/item/(\d+)',
            r'/p/(\d+)',
            r'id[=:]\s*["\']?(\d+)',
            r'sku[=:]\s*["\']?(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, response.url, re.IGNORECASE)
            if match:
                return match.group(1)

        text_selectors = [
            '.product-id::text',
            '[class*="product-id"]::text',
            '[class*="goods-id"]::text',
        ]
        for sel in text_selectors:
            value = response.css(sel).get()
            if value and value.strip():
                return value.strip()

        return None

    def _extract_text(self, response, selectors):
        for sel in selectors:
            value = response.css(sel).get()
            if value and value.strip():
                return value.strip()
        return None

    def _extract_price(self, response, selectors):
        for sel in selectors:
            value = response.css(sel).get()
            if value:
                price = self._parse_price(value)
                if price is not None:
                    return price
        return None

    def _parse_price(self, text):
        if not text:
            return None
        text = text.strip()
        patterns = [
            r'[\d,]+\.?\d*',
            r'¥\s*([\d,]+\.?\d*)',
            r'￥\s*([\d,]+\.?\d*)',
            r'\$\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    price_str = match.group(1) if match.groups() else match.group(0)
                    price_str = price_str.replace(',', '')
                    return float(price_str)
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_currency(self, response):
        text = response.text[:5000]
        if '¥' in text or '￥' in text or 'CNY' in text.upper():
            return 'CNY'
        if '$' in text or 'USD' in text.upper():
            return 'USD'
        if '€' in text or 'EUR' in text.upper():
            return 'EUR'
        if '£' in text or 'GBP' in text.upper():
            return 'GBP'
        return 'CNY'

    def _extract_stock_status(self, response):
        stock_texts = [
            '.stock::text',
            '.stock-status::text',
            '[class*="stock"]::text',
            '[class*="inventory"]::text',
        ]
        for sel in stock_texts:
            value = response.css(sel).get()
            if value:
                value = value.lower()
                if any(w in value for w in ['out', '售罄', '缺货', '无货']):
                    return False
                if any(w in value for w in ['in', '有货', '现货', '充足']):
                    return True

        add_to_cart = response.css('.add-to-cart, .buy-btn, [class*="cart"]')
        if add_to_cart:
            disabled = add_to_cart.attrib.get('disabled', '')
            if disabled or 'disabled' in add_to_cart.attrib.get('class', ''):
                return False
            return True

        return None

    def _detect_promotion(self, response):
        text = response.text[:10000].lower()
        promo_keywords = SPIDER_CONFIG.get('promo_keywords', [])
        for keyword in promo_keywords:
            if keyword.lower() in text:
                return True

        promo_elements = [
            '.promotion',
            '.promo',
            '.discount',
            '.coupon',
            '[class*="promo"]',
            '[class*="discount"]',
            '[class*="coupon"]',
        ]
        for sel in promo_elements:
            if response.css(sel):
                return True

        return False

    def _extract_promotion_info(self, response):
        promo_selectors = [
            '.promotion-info::text',
            '.promo-text::text',
            '.discount-info::text',
            '[class*="promo"]::text',
            '[class*="discount"]::text',
            '[class*="coupon"]::text',
        ]
        for sel in promo_selectors:
            value = response.css(sel).get()
            if value and value.strip():
                return value.strip()
        return None

    def _classify_promotion_type(self, promo_info):
        if not promo_info:
            return None

        promo_info_lower = promo_info.lower()
        type_map = {
            'discount': ['折扣', '折', 'discount', '%', 'off'],
            'coupon': ['券', 'coupon', 'voucher'],
            'flash_sale': ['秒杀', '限时', 'flash', 'timed'],
            'buy_get': ['买赠', '买一送一', 'buy', 'get', 'free'],
            'full_reduction': ['满减', '满', 'full', 'reduce'],
            'bundle': ['套餐', '组合', 'bundle', 'combo'],
        }

        for ptype, keywords in type_map.items():
            if any(kw in promo_info_lower for kw in keywords):
                return ptype

        return 'general'

    def _extract_image(self, response):
        img_selectors = [
            '.product-image img::attr(src)',
            '.main-image::attr(src)',
            'img.product-img::attr(src)',
            'meta[property="og:image"]::attr(content)',
        ]
        for sel in img_selectors:
            value = response.css(sel).get()
            if value:
                return value
        return None

    def _extract_rating(self, response):
        rating_selectors = [
            '.rating::text',
            '.score::text',
            '[class*="rating"]::text',
            '[class*="score"]::text',
            'meta[itemprop="ratingValue"]::attr(content)',
        ]
        for sel in rating_selectors:
            value = response.css(sel).get()
            if value:
                match = re.search(r'[\d.]+', value)
                if match:
                    try:
                        return float(match.group(0))
                    except ValueError:
                        continue
        return None

    def _extract_review_count(self, response):
        review_selectors = [
            '.review-count::text',
            '.comment-count::text',
            '[class*="review"] [class*="count"]::text',
            '[class*="comment"] [class*="count"]::text',
            '[class*="ratingCount"]::text',
        ]
        for sel in review_selectors:
            value = response.css(sel).get()
            if value:
                match = re.search(r'[\d,]+', value)
                if match:
                    try:
                        return int(match.group(0).replace(',', ''))
                    except ValueError:
                        continue
        return None