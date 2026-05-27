import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import yaml
import numpy as np


@dataclass
class ClickRecord:
    click_id: str
    ip: str
    device_id: str
    publisher_id: str
    campaign_id: str
    timestamp: float
    fraud_score: float
    is_fraud: bool
    action_taken: str
    cost: float = 0.0
    attributed_conversion: Optional[str] = None


@dataclass
class ConversionRecord:
    conversion_id: str
    ip: str
    device_id: str
    campaign_id: str
    timestamp: float
    revenue: float
    conversion_type: str
    attributed_click: Optional[str] = None


@dataclass
class AttributionResult:
    campaign_id: str
    total_clicks: int
    total_conversions: int
    fraud_clicks: int
    legitimate_clicks: int
    legitimate_conversions: int
    fraud_conversion_loss: int
    total_cost: float
    total_revenue: float
    fraud_cost: float
    lost_revenue: float
    roi: float
    fraud_rate: float
    conversion_rate: float


@dataclass
class PublisherAttribution:
    publisher_id: str
    total_clicks: int
    total_conversions: int
    fraud_clicks: int
    fraud_cost: float
    legitimate_revenue: float
    roi: float


class AttributionAnalyzer:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.clicks: Dict[str, ClickRecord] = {}
        self.conversions: Dict[str, ConversionRecord] = {}
        
        self.ip_to_clicks: Dict[str, List[str]] = defaultdict(list)
        self.device_to_clicks: Dict[str, List[str]] = defaultdict(list)
        self.campaign_to_clicks: Dict[str, List[str]] = defaultdict(list)
        self.publisher_to_clicks: Dict[str, List[str]] = defaultdict(list)
        
        self.ip_to_conversions: Dict[str, List[str]] = defaultdict(list)
        self.device_to_conversions: Dict[str, List[str]] = defaultdict(list)
        self.campaign_to_conversions: Dict[str, List[str]] = defaultdict(list)
        
        self.attribution_window = self.config.get('attribution', {}).get(
            'attribution_window_hours', 24
        ) * 3600
        self.default_cpc = self.config.get('attribution', {}).get('default_cpc', 0.5)
        self.default_revenue = self.config.get('attribution', {}).get('default_revenue', 10.0)
        
        self.attribution_done = False

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if 'attribution' not in config:
                config['attribution'] = {
                    'attribution_window_hours': 24,
                    'default_cpc': 0.5,
                    'default_revenue': 10.0
                }
            return config

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def add_click(self, click_id: str, ip: str, device_id: str, 
                  publisher_id: str, campaign_id: str, timestamp: float = None,
                  fraud_score: float = 0.0, is_fraud: bool = False,
                  action_taken: str = "allow", cost: float = None) -> str:
        if timestamp is None:
            timestamp = time.time()
        
        cost = cost if cost is not None else self.default_cpc
        
        if not click_id:
            click_id = self._generate_id('click')
        
        click = ClickRecord(
            click_id=click_id,
            ip=ip,
            device_id=device_id,
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            timestamp=timestamp,
            fraud_score=fraud_score,
            is_fraud=is_fraud,
            action_taken=action_taken,
            cost=cost
        )
        
        self.clicks[click_id] = click
        self.ip_to_clicks[ip].append(click_id)
        self.device_to_clicks[device_id].append(click_id)
        self.campaign_to_clicks[campaign_id].append(click_id)
        self.publisher_to_clicks[publisher_id].append(click_id)
        
        self.attribution_done = False
        return click_id

    def add_conversion(self, conversion_id: str, ip: str, device_id: str,
                       campaign_id: str, timestamp: float = None,
                       revenue: float = None, conversion_type: str = "purchase") -> str:
        if timestamp is None:
            timestamp = time.time()
        
        revenue = revenue if revenue is not None else self.default_revenue
        
        if not conversion_id:
            conversion_id = self._generate_id('conv')
        
        conversion = ConversionRecord(
            conversion_id=conversion_id,
            ip=ip,
            device_id=device_id,
            campaign_id=campaign_id,
            timestamp=timestamp,
            revenue=revenue,
            conversion_type=conversion_type
        )
        
        self.conversions[conversion_id] = conversion
        self.ip_to_conversions[ip].append(conversion_id)
        self.device_to_conversions[device_id].append(conversion_id)
        self.campaign_to_conversions[campaign_id].append(conversion_id)
        
        self.attribution_done = False
        return conversion_id

    def run_attribution(self):
        for click in self.clicks.values():
            click.attributed_conversion = None
        
        for conversion in self.conversions.values():
            conversion.attributed_click = None
        
        for conversion_id, conversion in self.conversions.items():
            matching_clicks = self._find_matching_clicks(conversion)
            
            if matching_clicks:
                best_click = self._select_best_click(matching_clicks)
                if best_click:
                    best_click.attributed_conversion = conversion_id
                    conversion.attributed_click = best_click.click_id
        
        self.attribution_done = True

    def _find_matching_clicks(self, conversion: ConversionRecord) -> List[ClickRecord]:
        matching = []
        
        window_start = conversion.timestamp - self.attribution_window
        
        ip_clicks = [
            self.clicks[cid] 
            for cid in self.ip_to_clicks.get(conversion.ip, [])
            if cid in self.clicks
        ]
        
        device_clicks = [
            self.clicks[cid] 
            for cid in self.device_to_clicks.get(conversion.device_id, [])
            if cid in self.clicks
        ]
        
        all_clicks = set(ip_clicks + device_clicks)
        
        for click in all_clicks:
            if (click.campaign_id == conversion.campaign_id and
                window_start <= click.timestamp <= conversion.timestamp and
                not click.is_fraud and
                click.attributed_conversion is None):
                matching.append(click)
        
        return matching

    def _select_best_click(self, clicks: List[ClickRecord]) -> Optional[ClickRecord]:
        if not clicks:
            return None
        
        clicks.sort(key=lambda x: -x.timestamp)
        return clicks[0]

    def calculate_campaign_attribution(self, campaign_id: str) -> AttributionResult:
        if not self.attribution_done:
            self.run_attribution()
        
        click_ids = self.campaign_to_clicks.get(campaign_id, [])
        conversion_ids = self.campaign_to_conversions.get(campaign_id, [])
        
        clicks = [self.clicks[cid] for cid in click_ids if cid in self.clicks]
        conversions = [self.conversions[cid] for cid in conversion_ids if cid in self.conversions]
        
        total_clicks = len(clicks)
        total_conversions = len(conversions)
        fraud_clicks = sum(1 for c in clicks if c.is_fraud)
        legitimate_clicks = total_clicks - fraud_clicks
        
        legitimate_conversions = sum(
            1 for conv in conversions 
            if conv.attributed_click and 
               self.clicks.get(conv.attributed_click, None) and 
               not self.clicks[conv.attributed_click].is_fraud
        )
        
        fraud_conversion_loss = sum(
            1 for conv in conversions
            if conv.attributed_click is None
        )
        
        total_cost = sum(c.cost for c in clicks)
        fraud_cost = sum(c.cost for c in clicks if c.is_fraud)
        
        total_revenue = sum(c.revenue for c in conversions if c.attributed_click)
        lost_revenue = sum(c.revenue for c in conversions if not c.attributed_click)
        
        roi = (total_revenue - total_cost) / max(total_cost, 0.001)
        fraud_rate = fraud_clicks / max(total_clicks, 1)
        conversion_rate = legitimate_conversions / max(legitimate_clicks, 1)
        
        return AttributionResult(
            campaign_id=campaign_id,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            fraud_clicks=fraud_clicks,
            legitimate_clicks=legitimate_clicks,
            legitimate_conversions=legitimate_conversions,
            fraud_conversion_loss=fraud_conversion_loss,
            total_cost=total_cost,
            total_revenue=total_revenue,
            fraud_cost=fraud_cost,
            lost_revenue=lost_revenue,
            roi=roi,
            fraud_rate=fraud_rate,
            conversion_rate=conversion_rate
        )

    def calculate_publisher_attribution(self, publisher_id: str) -> PublisherAttribution:
        if not self.attribution_done:
            self.run_attribution()
        
        click_ids = self.publisher_to_clicks.get(publisher_id, [])
        clicks = [self.clicks[cid] for cid in click_ids if cid in self.clicks]
        
        total_clicks = len(clicks)
        fraud_clicks = sum(1 for c in clicks if c.is_fraud)
        fraud_cost = sum(c.cost for c in clicks if c.is_fraud)
        total_cost = sum(c.cost for c in clicks)
        
        legitimate_revenue = 0.0
        total_conversions = 0
        
        for click in clicks:
            if click.attributed_conversion and not click.is_fraud:
                conv = self.conversions.get(click.attributed_conversion)
                if conv:
                    legitimate_revenue += conv.revenue
                    total_conversions += 1
        
        roi = (legitimate_revenue - total_cost) / max(total_cost, 0.001)
        
        return PublisherAttribution(
            publisher_id=publisher_id,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            fraud_clicks=fraud_clicks,
            fraud_cost=fraud_cost,
            legitimate_revenue=legitimate_revenue,
            roi=roi
        )

    def get_all_campaigns_summary(self) -> List[AttributionResult]:
        campaign_ids = set(self.campaign_to_clicks.keys()) | set(self.campaign_to_conversions.keys())
        return [self.calculate_campaign_attribution(cid) for cid in campaign_ids]

    def get_all_publishers_summary(self) -> List[PublisherAttribution]:
        publisher_ids = self.publisher_to_clicks.keys()
        return [self.calculate_publisher_attribution(pid) for pid in publisher_ids]

    def get_fraud_impact_summary(self) -> Dict[str, Any]:
        if not self.attribution_done:
            self.run_attribution()
        
        all_clicks = list(self.clicks.values())
        all_conversions = list(self.conversions.values())
        
        total_clicks = len(all_clicks)
        total_conversions = len(all_conversions)
        fraud_clicks = sum(1 for c in all_clicks if c.is_fraud)
        fraud_cost = sum(c.cost for c in all_clicks if c.is_fraud)
        total_cost = sum(c.cost for c in all_clicks)
        
        attributed_revenue = sum(c.revenue for c in all_conversions if c.attributed_click)
        lost_revenue = sum(c.revenue for c in all_conversions if not c.attributed_click)
        
        fraud_related_loss = sum(
            conv.revenue 
            for conv in all_conversions 
            if not conv.attributed_click
        )
        
        campaign_results = self.get_all_campaigns_summary()
        publisher_results = self.get_all_publishers_summary()
        
        worst_publishers = sorted(
            publisher_results,
            key=lambda x: x.fraud_clicks / max(x.total_clicks, 1),
            reverse=True
        )[:5]
        
        return {
            'summary': {
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'fraud_clicks': fraud_clicks,
                'fraud_rate': fraud_clicks / max(total_clicks, 1),
                'total_cost': total_cost,
                'fraud_cost': fraud_cost,
                'fraud_cost_percentage': fraud_cost / max(total_cost, 0.001),
                'total_attributed_revenue': attributed_revenue,
                'lost_revenue': lost_revenue,
                'fraud_related_revenue_loss': fraud_related_loss
            },
            'worst_publishers': [asdict(p) for p in worst_publishers],
            'campaign_breakdown': [asdict(c) for c in campaign_results]
        }

    def get_time_series_data(self, hours: int = 24) -> Dict[str, Any]:
        if not self.attribution_done:
            self.run_attribution()
        
        now = time.time()
        start_time = now - hours * 3600
        
        hourly_clicks = defaultdict(lambda: {'total': 0, 'fraud': 0})
        hourly_conversions = defaultdict(lambda: {'total': 0, 'attributed': 0})
        hourly_cost = defaultdict(float)
        hourly_revenue = defaultdict(float)
        
        for click in self.clicks.values():
            if click.timestamp >= start_time:
                hour_key = datetime.fromtimestamp(click.timestamp).strftime('%Y-%m-%d %H:00')
                hourly_clicks[hour_key]['total'] += 1
                if click.is_fraud:
                    hourly_clicks[hour_key]['fraud'] += 1
                hourly_cost[hour_key] += click.cost
        
        for conv in self.conversions.values():
            if conv.timestamp >= start_time:
                hour_key = datetime.fromtimestamp(conv.timestamp).strftime('%Y-%m-%d %H:00')
                hourly_conversions[hour_key]['total'] += 1
                if conv.attributed_click:
                    hourly_conversions[hour_key]['attributed'] += 1
                    hourly_revenue[hour_key] += conv.revenue
        
        sorted_hours = sorted(hourly_clicks.keys())
        
        return {
            'time_labels': sorted_hours,
            'clicks': {
                'total': [hourly_clicks[h]['total'] for h in sorted_hours],
                'fraud': [hourly_clicks[h]['fraud'] for h in sorted_hours]
            },
            'conversions': {
                'total': [hourly_conversions[h]['total'] for h in sorted_hours],
                'attributed': [hourly_conversions[h]['attributed'] for h in sorted_hours]
            },
            'cost': [hourly_cost[h] for h in sorted_hours],
            'revenue': [hourly_revenue[h] for h in sorted_hours]
        }

    def generate_report(self) -> Dict[str, Any]:
        impact = self.get_fraud_impact_summary()
        time_series = self.get_time_series_data()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'fraud_impact': impact,
            'time_series': time_series,
            'recommendations': self._generate_recommendations(impact)
        }

    def _generate_recommendations(self, impact: Dict[str, Any]) -> List[str]:
        recommendations = []
        summary = impact['summary']
        
        if summary['fraud_rate'] > 0.2:
            recommendations.append(
                f"高欺诈率警告: 当前欺诈率为 {summary['fraud_rate']:.1%}, 建议加强检测规则"
            )
        
        if summary['fraud_cost_percentage'] > 0.15:
            recommendations.append(
                f"欺诈成本过高: 已浪费 {summary['fraud_cost']:.2f} 元 ({summary['fraud_cost_percentage']:.1%}), "
                f"建议对高风险发布商实施更严格的审核"
            )
        
        for pub in impact['worst_publishers'][:3]:
            fraud_rate = pub['fraud_clicks'] / max(pub['total_clicks'], 1)
            if fraud_rate > 0.3:
                recommendations.append(
                    f"重点关注发布商 {pub['publisher_id']}: 欺诈率 {fraud_rate:.1%}, "
                    f"已浪费成本 {pub['fraud_cost']:.2f} 元"
                )
        
        if not recommendations:
            recommendations.append("系统运行正常，欺诈率在可控范围内")
        
        return recommendations

    def reset(self):
        self.clicks.clear()
        self.conversions.clear()
        self.ip_to_clicks.clear()
        self.device_to_clicks.clear()
        self.campaign_to_clicks.clear()
        self.publisher_to_clicks.clear()
        self.ip_to_conversions.clear()
        self.device_to_conversions.clear()
        self.campaign_to_conversions.clear()
        self.attribution_done = False
