import random
import json
from datetime import datetime, timedelta
import logging
import uuid
from config import Config

logger = logging.getLogger(__name__)


class MockDataGenerator:
    def __init__(self):
        self.weibo_contents = [
            "今天的天气真好，心情也跟着好起来了！",
            "这个产品真的太差劲了，客服态度也不好，很失望。",
            "刚刚看完这部电影，强烈推荐给大家，太感人了。",
            "公司新出的政策真让人无语，完全不考虑员工感受。",
            "今天学习了很多新知识，感觉很充实。",
            "这家餐厅的菜品味道一般，价格还很贵，不推荐。",
            "终于拿到了心心念念的证书，太开心了！",
            "这个事件的官方回应太敷衍了，大家都很不满。",
            "今天和朋友聚会玩得很开心，希望以后常聚。",
            "最近工作压力好大，感觉快撑不住了。",
            "这个新功能太好用了，开发团队辛苦了！",
            "这次活动组织得很混乱，体验很差。",
            "分享一个很棒的学习资源，希望对大家有帮助。",
            "又是被内卷的一天，什么时候是个头啊。",
            "今天做了一个很重要的决定，希望是对的。",
            "这个品牌的质量越来越差了，不会再买了。",
            "感谢所有帮助过我的人，谢谢你们！",
            "这个项目的进度严重滞后，大家都很焦虑。",
            "周末去爬山了，风景好美，心情舒畅。",
            "这个消息太突然了，一时难以接受。"
        ]
        
        self.twitter_contents = [
            "Just had an amazing experience! Highly recommend to everyone.",
            "Terrible service, will never use this company again. So disappointed.",
            "Breaking: Major announcement expected later today.",
            "Love this new feature! Great job team!",
            "This is so frustrating, why does this always happen?",
            "Feeling grateful today for all the opportunities I've had.",
            "Just finished reading this incredible book, changed my perspective.",
            "The quality has really gone downhill lately, not happy.",
            "Excited to announce our new product launch next week!",
            "This situation is getting out of hand, need action now.",
            "Beautiful day outside, perfect for a walk in the park.",
            "Customer service was unhelpful and rude. Avoid at all costs.",
            "Just learned something new today, never stop learning!",
            "This policy change is going to affect so many people negatively.",
            "Congratulations to the team on a successful launch!",
            "The wait time is ridiculous, been waiting for hours.",
            "Working on something exciting, can't wait to share more!",
            "This is exactly what we needed, thank you for listening.",
            "Disappointed with the lack of communication from leadership.",
            "Today was a good day, feeling positive about the future."
        ]
        
        self.forum_contents = [
            "兄弟们，这个游戏新版本太香了！",
            "求助，有人遇到过这种情况吗？已经困扰我很久了。",
            "理性讨论，这次事件到底谁对谁错？",
            "分享一个实用的小技巧，亲测有效！",
            "这波操作我给满分，太厉害了！",
            "建议大家避雷，这家店真的很坑。",
            "终于解决了这个问题，感谢论坛的各位大佬！",
            "有没有和我一样觉得这个设计很反人类的？",
            "新人报道，请多关照！",
            "这个话题热度太高了，到处都在讨论。",
            "实测对比，A比B确实好用很多。",
            "心态崩了，努力了这么久还是失败了。",
            "纯路人，说句公道话...",
            "这个方案不错，可行性很高。",
            "又是被割韭菜的一天，唉。",
            "感谢楼主分享，学到了很多！",
            "这个瓜我吃完了，总结一下...",
            "建议加精，这篇帖子质量很高。",
            "有没有懂行的帮忙看看，这是什么情况？",
            "今天运气真好，抽中了大奖！"
        ]
        
        self.authors = [
            "阳光少年", "快乐小猫", "追梦人", "夜空星辰", "清风徐来",
            "快乐每一天", "小确幸", "奋斗青年", "生活记录者", "时光旅人",
            "knowledge_seeker", "happy_user", "tech_enthusiast", "casual_observer",
            "forum_member", "helpful_hand", "newbie_2024", "experienced_user",
            "数码爱好者", "美食探店", "旅行达人", "职场老兵", "学生党"
        ]
        
        self.platforms = ['weibo', 'twitter', 'hupu', 'zhihu', 'tieba']
    
    def generate_post(self, platform=None, count=1, time_range_hours=24):
        if platform:
            platforms = [platform]
        else:
            platforms = self.platforms
        
        posts = []
        for _ in range(count):
            selected_platform = random.choice(platforms)
            
            if selected_platform == 'weibo':
                content = random.choice(self.weibo_contents)
            elif selected_platform == 'twitter':
                content = random.choice(self.twitter_contents)
            else:
                content = random.choice(self.forum_contents)
            
            now = datetime.utcnow()
            random_offset = random.uniform(0, time_range_hours * 3600)
            timestamp = now - timedelta(seconds=random_offset)
            
            post = {
                'platform': selected_platform,
                'post_id': f'{selected_platform}_{uuid.uuid4().hex[:12]}',
                'content': content,
                'author': random.choice(self.authors),
                'author_id': f'user_{uuid.uuid4().hex[:8]}',
                'post_url': f'https://example.com/post/{uuid.uuid4().hex}',
                'timestamp': timestamp.isoformat(),
                'likes': random.randint(0, 10000),
                'shares': random.randint(0, 5000),
                'comments': random.randint(0, 2000),
                'views': random.randint(100, 100000),
                'raw_data': json.dumps({'generated': True, 'seed': random.randint(0, 10000)}, ensure_ascii=False),
                'collected_at': now.isoformat()
            }
            
            posts.append(post)
        
        return posts if count > 1 else posts[0]
    
    def generate_batch(self, count=100, platform_distribution=None):
        if not platform_distribution:
            platform_distribution = {
                'weibo': 0.3,
                'twitter': 0.25,
                'hupu': 0.15,
                'zhihu': 0.15,
                'tieba': 0.15
            }
        
        posts = []
        for platform, weight in platform_distribution.items():
            platform_count = int(count * weight)
            posts.extend(self.generate_post(platform=platform, count=platform_count))
        
        random.shuffle(posts)
        return posts
    
    def generate_propagation_path(self, root_post_id, depth=3, platform='weibo'):
        paths = []
        current_node = f'user_{uuid.uuid4().hex[:8]}'
        
        for d in range(depth):
            num_children = random.randint(1, 5)
            for _ in range(num_children):
                target_node = f'user_{uuid.uuid4().hex[:8]}'
                path = {
                    'root_post_id': root_post_id,
                    'platform': platform,
                    'source_node': current_node,
                    'target_node': target_node,
                    'depth': d + 1,
                    'propagation_time': (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat(),
                    'content_snippet': random.choice([
                        "转发了", "评论了", "点赞了", "分享了", "@了好友"
                    ])
                }
                paths.append(path)
            
            if random.random() < 0.7 and num_children > 0:
                current_node = random.choice([p['target_node'] for p in paths[-num_children:]])
        
        return paths
