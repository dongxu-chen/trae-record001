import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class HouseholdProfile:
    household_id: str
    household_type: str
    dwelling_size: int
    num_occupants: int
    region: str
    has_ac: bool = True
    has_ev: bool = False
    has_solar: bool = False


class HouseholdEnergyDataset:
    def __init__(self, n_households: int = 100):
        self.n_households = n_households
        self.households: List[HouseholdProfile] = []
        self.energy_data: Dict[str, Dict[str, float]] = {}
        self.appliance_breakdown: Dict[str, Dict[str, float]] = {}
        
        self._generate_synthetic_dataset()
    
    def _generate_synthetic_dataset(self):
        np.random.seed(42)
        
        household_types = ['单身', '两口之家', '三口之家', '多口之家', '老年家庭']
        dwelling_sizes = [40, 60, 80, 100, 120, 150]
        regions = ['北方', '南方', '东部', '西部']
        
        for i in range(self.n_households):
            hh_type = np.random.choice(household_types, p=[0.2, 0.25, 0.35, 0.15, 0.05])
            
            if hh_type == '单身':
                num_occupants = 1
                base_size = 50
            elif hh_type == '两口之家':
                num_occupants = 2
                base_size = 70
            elif hh_type == '三口之家':
                num_occupants = 3
                base_size = 90
            elif hh_type == '多口之家':
                num_occupants = np.random.randint(4, 6)
                base_size = 120
            else:
                num_occupants = np.random.randint(1, 3)
                base_size = 60
            
            base_idx = np.argmin([abs(s - base_size) for s in dwelling_sizes])
            size_idx = min(max(np.random.randint(-1, 2) + base_idx, 0), len(dwelling_sizes)-1)
            
            profile = HouseholdProfile(
                household_id=f'HH_{i:03d}',
                household_type=hh_type,
                dwelling_size=dwelling_sizes[size_idx],
                num_occupants=num_occupants,
                region=np.random.choice(regions),
                has_ac=np.random.random() > 0.1,
                has_ev=np.random.random() > 0.85,
                has_solar=np.random.random() > 0.9
            )
            
            self.households.append(profile)
            
            base_energy = self._calculate_base_energy(profile)
            
            total_energy = base_energy * np.random.uniform(0.7, 1.5)
            
            self.energy_data[profile.household_id] = {
                'monthly_total': total_energy,
                'daily_avg': total_energy / 30,
                'peak_power': total_energy / 30 / 24 * 3
            }
            
            self.appliance_breakdown[profile.household_id] = self._generate_appliance_breakdown(
                profile, total_energy)
    
    def _calculate_base_energy(self, profile: HouseholdProfile) -> float:
        base_kwh = 100
        
        base_kwh += profile.num_occupants * 30
        
        size_factor = profile.dwelling_size / 80
        base_kwh *= size_factor
        
        if profile.has_ac:
            if profile.region in ['南方', '东部']:
                base_kwh += 80
            else:
                base_kwh += 50
        
        if profile.has_ev:
            base_kwh += 150
        
        if profile.has_solar:
            base_kwh *= 0.7
        
        if profile.household_type == '老年家庭':
            base_kwh *= 1.2
        
        return base_kwh
    
    def _generate_appliance_breakdown(self, profile: HouseholdProfile, total: float) -> Dict[str, float]:
        breakdown = {}
        
        base_ratios = {
            'refrigerator': 0.15,
            'lighting': 0.10,
            'air_conditioner': 0.25 if profile.has_ac else 0.05,
            'washing_machine': 0.05,
            'kitchen': 0.20,
            'entertainment': 0.10,
            'water_heater': 0.10,
            'other': 0.05
        }
        
        if profile.has_ev:
            base_ratios['ev_charger'] = 0.20
            factor = 1.0 / 1.2
            for k in base_ratios:
                if k != 'ev_charger':
                    base_ratios[k] *= factor
        
        for app, ratio in base_ratios.items():
            variation = np.random.uniform(0.8, 1.2)
            breakdown[app] = total * ratio * variation
        
        return breakdown


class HouseholdComparator:
    def __init__(self, dataset: HouseholdEnergyDataset = None):
        self.dataset = dataset or HouseholdEnergyDataset(n_households=100)
        self.appliance_names_cn = {
            'refrigerator': '冰箱',
            'lighting': '照明',
            'air_conditioner': '空调',
            'washing_machine': '洗衣机',
            'kitchen': '厨房电器',
            'entertainment': '娱乐设备',
            'water_heater': '热水器',
            'ev_charger': '电动车充电',
            'other': '其他'
        }
    
    def find_peers(self, target_profile: HouseholdProfile) -> List[str]:
        peer_ids = []
        
        for hh in self.dataset.households:
            type_match = hh.household_type == target_profile.household_type
            size_match = abs(hh.dwelling_size - target_profile.dwelling_size) <= 30
            occupant_match = abs(hh.num_occupants - target_profile.num_occupants) <= 1
            region_match = hh.region == target_profile.region
            ac_match = hh.has_ac == target_profile.has_ac
            ev_match = hh.has_ev == target_profile.has_ev
            
            score = sum([type_match * 3, size_match * 2, occupant_match * 2, 
                        region_match * 1, ac_match * 2, ev_match * 2])
            
            if score >= 8:
                peer_ids.append(hh.household_id)
        
        if len(peer_ids) < 10:
            peer_ids = [hh.household_id for hh in self.dataset.households 
                       if hh.household_type == target_profile.household_type][:20]
        
        return peer_ids
    
    def calculate_percentile(self, value: float, all_values: List[float]) -> Tuple[float, str]:
        if not all_values:
            return 50.0, '中等'
        
        percentile = stats.percentileofscore(all_values, value)
        
        if percentile <= 20:
            level = '非常节能'
        elif percentile <= 40:
            level = '比较节能'
        elif percentile <= 60:
            level = '中等水平'
        elif percentile <= 80:
            level = '偏高'
        else:
            level = '偏高较多'
        
        return round(percentile, 1), level
    
    def compare_household(self,
                          target_profile: HouseholdProfile,
                          target_energy: Dict[str, float],
                          target_appliance_breakdown: Dict[str, float]) -> Dict:
        
        peer_ids = self.find_peers(target_profile)
        
        peer_total_energy = [self.dataset.energy_data[pid]['monthly_total'] 
                            for pid in peer_ids]
        
        target_total = target_energy.get('monthly_total', target_energy.get('total', 0))
        
        overall_percentile, overall_level = self.calculate_percentile(target_total, peer_total_energy)
        
        peer_stats = {
            'count': len(peer_ids),
            'min': round(min(peer_total_energy), 1),
            'max': round(max(peer_total_energy), 1),
            'mean': round(np.mean(peer_total_energy), 1),
            'median': round(np.median(peer_total_energy), 1),
            'p25': round(np.percentile(peer_total_energy, 25), 1),
            'p75': round(np.percentile(peer_total_energy, 75), 1)
        }
        
        appliance_comparison = {}
        for app, target_val in target_appliance_breakdown.items():
            if app in self.appliance_names_cn:
                peer_vals = [self.dataset.appliance_breakdown[pid].get(app, 0) 
                            for pid in peer_ids if app in self.dataset.appliance_breakdown[pid]]
                
                if peer_vals:
                    pctl, level = self.calculate_percentile(target_val, peer_vals)
                    appliance_comparison[app] = {
                        'name_cn': self.appliance_names_cn[app],
                        'target_monthly': round(target_val, 1),
                        'peer_avg': round(np.mean(peer_vals), 1),
                        'percentile': pctl,
                        'level': level,
                        'vs_avg': round((target_val - np.mean(peer_vals)) / np.mean(peer_vals) * 100, 1) if np.mean(peer_vals) > 0 else 0
                    }
        
        potential_savings = 0
        saving_advice = []
        
        for app, comp in appliance_comparison.items():
            if comp['percentile'] > 60:
                savings = comp['target_monthly'] - comp['peer_avg']
                if savings > 5:
                    potential_savings += savings
                    saving_advice.append({
                        'appliance': comp['name_cn'],
                        'potential_saving': round(savings, 1),
                        'advice': f'{comp["name_cn"]}能耗高于同类型家庭均值{comp["vs_avg"]}%，建议检查使用习惯或考虑更换节能型号'
                    })
        
        benchmark = {
            'efficient': peer_stats['p25'],
            'average': peer_stats['median'],
            'current': target_total,
            'potential_saving_total': round(max(0, target_total - peer_stats['p25']), 1)
        }
        
        return {
            'target_profile': {
                'household_type': target_profile.household_type,
                'dwelling_size': target_profile.dwelling_size,
                'num_occupants': target_profile.num_occupants,
                'region': target_profile.region
            },
            'peer_group': {
                'size': len(peer_ids),
                'description': f'找到{len(peer_ids)}个相似家庭进行对比'
            },
            'overall': {
                'target_monthly_kwh': round(target_total, 1),
                'peer_stats': peer_stats,
                'percentile': overall_percentile,
                'level': overall_level,
                'vs_peer_avg': round((target_total - peer_stats['mean']) / peer_stats['mean'] * 100, 1) if peer_stats['mean'] > 0 else 0
            },
            'appliance_comparison': appliance_comparison,
            'benchmark': benchmark,
            'saving_recommendations': sorted(saving_advice, key=lambda x: x['potential_saving'], reverse=True)
        }


def get_percentile_ranking(energy_value: float, all_values: List[float]) -> Dict:
    from scipy import stats
    
    percentile = stats.percentileofscore(all_values, energy_value)
    
    ranks = [
        (0, 10, '前10%', '极其优秀'),
        (10, 25, '前25%', '非常优秀'),
        (25, 50, '中上水平', '表现良好'),
        (50, 75, '中等偏下', '有提升空间'),
        (75, 90, '偏高', '需要改进'),
        (90, 100, '偏高明显', '重点关注')
    ]
    
    for low, high, rank_str, desc in ranks:
        if low <= percentile < high:
            rank = rank_str
            description = desc
            break
    else:
        rank = '前10%'
        description = '极其优秀'
    
    return {
        'value': round(energy_value, 2),
        'percentile': round(percentile, 1),
        'rank': rank,
        'description': description,
        'better_than': round(100 - percentile, 1)
    }


if __name__ == '__main__':
    from scipy import stats
    
    print("Generating household dataset...")
    dataset = HouseholdEnergyDataset(n_households=100)
    
    print(f"\nGenerated {dataset.n_households} households")
    print(f"  Household types:")
    types = {}
    for hh in dataset.households:
        t = hh.household_type
        types[t] = types.get(t, 0) + 1
    for t, c in types.items():
        print(f"    {t}: {c}")
    
    print(f"\nCreating comparator...")
    comparator = HouseholdComparator(dataset)
    
    target_profile = HouseholdProfile(
        household_id='TARGET',
        household_type='三口之家',
        dwelling_size=90,
        num_occupants=3,
        region='南方',
        has_ac=True,
        has_ev=False,
        has_solar=False
    )
    
    target_energy = {
        'monthly_total': 450.0
    }
    
    target_appliance_breakdown = {
        'refrigerator': 60,
        'lighting': 45,
        'air_conditioner': 150,
        'washing_machine': 25,
        'kitchen': 90,
        'entertainment': 40,
        'water_heater': 40
    }
    
    print(f"\nComparing target household...")
    result = comparator.compare_household(target_profile, target_energy, target_appliance_breakdown)
    
    print(f"\n=== Household Comparison Results ===")
    print(f"\nPeer Group: {result['peer_group']['size']} similar households")
    
    print(f"\nOverall Ranking:")
    print(f"  Monthly Energy: {result['overall']['target_monthly_kwh']} kWh")
    print(f"  Peer Average: {result['overall']['peer_stats']['mean']} kWh")
    print(f"  Percentile: {result['overall']['percentile']}%")
    print(f"  Level: {result['overall']['level']}")
    print(f"  vs Average: {result['overall']['vs_peer_avg']:+}%")
    
    print(f"\nAppliance Comparison:")
    for app, comp in result['appliance_comparison'].items():
        print(f"\n  {comp['name_cn']}:")
        print(f"    Yours: {comp['target_monthly']} kWh")
        print(f"    Peer Avg: {comp['peer_avg']} kWh")
        print(f"    Percentile: {comp['percentile']}%")
        print(f"    vs Average: {comp['vs_avg']:+}%")
        print(f"    Level: {comp['level']}")
    
    print(f"\nSaving Recommendations:")
    if result['saving_recommendations']:
        for rec in result['saving_recommendations']:
            print(f"  - {rec['appliance']}: 潜在节约 {rec['potential_saving']} kWh/月")
            print(f"    {rec['advice']}")
    else:
        print("  所有电器能耗均处于优秀水平！")
    
    print(f"\nBenchmark:")
    print(f"  Efficient Level (P25): {result['benchmark']['efficient']} kWh")
    print(f"  Average Level (P50): {result['benchmark']['average']} kWh")
    print(f"  Your Usage: {result['benchmark']['current']} kWh")
    print(f"  Potential Savings: {result['benchmark']['potential_saving_total']} kWh/月")
