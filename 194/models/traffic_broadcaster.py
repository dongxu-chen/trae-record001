import numpy as np
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, PRED_HORIZONS, CONGESTION_MIN, CONGESTION_MAX


class TrafficBroadcaster:
    def __init__(self):
        self.congestion_levels = [
            (0, 2, "非常顺畅", "green"),
            (2, 4, "轻微拥堵", "yellow"),
            (4, 6, "中度拥堵", "orange"),
            (6, 8, "严重拥堵", "red"),
            (8, 10, "极度严重", "darkred"),
        ]

    def get_congestion_level(self, value):
        for low, high, name, color in self.congestion_levels:
            if low <= value < high:
                return name, color
        return "极度严重", "darkred"

    def analyze_trend(self, historical_data, predictions, road_id):
        if len(historical_data) == 0:
            return "stable", 0.0

        recent_avg = np.mean(historical_data[-3:]) if len(historical_data) >= 3 else historical_data[0]
        future_avg = np.mean(predictions[road_id])

        diff = future_avg - recent_avg

        if diff > 1.5:
            trend = "worsening_rapidly"
        elif diff > 0.5:
            trend = "worsening"
        elif diff < -1.5:
            trend = "improving_rapidly"
        elif diff < -0.5:
            trend = "improving"
        else:
            trend = "stable"

        return trend, diff

    def generate_hourly_broadcast(self, predictions, timestamps, road_ids, current_time=None):
        if current_time is None:
            current_time = datetime.now()

        unique_times = sorted(list(set(timestamps)))
        if len(unique_times) == 0:
            return "暂无路况数据"

        time_idx = min(len(unique_times) - 1, 0)
        target_time = unique_times[time_idx]

        broadcast = f"【路况播报】{current_time.strftime('%Y年%m月%d日 %H点%M分')}\n\n"
        broadcast += f"现在为您播报{target_time.strftime('%H:%M')}的路况预测\n\n"

        overall_stats = self._get_overall_stats(predictions, timestamps, road_ids, time_idx)
        broadcast += f"📊 整体路况：{overall_stats['overall_level']}\n"
        broadcast += f"   平均拥堵指数：{overall_stats['avg_congestion']:.2f}\n"
        broadcast += f"   拥堵路段：{overall_stats['congested_count']}/{NUM_ROADS} 条\n\n"

        hotspots = self._get_hotspots(predictions, timestamps, road_ids, time_idx, top_k=3)
        if hotspots:
            broadcast += "⚠️  拥堵热点：\n"
            for i, (road_id, congestion) in enumerate(hotspots, 1):
                level, _ = self.get_congestion_level(congestion)
                broadcast += f"   {i}. 路段{road_id}：{level} ({congestion:.1f})\n"
            broadcast += "\n"

        smooth_roads = self._get_smooth_roads(predictions, timestamps, road_ids, time_idx, top_k=3)
        if smooth_roads:
            broadcast += "✅ 推荐通行：\n"
            for i, (road_id, congestion) in enumerate(smooth_roads, 1):
                level, _ = self.get_congestion_level(congestion)
                broadcast += f"   {i}. 路段{road_id}：{level} ({congestion:.1f})\n"
            broadcast += "\n"

        future_outlook = self._generate_future_outlook(predictions, road_ids)
        broadcast += f"🔮 趋势预测：{future_outlook}\n\n"

        broadcast += "祝您出行顺利，一路平安！"

        return broadcast

    def _get_overall_stats(self, predictions, timestamps, road_ids, time_idx):
        target_time = sorted(list(set(timestamps)))[time_idx]
        mask = timestamps == target_time
        preds_at_time = predictions[mask]

        avg_congestion = np.mean(preds_at_time)
        congested_count = np.sum(preds_at_time > 4)
        overall_level, _ = self.get_congestion_level(avg_congestion)

        return {
            "avg_congestion": avg_congestion,
            "congested_count": congested_count,
            "overall_level": overall_level,
        }

    def _get_hotspots(self, predictions, timestamps, road_ids, time_idx, top_k=5):
        target_time = sorted(list(set(timestamps)))[time_idx]
        mask = timestamps == target_time
        roads_at_time = road_ids[mask]
        preds_at_time = predictions[mask]

        sorted_indices = np.argsort(-preds_at_time[:, 0])
        hotspots = []
        for i in sorted_indices[:top_k]:
            if preds_at_time[i, 0] > 4:
                hotspots.append((int(roads_at_time[i]), float(preds_at_time[i, 0])))
        return hotspots

    def _get_smooth_roads(self, predictions, timestamps, road_ids, time_idx, top_k=5):
        target_time = sorted(list(set(timestamps)))[time_idx]
        mask = timestamps == target_time
        roads_at_time = road_ids[mask]
        preds_at_time = predictions[mask]

        sorted_indices = np.argsort(preds_at_time[:, 0])
        smooth = []
        for i in sorted_indices[:top_k]:
            if preds_at_time[i, 0] < 4:
                smooth.append((int(roads_at_time[i]), float(preds_at_time[i, 0])))
        return smooth

    def _generate_future_outlook(self, predictions, road_ids):
        avg_15 = np.mean(predictions[:, 0])
        avg_30 = np.mean(predictions[:, 1])
        avg_60 = np.mean(predictions[:, 2])

        if avg_60 > avg_30 > avg_15 and avg_60 - avg_15 > 1:
            return "预计未来1小时拥堵将逐渐加重，请错峰出行"
        elif avg_60 < avg_30 < avg_15 and avg_15 - avg_60 > 1:
            return "预计未来1小时路况将逐渐好转，可以正常出行"
        elif max(avg_15, avg_30, avg_60) - min(avg_15, avg_30, avg_60) < 0.5:
            return "预计未来1小时路况整体保持稳定"
        else:
            return "预计未来1小时路况有波动，请关注实时更新"

    def generate_road_broadcast(self, road_id, predictions, historical_data=None):
        if road_id >= len(predictions):
            return f"路段{road_id}暂无数据"

        pred_15, pred_30, pred_60 = predictions[road_id]

        level_15, color_15 = self.get_congestion_level(pred_15)
        level_30, color_30 = self.get_congestion_level(pred_30)
        level_60, color_60 = self.get_congestion_level(pred_60)

        broadcast = f"【路段{road_id}路况播报】\n\n"
        broadcast += f"🕐 15分钟后：{level_15}（指数 {pred_15:.1f}）\n"
        broadcast += f"🕑 30分钟后：{level_30}（指数 {pred_30:.1f}）\n"
        broadcast += f"🕒 60分钟后：{level_60}（指数 {pred_60:.1f}）\n\n"

        trend_text = self._generate_road_trend_text(pred_15, pred_30, pred_60)
        broadcast += f"📈 趋势分析：{trend_text}\n\n"

        if pred_15 > 6:
            broadcast += "⚠️  建议：当前拥堵严重，建议绕行或错峰出行\n"
        elif pred_15 > 4:
            broadcast += "⚠️  建议：当前行驶缓慢，请保持车距\n"
        else:
            broadcast += "✅ 建议：路况良好，可正常通行\n"

        return broadcast

    def _generate_road_trend_text(self, p15, p30, p60):
        if p60 > p30 > p15 and p60 - p15 > 1:
            return f"拥堵持续加重，60分钟后指数预计上升{(p60 - p15):.1f}"
        elif p60 < p30 < p15 and p15 - p60 > 1:
            return f"拥堵逐渐缓解，60分钟后指数预计下降{(p15 - p60):.1f}"
        elif p30 > p15 and p60 < p30:
            return f"先加重后缓解，30分钟左右达到峰值"
        elif p30 < p15 and p60 > p30:
            return f"先缓解后加重，30分钟左右最为顺畅"
        else:
            return "整体保持稳定，波动不大"

    def generate_push_notification(self, predictions, timestamps, road_ids, user_route=None):
        current_time = datetime.now()

        unique_times = sorted(list(set(timestamps)))
        if len(unique_times) == 0:
            return []

        notifications = []

        hotspots = self._get_hotspots(predictions, timestamps, road_ids, 0, top_k=3)
        if hotspots and hotspots[0][1] > 7:
            notifications.append({
                "type": "alert",
                "title": "严重拥堵预警",
                "body": f"路段{hotspots[0][0]}出现严重拥堵（指数{hotspots[0][1]:.1f}），请绕行",
                "priority": "high",
                "time": current_time.strftime("%H:%M")
            })

        if user_route:
            start, end = user_route
            route_congestion = self._check_route_congestion(start, end, predictions, road_ids, timestamps)
            if route_congestion > 5:
                notifications.append({
                    "type": "route",
                    "title": "路线拥堵提醒",
                    "body": f"您的常用路线预计{route_congestion:.1f}，建议选择备选路线",
                    "priority": "medium",
                    "time": current_time.strftime("%H:%M")
                })

        overall = self._get_overall_stats(predictions, timestamps, road_ids, 0)
        notifications.append({
            "type": "summary",
            "title": f"{current_time.strftime('%H:%M')}路况概况",
            "body": f"整体{overall['overall_level']}，{overall['congested_count']}条路段拥堵",
            "priority": "low",
            "time": current_time.strftime("%H:%M")
        })

        return notifications

    def _check_route_congestion(self, start, end, predictions, road_ids, timestamps):
        target_time = sorted(list(set(timestamps)))[0]
        mask = timestamps == target_time

        roads_on_route = list(range(min(start, end), max(start, end) + 1))
        total_congestion = 0.0
        count = 0

        for road_id in roads_on_route:
            road_mask = mask & (road_ids == road_id)
            if np.any(road_mask):
                total_congestion += predictions[road_mask, 0][0]
                count += 1

        return total_congestion / max(count, 1) if count > 0 else 0.0

    def generate_voice_broadcast_text(self, predictions, timestamps, road_ids, current_time=None):
        if current_time is None:
            current_time = datetime.now()

        unique_times = sorted(list(set(timestamps)))
        if len(unique_times) == 0:
            return "暂无路况数据"

        overall = self._get_overall_stats(predictions, timestamps, road_ids, 0)
        hotspots = self._get_hotspots(predictions, timestamps, road_ids, 0, top_k=3)

        text = f"各位听众好，现在是{current_time.strftime('%H点%M分')}的交通路况播报。"

        text += f"整体路况{overall['overall_level']}，"
        text += f"平均拥堵指数{overall['avg_congestion']:.1f}，"
        text += f"目前有{overall['congested_count']}条路段出现拥堵。"

        if hotspots:
            text += "需要注意的拥堵路段有："
            hotspot_descriptions = []
            for road_id, congestion in hotspots:
                level, _ = self.get_congestion_level(congestion)
                hotspot_descriptions.append(f"路段{road_id}{level}")
            text += "、".join(hotspot_descriptions) + "。"

        future_outlook = self._generate_future_outlook(predictions, road_ids)
        text += f"趋势方面，{future_outlook}。"

        text += "以上就是本时段的路况播报，感谢收听，祝您出行顺利。"

        return text

    def save_broadcast_to_file(self, broadcast, output_dir, filename=None):
        os.makedirs(output_dir, exist_ok=True)
        if filename is None:
            filename = f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(broadcast)
        print(f"Saved broadcast to {filepath}")
        return filepath


if __name__ == "__main__":
    broadcaster = TrafficBroadcaster()

    predictions = np.random.uniform(0, 10, (NUM_ROADS, 3))
    timestamps = np.array([datetime(2024, 1, 1, 8, 0) for _ in range(NUM_ROADS)])
    road_ids = np.arange(NUM_ROADS)

    broadcast = broadcaster.generate_hourly_broadcast(predictions, timestamps, road_ids)
    print(broadcast)

    print("\n" + "=" * 60)
    print("语音播报文本:")
    voice_text = broadcaster.generate_voice_broadcast_text(predictions, timestamps, road_ids)
    print(voice_text)

    print("\n" + "=" * 60)
    print("推送通知:")
    notifications = broadcaster.generate_push_notification(predictions, timestamps, road_ids, user_route=(0, 10))
    for notif in notifications:
        print(f"[{notif['priority'].upper()}] {notif['title']}: {notif['body']}")
