import scrapy
from datetime import datetime
import json
import logging
from urllib.parse import urljoin
from .base_spider import BaseSocialSpider
from config import Config

logger = logging.getLogger(__name__)


class ForumSpider(BaseSocialSpider):
    name = 'forum'
    allowed_domains = ['bbs.hupu.com', 'zhihu.com', 'tieba.baidu.com']
    
    def __init__(self, urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls = urls or Config.FORUM_URLS
        
    def start_requests(self):
        for url in self.urls:
            yield scrapy.Request(url, callback=self.parse_forum, meta={'base_url': url})
    
    def parse_forum(self, response):
        base_url = response.meta.get('base_url')
        
        if 'hupu.com' in base_url:
            yield from self.parse_hupu(response)
        elif 'zhihu.com' in base_url:
            yield from self.parse_zhihu(response)
        elif 'tieba.baidu.com' in base_url:
            yield from self.parse_tieba(response)
    
    def parse_hupu(self, response):
        logger.info("Parsing Hupu forum")
        
        threads = response.css('li.post-list-item')
        for thread in threads:
            try:
                title = thread.css('a.title::text').get()
                thread_url = thread.css('a.title::attr(href)').get()
                
                if not title or not thread_url:
                    continue
                
                if not thread_url.startswith('http'):
                    thread_url = urljoin('https://bbs.hupu.com', thread_url)
                
                author = thread.css('span.author a::text').get()
                reply_count = thread.css('span.replies::text').get()
                view_count = thread.css('span.views::text').get()
                time_text = thread.css('span.time::text').get()
                
                timestamp = self._parse_hupu_time(time_text)
                
                post_id = thread_url.split('/')[-1].replace('.html', '')
                
                item = self.create_post_item(
                    platform='hupu',
                    post_id=f'hupu_{post_id}',
                    content=title,
                    author=author,
                    author_id='',
                    post_url=thread_url,
                    timestamp=timestamp.isoformat() if timestamp else datetime.utcnow().isoformat(),
                    likes=0,
                    shares=0,
                    comments=self._parse_int(reply_count),
                    views=self._parse_int(view_count),
                    raw_data=json.dumps({'forum': 'hupu'}, ensure_ascii=False)
                )
                
                yield item
                
            except Exception as e:
                logger.error(f"Error parsing Hupu thread: {e}")
                continue
    
    def parse_zhihu(self, response):
        logger.info("Parsing Zhihu")
        
        questions = response.css('div.QuestionItem, div.List-item')
        for question in questions:
            try:
                title = question.css('h2.ContentItem-title a::text').get()
                if not title:
                    title = question.css('a.QuestionItem-title::text').get()
                
                question_url = question.css('h2.ContentItem-title a::attr(href)').get()
                if not question_url:
                    question_url = question.css('a.QuestionItem-title::attr(href)').get()
                
                if not title or not question_url:
                    continue
                
                if not question_url.startswith('http'):
                    question_url = urljoin('https://www.zhihu.com', question_url)
                
                author = question.css('div.AuthorInfo a::text').get()
                vote_count = question.css('button.VoteButton--up::text').get()
                answer_count = question.css('meta[itemprop="answerCount"]::attr(content)').get()
                
                post_id = question_url.split('/')[-1]
                
                item = self.create_post_item(
                    platform='zhihu',
                    post_id=f'zhihu_{post_id}',
                    content=title,
                    author=author,
                    author_id='',
                    post_url=question_url,
                    timestamp=datetime.utcnow().isoformat(),
                    likes=self._parse_int(vote_count),
                    shares=0,
                    comments=self._parse_int(answer_count),
                    views=0,
                    raw_data=json.dumps({'forum': 'zhihu'}, ensure_ascii=False)
                )
                
                yield item
                
            except Exception as e:
                logger.error(f"Error parsing Zhihu question: {e}")
                continue
    
    def parse_tieba(self, response):
        logger.info("Parsing Baidu Tieba")
        
        threads = response.css('li.j_thread_list')
        for thread in threads:
            try:
                title = thread.css('a.j_th_tit::text').get()
                thread_url = thread.css('a.j_th_tit::attr(href)').get()
                
                if not title or not thread_url:
                    continue
                
                if not thread_url.startswith('http'):
                    thread_url = urljoin('https://tieba.baidu.com', thread_url)
                
                author = thread.css('span.tb_icon_author a::text').get()
                reply_count = thread.css('span.threadlist_rep_num::text').get()
                
                post_id = thread_url.split('/')[-1]
                
                item = self.create_post_item(
                    platform='tieba',
                    post_id=f'tieba_{post_id}',
                    content=title,
                    author=author,
                    author_id='',
                    post_url=thread_url,
                    timestamp=datetime.utcnow().isoformat(),
                    likes=0,
                    shares=0,
                    comments=self._parse_int(reply_count),
                    views=0,
                    raw_data=json.dumps({'forum': 'tieba'}, ensure_ascii=False)
                )
                
                yield item
                
            except Exception as e:
                logger.error(f"Error parsing Tieba thread: {e}")
                continue
    
    def _parse_hupu_time(self, time_str):
        if not time_str:
            return None
        time_str = time_str.strip()
        try:
            if len(time_str) > 5 and '-' in time_str:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            else:
                return datetime.strptime(time_str, '%H:%M')
        except:
            return datetime.utcnow()
    
    def _parse_int(self, text):
        if not text:
            return 0
        digits = ''.join([c for c in text if c.isdigit()])
        return int(digits) if digits else 0
