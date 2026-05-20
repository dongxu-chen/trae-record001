from dataclasses import dataclass, asdict
from typing import Optional
import json
import time


@dataclass
class BaseMessage:
    timestamp: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class ViewerMessage(BaseMessage):
    viewer_id: str
    action: str


@dataclass
class OnlineMessage(BaseMessage):
    online_count: int


@dataclass
class LikeMessage(BaseMessage):
    user_id: str
    count: int


@dataclass
class TransactionMessage(BaseMessage):
    order_id: str
    user_id: str
    product_id: str
    product_name: str
    amount: float
    quantity: int


@dataclass
class ProductClickMessage(BaseMessage):
    user_id: str
    product_id: str
    product_name: str
    duration: int


@dataclass
class DanmuMessage(BaseMessage):
    user_id: str
    user_name: str
    content: str
    is_vip: bool = False


DANMU_POOL = [
    "主播好帅！",
    "这个产品多少钱？",
    "有没有优惠啊",
    "已下单，期待发货",
    "主播能详细介绍一下吗",
    "这个颜色好看",
    "质量怎么样",
    "有没有运费险",
    "主播声音好好听",
    "秒杀秒杀！",
    "太划算了吧",
    "我要抢！",
    "还有货吗",
    "直播间的宝宝们点点赞",
    "关注主播不迷路",
    "主播推荐的都好",
    "这个适合敏感肌吗",
    "能试一下吗",
    "主播今天真好看",
    "买它买它！",
    "性价比很高",
    "上次买的很好用",
    "回购来了",
    "发货快吗",
    "有赠品吗",
    "主播辛苦了",
    "666666",
    "冲冲冲！",
    "抢不到啊",
    "再上点库存吧",
    "质量太差了",
    "物流很慢",
    "不推荐购买",
    "客服态度不好",
    "有点贵啊",
]

PRODUCT_POOL = [
    {"id": "P001", "name": "高端护肤精华液", "price": 299.0},
    {"id": "P002", "name": "时尚连衣裙", "price": 459.0},
    {"id": "P003", "name": "智能蓝牙耳机", "price": 199.0},
    {"id": "P004", "name": "保温杯", "price": 89.0},
    {"id": "P005", "name": "运动跑鞋", "price": 359.0},
    {"id": "P006", "name": "口红礼盒", "price": 168.0},
    {"id": "P007", "name": "家用榨汁机", "price": 249.0},
    {"id": "P008", "name": "颈椎按摩仪", "price": 399.0},
    {"id": "P009", "name": "防晒霜套装", "price": 128.0},
    {"id": "P010", "name": "儿童学习桌", "price": 899.0},
]
