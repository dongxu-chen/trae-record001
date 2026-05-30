import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from data_store import DataStore
from models import BookReviewSummary, Book


class ReviewSummarizer:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self._init_book_knowledge()

    def _init_book_knowledge(self):
        self.book_summary_templates = {
            '科幻': {
                'summary_template': '{author}的代表作《{title}》是一部{genres}小说，以其宏大的世界观和深刻的思想内涵著称。故事围绕{core_theme}展开，探讨了{key_idea}等重要议题。',
                'pros': ['想象力丰富，世界观宏大', '思想深刻，引人深思', '情节紧凑，悬念迭起', '科学设定严谨'],
                'cons': ['部分科学概念可能较难理解', '节奏有时偏慢', '人物塑造相对薄弱'],
                'themes': ['科技与人性', '未来社会', '宇宙探索', '人类命运'],
                'audience': ['科幻爱好者', '思想深度追求者', '理工科背景读者']
            },
            '悬疑': {
                'summary_template': '{author}的《{title}》是一部精彩的{genres}作品。故事以{core_theme}为主线，层层递进的悬念和出人意料的转折让读者欲罢不能。',
                'pros': ['悬念设置精妙', '情节反转出人意料', '逻辑推理严密', '节奏把控到位'],
                'cons': ['部分情节可能过于刻意', '结局可能不符合所有人预期', '有时过于强调技巧'],
                'themes': ['人性善恶', '真相探寻', '正义与邪恶', '心理博弈'],
                'audience': ['推理小说爱好者', '喜欢挑战智商的读者', '悬疑控']
            },
            '经典': {
                'summary_template': '{author}的《{title}》是文学史上的经典之作。这部作品以{core_theme}为核心，深刻反映了{key_idea}，至今仍具有重要的现实意义。',
                'pros': ['文学价值极高', '思想内涵深刻', '人物形象丰满', '语言优美'],
                'cons': ['时代背景可能有距离感', '阅读门槛相对较高', '节奏可能偏慢'],
                'themes': ['人性本质', '社会现实', '历史变迁', '文化传承'],
                'audience': ['文学爱好者', '深度阅读者', '学生群体']
            },
            '奇幻': {
                'summary_template': '{author}在《{title}》中构建了一个令人神往的{genres}世界。故事讲述了{core_theme}的壮丽冒险，充满了魔法、勇气与成长。',
                'pros': ['世界观设定精彩', '想象力天马行空', '英雄主义主题激励人心', '系列作品延展性强'],
                'cons': ['篇幅较长', '部分设定可能复杂', '非奇幻爱好者可能难以代入'],
                'themes': ['勇气与成长', '善与恶的对决', '友情与忠诚', '自我发现'],
                'audience': ['奇幻文学粉丝', '青少年读者', '喜欢冒险故事的读者']
            },
            '治愈': {
                'summary_template': '{author}的《{title}》是一部温暖治愈的{genres}作品。通过{core_theme}，传递了{key_idea}的人生哲理，给读者带来心灵的慰藉。',
                'pros': ['温暖治愈', '情感细腻', '充满正能量', '适合放松阅读'],
                'cons': ['情节可能偏平淡', '戏剧冲突较弱', '不喜欢慢节奏的读者可能觉得无聊'],
                'themes': ['生活的美好', '人际关系', '自我接纳', '希望与勇气'],
                'audience': ['压力大的上班族', '需要心理慰藉的读者', '喜欢温情故事的人']
            },
            '历史': {
                'summary_template': '{author}的《{title}》是一部优秀的{genres}著作。作者以独特的视角解读了{core_theme}，让读者重新审视{key_idea}。',
                'pros': ['史料详实', '观点新颖', '叙事生动', '发人深省'],
                'cons': ['内容可能较为厚重', '需要一定背景知识', '学术性较强'],
                'themes': ['历史规律', '文明演进', '制度变迁', '人类智慧'],
                'audience': ['历史爱好者', '知识分子', '终身学习者']
            },
        }

        self.book_specific_knowledge = {
            1: {
                'title': '三体',
                'core_theme': '外星文明与地球文明的碰撞',
                'key_idea': '宇宙黑暗森林法则与人类命运',
                'custom_pros': ['宇宙社会学设定惊艳', '刘慈欣式宏大叙事', '对科学与哲学的深度融合'],
                'custom_cons': ['部分女性角色塑造有争议', '科学术语较多']
            },
            2: {
                'title': '黑暗森林',
                'core_theme': '宇宙社会学公理与星际战争',
                'key_idea': '黑暗森林法则的完整阐述',
                'custom_pros': ['罗辑人设饱满', '面壁者计划悬念迭起', '宇宙图景震撼人心'],
                'custom_cons': ['节奏前慢后快', '部分设定需要消化']
            },
            3: {
                'title': '死神永生',
                'core_theme': '文明的终极命运与时间的尽头',
                'key_idea': '宇宙维度与时间的终极思考',
                'custom_pros': ['云天明童话惊艳', '结局意境深远', '哲学思辨达到顶峰'],
                'custom_cons': ['程心角色争议大', '部分情节略理想化']
            },
            11: {
                'title': '哈利波特与魔法石',
                'core_theme': '少年魔法师的成长与冒险',
                'key_idea': '爱与勇气战胜黑暗',
                'custom_pros': ['魔法世界引人入胜', '人物成长线清晰', '适合各年龄段'],
                'custom_cons': ['第一部相对简单', '反派设定略显模式化']
            },
        }

    def _extract_rating_sentiment(self, book_id: int) -> Dict[str, float]:
        ratings = self.data_store.get_book_ratings(book_id)
        if not ratings:
            return {'positive': 0.6, 'neutral': 0.3, 'negative': 0.1}

        rating_values = list(ratings.values())
        avg_rating = np.mean(rating_values)
        std_rating = np.std(rating_values) if len(rating_values) > 1 else 0

        positive = min(1.0, avg_rating / 5.0 + 0.2)
        negative = max(0.0, 1.0 - positive - 0.3)
        neutral = 1.0 - positive - negative

        return {
            'positive': positive,
            'neutral': neutral,
            'negative': negative,
            'avg_rating': avg_rating,
            'controversy': std_rating
        }

    def _get_primary_genre(self, book: Book) -> str:
        genre_priority = ['科幻', '悬疑', '推理', '奇幻', '历史', '经典', '治愈', '温情', '哲学']
        for genre in genre_priority:
            if genre in book.genres:
                return genre
        return book.genres[0] if book.genres else '经典'

    def generate_summary(self, book_id: int, force_regenerate: bool = False) -> BookReviewSummary:
        if not force_regenerate:
            existing = self.data_store.get_review_summary(book_id)
            if existing:
                return existing

        book = self.data_store.get_book(book_id)
        if not book:
            raise ValueError(f"书籍 {book_id} 不存在")

        primary_genre = self._get_primary_genre(book)
        template = self.book_summary_templates.get(primary_genre, self.book_summary_templates['经典'])
        specific = self.book_specific_knowledge.get(book_id, {})

        core_theme = specific.get('core_theme', f"{book.genres[0] if book.genres else '精彩'}故事")
        key_idea = specific.get('key_idea', '深刻的人生哲理')

        genres_str = '、'.join(book.genres)
        summary = template['summary_template'].format(
            author=book.author,
            title=book.title,
            genres=genres_str,
            core_theme=core_theme,
            key_idea=key_idea
        )

        sentiment = self._extract_rating_sentiment(book_id)

        pros = template['pros'].copy()
        if 'custom_pros' in specific:
            pros = specific['custom_pros'] + pros[:2]

        cons = template['cons'].copy()
        if 'custom_cons' in specific:
            cons = specific['custom_cons'] + cons[:1]

        if sentiment['avg_rating'] >= 4.5:
            pros.append(f"读者评价极高，平均评分{sentiment['avg_rating']:.1f}分")
        elif sentiment['avg_rating'] >= 4.0:
            pros.append(f"读者评价良好，平均评分{sentiment['avg_rating']:.1f}分")

        if sentiment['controversy'] >= 1.0:
            cons.append('读者评价分歧较大')

        key_themes = template['themes']
        target_audience = template['audience']

        if sentiment['positive'] > 0.7:
            summary += f" 该书广受好评，{sentiment['positive']*100:.0f}%的读者给出了正面评价。"
        elif sentiment['negative'] > 0.3:
            summary += f" 该书评价存在一定分歧，部分读者持有不同看法。"

        summary_obj = BookReviewSummary(
            book_id=book_id,
            summary=summary,
            pros=pros[:5],
            cons=cons[:3],
            key_themes=key_themes[:4],
            target_audience=target_audience[:3],
            generated_at=datetime.now()
        )

        self.data_store.save_review_summary(summary_obj)
        return summary_obj

    def batch_generate_summaries(self, book_ids: Optional[List[int]] = None) -> List[BookReviewSummary]:
        if book_ids is None:
            book_ids = self.data_store.get_all_books()

        summaries = []
        for book_id in book_ids:
            try:
                summary = self.generate_summary(book_id)
                summaries.append(summary)
            except Exception as e:
                print(f"生成书籍 {book_id} 摘要失败: {e}")
        return summaries

    def get_comparative_summary(self, book_ids: List[int]) -> Dict:
        if len(book_ids) < 2:
            raise ValueError("至少需要2本书才能比较")

        summaries = [self.generate_summary(bid) for bid in book_ids]
        books = [self.data_store.get_book(bid) for bid in book_ids]

        all_pros = set()
        all_cons = set()
        all_themes = set()

        for s in summaries:
            all_pros.update(s.pros)
            all_cons.update(s.cons)
            all_themes.update(s.key_themes)

        common_pros = set.intersection(*[set(s.pros) for s in summaries])
        common_themes = set.intersection(*[set(s.key_themes) for s in summaries])

        return {
            'books': [
                {
                    'book_id': b.book_id,
                    'title': b.title,
                    'author': b.author,
                    'avg_rating': b.avg_rating,
                    'genres': b.genres
                } for b in books if b
            ],
            'common_pros': list(common_pros),
            'common_themes': list(common_themes),
            'unique_points': [
                {
                    'book_id': s.book_id,
                    'unique_pros': [p for p in s.pros if p not in common_pros],
                    'unique_cons': s.cons
                } for s in summaries
            ],
            'recommendation_basis': {
                'highest_rated': max(books, key=lambda b: b.avg_rating if b else 0).title if books else None,
                'most_accessible': min(books, key=lambda b: len(b.genres) if b else 0).title if books else None
            }
        }

    def get_reading_guide(self, book_id: int) -> Dict:
        summary = self.generate_summary(book_id)
        book = self.data_store.get_book(book_id)
        if not book:
            raise ValueError(f"书籍 {book_id} 不存在")

        primary_genre = self._get_primary_genre(book)

        difficulty_map = {
            '哲学': 5,
            '历史': 4,
            '经典': 4,
            '社科': 4,
            '科幻': 3,
            '奇幻': 2,
            '悬疑': 2,
            '治愈': 1,
            '童话': 1
        }
        difficulty = difficulty_map.get(primary_genre, 3)

        time_estimate = {
            1: '3-5天',
            2: '5-7天',
            3: '7-10天',
            4: '10-15天',
            5: '15-20天'
        }

        reading_tips = {
            '科幻': ['注意理解科学设定，可以边读边查资料', '关注作者的核心思想表达', '建议配合书评讨论加深理解'],
            '悬疑': ['注意细节和伏笔', '尝试自己推理真相', '读完后回顾关键情节'],
            '经典': ['了解时代背景有助于理解', '可以参考相关文学评论', '建议做读书笔记'],
            '奇幻': ['先熟悉世界观设定', '关注人物成长曲线', '可以搭配地图或设定集阅读'],
            '治愈': ['适合碎片化阅读', '心情不好时读效果更佳', '可以反复品味'],
        }

        return {
            'book_id': book_id,
            'title': book.title,
            'author': book.author,
            'summary': summary.summary,
            'reading_difficulty': difficulty,
            'estimated_reading_time': time_estimate[difficulty],
            'target_audience': summary.target_audience,
            'key_themes': summary.key_themes,
            'reading_tips': reading_tips.get(primary_genre, ['按个人节奏阅读', '享受阅读过程']),
            'pros': summary.pros,
            'cons': summary.cons,
            'is_series': book.series_id is not None,
            'series_info': None
        }
