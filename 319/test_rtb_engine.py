import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def reset_redis_singleton():
    try:
        from src.redis_client import RedisClient
        RedisClient._instance = None
        RedisClient._pool = None
    except ImportError:
        pass

reset_redis_singleton()

_redis_patch = patch('src.redis_client.RedisClient')
_mock_redis = _redis_patch.start()
_mock_redis_instance = MagicMock()
_mock_redis.return_value = _mock_redis_instance

def setup_default_mocks():
    import random as rnd
    _mock_redis_instance.get_budget.return_value = None
    _mock_redis_instance.set_budget.return_value = True
    _mock_redis_instance.get_remaining_budget.return_value = 1000.0
    _mock_redis_instance.get_hourly_remaining.return_value = 100.0
    _mock_redis_instance.get_pace.return_value = 1.0
    _mock_redis_instance.get_cached_prediction.return_value = None
    _mock_redis_instance.cache_prediction.return_value = True
    _mock_redis_instance.check_all_frequency_limits.return_value = (True, [])
    _mock_redis_instance.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "6h": 2, "24h": 5, "7d": 10})
    _mock_redis_instance.get_frequency.return_value = 1
    _mock_redis_instance.get_sliding_window_count.return_value = 1
    _mock_redis_instance.get_sliding_window_timestamps.return_value = [1234567890000, 1234567891000]
    _mock_redis_instance.add_impression_sliding_window.return_value = (1, True, 0)
    _mock_redis_instance.record_impression_sliding_window.return_value = ({"1h": 1, "6h": 2, "24h": 5, "7d": 10}, {"1h": True, "6h": True, "24h": True, "7d": True})
    _mock_redis_instance.increment_frequency.return_value = True
    _mock_redis_instance._get_sliding_window_key.return_value = "freq:sw:user1:ad1:1h"
    _mock_redis_instance.record_bid.return_value = True
    _mock_redis_instance.get_bid_history.return_value = None
    _mock_redis_instance.consume_budget.return_value = True
    _mock_redis_instance.get_user_profile.return_value = None
    _mock_redis_instance.save_user_profile.return_value = True
    _mock_redis_instance.clear_all.return_value = True
    _mock_redis_instance.delete_key.return_value = True
    _mock_redis_instance.get_all_keys.return_value = []
    _mock_redis_instance.consume_hourly_budget.return_value = True
    _mock_redis_instance.set_hourly_budget.return_value = True
    _mock_redis_instance.update_pace.return_value = True
    
    def mock_get_layer_budget(layer_name, campaign_id):
        return {
            'allocated': 1000.0,
            'spent': rnd.uniform(0, 500),
            'impressions': rnd.randint(0, 100),
            'clicks': rnd.randint(0, 10),
        }
    _mock_redis_instance.get_layer_budget.side_effect = mock_get_layer_budget
    
    def mock_consume_layer_budget(layer_name, campaign_id, amount):
        return True
    _mock_redis_instance.consume_layer_budget.side_effect = mock_consume_layer_budget
    
    _mock_redis_instance.record_layer_impression.return_value = True
    _mock_redis_instance.record_layer_click.return_value = True
    _mock_redis_instance.record_layer_cost.return_value = True

setup_default_mocks()


class TestTrafficLayer(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.traffic_layer import TrafficLayer
        self.traffic_layer = TrafficLayer()

    def test_classify_high_value(self):
        layer_name, layer_info = self.traffic_layer.classify(0.08, 0.05)
        self.assertEqual(layer_name, "S")
        self.assertEqual(layer_info["bid_multiplier"], 1.5)

    def test_classify_medium_value(self):
        layer_name, layer_info = self.traffic_layer.classify(0.03, 0.02)
        self.assertEqual(layer_name, "A")
        self.assertEqual(layer_info["bid_multiplier"], 1.2)

    def test_classify_low_value(self):
        layer_name, layer_info = self.traffic_layer.classify(0.005, 0.001)
        self.assertEqual(layer_name, "C")
        self.assertEqual(layer_info["bid_multiplier"], 0.7)

    def test_get_layer_multiplier(self):
        self.assertEqual(self.traffic_layer.get_layer_multiplier("S"), 1.5)
        self.assertEqual(self.traffic_layer.get_layer_multiplier("A"), 1.2)
        self.assertEqual(self.traffic_layer.get_layer_multiplier("B"), 1.0)
        self.assertEqual(self.traffic_layer.get_layer_multiplier("C"), 0.7)
        self.assertEqual(self.traffic_layer.get_layer_multiplier("unknown"), 1.0)

    def test_get_layer_budget_share(self):
        shares = sum([self.traffic_layer.get_layer_budget_share(l["name"]) for l in self.traffic_layer.layers])
        self.assertAlmostEqual(shares, 1.0)


class TestDataGenerator(unittest.TestCase):
    def setUp(self):
        from src.data_generator import DataGenerator
        self.generator = DataGenerator()

    def test_generate_user_profile(self):
        profile = self.generator.generate_user_profile("user_001")
        self.assertIn("user_id", profile)
        self.assertIn("user_gender", profile)
        self.assertIn("user_age_group", profile)
        self.assertIn("user_city", profile)
        self.assertEqual(profile["user_id"], "user_001")

    def test_generate_context(self):
        context = self.generator.generate_context()
        self.assertIn("device_type", context)
        self.assertIn("os_type", context)
        self.assertIn("time_slot", context)
        self.assertIn("ip", context)

    def test_generate_ad_info(self):
        ad_info = self.generator.generate_ad_info("ad_001")
        self.assertIn("ad_id", ad_info)
        self.assertIn("ad_category", ad_info)
        self.assertIn("ad_ctr_history", ad_info)
        self.assertEqual(ad_info["ad_id"], "ad_001")

    def test_generate_bid_request(self):
        request = self.generator.generate_bid_request(
            user_id="user_001",
            ad_id="ad_001",
            campaign_id="test_campaign"
        )
        self.assertIn("request_id", request)
        self.assertEqual(request["user_id"], "user_001")
        self.assertEqual(request["ad_id"], "ad_001")
        self.assertEqual(request["campaign_id"], "test_campaign")
        self.assertIn("user_profile", request)
        self.assertIn("context", request)
        self.assertIn("ad_info", request)

    def test_generate_training_data(self):
        X, ctr_y, cvr_y = self.generator.generate_training_data(sample_count=100, feature_dim=50)
        self.assertEqual(X.shape, (100, 50))
        self.assertEqual(ctr_y.shape, (100,))
        self.assertEqual(cvr_y.shape, (100,))
        self.assertTrue(np.all((ctr_y == 0) | (ctr_y == 1)))
        self.assertTrue(np.all((cvr_y == 0) | (cvr_y == 1)))


class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        self.extractor = FeatureExtractor()

    def test_hash_feature(self):
        idx1 = self.extractor._hash_feature("gender", "M")
        idx2 = self.extractor._hash_feature("gender", "M")
        self.assertEqual(idx1, idx2)
        self.assertTrue(0 <= idx1 < self.extractor.feature_dim)

    def test_extract_categorical_features(self):
        data = {"user_gender": "M", "user_age_group": "25-34"}
        features = self.extractor._extract_categorical_features(data)
        self.assertEqual(features.shape, (self.extractor.feature_dim,))
        self.assertTrue(np.any(features > 0))

    def test_extract_numerical_features(self):
        data = {"user_income": 10000, "user_active_days": 100}
        features = self.extractor._extract_numerical_features(data)
        self.assertEqual(features.shape, (self.extractor.feature_dim,))
        self.assertTrue(np.any(features > 0))

    def test_extract_cross_features(self):
        data = {"user_interest": "tech", "ad_category": "electronics"}
        features = self.extractor._extract_cross_features(data)
        self.assertEqual(features.shape, (self.extractor.feature_dim,))

    def test_extract_features(self):
        user_profile = {"user_gender": "M", "user_age_group": "25-34"}
        context = {"device_type": "mobile"}
        ad_info = {"ad_category": "electronics"}
        features = self.extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, self.extractor.feature_dim))

    def test_get_feature_hash(self):
        user_profile = {"user_gender": "M"}
        context = {"device_type": "mobile"}
        ad_info = {"ad_category": "electronics"}
        hash1 = self.extractor.get_feature_hash(user_profile, context, ad_info)
        hash2 = self.extractor.get_feature_hash(user_profile, context, ad_info)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)


class TestPredictionModel(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import PredictionModel
        self.model = PredictionModel()

    def test_model_initialization(self):
        self.assertIsNotNone(self.model.ctr_model)
        self.assertIsNotNone(self.model.cvr_model)

    def test_predict(self):
        user_profile = {"user_gender": "M", "user_age_group": "25-34", "user_income": 10000}
        context = {"device_type": "mobile", "time_slot": "morning"}
        ad_info = {"ad_category": "electronics", "ad_ctr_history": 0.05}
        ctr, cvr = self.model.predict(user_profile, context, ad_info)
        self.assertTrue(0 <= ctr <= 1)
        self.assertTrue(0 <= cvr <= 1)


class TestFrequencyController(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.frequency_control import FrequencyController
        self.frequency_controller = FrequencyController()
        self.frequency_controller.redis_client.get_sliding_window_count.side_effect = None
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 1

    def test_can_show_allowed(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "24h": 5})
        allowed, violated, counts = self.frequency_controller.can_show("user1", "ad1")
        self.assertTrue(allowed)
        self.assertEqual(violated, [])
        self.assertIn("1h", counts)

    def test_can_show_violated(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (False, ["1h"], {"1h": 5, "24h": 5})
        allowed, violated, counts = self.frequency_controller.can_show("user1", "ad1")
        self.assertFalse(allowed)
        self.assertIn("1h", violated)

    def test_get_frequency_decay_penalty_high_frequency(self):
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 5
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [
            int(time.time() * 1000) - 60000 * i for i in range(5)
        ]
        penalty = self.frequency_controller.get_frequency_decay_penalty("user1", "ad1")
        self.assertTrue(0 < penalty < 1)

    def test_get_frequency_decay_penalty_low_frequency(self):
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 0
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = []
        penalty = self.frequency_controller.get_frequency_decay_penalty("user1", "ad1")
        self.assertEqual(penalty, 1.0)

    def test_get_bid_adjustment_allowed(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "24h": 5})
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 1
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [
            int(time.time() * 1000) - 60000
        ]
        adjustment = self.frequency_controller.get_bid_adjustment("user1", "ad1")
        self.assertTrue(0 < adjustment <= 1)

    def test_get_bid_adjustment_blocked(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (False, ["1h"], {"1h": 5, "24h": 5})
        adjustment = self.frequency_controller.get_bid_adjustment("user1", "ad1")
        self.assertEqual(adjustment, 0.0)


class TestBudgetManager(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.budget_manager import BudgetManager
        self.budget_manager = BudgetManager("test_campaign")
        self.budget_manager.pid_enabled = False

    def test_get_budget_utilization_rate(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        rate = self.budget_manager.get_budget_utilization_rate()
        self.assertAlmostEqual(rate, 0.3)

    def test_get_budget_utilization_rate_zero(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 0.0,
            'spent': 0.0
        }
        rate = self.budget_manager.get_budget_utilization_rate()
        self.assertEqual(rate, 0.0)

    def test_get_pace_adjustment_emergency(self):
        self.budget_manager.redis_client.get_pace.return_value = 1.0
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 9000.0
        }
        adjustment = self.budget_manager.get_pace_adjustment()
        self.assertTrue(0 < adjustment < 1)

    def test_get_pace_adjustment_fast_pace(self):
        self.budget_manager.redis_client.get_pace.return_value = 1.5
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        adjustment = self.budget_manager.get_pace_adjustment()
        self.assertTrue(0.5 <= adjustment < 1)

    def test_get_pace_adjustment_slow_pace(self):
        self.budget_manager.redis_client.get_pace.return_value = 0.5
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 1000.0
        }
        adjustment = self.budget_manager.get_pace_adjustment()
        self.assertTrue(1 < adjustment <= 1.5)

    def test_get_bid_multiplier_high_utilization(self):
        self.budget_manager.redis_client.get_pace.return_value = 1.0
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 9500.0
        }
        multiplier = self.budget_manager.get_bid_multiplier()
        self.assertTrue(0 < multiplier < 0.5)

    def test_get_bid_multiplier_low_utilization(self):
        self.budget_manager.redis_client.get_pace.return_value = 1.0
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 1000.0
        }
        multiplier = self.budget_manager.get_bid_multiplier()
        self.assertEqual(multiplier, 1.0)

    def test_clamp_bid(self):
        self.assertEqual(self.budget_manager.clamp_bid(0.005), 0.01)
        self.assertEqual(self.budget_manager.clamp_bid(15.0), 10.0)
        self.assertEqual(self.budget_manager.clamp_bid(5.0), 5.0)

    def test_can_consume_true(self):
        self.budget_manager.redis_client.get_remaining_budget.return_value = 1000.0
        self.budget_manager.redis_client.get_hourly_remaining.return_value = 100.0
        result, details = self.budget_manager.can_consume(50.0)
        self.assertTrue(result)
        self.assertEqual(details["requested_amount"], 50.0)
        self.assertEqual(details["remaining_total"], 1000.0)
        self.assertEqual(details["hourly_remaining"], 100.0)

    def test_can_consume_false_insufficient_total(self):
        self.budget_manager.redis_client.get_remaining_budget.return_value = 10.0
        self.budget_manager.redis_client.get_hourly_remaining.return_value = 100.0
        result, details = self.budget_manager.can_consume(50.0)
        self.assertFalse(result)
        self.assertEqual(details["remaining_total"], 10.0)

    def test_can_consume_false_insufficient_hourly(self):
        self.budget_manager.redis_client.get_remaining_budget.return_value = 1000.0
        self.budget_manager.redis_client.get_hourly_remaining.return_value = 10.0
        result, details = self.budget_manager.can_consume(50.0)
        self.assertFalse(result)
        self.assertEqual(details["hourly_remaining"], 10.0)

    def test_can_consume_false_negative_amount(self):
        self.budget_manager.redis_client.get_remaining_budget.return_value = 1000.0
        self.budget_manager.redis_client.get_hourly_remaining.return_value = 100.0
        result, details = self.budget_manager.can_consume(-10.0)
        self.assertFalse(result)

    def test_get_smooth_consumption_rate(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 500.0
        }
        rate = self.budget_manager.get_smooth_consumption_rate()
        self.assertTrue(0.5 <= rate <= 1.5)


class TestBidEngine(unittest.TestCase):
    def setUp(self):
        from src.bid_engine import BidRequest, BidResponse
        self.BidRequest = BidRequest
        self.BidResponse = BidResponse

    def test_bid_request_creation(self):
        bid_request = self.BidRequest(
            request_id="test_req_001",
            user_id="user_001",
            ad_id="ad_001",
            campaign_id="test_campaign",
            user_profile={"user_gender": "M", "user_age_group": "25-34"},
            context={"device_type": "mobile"},
            ad_info={"ad_category": "electronics"},
            floor_price=0.01,
            cpa_goal=10.0,
        )
        self.assertEqual(bid_request.request_id, "test_req_001")
        self.assertEqual(bid_request.user_id, "user_001")
        self.assertEqual(bid_request.floor_price, 0.01)

    def test_bid_response_to_dict(self):
        response = self.BidResponse(
            request_id="req_001",
            bid_id="bid_001",
            success=True,
            bid_price=0.05,
            reason="SUCCESS",
            details={"ctr": 0.05}
        )
        resp_dict = response.to_dict()
        self.assertEqual(resp_dict["request_id"], "req_001")
        self.assertEqual(resp_dict["bid_id"], "bid_001")
        self.assertTrue(resp_dict["success"])
        self.assertEqual(resp_dict["bid_price"], 0.05)
        self.assertIn("timestamp", resp_dict)

    def test_calculate_base_bid_logic(self):
        ctr, cvr = 0.05, 0.02
        cpa_goal = 10.0
        expected_value = ctr * cvr * cpa_goal
        base_bid = expected_value * 0.5
        self.assertAlmostEqual(base_bid, 0.005)


class TestConfig(unittest.TestCase):
    def test_config_loading(self):
        from config import config
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.redis)
        self.assertIsNotNone(config.kafka)
        self.assertIsNotNone(config.model)
        self.assertIsNotNone(config.budget)
        self.assertIsNotNone(config.frequency)
        self.assertIsNotNone(config.traffic)

    def test_budget_config(self):
        from config import config
        self.assertEqual(config.budget.min_bid, 0.01)
        self.assertEqual(config.budget.max_bid, 10.0)
        self.assertTrue(config.budget.total_budget > 0)

    def test_frequency_config(self):
        from config import config
        self.assertIn("1h", config.frequency.limits)
        self.assertIn("24h", config.frequency.limits)

    def test_traffic_config(self):
        from config import config
        layer_names = [l["name"] for l in config.traffic.layers]
        self.assertIn("S", layer_names)
        self.assertIn("A", layer_names)
        self.assertIn("B", layer_names)
        self.assertIn("C", layer_names)


class TestEnhancedFeatures(unittest.TestCase):
    def test_temporal_feature_extraction(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        extractor = FeatureExtractor()
        
        user_profile = {"user_gender": "M", "user_age_group": "25-34", "user_city": "beijing"}
        context = {
            "device_type": "mobile",
            "time_slot": "evening_peak",
            "hour_of_day": "h20",
            "day_of_week": "d5",
            "is_weekend": "yes",
            "is_holiday": "no",
            "hour": 20,
            "minute": 30,
        }
        ad_info = {"ad_category": "electronics", "ad_position": "top", "ad_placement": "feed"}
        
        features = extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, extractor.feature_dim))
        self.assertTrue(np.any(features > 0))

    def test_location_feature_extraction(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        extractor = FeatureExtractor()
        
        user_profile = {
            "user_gender": "M",
            "user_age_group": "25-34",
            "user_city": "beijing",
            "city_tier": "tier1",
            "province": "beijing",
        }
        context = {"device_type": "mobile"}
        ad_info = {"ad_category": "electronics"}
        
        features = extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, extractor.feature_dim))

    def test_rfm_feature_extraction(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        extractor = FeatureExtractor()
        
        user_profile = {
            "user_gender": "M",
            "user_age_group": "25-34",
            "user_last_visit_days": 5,
            "user_active_days": 100,
            "user_total_spend": 5000,
        }
        context = {"device_type": "mobile"}
        ad_info = {"ad_category": "electronics"}
        
        features = extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, extractor.feature_dim))

    def test_ad_position_feature_extraction(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        extractor = FeatureExtractor()
        
        user_profile = {"user_gender": "M", "user_age_group": "25-34"}
        context = {"device_type": "mobile"}
        ad_info = {
            "ad_category": "electronics",
            "ad_position": "top",
            "ad_placement": "feed",
            "ad_position_score": 1.0,
            "ad_creative_type": "video",
        }
        
        features = extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, extractor.feature_dim))

    def test_cross_feature_with_time_location(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.prediction_model import FeatureExtractor
        extractor = FeatureExtractor()
        
        user_profile = {
            "user_gender": "M",
            "user_age_group": "25-34",
            "user_city": "shanghai",
            "city_tier": "tier1",
            "user_interest": "tech",
        }
        context = {
            "device_type": "mobile",
            "time_slot": "morning_peak",
            "hour_of_day": "h8",
            "day_of_week": "d1",
        }
        ad_info = {
            "ad_category": "electronics",
            "ad_position": "top",
        }
        
        features = extractor.extract_features(user_profile, context, ad_info)
        self.assertEqual(features.shape, (1, extractor.feature_dim))


class TestAdaptivePID(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.budget_manager import AdaptivePIDController
        self.pid = AdaptivePIDController(
            kp_init=1.0,
            ki_init=0.1,
            kd_init=0.05,
            adaptation_rate=0.1,
        )
        self.pid.tuning_interval = 0

    def test_pid_initialization(self):
        self.assertEqual(self.pid.kp, 1.0)
        self.assertEqual(self.pid.ki, 0.1)
        self.assertEqual(self.pid.kd, 0.05)
        self.assertEqual(self.pid.kp_init, 1.0)

    def test_pid_calculate_output(self):
        actual_spend = 0.3
        target_spend = 0.5
        day_progress = 0.5
        
        output, info = self.pid.calculate_output(actual_spend, target_spend, day_progress)
        
        self.assertTrue(0.3 <= output <= 1.8)
        self.assertIn("error", info)
        self.assertIn("kp", info)
        self.assertIn("ki", info)
        self.assertIn("kd", info)
        self.assertIn("output", info)
        self.assertIn("mae", info)

    def test_pid_adaptation_high_error(self):
        initial_kp = self.pid.kp
        initial_ki = self.pid.ki
        
        for i in range(15):
            self.pid.calculate_output(0.1, 0.5, 0.5)
        
        self.assertGreater(self.pid.kp, initial_kp)
        self.assertGreater(self.pid.ki, initial_ki)

    def test_pid_adaptation_oscillation(self):
        initial_kd = self.pid.kd
        
        for i in range(15):
            error = 0.2 if i % 2 == 0 else -0.2
            self.pid.calculate_output(0.3 + error, 0.3, 0.5)
        
        self.assertGreater(self.pid.kd, initial_kd)

    def test_pid_reset(self):
        for i in range(10):
            self.pid.calculate_output(0.1, 0.5, 0.5)
        
        self.pid.reset()
        
        self.assertEqual(self.pid.kp, self.pid.kp_init)
        self.assertEqual(self.pid.ki, self.pid.ki_init)
        self.assertEqual(self.pid.kd, self.pid.kd_init)
        self.assertEqual(self.pid.integral, 0.0)
        self.assertEqual(len(self.pid.errors), 0)

    def test_pid_get_parameters(self):
        params = self.pid.get_parameters()
        self.assertIn("kp", params)
        self.assertIn("ki", params)
        self.assertIn("kd", params)
        self.assertIn("kp_init", params)

    def test_pid_output_clamping(self):
        outputs = []
        for _ in range(10):
            output, _ = self.pid.calculate_output(0.0, 1.0, 0.5)
            outputs.append(output)
        
        for output in outputs:
            self.assertGreaterEqual(output, 0.3)
            self.assertLessEqual(output, 1.8)


class TestSlidingWindowFrequency(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.frequency_control import FrequencyController
        self.frequency_controller = FrequencyController()
        self.frequency_controller.redis_client.get_sliding_window_count.side_effect = None
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 1

    def test_sliding_window_can_show(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "24h": 5})
        allowed, violated, counts = self.frequency_controller.can_show("user1", "ad1")
        self.assertTrue(allowed)
        self.assertEqual(violated, [])
        self.assertIn("1h", counts)
        self.assertIn("24h", counts)

    def test_sliding_window_violated(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (False, ["1h"], {"1h": 5, "24h": 5})
        allowed, violated, counts = self.frequency_controller.can_show("user1", "ad1")
        self.assertFalse(allowed)
        self.assertIn("1h", violated)

    def test_record_impression_sliding_window(self):
        expected_counts = {"1h": 2, "6h": 3, "24h": 6, "7d": 11}
        expected_within = {"1h": True, "6h": True, "24h": True, "7d": True}
        self.frequency_controller.redis_client.record_impression_sliding_window.return_value = (expected_counts, expected_within)
        
        counts, within_limits = self.frequency_controller.record_impression("user1", "ad1")
        self.assertEqual(counts["1h"], 2)
        self.assertTrue(within_limits["1h"])

    def test_get_sliding_window_details(self):
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 3
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [1234567890000, 1234567891000, 1234567892000]
        
        details = self.frequency_controller.get_sliding_window_details("user1", "ad1", "24h")
        self.assertIn("24h", details)
        self.assertEqual(details["24h"]["count"], 3)
        self.assertIn("timestamps", details["24h"])
        self.assertIn("impressions_per_hour", details["24h"])

    def test_calculate_time_decay_penalty(self):
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 3
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [1234567890000]
        
        penalty = self.frequency_controller.calculate_time_decay_penalty("user1", "ad1")
        self.assertTrue(0.1 <= penalty <= 1.0)

    def test_frequency_forecast(self):
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 5
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [
            1234567890000, 1234567891000, 1234567892000, 1234567893000, 1234567894000
        ]
        
        forecast = self.frequency_controller.calculate_frequency_forecast("user1", "ad1", next_hours=24)
        self.assertIn("1h", forecast)
        self.assertIn("24h", forecast)
        for window_name, info in forecast.items():
            self.assertIn("current_count", info)
            self.assertIn("estimated_total", info)
            self.assertIn("will_exceed_limit", info)

    def test_get_optimal_bid_adjustment(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "24h": 5})
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 1
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [1234567890000]
        
        adjustment, details = self.frequency_controller.get_optimal_bid_adjustment(
            "user1", "ad1", 0.5, 0.05
        )
        self.assertTrue(0.0 <= adjustment <= 1.0)
        self.assertIn("allowed", details)
        self.assertIn("decay_penalty", details)
        self.assertIn("forecast_factor", details)

    def test_frequency_distribution(self):
        self.frequency_controller.redis_client.get_all_keys.return_value = [
            "freq:sw:user1:ad1:24h",
            "freq:sw:user2:ad1:24h",
            "freq:sw:user3:ad1:24h",
        ]
        self.frequency_controller.redis_client.get_sliding_window_count.side_effect = [1, 3, 5]
        
        distribution = self.frequency_controller.get_frequency_distribution("ad1", "24h")
        self.assertIsInstance(distribution, dict)
        self.assertEqual(sum(distribution.values()), 3)

    def test_get_frequency_summary(self):
        self.frequency_controller.redis_client.check_sliding_window_limits.return_value = (True, [], {"1h": 1, "24h": 5})
        self.frequency_controller.redis_client.get_sliding_window_count.return_value = 1
        self.frequency_controller.redis_client.get_sliding_window_timestamps.return_value = [1234567890000]
        
        summary = self.frequency_controller.get_user_frequency_summary("user1", "ad1")
        self.assertIn("user_id", summary)
        self.assertIn("allowed", summary)
        self.assertIn("current_counts", summary)
        self.assertIn("decay_penalty", summary)
        self.assertIn("window_details", summary)
        self.assertIn("frequency_forecast", summary)


class TestBudgetManagerWithPID(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.budget_manager import BudgetManager
        self.budget_manager = BudgetManager("test_campaign")

    def test_pid_controller_integration(self):
        self.assertIsNotNone(self.budget_manager.pid_controller)
        self.assertTrue(self.budget_manager.pid_enabled)

    def test_calculate_pid_adjustment(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        output, info = self.budget_manager.calculate_pid_adjustment()
        self.assertTrue(0.3 <= output <= 1.8)
        self.assertIn("error", info)
        self.assertIn("kp", info)

    def test_get_pid_status(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        status = self.budget_manager.get_pid_status()
        self.assertTrue(status["enabled"])
        self.assertIn("parameters", status)
        self.assertIn("last_output", status)
        self.assertIn("metrics", status)

    def test_pid_in_pace_adjustment(self):
        self.budget_manager.redis_client.get_pace.return_value = 1.0
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        adjustment = self.budget_manager.get_pace_adjustment()
        self.assertTrue(0.1 <= adjustment <= 1.8)

    def test_reset_pid_controller(self):
        initial_params = self.budget_manager.pid_controller.get_parameters()
        for _ in range(10):
            self.budget_manager.calculate_pid_adjustment()
        
        self.budget_manager.reset_pid_controller()
        
        reset_params = self.budget_manager.pid_controller.get_parameters()
        self.assertEqual(reset_params["kp"], initial_params["kp_init"])
        self.assertEqual(reset_params["ki"], initial_params["ki_init"])

    def test_budget_status_includes_pid(self):
        self.budget_manager.redis_client.get_budget.return_value = {
            'total': 10000.0,
            'spent': 3000.0
        }
        status = self.budget_manager.get_budget_status()
        self.assertIn("pid_status", status)
        self.assertIsNotNone(status["pid_status"])


class TestDataGeneratorEnhanced(unittest.TestCase):
    def setUp(self):
        from src.data_generator import DataGenerator
        self.generator = DataGenerator()

    def test_generate_user_profile_enhanced(self):
        profile = self.generator.generate_user_profile("user_001")
        self.assertIn("user_education", profile)
        self.assertIn("user_occupation", profile)
        self.assertIn("user_marital_status", profile)
        self.assertIn("city_tier", profile)
        self.assertIn("province", profile)
        self.assertIn("user_intent", profile)
        self.assertIn("purchase_intent", profile)
        self.assertIn("user_avg_session_duration", profile)
        self.assertIn("user_last_visit_days", profile)
        self.assertIn("price_sensitivity", profile)

    def test_generate_context_enhanced(self):
        context = self.generator.generate_context()
        self.assertIn("os_version", context)
        self.assertIn("hour_of_day", context)
        self.assertIn("day_of_week", context)
        self.assertIn("is_weekend", context)
        self.assertIn("is_holiday", context)
        self.assertIn("network_type", context)
        self.assertIn("carrier", context)
        self.assertIn("app_category", context)
        self.assertIn("content_category", context)
        self.assertIn("weather", context)
        self.assertIn("temperature_level", context)
        self.assertIn("hour", context)
        self.assertIn("minute", context)

    def test_generate_ad_info_enhanced(self):
        ad_info = self.generator.generate_ad_info("ad_001")
        self.assertIn("ad_placement", ad_info)
        self.assertIn("ad_position", ad_info)
        self.assertIn("ad_position_score", ad_info)
        self.assertIn("ad_creative_type", ad_info)
        self.assertIn("ad_impression_count", ad_info)
        self.assertIn("ad_click_count", ad_info)
        self.assertIn("ad_conversion_count", ad_info)


class TestExplorationEngine(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.exploration import ExplorationEngine, ExplorationStrategy, BiddingStrategy
        self.ExplorationStrategy = ExplorationStrategy
        self.ExplorationEngine = ExplorationEngine
        self.engine = ExplorationEngine(
            strategy=ExplorationStrategy.UCB,
            epsilon=0.2,
            min_trials_for_exploitation=10,
            ucb_c=2.0,
        )
    
    def test_initialization(self):
        self.assertEqual(self.engine.strategy, self.ExplorationStrategy.UCB)
        self.assertEqual(self.engine.epsilon, 0.2)
        self.assertGreater(len(self.engine.strategies), 0)
        self.assertIn("conservative", self.engine.strategies)
        self.assertIn("balanced", self.engine.strategies)
        self.assertIn("aggressive", self.engine.strategies)
    
    def test_default_strategies(self):
        strategy_names = self.engine.get_available_strategies()
        self.assertIn("conservative", strategy_names)
        self.assertIn("balanced", strategy_names)
        self.assertIn("aggressive", strategy_names)
        self.assertIn("explore_high_ctr", strategy_names)
        self.assertIn("explore_high_cvr", strategy_names)
    
    def test_add_custom_strategy(self):
        from src.exploration import BiddingStrategy
        custom = BiddingStrategy(
            name="custom_strategy",
            bid_multiplier=1.5,
            ctr_weight=2.0,
            is_exploratory=True,
        )
        self.engine.add_strategy(custom)
        self.assertIn("custom_strategy", self.engine.strategies)
    
    def test_select_strategy_ucb(self):
        for _ in range(20):
            name, strategy, details = self.engine.select_strategy()
            self.assertIn(name, self.engine.strategies)
            self.assertIn("is_exploration", details)
            self.assertIn("exploration_rate", details)
    
    def test_select_strategy_epsilon_greedy(self):
        from src.exploration import ExplorationStrategy
        self.engine.strategy = ExplorationStrategy.EPSILON_GREEDY
        self.engine.epsilon = 1.0
        
        name, strategy, details = self.engine.select_strategy()
        self.assertTrue(details["is_exploration"])
    
    def test_apply_strategy_to_bid(self):
        from src.exploration import BiddingStrategy
        strategy = BiddingStrategy(
            name="test",
            bid_multiplier=1.2,
            frequency_penalty_weight=0.8,
            budget_pace_weight=1.1,
            ctr_weight=1.5,
            cvr_weight=1.0,
        )
        
        adjusted = self.engine.apply_strategy_to_bid(
            base_bid=1.0,
            strategy=strategy,
            ctr=0.05,
            cvr=0.01,
            frequency_penalty=0.9,
            budget_pace=1.0,
            floor_price=0.01,
        )
        self.assertGreater(adjusted, 0)
        self.assertIsInstance(adjusted, float)
    
    def test_record_result(self):
        self.engine.record_result(
            strategy_name="balanced",
            reward=1.5,
            success=True,
            metadata={"bid": 1.0},
        )
        
        stats = self.engine.strategy_stats["balanced"]
        self.assertEqual(stats.trials, 1)
        self.assertEqual(stats.successes, 1)
        self.assertAlmostEqual(stats.mean_reward, 1.5)
    
    def test_ucb_exploration_bonus(self):
        self.engine.strategy_stats["balanced"].trials = 100
        self.engine.strategy_stats["balanced"].total_reward = 50.0
        self.engine.total_trials = 100
        
        self.engine.strategy_stats["explore_high_ctr"].trials = 5
        self.engine.strategy_stats["explore_high_ctr"].total_reward = 3.0
        
        name, _, _ = self.engine.select_strategy()
        self.assertIn(name, self.engine.strategies)
    
    def test_get_strategy_summary(self):
        for i in range(5):
            self.engine.select_strategy()
            self.engine.record_result("balanced", reward=float(i), success=i % 2 == 0)
        
        summary = self.engine.get_strategy_summary()
        self.assertIn("total_trials", summary)
        self.assertIn("best_strategy", summary)
        self.assertIn("strategies", summary)
        self.assertEqual(summary["total_trials"], 5)
    
    def test_get_top_strategies(self):
        strategies = ["balanced", "aggressive", "conservative"]
        for i, name in enumerate(strategies):
            for _ in range(10):
                self.engine.record_result(name, reward=float(i + 1), success=True)
        
        top = self.engine.get_top_strategies(top_n=3)
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0][0], "conservative")
    
    def test_epsilon_decay(self):
        initial_epsilon = self.engine.epsilon
        for _ in range(100):
            self.engine.select_strategy()
        
        self.assertLessEqual(self.engine.epsilon, initial_epsilon)
        self.assertGreaterEqual(self.engine.epsilon, self.engine.min_epsilon)
    
    def test_save_and_load_state(self):
        for i in range(5):
            self.engine.record_result("balanced", reward=float(i), success=True)
        
        state = self.engine.save_state()
        self.assertIn("total_trials", state)
        self.assertIn("strategies", state)
        
        new_engine = self.ExplorationEngine()
        new_engine.load_state(state)
        
        self.assertEqual(new_engine.strategy_stats["balanced"].trials, 5)
    
    def test_reset(self):
        for _ in range(10):
            self.engine.select_strategy()
            self.engine.record_result("balanced", 1.0, True)
        
        self.engine.reset()
        
        self.assertEqual(self.engine.total_trials, 0)
        self.assertEqual(self.engine.strategy_stats["balanced"].trials, 0)
    
    def test_thompson_sampling(self):
        from src.exploration import ExplorationStrategy
        self.engine.strategy = ExplorationStrategy.THOMPSON_SAMPLING
        
        for _ in range(10):
            self.engine.record_result("balanced", reward=1.0, success=True)
            self.engine.record_result("aggressive", reward=0.5, success=False)
        
        name, _, _ = self.engine.select_strategy()
        self.assertIn(name, self.engine.strategies)
    
    def test_boltzmann_selection(self):
        from src.exploration import ExplorationStrategy
        self.engine.strategy = ExplorationStrategy.BOLTZMANN
        self.engine.boltzmann_temperature = 0.5
        
        for _ in range(5):
            name, _, _ = self.engine.select_strategy()
            self.assertIn(name, self.engine.strategies)


class TestBidEngineWithExploration(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
        from src.bid_engine import BidEngine, BidRequest
        self.bid_engine = BidEngine("test_explore", enable_exploration=True)
        self.create_test_bid_request = lambda: BidRequest(
            request_id="test_req_1",
            user_id="user_123",
            ad_id="ad_456",
            campaign_id="test_explore",
            user_profile={"user_gender": "M", "user_age_group": "25-34", "user_city": "beijing"},
            context={"device_type": "mobile", "time_slot": "evening_peak"},
            ad_info={"ad_category": "electronics", "ad_position": "top"},
            floor_price=0.01,
            cpa_goal=10.0,
        )
    
    def test_exploration_enabled(self):
        self.assertTrue(self.bid_engine.enable_exploration)
        self.assertIsNotNone(self.bid_engine.exploration_engine)
    
    def test_process_bid_with_exploration(self):
        request = self.create_test_bid_request()
        response = self.bid_engine.process_bid(request)
        
        self.assertIsNotNone(response)
        if response.success:
            self.assertIn("strategy_name", response.details)
            self.assertIn("is_exploration", response.details)
    
    def test_apply_exploration_adjustment(self):
        adjusted, details = self.bid_engine._apply_exploration_adjustment(
            current_bid=1.0,
            ctr=0.05,
            cvr=0.01,
            frequency_penalty=0.9,
            budget_pace=1.0,
            floor_price=0.01,
        )
        self.assertGreater(adjusted, 0)
        self.assertIn("strategy_name", details)
    
    def test_record_exploration_result(self):
        self.bid_engine.record_exploration_result(
            strategy_name="balanced",
            bid_price=0.5,
            ctr=0.05,
            cvr=0.01,
            was_clicked=True,
            was_converted=False,
        )
        
        status = self.bid_engine.get_exploration_status()
        self.assertIn("strategies", status)
        self.assertGreater(status["strategies"]["balanced"]["trials"], 0)
    
    def test_get_exploration_status(self):
        status = self.bid_engine.get_exploration_status()
        self.assertIn("enabled", status)
        if status["enabled"]:
            self.assertIn("total_trials", status)
            self.assertIn("best_strategy", status)
    
    def test_engine_status_includes_exploration(self):
        engine_status = self.bid_engine.get_engine_status()
        self.assertIn("exploration_enabled", engine_status)
        self.assertTrue(engine_status["exploration_enabled"])


class TestAuctionSimulator(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
    
    def _create_simulator(self):
        from src.auction_simulator import AuctionSimulator
        from src.bid_engine import BidEngine
        bid_engine = BidEngine("sim_test", enable_exploration=True)
        return AuctionSimulator(
            bid_engine=bid_engine,
            num_competitors=3,
            random_seed=42,
        )
    
    def test_initialization(self):
        simulator = self._create_simulator()
        self.assertEqual(simulator.num_competitors, 3)
        self.assertEqual(len(simulator.competitors), 3)
        self.assertEqual(simulator.stats.total_auctions, 0)
    
    def test_competitor_bidding(self):
        simulator = self._create_simulator()
        bids = simulator._generate_competitor_bids(
            base_bid=1.0,
            ctr=0.05,
            cvr=0.01,
            floor_price=0.01,
        )
        self.assertEqual(len(bids), 3)
        for bid in bids:
            self.assertGreaterEqual(bid, 0.01)
            self.assertLessEqual(bid, 10.0)
    
    def test_run_single_auction(self):
        simulator = self._create_simulator()
        record = simulator.run_single_auction()
        
        self.assertIsNotNone(record)
        self.assertIn(record.result.value, ["won", "lost", "skipped"])
        self.assertIsInstance(record.our_bid, float)
        self.assertIsInstance(record.profit, float)
    
    def test_run_simulation(self):
        simulator = self._create_simulator()
        stats = simulator.run_simulation(num_auctions=10)
        
        self.assertEqual(stats.total_auctions, 10)
        self.assertEqual(stats.auctions_won + stats.auctions_lost + stats.auctions_skipped, 10)
        self.assertGreaterEqual(stats.total_cost, 0)
    
    def test_simulation_callback(self):
        simulator = self._create_simulator()
        callback_calls = []
        
        def callback(count, record, stats):
            callback_calls.append(count)
        
        simulator.run_simulation(num_auctions=20, callback=callback, batch_size=10)
        
        self.assertEqual(len(callback_calls), 2)
        self.assertEqual(callback_calls, [10, 20])
    
    def test_determine_click_and_conversion(self):
        simulator = self._create_simulator()
        
        clicked_count = 0
        converted_count = 0
        for _ in range(100):
            clicked, converted = simulator._determine_click_and_conversion(0.1, 0.05, 1.0)
            if clicked:
                clicked_count += 1
            if converted:
                converted_count += 1
        
        self.assertGreater(clicked_count, 0)
        self.assertGreaterEqual(converted_count, 0)
        self.assertLessEqual(converted_count, clicked_count)
    
    def test_calculate_revenue(self):
        simulator = self._create_simulator()
        
        revenue1 = simulator._calculate_revenue(True, True, 20.0)
        self.assertEqual(revenue1, 22.0)
        
        revenue2 = simulator._calculate_revenue(True, False, 20.0)
        self.assertEqual(revenue2, 2.0)
        
        revenue3 = simulator._calculate_revenue(False, False, 20.0)
        self.assertEqual(revenue3, 0.0)
    
    def test_get_strategy_comparison(self):
        simulator = self._create_simulator()
        simulator.run_simulation(num_auctions=20)
        
        comparison = simulator.get_strategy_comparison()
        self.assertIsInstance(comparison, dict)
        for strategy, metrics in comparison.items():
            self.assertIn("win_rate", metrics)
            self.assertIn("total_profit", metrics)
            self.assertIn("roas", metrics)
    
    def test_export_and_load_history(self):
        import tempfile
        import os
        
        simulator = self._create_simulator()
        simulator.run_simulation(num_auctions=5)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            data = simulator.export_history(filepath=filepath, limit=3)
            self.assertEqual(len(data), 3)
            
            loaded = simulator.load_history(filepath)
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[0].auction_id, data[0]["auction_id"])
        finally:
            os.unlink(filepath)
    
    def test_reset(self):
        simulator = self._create_simulator()
        simulator.run_simulation(num_auctions=10)
        self.assertGreater(simulator.stats.total_auctions, 0)
        
        simulator.reset()
        self.assertEqual(simulator.stats.total_auctions, 0)
        self.assertEqual(len(simulator.auction_history), 0)
    
    def test_run_replay(self):
        simulator = self._create_simulator()
        simulator.run_simulation(num_auctions=5)
        
        history_data = simulator.export_history(limit=3)
        
        replay_stats = simulator.run_replay(history_data)
        self.assertEqual(replay_stats.total_auctions, 3)
    
    def test_get_summary(self):
        simulator = self._create_simulator()
        simulator.run_simulation(num_auctions=5)
        
        summary = simulator.get_summary()
        self.assertIn("stats", summary)
        self.assertIn("num_competitors", summary)
        self.assertIn("strategy_comparison", summary)
        self.assertIn("exploration_status", summary)


class TestAutoTuner(unittest.TestCase):
    def setUp(self):
        reset_redis_singleton()
        setup_default_mocks()
    
    def _create_tuner(self):
        from src.auto_tuner import AutoTuner
        return AutoTuner(
            metric="total_profit",
            direction="maximize",
            n_trials=3,
            random_seed=42,
        )
    
    def test_initialization(self):
        try:
            tuner = self._create_tuner()
            self.assertEqual(tuner.metric, "total_profit")
            self.assertEqual(tuner.direction, "maximize")
            self.assertEqual(tuner.n_trials, 3)
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_parameter_ranges(self):
        try:
            tuner = self._create_tuner()
            self.assertGreater(len(tuner.parameter_ranges), 0)
            
            param_names = [p.name for p in tuner.parameter_ranges]
            self.assertIn("bid_base_multiplier", param_names)
            self.assertIn("ctr_weight", param_names)
            self.assertIn("exploration_strategy", param_names)
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_add_parameter_range(self):
        try:
            from src.auto_tuner import ParameterRange
            tuner = self._create_tuner()
            
            custom_param = ParameterRange(
                name="custom_param",
                param_type="float",
                low=0.1,
                high=2.0,
                step=0.1,
            )
            tuner.add_parameter_range(custom_param)
            
            param_names = [p.name for p in tuner.parameter_ranges]
            self.assertIn("custom_param", param_names)
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_apply_params_to_config(self):
        try:
            tuner = self._create_tuner()
            
            params = {
                "bid_base_multiplier": 1.2,
                "ctr_weight": 1.5,
                "exploration_strategy": "ucb",
                "pid_kp": 1.5,
                "pid_ki": 0.2,
                "pid_kd": 0.1,
            }
            
            tuner._apply_params_to_config(params)
            
            from config import config
            self.assertEqual(config.exploration.strategy, "ucb")
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_extract_metric(self):
        try:
            from src.auction_simulator import SimulationStats
            tuner = self._create_tuner()
            
            stats = SimulationStats(
                total_auctions=100,
                auctions_won=50,
                total_profit=1000.0,
                total_cost=500.0,
                total_revenue=1500.0,
            )
            
            value = tuner._extract_metric(stats)
            self.assertEqual(value, 1000.0)
            
            tuner.metric = "roas"
            roas_value = tuner._extract_metric(stats)
            self.assertEqual(roas_value, 3.0)
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_generate_optimal_strategy(self):
        try:
            from src.auto_tuner import TuningResult
            tuner = self._create_tuner()
            
            result = TuningResult(
                best_params={
                    "bid_base_multiplier": 1.3,
                    "ctr_weight": 1.8,
                    "cvr_weight": 2.2,
                    "frequency_penalty_weight": 0.9,
                },
                best_value=500.0,
                metric="total_profit",
                n_trials=10,
                study_name="test",
                duration=10.0,
            )
            
            strategy = tuner.generate_optimal_strategy(result, name="test_optimal")
            self.assertEqual(strategy["name"], "test_optimal")
            self.assertEqual(strategy["bid_multiplier"], 1.3)
            self.assertEqual(strategy["ctr_weight"], 1.8)
        except ImportError:
            self.skipTest("Optuna not installed")
    
    def test_tuning_result_save_load(self):
        try:
            import tempfile
            import os
            from src.auto_tuner import TuningResult
            
            result = TuningResult(
                best_params={"param1": 1.0},
                best_value=100.0,
                metric="total_profit",
                n_trials=5,
                study_name="test_save",
                duration=5.0,
                trial_results=[{"trial_number": 1, "value": 50.0}],
            )
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                filepath = f.name
            
            try:
                result.save(filepath)
                loaded = TuningResult.load(filepath)
                self.assertEqual(loaded.best_value, 100.0)
                self.assertEqual(loaded.n_trials, 5)
            finally:
                os.unlink(filepath)
        except ImportError:
            self.skipTest("Optuna not installed")


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("RTB Bid Engine Unit Tests")
        print("=" * 60)
        unittest.main(verbosity=2)
    finally:
        _redis_patch.stop()
