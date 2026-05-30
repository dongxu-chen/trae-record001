import random
from datetime import datetime, timedelta

from database import get_db
from sensor_simulator import ZONE_CONFIGS

NAVIGATION_STEPS_A = [
    {"instruction": "从入口A进入，前方50米右转", "distance": 50, "icon": "right"},
    {"instruction": "沿主干道直行200米", "distance": 200, "icon": "straight"},
    {"instruction": "经过B区入口，继续前行", "distance": 100, "icon": "straight"},
    {"instruction": "到达目标区域入口", "distance": 50, "icon": "arrive"},
]

NAVIGATION_STEPS_B = [
    {"instruction": "从入口B进入，左转进入地下通道", "distance": 80, "icon": "left"},
    {"instruction": "沿通道直行150米", "distance": 150, "icon": "straight"},
    {"instruction": "经过D区入口，继续前行", "distance": 100, "icon": "straight"},
    {"instruction": "到达目标区域入口", "distance": 50, "icon": "arrive"},
]

ZONE_NAV_OFFSETS = {
    "A": {"extra_dist": 0, "extra_time": 0},
    "B": {"extra_dist": 50, "extra_time": 0.5},
    "C": {"extra_dist": 100, "extra_time": 1.0},
    "D": {"extra_dist": 150, "extra_time": 1.5},
    "E": {"extra_dist": 120, "extra_time": 1.2},
}


async def generate_navigation_route(zone_id: str, entrance: str = "A", vehicle_plate: str = None) -> dict:
    if zone_id not in ZONE_CONFIGS:
        raise ValueError(f"Unknown zone: {zone_id}")

    walk_dist = 100
    has_reservation = False

    db = await get_db()
    try:
        async with db.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                walk_dist = row[4] if entrance.upper() == "B" else row[3]

        if vehicle_plate:
            async with db.execute(
                "SELECT id FROM reservations WHERE vehicle_plate = ? AND zone_id = ? AND status = 'active'",
                (vehicle_plate, zone_id),
            ) as cursor:
                row = await cursor.fetchone()
                has_reservation = row is not None
    finally:
        await db.close()

    base_steps = NAVIGATION_STEPS_A if entrance.upper() == "A" else NAVIGATION_STEPS_B
    offset = ZONE_NAV_OFFSETS.get(zone_id, {"extra_dist": 50, "extra_time": 0.5})

    steps = []
    for i, step in enumerate(base_steps):
        s = dict(step)
        if i == len(base_steps) - 1:
            s["instruction"] = s["instruction"].replace("目标区域", f"{zone_id}区")
            if zone_id in ("C", "D", "E"):
                s["instruction"] += "，请下至地下停车场"
        s["distance"] += offset["extra_dist"] if i == 1 else 0
        steps.append(s)

    steps.append({
        "instruction": f"停车后步行{int(walk_dist)}米到达目的地",
        "distance": int(walk_dist),
        "icon": "walk",
    })

    total_drive = sum(s["distance"] for s in steps[:-1])
    drive_time = round(total_drive / 300 + offset["extra_time"], 1)
    walk_time = round(walk_dist / 80, 1)

    eta = datetime.now() + timedelta(minutes=drive_time + 2)

    if has_reservation:
        steps.insert(0, {
            "instruction": f"已检测到预约车辆 {vehicle_plate}，车位已预留",
            "distance": 0,
            "icon": "reservation",
        })

    push_status = "sent" if random.random() > 0.2 else "pending"
    push_target = f"车机-{vehicle_plate or 'UNKNOWN'}"

    return {
        "zone_id": zone_id,
        "entrance": entrance,
        "driving_distance": total_drive,
        "driving_time_minutes": drive_time,
        "walking_distance": walk_dist,
        "walking_time_minutes": walk_time,
        "turn_by_turn": steps,
        "estimated_arrival": eta.strftime("%H:%M"),
        "has_reservation": has_reservation,
        "push_status": push_status,
        "push_target": push_target,
    }
