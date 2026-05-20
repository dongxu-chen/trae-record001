"""
UBI驾驶行为定价模型
支持动态热加载
"""


def calculate_premium(engine, policy_data=None):
    """
    UBI保费计算函数
    
    Args:
        engine: ZeroCopyPricingEngine实例
        policy_data: 保单数据（可选）
    """
    if engine.backend == "polars":
        df = engine.df
        
        base_premium = df.with_columns(
            (df['insured_amount'] * 0.005).alias('base_premium')
        )
        
        mileage_discount = (10000 - df['annual_mileage']) / 10000 * 0.1
        mileage_discount = mileage_discount.clip_min(0)
        
        driving_years_bonus = (df['driving_years'] / 20).clip_max(1.0) * 0.1
        
        hard_accel_surcharge = (df['hard_acceleration_count'] - 5).clip_min(0) / 100 * 0.05
        hard_brake_surcharge = (df['hard_braking_count'] - 5).clip_min(0) / 100 * 0.05
        
        safe_score_bonus = (df['safe_driving_score'] - 60) / 40 * 0.15
        safe_score_bonus = safe_score_bonus.clip_min(0)
        
        final_multiplier = (
            1.0
            - mileage_discount
            - driving_years_bonus
            - safe_score_bonus
            + hard_accel_surcharge
            + hard_brake_surcharge
        )
        
        df = df.with_columns(
            base_premium=base_premium,
            mileage_discount=mileage_discount,
            driving_years_bonus=driving_years_bonus,
            safe_score_bonus=safe_score_bonus,
            final_multiplier=final_multiplier,
            final_premium=base_premium * final_multiplier
        )
        
        engine.df = df
    else:
        df = engine.df
        df['base_premium'] = df['insured_amount'] * 0.005
        
        mileage_ratio = (10000 - df['annual_mileage']) / 10000
        df['mileage_discount'] = mileage_ratio.clip(0, 0.1)
        
        driving_years_ratio = df['driving_years'] / 20
        df['driving_years_bonus'] = driving_years_ratio.clip(0, 0.1)
        
        hard_accel_ratio = (df['hard_acceleration_count'] - 5).clip(0) / 100
        df['hard_accel_surcharge'] = hard_accel_ratio * 0.05
        
        hard_brake_ratio = (df['hard_braking_count'] - 5).clip(0) / 100
        df['hard_brake_surcharge'] = hard_brake_ratio * 0.05
        
        safe_score_ratio = (df['safe_driving_score'] - 60) / 40
        df['safe_score_bonus'] = safe_score_ratio.clip(0, 0.15)
        
        df['final_multiplier'] = (
            1.0
            - df['mileage_discount']
            - df['driving_years_bonus']
            - df['safe_score_bonus']
            + df['hard_accel_surcharge']
            + df['hard_brake_surcharge']
        )
        
        df['final_premium'] = df['base_premium'] * df['final_multiplier']
    
    return engine.first()


def get_model_info():
    return {
        "name": "UBI驾驶行为定价模型",
        "version": "1.0.0",
        "description": "基于行驶里程、驾驶习惯的UBI定价模型",
        "factors": [
            "annual_mileage",
            "hard_acceleration_count",
            "hard_braking_count",
            "safe_driving_score",
            "driving_years"
        ]
    }
