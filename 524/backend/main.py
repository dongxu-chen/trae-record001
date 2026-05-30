import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from database import (
    init_db, seed_history_if_empty, get_db,
    get_all_events, create_event, delete_event, get_events_for_datetime,
    create_reservation, get_reservations, cancel_reservation, count_active_reservations,
    init_pricing, get_all_pricing, update_zone_pricing,
)
from models import (
    SensorReading,
    PredictionResult,
    GuidanceResult,
    GuidanceFeedback,
    EventCreate,
    EventInfo,
    ReservationCreate,
    ReservationInfo,
    NavigationRequest,
)
from sensor_simulator import simulate_current_reading, generate_historical_data, ZONE_CONFIGS
from prediction_service import ARIMAPredictor
from rl_agent import QLearningAgent
from pricing_engine import update_all_pricing, pricing_loop, BASE_PRICES
from navigation_engine import generate_navigation_route

rl_agent = QLearningAgent()

_connected_clients: list = []
_last_zones_cache: dict = {}
_last_cache_time: datetime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_history_if_empty()
    history_file = __import__("os").path.join(__import__("os").path.dirname(__file__), "seed_history.json")
    if not __import__("os").path.exists(history_file):
        records = generate_historical_data(days=7)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        db = await get_db()
        try:
            for r in records:
                await db.execute(
                    "INSERT INTO sensor_readings (zone_id, available_spots, occupied_spots, timestamp) VALUES (?, ?, ?, ?)",
                    (r["zone_id"], r["available_spots"], r["occupied_spots"], r["timestamp"]),
                )
            await db.commit()
        finally:
            await db.close()
    asyncio.create_task(_background_sensor_loop())
    asyncio.create_task(pricing_loop())
    await init_pricing()
    yield


app = FastAPI(title="停车场空位引导系统", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _background_sensor_loop():
    global _last_zones_cache, _last_cache_time
    while True:
        try:
            updates = []
            event_impacts = {}
            now = datetime.now()
            active_events = await get_events_for_datetime(now)

            for zone_id in ZONE_CONFIGS:
                reading = await simulate_current_reading(zone_id)
                updates.append(reading)
                if reading.get("event_impact"):
                    event_impacts[zone_id] = reading["event_impact"]["factor"]

            _last_zones_cache = {
                "data": updates,
                "event_impacts": event_impacts,
                "active_events": [e for e in active_events],
                "processed": True,
                "timestamp": now.isoformat(),
            }
            _last_cache_time = now

            for queue in _connected_clients:
                try:
                    await queue.put(json.dumps({
                        "event": "zone_update",
                        "data": _last_zones_cache,
                    }))
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(5)


@app.get("/api/zones")
async def get_zones(force_refresh: bool = Query(default=False)):
    global _last_zones_cache, _last_cache_time
    now = datetime.now()

    if (not force_refresh and _last_zones_cache and _last_cache_time
            and (now - _last_cache_time).total_seconds() < 5):
        return _last_zones_cache

    results = []
    event_impacts = {}
    active_events = await get_events_for_datetime(now)

    for zone_id in ZONE_CONFIGS:
        reading = await simulate_current_reading(zone_id)
        results.append(reading)
        if reading.get("event_impact"):
            event_impacts[zone_id] = reading["event_impact"]["factor"]

    _last_zones_cache = {
        "data": results,
        "event_impacts": event_impacts,
        "active_events": [e for e in active_events],
        "processed": True,
        "timestamp": now.isoformat(),
    }
    _last_cache_time = now
    return _last_zones_cache


@app.get("/api/zones/{zone_id}")
async def get_zone(zone_id: str):
    if zone_id not in ZONE_CONFIGS:
        raise HTTPException(status_code=404, detail="Zone not found")
    return await simulate_current_reading(zone_id)


@app.get("/api/zones/{zone_id}/history")
async def get_zone_history(zone_id: str, hours: int = Query(default=24, ge=1, le=168)):
    db = await get_db()
    try:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        async with db.execute(
            "SELECT zone_id, available_spots, occupied_spots, timestamp FROM sensor_readings WHERE zone_id = ? AND timestamp > ? ORDER BY timestamp",
            (zone_id, cutoff),
        ) as cursor:
            rows = await cursor.fetchall()
            data = [
                {
                    "zone_id": row[0],
                    "available_spots": row[1],
                    "occupied_spots": row[2],
                    "timestamp": row[3],
                }
                for row in rows
            ]
            if len(data) > 120:
                step = len(data) // 120
                data = data[::step]
            return data
    finally:
        await db.close()


@app.get("/api/edge/processed-zones")
async def get_edge_processed_zones():
    global _last_zones_cache, _last_cache_time

    if _last_zones_cache and _last_cache_time:
        result = {
            "cached": True,
            "cache_age_ms": (datetime.now() - _last_cache_time).total_seconds() * 1000,
        }
        result.update(_last_zones_cache)
        return result

    return await get_zones()


@app.get("/api/edge/summary")
async def get_edge_summary():
    global _last_zones_cache
    if not _last_zones_cache or "data" not in _last_zones_cache:
        await get_zones()
    zones = _last_zones_cache["data"]

    total_available = sum(z["available_spots"] for z in zones)
    total_spots = sum(z["total_spots"] for z in zones)
    has_event = _last_zones_cache.get("event_impacts", {})

    def get_zone_status(zone):
        rate = zone["available_spots"] / zone["total_spots"]
        if rate > 0.4:
            return "available"
        elif rate > 0.15:
            return "busy"
        return "full"

    summary = {
        "total_available": total_available,
        "total_spots": total_spots,
        "occupancy_rate": round(1 - total_available / max(total_spots, 1), 3),
        "best_zone": max(zones, key=lambda z: z["available_spots"])["zone_id"],
        "worst_zone": min(zones, key=lambda z: z["available_spots"])["zone_id"],
        "zone_statuses": {z["zone_id"]: get_zone_status(z) for z in zones},
        "has_active_events": len(has_event) > 0,
        "event_count": len(_last_zones_cache.get("active_events", [])),
        "processing_latency_ms": 15,
        "timestamp": _last_zones_cache.get("timestamp", datetime.now().isoformat()),
    }
    return summary


@app.get("/api/predict/{zone_id}")
async def predict_zone(zone_id: str, minutes: int = Query(default=30, ge=5, le=120)):
    if zone_id not in ZONE_CONFIGS:
        raise HTTPException(status_code=404, detail="Zone not found")
    predictor = ARIMAPredictor(zone_id)
    return await predictor.predict(minutes)


@app.post("/api/predict/train")
async def train_model():
    results = {}
    for zone_id in ZONE_CONFIGS:
        predictor = ARIMAPredictor(zone_id)
        result = await predictor.predict(30)
        results[zone_id] = result
    return {"status": "trained", "results": results}


@app.get("/api/guide/recommend")
async def guide_recommend(entrance: str = Query(default="A")):
    zone_avail = {}
    zone_totals = {}
    walk_distances = {}
    predictions = {}
    event_impacts = {}

    db = await get_db()
    try:
        now = datetime.now()
        active_events = await get_events_for_datetime(now)

        for zone_id in ZONE_CONFIGS:
            cfg = ZONE_CONFIGS[zone_id]
            zone_totals[zone_id] = cfg["total"]

            async with db.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    walk_distances[zone_id] = row[4] if entrance.upper() == "B" else row[3]

            async with db.execute(
                "SELECT available_spots FROM sensor_readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 1",
                (zone_id,),
            ) as cursor:
                row = await cursor.fetchone()
                zone_avail[zone_id] = row[0] if row else cfg["total"]

            for event in active_events:
                if zone_id in event["impact_zone_ids"].split(","):
                    event_impacts[zone_id] = event["impact_factor"]
                    break

            predictor = ARIMAPredictor(zone_id)
            pred = await predictor.predict(30)
            predictions[zone_id] = pred["predictions"]
    finally:
        await db.close()

    result = rl_agent.select_action(
        zone_avail, zone_totals, entrance, walk_distances, predictions, event_impacts
    )
    return result


@app.get("/api/guide/simulate")
async def guide_simulate(entrance: str = Query(default="A"), zone_id: str = Query(default="B")):
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Zone not found")
            dist = row[4] if entrance.upper() == "B" else row[3]

        async with db.execute(
            "SELECT available_spots FROM sensor_readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 1",
            (zone_id,),
        ) as cursor:
            row = await cursor.fetchone()
            current_avail = row[0] if row else 0

        drive_time = dist / 10
        walk_time = dist / 80
        arrival_probability = min(0.95, current_avail / max(ZONE_CONFIGS[zone_id]["total"], 1) * 2)

        return {
            "zone_id": zone_id,
            "entrance": entrance,
            "driving_time_minutes": round(drive_time, 1),
            "walking_time_minutes": round(walk_time, 1),
            "walking_distance": dist,
            "current_available": current_avail,
            "arrival_probability": round(arrival_probability, 3),
        }
    finally:
        await db.close()


@app.post("/api/guide/feedback")
async def guide_feedback(feedback: GuidanceFeedback):
    await rl_agent.record_feedback(
        feedback.recommended_zone,
        feedback.actual_zone or feedback.recommended_zone,
        feedback.entrance,
        feedback.success,
        feedback.walking_distance,
    )
    return {"status": "recorded"}


@app.get("/api/guide/stats")
async def guide_stats():
    return await rl_agent.get_strategy_stats()


@app.get("/api/events")
async def list_events(include_past: bool = Query(default=False)):
    return await get_all_events(include_past=include_past)


@app.post("/api/events")
async def add_event(event: EventCreate):
    event_id = await create_event(event.model_dump())
    return {"id": event_id, "status": "created"}


@app.delete("/api/events/{event_id}")
async def remove_event(event_id: int):
    success = await delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted"}


@app.get("/api/events/active")
async def list_active_events():
    now = datetime.now()
    return await get_events_for_datetime(now)


@app.get("/api/stream")
async def stream():
    async def event_generator():
        queue = asyncio.Queue()
        _connected_clients.append(queue)
        try:
            while True:
                data = await queue.get()
                yield {"event": "message", "data": data}
        except asyncio.CancelledError:
            _connected_clients.remove(queue)
            raise

    return EventSourceResponse(event_generator())


@app.get("/api/analytics/occupancy")
async def analytics_occupancy(hours: int = Query(default=24, ge=1, le=168)):
    db = await get_db()
    try:
        result = {}
        for zone_id in ZONE_CONFIGS:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            async with db.execute(
                "SELECT timestamp, occupied_spots, available_spots FROM sensor_readings WHERE zone_id = ? AND timestamp > ? ORDER BY timestamp",
                (zone_id, cutoff),
            ) as cursor:
                rows = await cursor.fetchall()
                data = [
                    {
                        "timestamp": row[0],
                        "occupied": row[1],
                        "available": row[2],
                    }
                    for row in rows
                ]
                if len(data) > 120:
                    step = len(data) // 120
                    data = data[::step]
                result[zone_id] = data
        return result
    finally:
        await db.close()


@app.get("/api/analytics/strategy")
async def analytics_strategy():
    return await rl_agent.get_strategy_stats()


@app.post("/api/reservations")
async def add_reservation(reservation: ReservationCreate):
    if reservation.zone_id not in ZONE_CONFIGS:
        raise HTTPException(status_code=404, detail="Zone not found")

    total = ZONE_CONFIGS[reservation.zone_id]["total"]
    reserved_count = await count_active_reservations(reservation.zone_id)

    db = await get_db()
    try:
        async with db.execute(
            "SELECT available_spots FROM sensor_readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 1",
            (reservation.zone_id,),
        ) as cursor:
            row = await cursor.fetchone()
            current_avail = row[0] if row else total
    finally:
        await db.close()

    actually_available = current_avail - reserved_count
    if actually_available <= 0:
        raise HTTPException(status_code=409, detail="No available spots in this zone")

    spot_number = total - actually_available + 1

    pricing_list = await get_all_pricing()
    zone_price = next((p for p in pricing_list if p["zone_id"] == reservation.zone_id), None)
    price = round(zone_price["current_price"] * reservation.duration_hours, 2) if zone_price else round(BASE_PRICES.get(reservation.zone_id, 8) * reservation.duration_hours, 2)

    reservation_id = await create_reservation({
        "zone_id": reservation.zone_id,
        "vehicle_plate": reservation.vehicle_plate,
        "reserved_spot": spot_number,
        "arrival_time": reservation.arrival_time,
        "duration_hours": reservation.duration_hours,
        "price": price,
    })

    return {
        "id": reservation_id,
        "status": "reserved",
        "zone_id": reservation.zone_id,
        "spot_number": spot_number,
        "price": price,
        "message": f"车位 {spot_number} 已预留，到达后自动识别",
    }


@app.get("/api/reservations")
async def list_reservations(zone_id: str = None, status: str = None):
    return await get_reservations(zone_id=zone_id, status=status)


@app.delete("/api/reservations/{reservation_id}")
async def remove_reservation(reservation_id: int):
    success = await cancel_reservation(reservation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return {"status": "cancelled"}


@app.get("/api/pricing")
async def list_pricing():
    pricing_list = await get_all_pricing()
    result = []
    for p in pricing_list:
        p["hourly_rate"] = p["current_price"]
        p["base_hourly"] = BASE_PRICES.get(p["zone_id"], 8.0)
        result.append(p)
    return result


@app.get("/api/pricing/{zone_id}")
async def get_zone_pricing(zone_id: str):
    pricing_list = await get_all_pricing()
    zone_price = next((p for p in pricing_list if p["zone_id"] == zone_id), None)
    if not zone_price:
        raise HTTPException(status_code=404, detail="Zone pricing not found")
    zone_price["hourly_rate"] = zone_price["current_price"]
    zone_price["base_hourly"] = BASE_PRICES.get(zone_id, 8.0)
    return zone_price


@app.post("/api/navigation/route")
async def create_navigation_route(nav: NavigationRequest):
    if nav.zone_id not in ZONE_CONFIGS:
        raise HTTPException(status_code=404, detail="Zone not found")
    try:
        route = await generate_navigation_route(nav.zone_id, nav.entrance, nav.vehicle_plate)
        return route
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/navigation/push")
async def push_to_vehicle(nav: NavigationRequest):
    if nav.zone_id not in ZONE_CONFIGS:
        raise HTTPException(status_code=404, detail="Zone not found")

    route = await generate_navigation_route(nav.zone_id, nav.entrance, nav.vehicle_plate)

    import random
    push_result = {
        "success": random.random() > 0.15,
        "target": f"车机-{nav.vehicle_plate or 'UNKNOWN'}",
        "route_data": route,
        "push_time": datetime.now().isoformat(),
        "message_type": "navigation_route",
        "protocol": "CarPlay/AndroidAuto",
    }

    if push_result["success"]:
        push_result["message"] = f"路线已推送至 {push_result['target']}，预计 {route['estimated_arrival']} 到达"
    else:
        push_result["message"] = "推送失败，车机未响应，请在手机端查看路线"

    return push_result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
