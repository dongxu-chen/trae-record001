import scrapy
from datetime import datetime, timedelta
import json
import logging
from .base_spider import BaseSocialSpider
from config import Config

logger = logging.getLogger(__name__)


class TwitterSpider(BaseSocialSpider):
    name = 'twitter'
    allowed_domains = ['twitter.com', 'x.com']
    
    def __init__(self, keywords=None, max_pages=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords or Config.TWITTER_SEARCH_KEYWORDS
        self.max_pages = max_pages
        
    def start_requests(self):
        for keyword in self.keywords:
            url = f'https://twitter.com/search?q={keyword}&f=live'
            yield scrapy.Request(url, callback=self.parse_search, meta={'keyword': keyword})
    
    def parse_search(self, response):
        keyword = response.meta.get('keyword')
        logger.info(f"Parsing Twitter search for '{keyword}'")
        
        tweets = response.css('article')
        for tweet in tweets:
            try:
                tweet_id = tweet.css('::attr(data-tweet-id)').get()
                if not tweet_id:
                    continue
                
                content = tweet.css('div[lang]::text').getall()
                content = ' '.join([t.strip() for t in content if t.strip()])
                
                author = tweet.css('span::text').get()
                author_handle = tweet.css('a[href^="/"]::attr(href)').get()
                if author_handle:
                    author_id = author_handle.lstrip('/')
                
                time_text = tweet.css('time::attr(datetime)').get()
                timestamp = datetime.fromisoformat(time_text.replace('Z', '+00:00')) if time_text else datetime.utcnow()
                
                stats = tweet.css('div[data-testid] span::text').getall()
                replies = self._parse_stat(stats, 0)
                retweets = self._parse_stat(stats, 1)
                likes = self._parse_stat(stats, 2)
                views = self._parse_stat(stats, 3)
                
                tweet_url = f'https://twitter.com/i/web/status/{tweet_id}'
                
                item = self.create_post_item(
                    platform='twitter',
                    post_id=tweet_id,
                    content=content,
                    author=author,
                    author_id=author_id if 'author_id' in locals() else '',
                    post_url=tweet_url,
                    timestamp=timestamp.isoformat(),
                    likes=likes,
                    shares=retweets,
                    comments=replies,
                    views=views,
                    raw_data=json.dumps({'keyword': keyword}, ensure_ascii=False)
                )
                
                yield item
                
            except Exception as e:
                logger.error(f"Error parsing Twitter tweet: {e}")
                continue
        
        next_cursor = response.css('div[data-testid="ScrollTimeline"] + div::attr(data-cursor)').get()
        if next_cursor and response.meta.get('page', 1) < self.max_pages:
            next_url = f'https://twitter.com/i/api/2/search/adaptive.json?cursor={next_cursor}'
            yield scrapy.Request(next_url, callback=self.parse_search, 
                               meta={'keyword': keyword, 'page': response.meta.get('page', 1) + 1})
    
    def _parse_stat(self, stats, index):
        if len(stats) > index:
            text = stats[index]
            digits = ''.join([c for c in text if c.isdigit()])
            if digits:
                num = int(digits)
                if 'K' in text or 'k' in text:
                    num *= 1000
                elif 'M' in text or 'm' in text:
                    num *= 1000000
                return num
        return 0
