from feast import Entity
from feast.types import String, Int64

user = Entity(
    name="user",
    join_keys=["user_id"],
    description="用户实体",
    tags={"domain": "user_profile"}
)

ad = Entity(
    name="ad",
    join_keys=["ad_id"],
    description="广告实体",
    tags={"domain": "ad_inventory"}
)

context = Entity(
    name="context",
    join_keys=["context_id"],
    description="上下文实体",
    tags={"domain": "context"}
)
