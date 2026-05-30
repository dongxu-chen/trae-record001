import asyncio
from datetime import datetime, timedelta

from database import (
    get_all_pricing, update_zone_pricing, count_active_reservations,
    get_events_for_datetime,
)
from sensor_simulator import ZONE_CONFIGS


BASE_PRICES = {"A": 8.0, "B": 8.0, "C": 10.0, "D": 6.0, "E": 6.0}

SURGE_THRESHOLDS = [
    (0.85, 2.5, "very_high"),
    (0.70, 2.0, "high"),
    (0.55, 1.5, "elevated"),
    (0.40, 1.2, "normal"),
    (0.0, 1.0, "low"),
]

EVENT_SURGE_BONUS = 0.5


def calculate_surge(occupancy_rate: float, event_factor: float = 1.0, reservation_count: int = 0) -> tuple[float, float, str]:
    surge = 1.0
    demand_level = "normal"

    for threshold, factor, level in SURGE_THRESHOLDS:
        if occupancy_rate >= threshold:
            surge = factor
            demand_level = level
            break

    if event_factor > 1.0:
        surge += EVENT_SURGE_BONUS * (event_factor - 1.0)
        if demand_level in ("low", "normal"):
            demand_level = "elevated"

    if reservation_count > 5:
        surge += 0.1 * (reservation_count - 5)

    surge = round(min(surge, 4.0), 2)
    return surge, round(surge, 2), demand_level


async def update_all_pricing():
    now = datetime.now()
    active_events = await get_events_for_datetime(now)

    for zone_id in ZONE_CONFIGS:
        cfg = ZONE_CONFIGS[zone_id]
        total = cfg["total"]

        from database import get_db
        db = await get_db()
        try:
            async with db.execute(
                "SELECT available_spots FROM sensor_readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 1",
                (zone_id,),
            ) as cursor:
                row = await cursor.fetchone()
                available = row[0] if row else total
        finally:
            await db.close()

        occupancy_rate = 1 - available / max(total, 1)

        event_factor = 1.0
        for event in active_events:
            if zone_id in [z.strip() for z in event["impact_zone_ids"].split(",")]:
                event_factor = max(event_factor, event["impact_factor"])

        reservation_count = await count_active_reservations(zone_id)
        surge, surge_factor, demand_level = calculate_surge(occupancy_rate, event_factor, reservation_count)

        base_price = BASE_PRICES.get(zone_id, 8.0)
        current_price = round(base_price * surge, 1)

        await update_zone_pricing(zone_id, current_price, surge_factor, demand_level)


async def pricing_loop():
    while True:
        try:
            await update_all_pricing()
        except Exception:
            pass
        await asyncio.sleep(10)
