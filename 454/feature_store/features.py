from feast import FeatureView, Field, FileSource
from feast.types import Float32, Int32, Int64
from datetime import timedelta
import os
from entities import user, ad, context

data_path = os.path.join(os.path.dirname(__file__), "data")

user_stats_source = FileSource(
    path=os.path.join(data_path, "user_stats.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

ad_stats_source = FileSource(
    path=os.path.join(data_path, "ad_stats.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

context_stats_source = FileSource(
    path=os.path.join(data_path, "context_stats.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

user_stats_fv = FeatureView(
    name="user_stats",
    entities=[user],
    ttl=timedelta(days=1),
    schema=[
        Field(name="user_age", dtype=Int32),
        Field(name="user_gender", dtype=Int32),
        Field(name="user_level", dtype=Int32),
        Field(name="user_consumption_level", dtype=Int32),
        Field(name="user_active_days_7d", dtype=Int32),
        Field(name="user_click_count_7d", dtype=Int32),
        Field(name="user_impression_count_7d", dtype=Int32),
        Field(name="user_ctr_7d", dtype=Float32),
        Field(name="user_category_preference", dtype=Int32),
        Field(name="user_city_level", dtype=Int32),
        Field(name="user_device_type", dtype=Int32),
        Field(name="user_registration_days", dtype=Int32),
    ],
    online=True,
    source=user_stats_source,
    tags={"team": "ctr_team"},
)

ad_stats_fv = FeatureView(
    name="ad_stats",
    entities=[ad],
    ttl=timedelta(days=1),
    schema=[
        Field(name="ad_category", dtype=Int32),
        Field(name="ad_campaign_id", dtype=Int32),
        Field(name="ad_advertiser_id", dtype=Int32),
        Field(name="ad_ctr_history", dtype=Float32),
        Field(name="ad_click_count_7d", dtype=Int32),
        Field(name="ad_impression_count_7d", dtype=Int32),
        Field(name="ad_price", dtype=Float32),
        Field(name="ad_position", dtype=Int32),
        Field(name="ad_creative_type", dtype=Int32),
        Field(name="ad_is_new", dtype=Int32),
    ],
    online=True,
    source=ad_stats_source,
    tags={"team": "ctr_team"},
)

context_stats_fv = FeatureView(
    name="context_stats",
    entities=[context],
    ttl=timedelta(days=1),
    schema=[
        Field(name="context_hour", dtype=Int32),
        Field(name="context_day_of_week", dtype=Int32),
        Field(name="context_is_weekend", dtype=Int32),
        Field(name="context_traffic_source", dtype=Int32),
        Field(name="context_network_type", dtype=Int32),
        Field(name="context_app_version", dtype=Int32),
        Field(name="context_scene_id", dtype=Int32),
        Field(name="context_page_id", dtype=Int32),
    ],
    online=True,
    source=context_stats_source,
    tags={"team": "ctr_team"},
)
