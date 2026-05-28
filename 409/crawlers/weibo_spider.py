import scrapy
from datetime import datetime, timedelta
import json
import logging
from .base_spider import BaseSocialSpider
from config import Config

logger = logging.getLogger(__name__)


class WeiboSpider(BaseSocialSpider):
    name = 'weibo'
    allowed_domains = ['weibo.com', 's.weibo.com']
    
    def __init__(self, keywords=None, max_pages=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords or Config.WEIBO_SEARCH_KEYWORDS
        self.max_pages = max_pages
        
    def start_requests(self):
        for keyword in self.keywords:
            for page in range(1, self.max_pages + 1):
                url = f'https://s.weibo.com/weibo?q={keyword}&page={page}'
                yield scrapy.Request(url, callback=self.parse_search, meta={'keyword': keyword, 'page': page})
    
    def parse_search(self, response):
        keyword = response.meta.get('keyword')
        page = response.meta.get('page')
        
        logger.info(f"Parsing Weibo search for '{keyword}' page {page}")
        
        cards = response.css('div.card-wrap')
        for card in cards:
            try:
                post_id = card.css('::attr(mid)').get()
                if not post_id:
                    continue
                
                content = card.css('p.txt::text').getall()
                content = ''.join([t.strip() for t in content if t.strip()])
                
                author = card.css('a.name::text').get()
                author_id = card.css('a.name::attr(href)').get()
                if author_id:
                    author_id = author_id.split('/')[-1]
                
                time_text = card.css('div.from a::text').get()
                timestamp = self._parse_time(time_text)
                
                stats = card.css('div.card-act li a::text').getall()
                likes = self._parse_number(stats[2] if len(stats) > 2 else '0')
                comments = self._parse_number(stats[1] if len(stats) > 1 else '0')
                shares = self._parse_number(stats[0] if len(stats) > 0 else '0')
                
                post_url = card.css('div.from a::attr(href)').get()
                if post_url and not post_url.startswith('http'):
                    post_url = 'https:' + post_url
                
                item = self.create_post_item(
                    platform='weibo',
                    post_id=post_id,
                    content=content,
                    author=author,
                    author_id=author_id,
                    post_url=post_url,
                    timestamp=timestamp.isoformat() if timestamp else datetime.utcnow().isoformat(),
                    likes=likes,
                    shares=shares,
                    comments=comments,
                    raw_data=json.dumps({'keyword': keyword}, ensure_ascii=False)
                )
                
                yield item
                
            except Exception as e:
                logger.error(f"Error parsing Weibo card: {e}")
                continue
        
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_search, meta={'keyword': keyword})
    
    def _parse_time(self, time_str):
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        if '分钟前' in time_str:
            minutes = int(''.join([c for c in time_str if c.isdigit()]) or 0)
            return datetime.utcnow() - timedelta(minutes=minutes)
        elif '小时前' in time_str:
            hours = int(''.join([c for c in time_str if c.isdigit()]) or 0)
            return datetime.utcnow() - timedelta(hours=hours)
        elif '昨天' in time_str:
            return datetime.utcnow() - timedelta(days=1)
        else:
            try:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            except:
                try:
                    return datetime.strptime(time_str, '%m-%d %H:%M')
                except:
                    return datetime.utcnow()
    
    def _parse_number(self, text):
        if not text:
            return 0
        digits = ''.join([c for c in text if c.isdigit()])
        if not digits:
            return 0
        num = int(digits)
        if '万' in text:
            num *= 10000
        return num
