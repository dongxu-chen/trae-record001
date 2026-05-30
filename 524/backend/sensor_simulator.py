import numpy as np
import random
from datetime import datetime, timedelta
from database import get_db, get_events_for_datetime

ZONE_CONFIGS = {
    "A": {"total": 50, "base_occupancy": 0.6, "peak_hours": [(8, 10), (17, 19)]},
    "B": {"total": 40, "base_occupancy": 0.55, "peak_hours": [(9, 11), (18, 20)]},
    "C": {"total": 60, "base_occupancy": 0.5, "peak_hours": [(7, 9), (16, 18)]},
    "D": {"total": 45, "base_occupancy": 0.45, "peak_hours": [(10, 12), (19, 21)]},
    "E": {"total": 55, "base_occupancy": 0.4, "peak_hours": [(11, 13), (20, 22)]},
}

EVENT_TYPES = {
    "concert": {"label": "演唱会", "base_factor": 1.6},
    "sports": {"label": "体育比赛", "base_factor": 1.8},
    "exhibition": {"label": "展览", "base_factor": 1.3},
    "conference": {"label": "会议", "base_factor": 1.2},
    "festival": {"label": "节日活动", "base_factor": 1.7},
}


def _calculate_event_impact(zone_id: str, dt: datetime, events: list[dict]) -> tuple[float, list[dict]]:
    total_factor = 1.0
    active_events = []
    for event in events:
        impact_zones = [z.strip() for z in event["impact_zone_ids"].split(",")]
        if zone_id in impact_zones:
            hour = dt.hour
            event_start = event["start_hour"]
            event_end = event["end_hour"]
            mid_hour = (event_start + event_end) / 2
            time_weight = 1 - abs(hour - mid_hour) / ((event_end - event_start) / 2 + 0.01)
            time_weight = max(0.3, min(1.0, time_weight))
            factor = 1 + (event["impact_factor"] - 1) * time_weight
            total_factor = max(total_factor, factor)
            active_events.append({
                "id": event["id"],
                "title": event["title"],
                "type": event["event_type"],
                "factor": round(factor, 3),
            })
    return total_factor, active_events


def _occupancy_for_hour(zone_id: str, hour: int, event_factor: float = 1.0) -> float:
    cfg = ZONE_CONFIGS[zone_id]
    base = cfg["base_occupancy"]
    for start, end in cfg["peak_hours"]:
        if start <= hour <= end:
            base += 0.25 * (1 - abs(hour - (start + end) / 2) / ((end - start) / 2 + 0.01))
    if 0 <= hour <= 5:
        base *= 0.3
    elif 6 <= hour <= 7:
        base *= 0.6
    base = min(base * event_factor, 0.99)
    noise = random.gauss(0, 0.05)
    return max(0.05, min(0.99, base + noise))


async def simulate_current_reading(zone_id: str) -> dict:
    cfg = ZONE_CONFIGS[zone_id]
    dt_now = datetime.now()
    hour = dt_now.hour
    events = await get_events_for_datetime(dt_now)
    event_factor, active_events = _calculate_event_impact(zone_id, dt_now, events)
    occupancy_rate = _occupancy_for_hour(zone_id, hour, event_factor)
    total = cfg["total"]
    occupied = int(total * occupancy_rate)
    occupied = max(0, min(total, occupied + random.randint(-2, 2)))
    available = total - occupied
    timestamp = dt_now.isoformat()

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sensor_readings (zone_id, available_spots, occupied_spots, timestamp) VALUES (?, ?, ?, ?)",
            (zone_id, available, occupied, timestamp),
        )
        await db.commit()
    finally:
        await db.close()

    event_impact = {
        "factor": round(event_factor, 3),
        "active_events": active_events,
    } if active_events else None

    return {
        "zone_id": zone_id,
        "total_spots": total,
        "occupied_spots": occupied,
        "available_spots": available,
        "occupancy_rate": round(occupied / total, 3),
        "timestamp": timestamp,
        "event_impact": event_impact,
    }


def generate_historical_data(days: int = 7) -> list[dict]:
    records = []
    now = datetime.now()
    start = now - timedelta(days=days)

    current = start
    while current < now:
        for zone_id, cfg in ZONE_CONFIGS.items():
            hour = current.hour
            occupancy_rate = _occupancy_for_hour(zone_id, hour, 1.0)
            total = cfg["total"]
            occupied = int(total * occupancy_rate)
            occupied = max(0, min(total, occupied + random.randint(-2, 2)))
            available = total - occupied
            records.append({
                "zone_id": zone_id,
                "available_spots": available,
                "occupied_spots": occupied,
                "timestamp": current.isoformat(),
            })
        current += timedelta(minutes=5)

    return records
