import argparse
import json
import random
import sys
import threading
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from config import config
from src.bid_engine import BidEngine, BidRequest
from src.data_generator import DataGenerator
from src.kafka_handler import KafkaHandler
from src.flink_job import FlinkRTBJob, SimulatedFlinkJob
from src.prediction_model import PredictionModel
from src.redis_client import RedisClient


app = FastAPI(title="RTB Bid Engine API", version="1.0.0")


class BidRequestModel(BaseModel):
    user_id: str
    ad_id: str
    campaign_id: str = "default"
    user_profile: dict
    context: dict
    ad_info: dict
    floor_price: float = 0.01
    cpa_goal: float = 10.0


class BidResponseModel(BaseModel):
    request_id: str
    bid_id: str
    success: bool
    bid_price: float
    reason: str
    details: dict
    timestamp: int


bid_engine: Optional[BidEngine] = None


@app.on_event("startup")
async def startup_event():
    global bid_engine
    print("Initializing RTB Bid Engine...")
    bid_engine = BidEngine(campaign_id="default")
    print("RTB Bid Engine initialized successfully")


@app.post("/bid", response_model=BidResponseModel)
async def process_bid(request: BidRequestModel):
    if bid_engine is None:
        raise HTTPException(status_code=503, detail="Bid engine not initialized")
    import uuid
    bid_request = BidRequest(
        request_id=str(uuid.uuid4()),
        user_id=request.user_id,
        ad_id=request.ad_id,
        campaign_id=request.campaign_id,
        user_profile=request.user_profile,
        context=request.context,
        ad_info=request.ad_info,
        floor_price=request.floor_price,
        cpa_goal=request.cpa_goal,
    )
    response = bid_engine.process_bid(bid_request)
    return response.to_dict()


@app.get("/status")
async def get_status():
    if bid_engine is None:
        raise HTTPException(status_code=503, detail="Bid engine not initialized")
    return bid_engine.get_engine_status()


@app.post("/click/{bid_id}")
async def record_click(bid_id: str):
    if bid_engine is None:
        raise HTTPException(status_code=503, detail="Bid engine not initialized")
    success = bid_engine.record_click(bid_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bid not found")
    return {"status": "success", "bid_id": bid_id}


@app.post("/reset")
async def reset_engine():
    if bid_engine is None:
        raise HTTPException(status_code=503, detail="Bid engine not initialized")
    bid_engine.reset_engine()
    return {"status": "success", "message": "Engine reset successfully"}


def run_simulation(args):
    print("=" * 60)
    print("RTB Bid Engine Simulation")
    print("=" * 60)
    data_generator = DataGenerator()
    if args.create_models:
        print("\nCreating mock XGBoost models...")
        data_generator.create_mock_models()
    if args.save_profiles:
        print("\nSaving user profiles to Redis...")
        data_generator.save_user_profiles_to_redis(count=args.profile_count)
    print("\nInitializing Bid Engine...")
    engine = BidEngine(campaign_id=args.campaign_id)
    print("\nStarting simulation...")
    print(f"Requests: {args.num_requests}, Delay: {args.delay}s")
    print("-" * 60)
    successful_bids = 0
    total_spend = 0.0
    rejected_bids = 0
    rejection_reasons = {}
    for i in range(args.num_requests):
        try:
            request_data = data_generator.generate_bid_request(campaign_id=args.campaign_id)
            import uuid
            bid_request = BidRequest(
                request_id=request_data["request_id"],
                user_id=request_data["user_id"],
                ad_id=request_data["ad_id"],
                campaign_id=request_data["campaign_id"],
                user_profile=request_data["user_profile"],
                context=request_data["context"],
                ad_info=request_data["ad_info"],
                floor_price=request_data["floor_price"],
                cpa_goal=request_data["cpa_goal"],
            )
            response = engine.process_bid(bid_request)
            if response.success:
                successful_bids += 1
                total_spend += response.bid_price
                print(f"[{i+1}] ✓ Bid: ${response.bid_price:.4f} | Layer: {response.details.get('traffic_layer', 'N/A')} | CTR: {response.details.get('ctr', 0):.4f} | CVR: {response.details.get('cvr', 0):.4f}")
            else:
                rejected_bids += 1
                reason = response.reason.split(":")[0]
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                print(f"[{i+1}] ✗ Rejected: {response.reason}")
            if args.delay > 0:
                time.sleep(args.delay)
        except KeyboardInterrupt:
            print("\nSimulation stopped by user")
            break
        except Exception as e:
            print(f"[{i+1}] Error: {e}")
    print("-" * 60)
    print("\nSimulation Results:")
    print(f"  Total Requests: {args.num_requests}")
    print(f"  Successful Bids: {successful_bids} ({successful_bids/args.num_requests*100:.1f}%)")
    print(f"  Rejected Bids: {rejected_bids} ({rejected_bids/args.num_requests*100:.1f}%)")
    print(f"  Total Spend: ${total_spend:.4f}")
    print(f"  Avg Bid Price: ${total_spend/successful_bids:.4f}" if successful_bids > 0 else "  Avg Bid Price: N/A")
    if rejection_reasons:
        print("\nRejection Reasons:")
        for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count} ({count/rejected_bids*100:.1f}%)")
    print("\n" + "=" * 60)
    print("Final Engine Status:")
    print(json.dumps(engine.get_engine_status(), indent=2, default=str))
    print("=" * 60)


def run_kafka_consumer(args):
    print("Starting Kafka consumer...")
    kafka_handler = KafkaHandler()
    try:
        def callback(response):
            print(f"Processed bid: {response['request_id']} -> {'success' if response['success'] else 'rejected'} | ${response['bid_price']:.4f}")
        kafka_handler.consume_bid_requests(callback=callback)
    except KeyboardInterrupt:
        print("Consumer stopped")


def run_kafka_producer(args):
    print("Starting Kafka producer simulation...")
    data_generator = DataGenerator()
    kafka_handler = KafkaHandler()
    kafka_handler.connect()
    try:
        for i in range(args.num_messages):
            request_data = data_generator.generate_bid_request()
            request_id = kafka_handler.send_bid_request(request_data)
            if request_id:
                print(f"[{i+1}] Sent bid request: {request_id}")
            if args.delay > 0:
                time.sleep(args.delay)
    except KeyboardInterrupt:
        print("Producer stopped")
    finally:
        kafka_handler.disconnect()


def run_flink_job(args):
    print("Starting Flink job...")
    if args.simulate:
        flink_job = SimulatedFlinkJob()
        flink_job.simulate_realtime_analytics(interval=args.interval)
    else:
        flink_job = FlinkRTBJob()
        if args.job_type == "analytics":
            flink_job.run_bid_analytics_job()
        elif args.job_type == "budget":
            flink_job.run_budget_pace_control_job()
        elif args.job_type == "frequency":
            flink_job.run_frequency_monitoring_job()
        else:
            flink_job.run_all_jobs()


def run_api_server(args):
    print(f"Starting API server on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port, workers=args.workers)


def run_demo(args):
    print("=" * 60)
    print("RTB Bid Engine Complete Demo")
    print("=" * 60)
    data_generator = DataGenerator()
    redis_client = RedisClient()
    print("\nStep 1: Initialize Redis data...")
    profiles = data_generator.save_user_profiles_to_redis(count=50)
    print("\nStep 2: Create mock prediction models...")
    predictor = data_generator.create_mock_models()
    print("\nStep 3: Initialize Bid Engine...")
    engine = BidEngine(campaign_id="demo_campaign")
    print("\nStep 4: Run sample bid requests...")
    print("-" * 60)
    results = []
    for i in range(20):
        user_id = f"user_{random.randint(0, 99)}"
        user_profile = redis_client.get_user_profile(user_id) or data_generator.generate_user_profile(user_id)
        context = data_generator.generate_context()
        ad_info = data_generator.generate_ad_info()
        request_data = {
            "user_id": user_id,
            "ad_id": ad_info["ad_id"],
            "campaign_id": "demo_campaign",
            "user_profile": user_profile,
            "context": context,
            "ad_info": ad_info,
            "floor_price": 0.05,
            "cpa_goal": 20.0,
        }
        import uuid
        bid_request = BidRequest(
            request_id=str(uuid.uuid4()),
            **request_data,
        )
        response = engine.process_bid(bid_request)
        results.append(response)
        status = "✓" if response.success else "✗"
        layer = response.details.get('traffic_layer', 'N/A')
        ctr = response.details.get('ctr', 0)
        cvr = response.details.get('cvr', 0)
        print(f"[{i+1}] {status} User:{user_id[:8]} | Layer:{layer} | CTR:{ctr:.4f} | CVR:{cvr:.4f} | Bid:${response.bid_price:.4f} | {response.reason}")
        time.sleep(0.1)
    print("-" * 60)
    print("\nStep 5: Feature Importance Analysis...")
    print("\nCTR Model Top Features:")
    ctr_importance = predictor.get_feature_importance("ctr")
    for feat, imp in sorted(ctr_importance.items(), key=lambda x: -x[1])[:5]:
        print(f"  {feat}: {imp:.2f}")
    print("\nCVR Model Top Features:")
    cvr_importance = predictor.get_feature_importance("cvr")
    for feat, imp in sorted(cvr_importance.items(), key=lambda x: -x[1])[:5]:
        print(f"  {feat}: {imp:.2f}")
    print("\n" + "=" * 60)
    print("Final System Status:")
    print(json.dumps(engine.get_engine_status(), indent=2, default=str))
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="RTB Real-time Bidding System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    sim_parser = subparsers.add_parser("simulate", help="Run bid simulation")
    sim_parser.add_argument("--num-requests", type=int, default=100, help="Number of bid requests")
    sim_parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    sim_parser.add_argument("--campaign-id", type=str, default="default", help="Campaign ID")
    sim_parser.add_argument("--create-models", action="store_true", help="Create mock XGBoost models")
    sim_parser.add_argument("--save-profiles", action="store_true", help="Save user profiles to Redis")
    sim_parser.add_argument("--profile-count", type=int, default=100, help="Number of user profiles to save")
    kafka_cons_parser = subparsers.add_parser("kafka-consumer", help="Run Kafka consumer")
    kafka_prod_parser = subparsers.add_parser("kafka-producer", help="Run Kafka producer")
    kafka_prod_parser.add_argument("--num-messages", type=int, default=100, help="Number of messages to send")
    kafka_prod_parser.add_argument("--delay", type=float, default=0.5, help="Delay between messages")
    flink_parser = subparsers.add_parser("flink", help="Run Flink job")
    flink_parser.add_argument("--job-type", type=str, default="analytics", choices=["analytics", "budget", "frequency", "all"])
    flink_parser.add_argument("--simulate", action="store_true", help="Run in simulation mode")
    flink_parser.add_argument("--interval", type=int, default=60, help="Simulation interval in seconds")
    api_parser = subparsers.add_parser("api", help="Run API server")
    api_parser.add_argument("--port", type=int, default=8000, help="API server port")
    api_parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    demo_parser = subparsers.add_parser("demo", help="Run complete demo")
    args = parser.parse_args()
    if args.command == "simulate":
        run_simulation(args)
    elif args.command == "kafka-consumer":
        run_kafka_consumer(args)
    elif args.command == "kafka-producer":
        run_kafka_producer(args)
    elif args.command == "flink":
        run_flink_job(args)
    elif args.command == "api":
        run_api_server(args)
    elif args.command == "demo":
        run_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
