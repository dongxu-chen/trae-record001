import json
import os
from datetime import datetime


class PriceCrawlerPipeline:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def open_spider(self, spider):
        self.items = []

    def close_spider(self, spider):
        if not self.items:
            return
        filename = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2, default=str)

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item
