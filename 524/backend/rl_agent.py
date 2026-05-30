import numpy as np
import json
import os
from database import get_db
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), "q_table.json")

ZONE_IDS = ["A", "B", "C", "D", "E"]

LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.9
EPSILON = 0.15

WALK_DISTANCE_WEIGHT = 0.08
MAX_DISTANCE_PENALTY = -20.0
SUCCESS_REWARD_BASE = 15.0
FAILURE_PENALTY = -10.0
DISTANCE_PENALTY_SCALE = 0.15


class QLearningAgent:
    def __init__(self):
        self.q_table: dict[str, dict[str, float]] = {}
        self._load_q_table()
        self._init_q_table()

    def _init_q_table(self):
        for zone in ZONE_IDS:
            if zone not in self.q_table:
                self.q_table[zone] = {}
            for action in ZONE_IDS:
                if action not in self.q_table[zone]:
                    self.q_table[zone][action] = 0.0

    def _load_q_table(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                self.q_table = json.load(f)

    def _save_q_table(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.q_table, f, indent=2)

    def _compute_utility_score(
        self,
        zone_id: str,
        zone_avail: dict[str, int],
        zone_totals: dict[str, int],
        walk_distances: dict[str, float],
    ) -> float:
        avail = zone_avail.get(zone_id, 0)
        total = zone_totals.get(zone_id, 1)
        distance = walk_distances.get(zone_id, 100)

        avail_score = min(1.0, avail / 5.0)
        distance_score = max(0, 1 - distance / 200)
        utility = 0.6 * avail_score + 0.4 * distance_score
        return round(utility, 3)

    def _discretize_state(
        self,
        zone_avail: dict[str, int],
        zone_totals: dict[str, int],
        event_impacts: dict[str, float] = None,
    ) -> str:
        parts = []
        for zid in ZONE_IDS:
            total = zone_totals.get(zid, 1)
            avail = zone_avail.get(zid, 0)
            rate = avail / total
            if rate > 0.5:
                state = "H"
            elif rate > 0.2:
                state = "M"
            else:
                state = "L"
            if event_impacts and zid in event_impacts and event_impacts[zid] > 1.2:
                state += "E"
            parts.append(f"{zid}:{state}")
        return "|".join(parts)

    def _get_state_key(
        self,
        zone_avail: dict[str, int],
        zone_totals: dict[str, int],
        event_impacts: dict[str, float] = None,
    ) -> str:
        state = self._discretize_state(zone_avail, zone_totals, event_impacts)
        if state not in self.q_table:
            self.q_table[state] = {action: 0.0 for action in ZONE_IDS}
        return state

    def select_action(
        self,
        zone_avail: dict[str, int],
        zone_totals: dict[str, int],
        entrance: str = "A",
        walk_distances: dict[str, float] = None,
        predictions: dict[str, list] = None,
        event_impacts: dict[str, float] = None,
    ) -> dict:
        state_key = self._get_state_key(zone_avail, zone_totals, event_impacts)
        q_values = self.q_table[state_key].copy()

        for zid in ZONE_IDS:
            avail = zone_avail.get(zid, 0)
            total = zone_totals.get(zid, 1)
            if avail == 0:
                q_values[zid] -= 100

            if walk_distances and zid in walk_distances:
                dist = walk_distances[zid]
                distance_penalty = -dist * WALK_DISTANCE_WEIGHT
                q_values[zid] += distance_penalty

            if event_impacts and zid in event_impacts and event_impacts[zid] > 1.2:
                q_values[zid] -= 15 * (event_impacts[zid] - 1)

            if predictions and zid in predictions:
                preds = predictions[zid]
                if preds:
                    predicted_avail = preds[-1].get("available_spots", 0)
                    if predicted_avail < 2:
                        q_values[zid] -= 20
                    elif predicted_avail > 5:
                        q_values[zid] += 5

        if np.random.random() < EPSILON:
            valid_zones = [z for z in ZONE_IDS if zone_avail.get(z, 0) > 0]
            if valid_zones:
                chosen = np.random.choice(valid_zones)
            else:
                chosen = np.random.choice(ZONE_IDS)
        else:
            max_q = max(q_values.values())
            best_actions = [a for a, v in q_values.items() if v == max_q]
            chosen = np.random.choice(best_actions)

        confidence = self._compute_confidence(state_key, chosen)
        reason = self._generate_reason(chosen, zone_avail, walk_distances, predictions, event_impacts)
        utility_score = self._compute_utility_score(chosen, zone_avail, zone_totals, walk_distances or {})

        alternatives = []
        sorted_actions = sorted(q_values.items(), key=lambda x: x[1], reverse=True)
        for zid, score in sorted_actions:
            if zid != chosen:
                alt_reason = self._generate_reason(zid, zone_avail, walk_distances, predictions, event_impacts)
                norm_score = max(0, min(1, (score + 100) / 150))
                alt_utility = self._compute_utility_score(zid, zone_avail, zone_totals, walk_distances or {})
                alternatives.append({
                    "zone_id": zid,
                    "score": round(norm_score, 3),
                    "utility_score": alt_utility,
                    "reason": alt_reason,
                })

        return {
            "recommended_zone": chosen,
            "estimated_wait_minutes": self._estimate_wait(chosen, zone_avail, zone_totals, predictions),
            "confidence": round(confidence, 3),
            "walking_distance": walk_distances.get(chosen, 50) if walk_distances else 50,
            "reason": reason,
            "alternatives": alternatives[:4],
            "utility_score": utility_score,
            "q_values": {k: round(v, 2) for k, v in q_values.items()},
        }

    def _compute_confidence(self, state_key: str, action: str) -> float:
        q_vals = self.q_table[state_key]
        max_q = max(q_vals.values())
        min_q = min(q_vals.values())
        if max_q == min_q:
            return 0.5
        return (q_vals[action] - min_q) / (max_q - min_q + 1e-6)

    def _estimate_wait(
        self, zone_id: str, zone_avail: dict[str, int],
        zone_totals: dict[str, int], predictions: dict[str, list]
    ) -> float:
        avail = zone_avail.get(zone_id, 0)
        if avail > 3:
            return 0.0
        if predictions and zone_id in predictions:
            preds = predictions[zone_id]
            for i, p in enumerate(preds):
                if p.get("available_spots", 0) >= 1:
                    return (i + 1) * 5.0
        return 15.0

    def _generate_reason(
        self, zone_id: str, zone_avail: dict[str, int],
        walk_distances: dict[str, float], predictions: dict[str, list],
        event_impacts: dict[str, float] = None,
    ) -> str:
        avail = zone_avail.get(zone_id, 0)
        total = zone_avail.get(zone_id, 0)
        parts = [f"{zone_id}区当前{avail}个空位"]
        if walk_distances and zone_id in walk_distances:
            dist = walk_distances[zone_id]
            if dist < 50:
                parts.append("步行距离较近")
            elif dist < 100:
                parts.append("步行距离适中")
            else:
                parts.append("步行距离较远")
        if predictions and zone_id in predictions:
            preds = predictions[zone_id]
            if preds:
                future = preds[-1].get("available_spots", 0)
                if future > avail:
                    parts.append("预测空位将增加")
                elif future < avail:
                    parts.append("预测空位将减少")
        if event_impacts and zone_id in event_impacts and event_impacts[zone_id] > 1.2:
            parts.append("受活动影响车位紧张")
        return "，".join(parts)

    def _calculate_reward(
        self,
        success: bool,
        recommended_zone: str,
        actual_zone: str,
        walking_distance: float,
    ) -> float:
        if success and recommended_zone == actual_zone:
            base_reward = SUCCESS_REWARD_BASE
            distance_penalty = -DISTANCE_PENALTY_SCALE * walking_distance
            distance_penalty = max(MAX_DISTANCE_PENALTY, distance_penalty)
            return base_reward + distance_penalty
        else:
            return FAILURE_PENALTY

    async def update(self, state_key: str, action: str, reward: float, next_state_key: str):
        if state_key not in self.q_table:
            self.q_table[state_key] = {a: 0.0 for a in ZONE_IDS}
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = {a: 0.0 for a in ZONE_IDS}

        current_q = self.q_table[state_key][action]
        max_next_q = max(self.q_table[next_state_key].values())
        new_q = current_q + LEARNING_RATE * (reward + DISCOUNT_FACTOR * max_next_q - current_q)
        self.q_table[state_key][action] = new_q
        self._save_q_table()

    async def record_feedback(
        self,
        recommended_zone: str,
        actual_zone: str,
        entrance: str,
        success: bool,
        walking_distance: float = 0,
    ):
        db = await get_db()
        try:
            conf = 0.5 if success else 0.0
            await db.execute(
                "INSERT INTO guidance_logs (recommended_zone, actual_zone, confidence, entrance, walking_distance) VALUES (?, ?, ?, ?, ?)",
                (recommended_zone, actual_zone, conf, entrance, walking_distance),
            )
            await db.commit()
        finally:
            await db.close()

        reward = self._calculate_reward(success, recommended_zone, actual_zone, walking_distance)
        state_key = "feedback_state"
        next_state_key = "feedback_next"
        await self.update(state_key, recommended_zone, reward, next_state_key)

    async def get_strategy_stats(self) -> dict:
        db = await get_db()
        try:
            async with db.execute(
                "SELECT recommended_zone, COUNT(*) as cnt FROM guidance_logs GROUP BY recommended_zone"
            ) as cursor:
                zone_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            async with db.execute(
                "SELECT COUNT(*) FROM guidance_logs WHERE recommended_zone = actual_zone"
            ) as cursor:
                row = await cursor.fetchone()
                success_count = row[0] if row else 0

            async with db.execute("SELECT COUNT(*) FROM guidance_logs") as cursor:
                row = await cursor.fetchone()
                total_count = row[0] if row else 0

            async with db.execute(
                "SELECT AVG(walking_distance), recommended_zone FROM guidance_logs WHERE walking_distance > 0 GROUP BY recommended_zone"
            ) as cursor:
                rows = await cursor.fetchall()
                avg_distances = {row[1]: round(row[0], 1) for row in rows}

            return {
                "zone_distribution": zone_counts,
                "success_rate": round(success_count / max(total_count, 1), 3),
                "total_guidance": total_count,
                "avg_walking_distances": avg_distances,
            }
        finally:
            await db.close()
