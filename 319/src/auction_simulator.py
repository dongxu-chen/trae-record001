import random
import time
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict, deque
from enum import Enum

from config import config
from src.data_generator import DataGenerator
from src.bid_engine import BidEngine, BidRequest
from src.exploration import ExplorationEngine, BiddingStrategy


class AuctionResult(Enum):
    WON = "won"
    LOST = "lost"
    SKIPPED = "skipped"


@dataclass
class AuctionRecord:
    auction_id: str
    timestamp: float
    user_id: str
    ad_id: str
    bid_request: Dict[str, Any]
    our_bid: float
    competitor_bids: List[float]
    winning_bid: float
    result: AuctionResult
    was_clicked: bool
    was_converted: bool
    cost: float
    revenue: float
    profit: float
    strategy_used: Optional[str] = None
    traffic_layer: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auction_id": self.auction_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "ad_id": self.ad_id,
            "our_bid": self.our_bid,
            "competitor_bids": self.competitor_bids,
            "winning_bid": self.winning_bid,
            "result": self.result.value,
            "was_clicked": self.was_clicked,
            "was_converted": self.was_converted,
            "cost": self.cost,
            "revenue": self.revenue,
            "profit": self.profit,
            "strategy_used": self.strategy_used,
            "traffic_layer": self.traffic_layer,
            "details": self.details,
        }


@dataclass
class Competitor:
    name: str
    bid_multiplier: float = 1.0
    bid_std: float = 0.3
    strategy: str = "fixed"
    ctr_weight: float = 1.0
    cvr_weight: float = 1.0
    
    def calculate_bid(
        self,
        base_bid: float,
        ctr: float,
        cvr: float,
        floor_price: float,
    ) -> float:
        if self.strategy == "fixed":
            bid = base_bid * self.bid_multiplier
        elif self.strategy == "aggressive":
            bid = base_bid * self.bid_multiplier * (1 + ctr * self.ctr_weight)
        elif self.strategy == "conservative":
            bid = base_bid * self.bid_multiplier * (0.8 + cvr * self.cvr_weight * 0.4)
        elif self.strategy == "value_based":
            bid = (ctr * self.ctr_weight + cvr * self.cvr_weight) * base_bid * self.bid_multiplier
        else:
            bid = base_bid * self.bid_multiplier
        
        bid += random.gauss(0, self.bid_std * base_bid)
        return max(floor_price, abs(bid))


@dataclass
class SimulationStats:
    total_auctions: int = 0
    auctions_won: int = 0
    auctions_lost: int = 0
    auctions_skipped: int = 0
    total_cost: float = 0.0
    total_revenue: float = 0.0
    total_profit: float = 0.0
    total_clicks: int = 0
    total_conversions: int = 0
    total_impressions: int = 0
    strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(lambda: {
        "trials": 0, "wins": 0, "clicks": 0, "conversions": 0,
        "cost": 0.0, "revenue": 0.0, "profit": 0.0
    }))
    layer_stats: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(lambda: {
        "trials": 0, "wins": 0, "clicks": 0, "conversions": 0,
        "cost": 0.0, "revenue": 0.0, "profit": 0.0
    }))
    bid_history: List[Tuple[float, float]] = field(default_factory=list)
    
    @property
    def win_rate(self) -> float:
        return self.auctions_won / self.total_auctions if self.total_auctions > 0 else 0.0
    
    @property
    def ctr(self) -> float:
        return self.total_clicks / self.total_impressions if self.total_impressions > 0 else 0.0
    
    @property
    def cvr(self) -> float:
        return self.total_conversions / self.total_clicks if self.total_clicks > 0 else 0.0
    
    @property
    def avg_bid(self) -> float:
        return sum(b for b, _ in self.bid_history) / len(self.bid_history) if self.bid_history else 0.0
    
    @property
    def roas(self) -> float:
        return self.total_revenue / self.total_cost if self.total_cost > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_auctions": self.total_auctions,
            "auctions_won": self.auctions_won,
            "auctions_lost": self.auctions_lost,
            "auctions_skipped": self.auctions_skipped,
            "win_rate": self.win_rate,
            "total_cost": self.total_cost,
            "total_revenue": self.total_revenue,
            "total_profit": self.total_profit,
            "total_clicks": self.total_clicks,
            "total_conversions": self.total_conversions,
            "ctr": self.ctr,
            "cvr": self.cvr,
            "avg_bid": self.avg_bid,
            "roas": self.roas,
            "strategy_stats": dict(self.strategy_stats),
            "layer_stats": dict(self.layer_stats),
        }


class AuctionSimulator:
    def __init__(
        self,
        bid_engine: Optional[BidEngine] = None,
        num_competitors: Optional[int] = None,
        random_seed: Optional[int] = None,
    ):
        self.bid_engine = bid_engine or BidEngine("simulation_campaign", enable_exploration=True)
        self.data_generator = DataGenerator()
        
        sim_config = config.simulator
        self.num_competitors = num_competitors or sim_config.num_competitors
        self.min_bid = sim_config.min_bid
        self.max_bid = sim_config.max_bid
        self.click_prob_base = sim_config.click_probability_base
        self.conversion_prob_base = sim_config.conversion_probability_base
        self.reserve_price = sim_config.reserve_price
        
        if random_seed is not None:
            random.seed(random_seed)
        
        self.competitors = self._initialize_competitors()
        self.auction_history: List[AuctionRecord] = []
        self.stats = SimulationStats()
    
    def _initialize_competitors(self) -> List[Competitor]:
        strategies = ["fixed", "aggressive", "conservative", "value_based"]
        competitors = []
        
        for i in range(self.num_competitors):
            strategy = strategies[i % len(strategies)]
            competitors.append(Competitor(
                name=f"competitor_{i+1}",
                bid_multiplier=0.7 + (i * 0.15),
                bid_std=0.2 + (i * 0.05),
                strategy=strategy,
                ctr_weight=0.8 + (i * 0.1),
                cvr_weight=0.5 + (i * 0.15),
            ))
        
        return competitors
    
    def _generate_competitor_bids(
        self,
        base_bid: float,
        ctr: float,
        cvr: float,
        floor_price: float,
    ) -> List[float]:
        bids = []
        for competitor in self.competitors:
            bid = competitor.calculate_bid(base_bid, ctr, cvr, floor_price)
            bid = min(self.max_bid, max(self.min_bid, bid))
            bids.append(round(bid, 4))
        return bids
    
    def _determine_click_and_conversion(
        self,
        ctr: float,
        cvr: float,
        bid_price: float,
    ) -> Tuple[bool, bool]:
        click_prob = min(1.0, self.click_prob_base + ctr * 0.8)
        if bid_price > 0:
            bid_factor = min(1.5, 1 + math.log(bid_price + 1) * 0.1)
            click_prob *= bid_factor
        
        was_clicked = random.random() < click_prob
        
        was_converted = False
        if was_clicked:
            conversion_prob = min(1.0, self.conversion_prob_base + cvr * 0.5)
            was_converted = random.random() < conversion_prob
        
        return was_clicked, was_converted
    
    def _calculate_revenue(
        self,
        was_clicked: bool,
        was_converted: bool,
        cpa_goal: float,
    ) -> float:
        revenue = 0.0
        if was_clicked:
            revenue += cpa_goal * 0.1
        if was_converted:
            revenue += cpa_goal
        return revenue
    
    def run_single_auction(
        self,
        bid_request: Optional[BidRequest] = None,
        use_strategies: Optional[List[str]] = None,
    ) -> AuctionRecord:
        if bid_request is None:
            user_id = f"user_{random.randint(0, 99999):05d}"
            user_profile = self.data_generator.generate_user_profile(user_id)
            context = self.data_generator.generate_context()
            ad_info = self.data_generator.generate_ad_info(f"ad_{random.randint(0, 100):03d}")
            bid_request = BidRequest(
                request_id=f"req_{int(time.time()*1000)}",
                user_id=user_id,
                ad_id=ad_info["ad_id"],
                campaign_id="simulation_campaign",
                user_profile=user_profile,
                context=context,
                ad_info=ad_info,
                floor_price=self.reserve_price,
                cpa_goal=20.0,
            )
        
        response = self.bid_engine.process_bid(bid_request)
        
        our_bid = response.bid_price
        ctr = response.details.get("ctr", 0.0)
        cvr = response.details.get("cvr", 0.0)
        strategy_used = response.details.get("strategy_name")
        traffic_layer = response.details.get("traffic_layer")
        
        if not response.success or our_bid <= 0:
            record = AuctionRecord(
                auction_id=f"auc_{int(time.time()*1000000)}",
                timestamp=time.time(),
                user_id=bid_request.user_id,
                ad_id=bid_request.ad_id,
                bid_request=bid_request.__dict__,
                our_bid=0.0,
                competitor_bids=[],
                winning_bid=0.0,
                result=AuctionResult.SKIPPED,
                was_clicked=False,
                was_converted=False,
                cost=0.0,
                revenue=0.0,
                profit=0.0,
                strategy_used=strategy_used,
                traffic_layer=traffic_layer,
                details=response.details,
            )
            self._update_stats(record)
            self.auction_history.append(record)
            return record
        
        base_bid = response.details.get("base_bid", our_bid)
        competitor_bids = self._generate_competitor_bids(
            base_bid, ctr, cvr, bid_request.floor_price
        )
        
        all_bids = [our_bid] + competitor_bids
        winning_bid = max(all_bids)
        result = AuctionResult.WON if our_bid >= winning_bid else AuctionResult.LOST
        
        cost = 0.0
        revenue = 0.0
        was_clicked = False
        was_converted = False
        
        if result == AuctionResult.WON:
            cost = winning_bid * 0.99
            was_clicked, was_converted = self._determine_click_and_conversion(
                ctr, cvr, our_bid
            )
            revenue = self._calculate_revenue(was_clicked, was_converted, bid_request.cpa_goal)
            
            if self.bid_engine.enable_exploration and strategy_used:
                self.bid_engine.record_exploration_result(
                    strategy_name=strategy_used,
                    bid_price=cost,
                    ctr=ctr,
                    cvr=cvr,
                    was_clicked=was_clicked,
                    was_converted=was_converted,
                )
        
        profit = revenue - cost
        
        record = AuctionRecord(
            auction_id=f"auc_{int(time.time()*1000000)}",
            timestamp=time.time(),
            user_id=bid_request.user_id,
            ad_id=bid_request.ad_id,
            bid_request=bid_request.__dict__,
            our_bid=our_bid,
            competitor_bids=competitor_bids,
            winning_bid=winning_bid,
            result=result,
            was_clicked=was_clicked,
            was_converted=was_converted,
            cost=cost,
            revenue=revenue,
            profit=profit,
            strategy_used=strategy_used,
            traffic_layer=traffic_layer,
            details=response.details,
        )
        
        self._update_stats(record)
        self.auction_history.append(record)
        return record
    
    def _update_stats(self, record: AuctionRecord):
        self.stats.total_auctions += 1
        
        if record.result == AuctionResult.WON:
            self.stats.auctions_won += 1
            self.stats.total_cost += record.cost
            self.stats.total_revenue += record.revenue
            self.stats.total_profit += record.profit
            self.stats.total_impressions += 1
            self.stats.bid_history.append((record.our_bid, record.winning_bid))
            
            if record.was_clicked:
                self.stats.total_clicks += 1
            if record.was_converted:
                self.stats.total_conversions += 1
        elif record.result == AuctionResult.LOST:
            self.stats.auctions_lost += 1
        else:
            self.stats.auctions_skipped += 1
        
        if record.strategy_used:
            s = self.stats.strategy_stats[record.strategy_used]
            s["trials"] += 1
            if record.result == AuctionResult.WON:
                s["wins"] += 1
                s["cost"] += record.cost
                s["revenue"] += record.revenue
                s["profit"] += record.profit
                if record.was_clicked:
                    s["clicks"] += 1
                if record.was_converted:
                    s["conversions"] += 1
        
        if record.traffic_layer:
            l = self.stats.layer_stats[record.traffic_layer]
            l["trials"] += 1
            if record.result == AuctionResult.WON:
                l["wins"] += 1
                l["cost"] += record.cost
                l["revenue"] += record.revenue
                l["profit"] += record.profit
                if record.was_clicked:
                    l["clicks"] += 1
                if record.was_converted:
                    l["conversions"] += 1
    
    def run_simulation(
        self,
        num_auctions: int,
        callback: Optional[Callable[[int, AuctionRecord, SimulationStats], None]] = None,
        batch_size: int = 100,
    ) -> SimulationStats:
        for i in range(num_auctions):
            record = self.run_single_auction()
            
            if callback is not None and (i + 1) % batch_size == 0:
                callback(i + 1, record, self.stats)
        
        return self.stats
    
    def run_replay(
        self,
        replay_records: List[Dict[str, Any]],
        override_bidding: Optional[Dict[str, Any]] = None,
    ) -> SimulationStats:
        original_stats = self.stats
        self.stats = SimulationStats()
        self.auction_history = []
        
        for record_data in replay_records:
            user_profile = record_data.get("bid_request", {}).get("user_profile", {})
            context = record_data.get("bid_request", {}).get("context", {})
            ad_info = record_data.get("bid_request", {}).get("ad_info", {})
            
            bid_request = BidRequest(
                request_id=record_data.get("auction_id", f"replay_{int(time.time()*1000)}"),
                user_id=record_data.get("user_id", "replay_user"),
                ad_id=record_data.get("ad_id", "replay_ad"),
                campaign_id="replay_campaign",
                user_profile=user_profile,
                context=context,
                ad_info=ad_info,
                floor_price=record_data.get("bid_request", {}).get("floor_price", self.reserve_price),
                cpa_goal=record_data.get("bid_request", {}).get("cpa_goal", 20.0),
            )
            
            self.run_single_auction(bid_request)
        
        final_stats = self.stats
        self.stats = original_stats
        
        return final_stats
    
    def get_strategy_comparison(self) -> Dict[str, Dict[str, float]]:
        comparison = {}
        for strategy, stats in self.stats.strategy_stats.items():
            trials = stats["trials"]
            if trials == 0:
                continue
            comparison[strategy] = {
                "trials": trials,
                "win_rate": stats["wins"] / trials,
                "ctr": stats["clicks"] / max(1, stats["wins"]),
                "cvr": stats["conversions"] / max(1, stats["clicks"]),
                "total_profit": stats["profit"],
                "avg_profit_per_auction": stats["profit"] / trials,
                "roas": stats["revenue"] / max(0.01, stats["cost"]),
            }
        return comparison
    
    def export_history(
        self,
        filepath: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        records = self.auction_history
        if limit is not None:
            records = records[-limit:]
        
        data = [record.to_dict() for record in records]
        
        if filepath is not None:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        return data
    
    def load_history(self, filepath: str) -> List[AuctionRecord]:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = []
        for item in data:
            record = AuctionRecord(
                auction_id=item["auction_id"],
                timestamp=item["timestamp"],
                user_id=item["user_id"],
                ad_id=item["ad_id"],
                bid_request=item.get("bid_request", {}),
                our_bid=item["our_bid"],
                competitor_bids=item.get("competitor_bids", []),
                winning_bid=item["winning_bid"],
                result=AuctionResult(item["result"]),
                was_clicked=item["was_clicked"],
                was_converted=item["was_converted"],
                cost=item["cost"],
                revenue=item["revenue"],
                profit=item["profit"],
                strategy_used=item.get("strategy_used"),
                traffic_layer=item.get("traffic_layer"),
                details=item.get("details", {}),
            )
            records.append(record)
        
        return records
    
    def reset(self):
        self.auction_history = []
        self.stats = SimulationStats()
        if self.bid_engine.exploration_engine is not None:
            self.bid_engine.exploration_engine.reset()
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "stats": self.stats.to_dict(),
            "num_competitors": self.num_competitors,
            "competitors": [c.name for c in self.competitors],
            "strategy_comparison": self.get_strategy_comparison(),
            "exploration_status": self.bid_engine.get_exploration_status(),
        }
