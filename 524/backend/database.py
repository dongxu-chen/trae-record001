import os
import json
import aiosqlite
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "parking.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS zones (
    zone_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    total_spots INTEGER NOT NULL,
    walk_distance_from_entrance_a REAL NOT NULL,
    walk_distance_from_entrance_b REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
    available_spots INTEGER NOT NULL,
    occupied_spots INTEGER NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
    predicted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_time DATETIME NOT NULL,
    predicted_available REAL NOT NULL,
    confidence REAL NOT NULL,
    model_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guidance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommended_zone TEXT NOT NULL REFERENCES zones(zone_id),
    actual_zone TEXT REFERENCES zones(zone_id),
    confidence REAL NOT NULL,
    entrance TEXT NOT NULL,
    walking_distance REAL NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    start_hour INTEGER NOT NULL,
    end_hour INTEGER NOT NULL,
    impact_zone_ids TEXT NOT NULL,
    impact_factor REAL NOT NULL DEFAULT 1.5,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
    vehicle_plate TEXT NOT NULL,
    reserved_spot INTEGER NOT NULL,
    arrival_time TEXT NOT NULL,
    duration_hours REAL NOT NULL DEFAULT 2.0,
    status TEXT NOT NULL DEFAULT 'active',
    price REAL NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
    base_price REAL NOT NULL DEFAULT 10.0,
    current_price REAL NOT NULL DEFAULT 10.0,
    surge_factor REAL NOT NULL DEFAULT 1.0,
    demand_level TEXT NOT NULL DEFAULT 'normal',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sensor_zone_time ON sensor_readings(zone_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_zone_time ON predictions(zone_id, predicted_at);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_reservations_zone_status ON reservations(zone_id, status);
CREATE INDEX IF NOT EXISTS idx_pricing_zone ON pricing(zone_id);
"""

SEED_SQL = """
INSERT OR IGNORE INTO zones (zone_id, name, total_spots, walk_distance_from_entrance_a, walk_distance_from_entrance_b)
VALUES
    ('A', 'A区-地面层', 50, 10, 120),
    ('B', 'B区-地面层', 40, 50, 80),
    ('C', 'C区-地下一层', 60, 90, 40),
    ('D', 'D区-地下一层', 45, 130, 20),
    ('E', 'E区-地下二层', 55, 100, 60);
"""

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "seed_history.json")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.executescript(SEED_SQL)
        await db.commit()
    finally:
        await db.close()


async def seed_history_if_empty():
    db = await get_db()
    try:
        async with db.execute("SELECT COUNT(*) FROM sensor_readings") as cursor:
            row = await cursor.fetchone()
            if row[0] > 0:
                return
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                await db.execute(
                    "INSERT INTO sensor_readings (zone_id, available_spots, occupied_spots, timestamp) VALUES (?, ?, ?, ?)",
                    (r["zone_id"], r["available_spots"], r["occupied_spots"], r["timestamp"]),
                )
            await db.commit()
    finally:
        await db.close()


async def get_events_for_datetime(dt: datetime) -> list[dict]:
    db = await get_db()
    try:
        date_str = dt.strftime("%Y-%m-%d")
        hour = dt.hour
        async with db.execute(
            "SELECT * FROM events WHERE event_date = ? AND start_hour <= ? AND end_hour >= ?",
            (date_str, hour, hour),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_all_events(include_past: bool = False) -> list[dict]:
    db = await get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        if include_past:
            async with db.execute("SELECT * FROM events ORDER BY event_date DESC, start_hour ASC") as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM events WHERE event_date >= ? ORDER BY event_date ASC, start_hour ASC",
                (today,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def create_event(data: dict) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO events
               (event_type, title, event_date, start_hour, end_hour, impact_zone_ids, impact_factor, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["event_type"],
                data["title"],
                data["event_date"],
                data["start_hour"],
                data["end_hour"],
                data["impact_zone_ids"],
                data.get("impact_factor", 1.5),
                data.get("description", ""),
            ),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def delete_event(event_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        await db.commit()
        return True
    finally:
        await db.close()


async def create_reservation(data: dict) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO reservations
               (zone_id, vehicle_plate, reserved_spot, arrival_time, duration_hours, status, price)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["zone_id"],
                data["vehicle_plate"],
                data["reserved_spot"],
                data["arrival_time"],
                data.get("duration_hours", 2.0),
                "active",
                data.get("price", 0),
            ),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_reservations(zone_id: str = None, status: str = None) -> list[dict]:
    db = await get_db()
    try:
        query = "SELECT * FROM reservations WHERE 1=1"
        params = []
        if zone_id:
            query += " AND zone_id = ?"
            params.append(zone_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY arrival_time ASC"
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        await db.close()


async def cancel_reservation(reservation_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
        await db.commit()
        return True
    finally:
        await db.close()


async def count_active_reservations(zone_id: str) -> int:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT COUNT(*) FROM reservations WHERE zone_id = ? AND status = 'active'",
            (zone_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    finally:
        await db.close()


async def init_pricing():
    db = await get_db()
    try:
        for zone_id, cfg in [
            ("A", 8.0), ("B", 8.0), ("C", 10.0), ("D", 6.0), ("E", 6.0),
        ]:
            async with db.execute("SELECT COUNT(*) FROM pricing WHERE zone_id = ?", (zone_id,)) as cursor:
                row = await cursor.fetchone()
                if row[0] == 0:
                    await db.execute(
                        "INSERT INTO pricing (zone_id, base_price, current_price, surge_factor, demand_level) VALUES (?, ?, ?, 1.0, 'normal')",
                        (zone_id, cfg, cfg),
                    )
        await db.commit()
    finally:
        await db.close()


async def get_all_pricing() -> list[dict]:
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM pricing ORDER BY zone_id") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        await db.close()


async def update_zone_pricing(zone_id: str, current_price: float, surge_factor: float, demand_level: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE pricing SET current_price = ?, surge_factor = ?, demand_level = ?, updated_at = ? WHERE zone_id = ?",
            (current_price, surge_factor, demand_level, datetime.now().isoformat(), zone_id),
        )
        await db.commit()
    finally:
        await db.close()
