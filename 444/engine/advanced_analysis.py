from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import defaultdict
from datetime import timedelta

from utils.helpers import parse_utc_datetime, get_utc_now


class BoughtFollowerDetector:
    def __init__(self, time_window_days: int = 7, burst_threshold: float = 2.0):
        self.time_window_days = time_window_days
        self.burst_threshold = burst_threshold

    def analyze_registration_pattern(self, followers: List[dict]) -> dict:
        reg_dates = []
        for f in followers:
            date_str = f.get("registration_date")
            parsed = parse_utc_datetime(date_str)
            if parsed:
                reg_dates.append((parsed, f.get("user_id", "")))

        if not reg_dates:
            return {
                "has_burst_pattern": False,
                "burst_score": 0.0,
                "peak_concentration_ratio": 0.0,
                "bursts": [],
                "new_account_ratio": 0.0,
                "avg_account_age_days": 0.0,
            }

        now = get_utc_now()
        ages = [(now - d[0]).days for d in reg_dates]
        avg_age = float(np.mean(ages)) if ages else 0.0

        new_accounts = sum(1 for age in ages if age < 30)
        new_account_ratio = new_accounts / max(len(ages), 1)

        sorted_dates = sorted(reg_dates, key=lambda x: x[0])
        oldest_date = sorted_dates[0][0]
        days_span = max((sorted_dates[-1][0] - oldest_date).days, 1)

        bursts = self._find_registration_bursts(sorted_dates)
        burst_score = self._calculate_burst_score(bursts, len(reg_dates))
        peak_ratio = self._calculate_peak_concentration(ages, days_span)

        has_burst = burst_score > self.burst_threshold or peak_ratio > 0.5

        return {
            "has_burst_pattern": has_burst,
            "burst_score": burst_score,
            "peak_concentration_ratio": peak_ratio,
            "bursts": bursts,
            "new_account_ratio": new_account_ratio,
            "avg_account_age_days": avg_age,
            "total_analyzed": len(reg_dates),
            "days_span": days_span,
        }

    def _find_registration_bursts(self, sorted_dates: List[Tuple]) -> List[dict]:
        bursts = []
        if len(sorted_dates) < 5:
            return bursts

        window_days = 7
        n = len(sorted_dates)

        for i in range(n):
            window_start = sorted_dates[i][0]
            window_end = window_start + timedelta(days=window_days)

            j = i
            while j < n and sorted_dates[j][0] <= window_end:
                j += 1

            window_count = j - i
            if window_count >= 5:
                expected_rate = n / max((sorted_dates[-1][0] - sorted_dates[0][0]).days, 1) * window_days
                if window_count > expected_rate * 1.5:
                    burst_users = [d[1] for d in sorted_dates[i:j]]
                    bursts.append({
                        "start_date": window_start.isoformat(),
                        "end_date": window_end.isoformat(),
                        "account_count": window_count,
                        "user_ids": burst_users,
                        "over_expected_ratio": window_count / max(expected_rate, 1),
                    })

        merged_bursts = []
        for burst in bursts:
            if not merged_bursts:
                merged_bursts.append(burst)
            else:
                last = merged_bursts[-1]
                if (parse_utc_datetime(burst["start_date"]) - parse_utc_datetime(last["end_date"])).days < 3:
                    last["end_date"] = burst["end_date"]
                    last["account_count"] = max(last["account_count"], burst["account_count"])
                    last["user_ids"] = list(set(last["user_ids"] + burst["user_ids"]))
                else:
                    merged_bursts.append(burst)

        return merged_bursts[:5]

    def _calculate_burst_score(self, bursts: List[dict], total_accounts: int) -> float:
        if not bursts or total_accounts == 0:
            return 0.0

        burst_accounts = sum(b["account_count"] for b in bursts)
        burst_ratio = burst_accounts / total_accounts
        avg_over_expected = np.mean([b["over_expected_ratio"] for b in bursts]) if bursts else 0

        return burst_ratio * avg_over_expected * 10

    def _calculate_peak_concentration(self, ages: List[int], days_span: int) -> float:
        if not ages or days_span == 0:
            return 0.0

        n_bins = min(20, max(days_span // 7, 5))
        hist, _ = np.histogram(ages, bins=n_bins)
        peak_count = hist.max()
        expected_per_bin = len(ages) / n_bins

        return peak_count / max(expected_per_bin, 1)

    def get_bought_follower_score(self, followers: List[dict]) -> float:
        analysis = self.analyze_registration_pattern(followers)

        score = 0.0
        if analysis["has_burst_pattern"]:
            score += min(analysis["burst_score"], 0.4)
        score += min(analysis["new_account_ratio"] * 0.5, 0.3)
        if analysis["avg_account_age_days"] < 60:
            score += 0.15
        if analysis["peak_concentration_ratio"] > 2.0:
            score += 0.15

        return min(score, 1.0)


class InteractionQualityAnalyzer:
    def __init__(self):
        pass

    def analyze_interaction_patterns(
        self,
        followers: List[dict],
        interactions: Optional[List[dict]] = None,
    ) -> dict:
        scores = {}
        all_metrics = []

        for follower in followers:
            metrics = self._calculate_interaction_metrics(follower, interactions)
            scores[follower.get("user_id", "")] = metrics
            all_metrics.append(metrics)

        avg_quality = float(np.mean([m["quality_score"] for m in all_metrics])) if all_metrics else 0.0

        low_quality_count = sum(1 for m in all_metrics if m["quality_score"] < 0.3)
        high_quality_count = sum(1 for m in all_metrics if m["quality_score"] > 0.7)

        return {
            "avg_quality_score": avg_quality,
            "low_quality_ratio": low_quality_count / max(len(all_metrics), 1),
            "high_quality_ratio": high_quality_count / max(len(all_metrics), 1),
            "follower_scores": scores,
            "total_analyzed": len(all_metrics),
        }

    def _calculate_interaction_metrics(
        self,
        follower: dict,
        interactions: Optional[List[dict]] = None,
    ) -> dict:
        score = 0.0
        flags = []

        engagement_rate = follower.get("engagement_rate", 0.0)
        if engagement_rate > 0.05:
            score += 0.25
        elif engagement_rate > 0.02:
            score += 0.15
        elif engagement_rate < 0.005:
            score -= 0.15
            flags.append("极低互动率")
        else:
            score += 0.05

        content_diversity = follower.get("content_diversity", 0.0)
        if content_diversity > 0.7:
            score += 0.25
        elif content_diversity > 0.4:
            score += 0.15
        elif content_diversity < 0.2:
            score -= 0.15
            flags.append("内容多样性低")
        else:
            score += 0.05

        repost_ratio = follower.get("repost_ratio", 0.0)
        if repost_ratio < 0.3:
            score += 0.2
        elif repost_ratio < 0.6:
            score += 0.1
        elif repost_ratio > 0.8:
            score -= 0.15
            flags.append("高转发比")
        else:
            score -= 0.05

        mention_ratio = follower.get("mention_ratio", 0.0)
        if 0.1 < mention_ratio < 0.5:
            score += 0.15
        elif mention_ratio < 0.02:
            score -= 0.1
            flags.append("极少提及他人")
        elif mention_ratio > 0.8:
            score -= 0.05

        hashtag_ratio = follower.get("hashtag_ratio", 0.0)
        if hashtag_ratio < 0.2:
            score += 0.1
        elif hashtag_ratio > 0.6:
            score -= 0.1
            flags.append("过多话题标签")

        activity_regularity = follower.get("activity_regularity", 0.5)
        if activity_regularity > 0.7:
            score += 0.15
        elif activity_regularity < 0.3:
            score -= 0.1
            flags.append("活动模式异常")

        duplicate_ratio = follower.get("duplicate_content_ratio", 0.0)
        if duplicate_ratio < 0.1:
            score += 0.1
        elif duplicate_ratio > 0.5:
            score -= 0.2
            flags.append("重复内容过多")

        avg_daily_posts = follower.get("avg_daily_posts", 0.0)
        if 0.1 < avg_daily_posts < 10:
            score += 0.1
        elif avg_daily_posts > 50:
            score -= 0.15
            flags.append("发帖频率异常")

        normalized_score = np.clip((score + 1.0) / 2.0, 0.0, 1.0)

        return {
            "quality_score": float(normalized_score),
            "engagement_component": float(np.clip(engagement_rate * 10, 0, 0.3)),
            "content_originality": float(np.clip(1 - repost_ratio - duplicate_ratio, 0, 0.3)),
            "interaction_naturalness": float(np.clip(mention_ratio * 2, 0, 0.2)),
            "activity_pattern": float(np.clip(activity_regularity, 0, 0.2)),
            "flags": flags,
        }

    def identify_bot_interactions(
        self,
        followers: List[dict],
        threshold: float = 0.3,
    ) -> List[str]:
        analysis = self.analyze_interaction_patterns(followers)
        bot_ids = []
        for user_id, metrics in analysis["follower_scores"].items():
            if metrics["quality_score"] < threshold:
                bot_ids.append(user_id)
        return bot_ids

    def get_quality_buckets(self, followers: List[dict]) -> Dict[str, int]:
        analysis = self.analyze_interaction_patterns(followers)
        buckets = {
            "very_low": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "very_high": 0,
        }
        for metrics in analysis["follower_scores"].values():
            score = metrics["quality_score"]
            if score < 0.2:
                buckets["very_low"] += 1
            elif score < 0.4:
                buckets["low"] += 1
            elif score < 0.6:
                buckets["medium"] += 1
            elif score < 0.8:
                buckets["high"] += 1
            else:
                buckets["very_high"] += 1
        return buckets
