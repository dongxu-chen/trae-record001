from feast import FeatureService
from features import user_stats_fv, ad_stats_fv, context_stats_fv

ctr_prediction_service = FeatureService(
    name="ctr_prediction_service",
    features=[
        user_stats_fv,
        ad_stats_fv,
        context_stats_fv,
    ],
    tags={"description": "CTR预估特征服务，包含用户、广告和上下文特征"},
)
