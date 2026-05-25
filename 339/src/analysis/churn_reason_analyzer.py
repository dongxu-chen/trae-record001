import os
import sys
import time
import re
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from common.logger import get_logger
from common.utils import load_config, safe_divide

logger = get_logger("ChurnReasonAnalyzer")


@dataclass
class FeedbackEntry:
    feedback_id: str
    user_id: str
    feedback_type: str
    content: str
    timestamp: float
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    topics: List[str] = field(default_factory=list)
    severity: int = 2
    resolved: bool = False
    resolution_time_hours: float = 0.0


@dataclass
class TicketEntry:
    ticket_id: str
    user_id: str
    category: str
    subcategory: str
    description: str
    priority: str
    status: str
    created_at: float
    closed_at: Optional[float] = None
    resolution_time_hours: float = 0.0
    sentiment: str = "neutral"
    churn_correlation: float = 0.0


@dataclass
class ChurnReason:
    reason_code: str
    reason_name: str
    category: str
    count: int
    percentage: float
    churn_rate: float
    avg_days_to_churn: float
    severity: float
    trend: str
    keywords: List[str]


CHURN_TOPIC_KEYWORDS = {
    "pricing": ["price", "cost", "expensive", "too much", "fee", "subscription", "renewal", "value", "worth", "cheap"],
    "product_issues": ["bug", "crash", "error", "broken", "not working", "slow", "glitch", "freeze", "technical", "issue"],
    "customer_service": ["support", "customer service", "help", "response", "slow support", "unhelpful", "rude", "no response", "ignored", "ticket"],
    "feature_request": ["feature", "missing", "need", "want", "should have", "lack of", "limited", "not enough", "can't", "cannot"],
    "ux_problems": ["confusing", "hard to use", "difficult", "interface", "ui", "ux", "complicated", "counterintuitive", "annoying", "frustrating"],
    "billing_issues": ["billing", "charge", "overcharged", "double charge", "refund", "payment", "credit card", "invoice", "wrong charge", "unauthorized"],
    "competition": ["competitor", "switch", "better", "alternative", "cheaper", "moved to", "left for", "another", "other service", "offered"],
    "content_quality": ["content", "quality", "selection", "variety", "not enough", "outdated", "boring", "repetitive", "irrelevant", "uninteresting"],
    "privacy_concerns": ["privacy", "security", "data", "spam", "ads", "tracking", "personal information", "sold", "leaked", "breach"],
    "onboarding": ["onboarding", "setup", "installation", "getting started", "tutorial", "guide", "documentation", "help", "confusing", "difficult"],
    "reliability": ["reliability", "uptime", "downtime", "unavailable", "service down", "connection", "disconnect", "loading", "lag", "timeout"],
    "communication": ["communication", "email", "notification", "too many", "annoying", "spam", "no update", "silent", "newsletter", "marketing"]
}

SENTIMENT_WORDS = {
    "positive": ["good", "great", "excellent", "love", "amazing", "best", "wonderful", "fantastic", "nice", "happy",
                "satisfied", "impressed", "helpful", "responsive", "quick", "easy", "simple", "perfect", "recommend", "5 star"],
    "negative": ["bad", "terrible", "awful", "hate", "worst", "horrible", "disappointed", "frustrated", "angry", "sad",
                "unsatisfied", "unimpressed", "unhelpful", "slow", "hard", "difficult", "broken", "useless", "waste", "1 star"]
}

CHURN_REASON_CATEGORIES = {
    "product": ["product_issues", "ux_problems", "reliability", "feature_request", "content_quality"],
    "service": ["customer_service", "billing_issues", "onboarding", "communication"],
    "business": ["pricing", "competition", "privacy_concerns"]
}


class ChurnReasonAnalyzer:
    def __init__(self, cache_manager=None):
        self.config = load_config()
        self.cache = cache_manager
        
        self.feedback_entries: List[FeedbackEntry] = []
        self.ticket_entries: List[TicketEntry] = []
        self.user_feedback: Dict[str, List[FeedbackEntry]] = defaultdict(list)
        self.user_tickets: Dict[str, List[TicketEntry]] = defaultdict(list)
        
        self.churn_reasons: Dict[str, ChurnReason] = {}
        self.topic_trends: Dict[str, List[float]] = defaultdict(list)
        
        self.analysis_window_days = self.config.get("analysis", {}).get(
            "churn_reason_window_days", 60
        )
        self.min_topic_count = self.config.get("analysis", {}).get(
            "min_topic_count", 5
        )
        
        logger.info("ChurnReasonAnalyzer initialized")

    def add_feedback(self, feedback_id: str, user_id: str, feedback_type: str,
                    content: str, timestamp: Optional[float] = None) -> FeedbackEntry:
        timestamp = timestamp or time.time()
        
        topics = self._extract_topics(content)
        sentiment, score = self._analyze_sentiment(content)
        severity = self._calculate_severity(topics, sentiment)
        
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            user_id=user_id,
            feedback_type=feedback_type,
            content=content,
            timestamp=timestamp,
            sentiment=sentiment,
            sentiment_score=score,
            topics=topics,
            severity=severity
        )
        
        self.feedback_entries.append(entry)
        self.user_feedback[user_id].append(entry)
        return entry

    def add_ticket(self, ticket_id: str, user_id: str, category: str,
                   subcategory: str, description: str, priority: str,
                   status: str, created_at: float,
                   closed_at: Optional[float] = None) -> TicketEntry:
        resolution_time = ((closed_at - created_at) / 3600) if closed_at else 0.0
        
        sentiment, score = self._analyze_sentiment(description)
        
        ticket = TicketEntry(
            ticket_id=ticket_id,
            user_id=user_id,
            category=category,
            subcategory=subcategory,
            description=description,
            priority=priority,
            status=status,
            created_at=created_at,
            closed_at=closed_at,
            resolution_time_hours=float(resolution_time),
            sentiment=sentiment
        )
        
        self.ticket_entries.append(ticket)
        self.user_tickets[user_id].append(ticket)
        return ticket

    def _extract_topics(self, text: str) -> List[str]:
        text_lower = text.lower()
        topics = []
        
        for topic, keywords in CHURN_TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    topics.append(topic)
                    break
        
        return list(set(topics))

    def _analyze_sentiment(self, text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        positive_count = 0
        negative_count = 0
        
        for word in SENTIMENT_WORDS["positive"]:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                positive_count += 1
        
        for word in SENTIMENT_WORDS["negative"]:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                negative_count += 1
        
        total = positive_count + negative_count
        if total == 0:
            return "neutral", 0.0
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            return "positive", score
        elif score < -0.2:
            return "negative", score
        else:
            return "neutral", score

    def _calculate_severity(self, topics: List[str], sentiment: str) -> int:
        base_severity = 2
        
        high_risk_topics = ["billing_issues", "privacy_concerns", "reliability", "customer_service"]
        for topic in topics:
            if topic in high_risk_topics:
                base_severity += 1
        
        if sentiment == "negative":
            base_severity += 1
        elif sentiment == "very_negative":
            base_severity += 2
        
        return min(base_severity, 5)

    def analyze_churn_reasons(self, user_churn_data: List[Dict]) -> Dict[str, Any]:
        if not NUMPY_AVAILABLE:
            return {"error": "numpy/pandas not available"}
        
        churned_users = set(u["user_id"] for u in user_churn_data if u.get("churned", False))
        active_users = set(u["user_id"] for u in user_churn_data if not u.get("churned", False))
        
        topic_counts_churned = Counter()
        topic_counts_active = Counter()
        
        user_topics: Dict[str, List[str]] = defaultdict(list)
        
        for feedback in self.feedback_entries:
            for topic in feedback.topics:
                user_topics[feedback.user_id].append(topic)
                if feedback.user_id in churned_users:
                    topic_counts_churned[topic] += 1
                elif feedback.user_id in active_users:
                    topic_counts_active[topic] += 1
        
        for ticket in self.ticket_entries:
            topic = ticket.category.lower().replace(" ", "_")
            if topic not in CHURN_TOPIC_KEYWORDS:
                topic = self._match_topic_to_category(ticket.description)
            if topic:
                user_topics[ticket.user_id].append(topic)
                if ticket.user_id in churned_users:
                    topic_counts_churned[topic] += 1
                elif ticket.user_id in active_users:
                    topic_counts_active[topic] += 1
        
        all_topics = set(list(topic_counts_churned.keys()) + list(topic_counts_active.keys()))
        
        results = {
            "overall": {
                "total_feedback": len(self.feedback_entries),
                "total_tickets": len(self.ticket_entries),
                "churned_users_analyzed": len(churned_users),
                "active_users_analyzed": len(active_users),
                "avg_feedback_per_churned": safe_divide(
                    sum(len(self.user_feedback.get(u, [])) for u in churned_users),
                    len(churned_users), 0.0
                ),
                "avg_tickets_per_churned": safe_divide(
                    sum(len(self.user_tickets.get(u, [])) for u in churned_users),
                    len(churned_users), 0.0
                )
            },
            "reasons": {},
            "by_category": defaultdict(lambda: {"count": 0, "churn_rate": 0.0, "reasons": []}),
            "trending_topics": [],
            "correlation_matrix": {},
            "user_reason_map": {},
            "key_insights": []
        }
        
        for topic in all_topics:
            if topic_counts_churned[topic] + topic_counts_active[topic] < self.min_topic_count:
                continue
            
            churned_with_topic = topic_counts_churned[topic]
            active_with_topic = topic_counts_active[topic]
            total_with_topic = churned_with_topic + active_with_topic
            
            churn_rate = safe_divide(churned_with_topic, total_with_topic, 0.0)
            baseline_churn_rate = safe_divide(len(churned_users), 
                                             len(churned_users) + len(active_users), 0.0)
            
            relative_risk = safe_divide(churn_rate, baseline_churn_rate, 1.0)
            
            days_to_churn_list = []
            for user_id in churned_users:
                user_topic_list = user_topics.get(user_id, [])
                if topic in user_topic_list:
                    churn_time = next(u.get("churn_time", time.time()) for u in user_churn_data 
                                     if u["user_id"] == user_id)
                    first_occurrence = min(
                        [f.timestamp for f in self.user_feedback.get(user_id, []) 
                         if topic in f.topics] +
                        [t.created_at for t in self.user_tickets.get(user_id, []) 
                         if self._match_topic_to_category(t.description) == topic],
                        default=churn_time
                    )
                    days_to_churn = (churn_time - first_occurrence) / 86400
                    if days_to_churn > 0:
                        days_to_churn_list.append(days_to_churn)
            
            avg_days_to_churn = float(np.mean(days_to_churn_list)) if days_to_churn_list else 0.0
            
            category = self._get_topic_category(topic)
            
            reason = ChurnReason(
                reason_code=topic,
                reason_name=topic.replace("_", " ").title(),
                category=category,
                count=total_with_topic,
                percentage=safe_divide(total_with_topic, 
                                      sum(topic_counts_churned.values()) + sum(topic_counts_active.values()), 0.0),
                churn_rate=float(churn_rate),
                avg_days_to_churn=avg_days_to_churn,
                severity=float(np.mean([f.severity for f in self.feedback_entries 
                                        if topic in f.topics])) if any(topic in f.topics for f in self.feedback_entries) else 2.0,
                trend=self._calculate_trend(topic),
                keywords=CHURN_TOPIC_KEYWORDS.get(topic, [])
            )
            
            self.churn_reasons[topic] = reason
            results["reasons"][topic] = self._reason_to_dict(reason, relative_risk, baseline_churn_rate)
            
            results["by_category"][category]["count"] += total_with_topic
            results["by_category"][category]["reasons"].append(topic)
            results["by_category"][category]["churn_rate"] = max(
                results["by_category"][category]["churn_rate"], churn_rate
            )
        
        for user_id, topics in user_topics.items():
            if topics:
                topic_counter = Counter(topics)
                top_topic = topic_counter.most_common(1)[0][0]
                results["user_reason_map"][user_id] = {
                    "primary_reason": top_topic,
                    "all_topics": list(set(topics)),
                    "topic_counts": dict(topic_counter)
                }
        
        sorted_reasons = sorted(
            results["reasons"].values(),
            key=lambda x: x["churn_rate"] * x["count"],
            reverse=True
        )
        
        results["top_reasons"] = sorted_reasons[:5]
        
        high_impact_reasons = [
            r for r in sorted_reasons 
            if r["relative_risk"] > 1.5 and r["count"] >= self.min_topic_count
        ]
        
        if high_impact_reasons:
            results["key_insights"].append(
                f"Identified {len(high_impact_reasons)} high-impact churn drivers "
                f"with >50% elevated churn risk"
            )
            
            for reason in high_impact_reasons[:3]:
                results["key_insights"].append(
                    f"'{reason['reason_name']}' affects {reason['count']} users "
                    f"with {reason['churn_rate']*100:.0f}% churn rate "
                    f"({reason['relative_risk']:.1f}x baseline)"
                )
        
        negative_sentiment_ratio = safe_divide(
            sum(1 for f in self.feedback_entries if f.sentiment == "negative"),
            len(self.feedback_entries), 0.0
        )
        if negative_sentiment_ratio > 0.3:
            results["key_insights"].append(
                f"High negative sentiment in feedback ({negative_sentiment_ratio*100:.0f}%), "
                f"correlates with increased churn"
            )
        
        results["trending_topics"] = self._identify_trending_topics()
        results["correlation_matrix"] = self._build_correlation_matrix(user_topics, user_churn_data)
        
        return results

    def _match_topic_to_category(self, description: str) -> Optional[str]:
        topics = self._extract_topics(description)
        return topics[0] if topics else None

    def _get_topic_category(self, topic: str) -> str:
        for category, topics in CHURN_REASON_CATEGORIES.items():
            if topic in topics:
                return category
        return "other"

    def _calculate_trend(self, topic: str) -> str:
        counts = self.topic_trends.get(topic, [])
        if len(counts) < 2:
            return "stable"
        
        recent_avg = float(np.mean(counts[-7:]))
        older_avg = float(np.mean(counts[:7])) if len(counts) >= 14 else recent_avg
        
        if recent_avg > older_avg * 1.3:
            return "increasing"
        elif recent_avg < older_avg * 0.7:
            return "decreasing"
        else:
            return "stable"

    def _identify_trending_topics(self) -> List[Dict[str, Any]]:
        now = time.time()
        week_ago = now - 7 * 86400
        two_weeks_ago = now - 14 * 86400
        
        topic_this_week = Counter()
        topic_last_week = Counter()
        
        for feedback in self.feedback_entries:
            if feedback.timestamp > week_ago:
                for topic in feedback.topics:
                    topic_this_week[topic] += 1
            elif feedback.timestamp > two_weeks_ago:
                for topic in feedback.topics:
                    topic_last_week[topic] += 1
        
        trending = []
        all_topics = set(list(topic_this_week.keys()) + list(topic_last_week.keys()))
        
        for topic in all_topics:
            current = topic_this_week.get(topic, 0)
            previous = topic_last_week.get(topic, 0)
            
            if previous > 0:
                growth = safe_divide(current - previous, previous, 0.0)
            elif current > 0:
                growth = float('inf')
            else:
                continue
            
            if current >= self.min_topic_count and growth > 0.2:
                trending.append({
                    "topic": topic,
                    "current_count": current,
                    "previous_count": previous,
                    "growth_rate": growth,
                    "severity": self.churn_reasons.get(topic, ChurnReason("", "", "", 0, 0, 0, 0, 0, "", [])).severity
                })
        
        return sorted(trending, key=lambda x: x["growth_rate"], reverse=True)[:10]

    def _build_correlation_matrix(self, user_topics: Dict[str, List[str]], 
                                  user_churn_data: List[Dict]) -> Dict[str, Dict[str, float]]:
        topic_pairs = defaultdict(lambda: {"both": 0, "only_a": 0, "only_b": 0, "neither": 0})
        
        churned_user_set = set(u["user_id"] for u in user_churn_data if u.get("churned", False))
        
        all_topics = set()
        for topics in user_topics.values():
            all_topics.update(topics)
        
        all_topics = list(all_topics)
        
        correlation_matrix = {}
        for i, topic_a in enumerate(all_topics):
            correlation_matrix[topic_a] = {}
            for j, topic_b in enumerate(all_topics):
                if i == j:
                    correlation_matrix[topic_a][topic_b] = 1.0
                    continue
                
                both = 0
                only_a = 0
                only_b = 0
                neither = 0
                
                for user_id, topics in user_topics.items():
                    has_a = topic_a in topics
                    has_b = topic_b in topics
                    
                    if has_a and has_b:
                        both += 1
                    elif has_a:
                        only_a += 1
                    elif has_b:
                        only_b += 1
                    else:
                        neither += 1
                
                total = both + only_a + only_b + neither
                if total == 0:
                    correlation_matrix[topic_a][topic_b] = 0.0
                    continue
                
                p_a = (both + only_a) / total
                p_b = (both + only_b) / total
                p_ab = both / total
                
                if p_a * p_b == 0:
                    correlation_matrix[topic_a][topic_b] = 0.0
                else:
                    correlation_matrix[topic_a][topic_b] = round(p_ab / (p_a * p_b), 2)
        
        return correlation_matrix

    def _reason_to_dict(self, reason: ChurnReason, relative_risk: float, 
                        baseline_churn_rate: float) -> Dict[str, Any]:
        return {
            "reason_code": reason.reason_code,
            "reason_name": reason.reason_name,
            "category": reason.category,
            "count": reason.count,
            "percentage": reason.percentage,
            "churn_rate": reason.churn_rate,
            "churn_rate_percentage": f"{reason.churn_rate*100:.0f}%",
            "baseline_churn_rate": baseline_churn_rate,
            "relative_risk": float(relative_risk),
            "elevated_risk": f"+{(relative_risk-1)*100:.0f}%",
            "avg_days_to_churn": reason.avg_days_to_churn,
            "severity": reason.severity,
            "severity_label": ["Very Low", "Low", "Medium", "High", "Critical"][min(int(reason.severity) - 1, 4)],
            "trend": reason.trend,
            "top_keywords": reason.keywords[:5]
        }

    def generate_churn_reason_report(self) -> Dict[str, Any]:
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_window_days": self.analysis_window_days,
            "data_summary": {
                "total_feedback": len(self.feedback_entries),
                "total_tickets": len(self.ticket_entries),
                "unique_users_with_feedback": len(self.user_feedback),
                "unique_users_with_tickets": len(self.user_tickets),
                "sentiment_distribution": {
                    "positive": sum(1 for f in self.feedback_entries if f.sentiment == "positive"),
                    "neutral": sum(1 for f in self.feedback_entries if f.sentiment == "neutral"),
                    "negative": sum(1 for f in self.feedback_entries if f.sentiment == "negative")
                }
            },
            "category_distribution": {},
            "high_priority_issues": [],
            "recommendations": []
        }
        
        category_counts = defaultdict(int)
        for reason in self.churn_reasons.values():
            category_counts[reason.category] += reason.count
        
        total = sum(category_counts.values())
        for category, count in category_counts.items():
            report["category_distribution"][category] = {
                "count": count,
                "percentage": safe_divide(count, total, 0.0),
                "top_reasons": sorted(
                    [r for r in self.churn_reasons.values() if r.category == category],
                    key=lambda x: x.churn_rate, reverse=True
                )[:3]
            }
        
        for reason in sorted(self.churn_reasons.values(), 
                            key=lambda x: x.churn_rate * x.count, reverse=True):
            if reason.churn_rate > 0.5 and reason.count >= self.min_topic_count:
                report["high_priority_issues"].append({
                    "reason": reason.reason_name,
                    "severity": reason.severity,
                    "affected_users": reason.count,
                    "churn_rate": reason.churn_rate,
                    "avg_days_to_churn": reason.avg_days_to_churn,
                    "urgency": "critical" if reason.severity >= 4 else "high"
                })
        
        report["recommendations"] = self._generate_recommendations()
        
        return report

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        recommendations = []
        
        sorted_reasons = sorted(
            self.churn_reasons.values(),
            key=lambda x: x.churn_rate * x.severity * x.count,
            reverse=True
        )
        
        for reason in sorted_reasons[:5]:
            priority = "high" if reason.severity >= 4 or reason.churn_rate > 0.6 else "medium"
            
            actions = {
                "pricing": "Review pricing strategy and consider tiered options or discounts",
                "product_issues": "Prioritize bug fixes and improve QA processes",
                "customer_service": "Increase support staffing and implement faster response SLA",
                "feature_request": "Evaluate top feature requests and add to roadmap",
                "ux_problems": "Conduct UX research and redesign problematic flows",
                "billing_issues": "Audit billing system and improve transparency",
                "competition": "Conduct competitive analysis and highlight unique value",
                "content_quality": "Expand content library and improve curation",
                "privacy_concerns": "Review privacy policy and enhance security features",
                "onboarding": "Improve onboarding flow with tutorials and in-app guidance",
                "reliability": "Invest in infrastructure improvements and monitoring",
                "communication": "Review communication frequency and preferences"
            }
            
            recommendations.append({
                "priority": priority,
                "area": reason.reason_name,
                "category": reason.category,
                "action": actions.get(reason.reason_code, f"Address {reason.reason_name} issues"),
                "affected_users": reason.count,
                "estimated_impact": f"Potentially reduce churn by {reason.churn_rate*100:.0f}% for affected users",
                "keywords": reason.keywords[:3]
            })
        
        return recommendations


def main():
    if not NUMPY_AVAILABLE:
        print("numpy/pandas not available. Cannot run churn reason analysis demo.")
        return
    
    print("=" * 70)
    print("CHURN REASON ANALYZER")
    print("=" * 70)
    
    analyzer = ChurnReasonAnalyzer()
    
    print("\n" + "-" * 70)
    print("Generating synthetic feedback and ticket data...")
    print("-" * 70)
    
    np.random.seed(42)
    n_users = 200
    user_ids = [f"user_{i:04d}" for i in range(n_users)]
    
    feedback_templates = [
        ("pricing", "The subscription is too expensive, I can't afford this cost anymore."),
        ("pricing", "The renewal price increased too much, not worth it."),
        ("product_issues", "The app keeps crashing every time I try to use it."),
        ("product_issues", "There's a bug that prevents me from completing my purchase."),
        ("customer_service", "My support ticket has been open for 5 days with no response."),
        ("customer_service", "The support team was very unhelpful and rude."),
        ("feature_request", "I wish there was a dark mode feature, it's hard to use at night."),
        ("feature_request", "Missing export functionality, this is a deal breaker for me."),
        ("ux_problems", "The interface is so confusing, I can't find anything."),
        ("ux_problems", "The checkout process is way too complicated."),
        ("billing_issues", "I was double charged this month, this is unacceptable."),
        ("billing_issues", "They charged me even after I canceled my subscription."),
        ("competition", "I found a better alternative that's cheaper and has more features."),
        ("competition", "Switching to a competitor that offers better value for money."),
        ("content_quality", "The content is outdated and not relevant anymore."),
        ("privacy_concerns", "Received too many spam emails after signing up."),
        ("onboarding", "The setup process was really difficult and confusing."),
        ("reliability", "The service was down for 2 days, very unreliable."),
        ("communication", "Getting way too many marketing emails every week."),
    ]
    
    ticket_categories = ["Technical", "Billing", "Feature Request", "Account", "General"]
    
    for i in range(300):
        user_id = np.random.choice(user_ids)
        topic, content = feedback_templates[np.random.randint(len(feedback_templates))]
        
        analyzer.add_feedback(
            feedback_id=f"fb_{i:05d}",
            user_id=user_id,
            feedback_type=np.random.choice(["survey", "review", "direct", "support"]),
            content=content,
            timestamp=time.time() - np.random.randint(0, 60) * 86400
        )
    
    for i in range(150):
        user_id = np.random.choice(user_ids)
        category = np.random.choice(ticket_categories)
        created = time.time() - np.random.randint(0, 45) * 86400
        closed = created + np.random.randint(1, 72) * 3600 if np.random.random() < 0.7 else None
        
        _, description = feedback_templates[np.random.randint(len(feedback_templates))]
        
        analyzer.add_ticket(
            ticket_id=f"ticket_{i:05d}",
            user_id=user_id,
            category=category,
            subcategory=category.lower().replace(" ", "_"),
            description=description,
            priority=np.random.choice(["low", "medium", "high", "critical"], p=[0.3, 0.4, 0.2, 0.1]),
            status=np.random.choice(["open", "closed", "pending"]),
            created_at=created,
            closed_at=closed
        )
    
    churn_data = []
    for user_id in user_ids:
        user_feedback_list = analyzer.user_feedback.get(user_id, [])
        user_ticket_list = analyzer.user_tickets.get(user_id, [])
        
        base_churn = 0.25
        
        churn_multiplier = 1.0
        for fb in user_feedback_list:
            if fb.sentiment == "negative":
                churn_multiplier *= 1.3
            if fb.severity >= 4:
                churn_multiplier *= 1.2
            if "billing_issues" in fb.topics or "customer_service" in fb.topics:
                churn_multiplier *= 1.25
        
        for ticket in user_ticket_list:
            if ticket.priority in ["high", "critical"]:
                churn_multiplier *= 1.15
            if ticket.status != "closed" and ticket.resolution_time_hours > 48:
                churn_multiplier *= 1.2
        
        churn_prob = min(base_churn * churn_multiplier, 0.95)
        churned = np.random.random() < churn_prob
        
        churn_data.append({
            "user_id": user_id,
            "churned": int(churned),
            "churn_time": time.time() if churned else None,
            "num_feedback": len(user_feedback_list),
            "num_tickets": len(user_ticket_list)
        })
    
    print(f"Generated {len(analyzer.feedback_entries)} feedback entries and {len(analyzer.ticket_entries)} tickets")
    print(f"Churned users in sample: {sum(1 for u in churn_data if u['churned'])}/{len(churn_data)}")
    
    print("\n" + "-" * 70)
    print("Analyzing churn reasons...")
    print("-" * 70)
    
    results = analyzer.analyze_churn_reasons(churn_data)
    
    print(f"\nOverall:")
    overall = results["overall"]
    print(f"  Total feedback: {overall['total_feedback']}")
    print(f"  Total tickets: {overall['total_tickets']}")
    print(f"  Avg feedback per churned user: {overall['avg_feedback_per_churned']:.1f}")
    
    print("\n" + "-" * 70)
    print("TOP CHURN REASONS (by impact)")
    print("-" * 70)
    
    for reason in results["top_reasons"]:
        print(f"\n  [{reason['category'].upper()}] {reason['reason_name']}:")
        print(f"    Affected users: {reason['count']}")
        print(f"    Churn rate: {reason['churn_rate_percentage']} (baseline: {reason['baseline_churn_rate']*100:.0f}%)")
        print(f"    Elevated risk: {reason['elevated_risk']}")
        print(f"    Avg days to churn: {reason['avg_days_to_churn']:.0f}")
        print(f"    Severity: {reason['severity_label']} ({reason['severity']:.1f}/5)")
        print(f"    Trend: {reason['trend']}")
        print(f"    Top keywords: {', '.join(reason['top_keywords'])}")
    
    print("\n" + "-" * 70)
    print("TRENDING TOPICS (past 2 weeks)")
    print("-" * 70)
    
    for trend in results["trending_topics"][:5]:
        growth_str = f"{trend['growth_rate']*100:.0f}%" if trend['growth_rate'] != float('inf') else "NEW"
        print(f"  {trend['topic']}: {trend['current_count']} mentions (growth: {growth_str})")
    
    print("\n" + "-" * 70)
    print("KEY INSIGHTS")
    print("-" * 70)
    
    for insight in results["key_insights"]:
        print(f"  - {insight}")
    
    print("\n" + "-" * 70)
    print("RECOMMENDATIONS")
    print("-" * 70)
    
    report = analyzer.generate_churn_reason_report()
    for rec in report["recommendations"][:5]:
        print(f"\n  [{rec['priority'].upper()}] {rec['area']}:")
        print(f"    Action: {rec['action']}")
        print(f"    Affected users: {rec['affected_users']}")
        print(f"    Impact: {rec['estimated_impact']}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
