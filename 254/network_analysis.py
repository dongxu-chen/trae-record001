import pandas as pd
import numpy as np
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class FraudNetworkAnalyzer:
    def __init__(self, claims_df):
        self.df = claims_df.copy()
        self.G = nx.Graph()
        self.fraud_groups = []
        
    def build_network(self):
        print("\n" + "="*70)
        print("BUILDING FRAUD DETECTION NETWORK")
        print("="*70)
        
        print("\nIdentifying shared identifiers across claims...")
        
        phone_groups = self._find_shared_entities('phone')
        address_groups = self._find_shared_entities('address')
        hospital_groups = self._find_shared_entities('hospital')
        bank_groups = self._find_shared_entities('bank_account')
        
        print(f"  - {len(phone_groups)} groups sharing phone numbers")
        print(f"  - {len(address_groups)} groups sharing addresses")
        print(f"  - {len(hospital_groups)} groups sharing hospitals")
        print(f"  - {len(bank_groups)} groups sharing bank accounts")
        
        self._build_graph(phone_groups, address_groups, hospital_groups, bank_groups)
        
        self._detect_fraud_rings()
        
        return self.fraud_groups
    
    def _find_shared_entities(self, column):
        groups = defaultdict(list)
        for idx, row in self.df.iterrows():
            if pd.notna(row[column]):
                groups[row[column]].append(idx)
        
        return {k: v for k, v in groups.items() if len(v) >= 2}
    
    def _build_graph(self, phone_groups, address_groups, hospital_groups, bank_groups):
        for idx, row in self.df.iterrows():
            self.G.add_node(
                row['claim_id'],
                type='claim',
                is_fraud=row['is_fraud'],
                fraud_prob=row.get('fraud_probability', 0.5),
                claim_amount=row['claim_amount'],
                name=row['name'],
                phone=row['phone'],
                address=row['address'],
                hospital=row['hospital'],
                bank=row['bank_account']
            )
        
        for phone, claim_indices in phone_groups.items():
            phone_node = f"PHONE:{phone}"
            self.G.add_node(phone_node, type='phone', value=phone)
            for idx in claim_indices:
                claim_id = self.df.iloc[idx]['claim_id']
                self.G.add_edge(claim_id, phone_node, relation='uses_phone')
        
        for address, claim_indices in address_groups.items():
            addr_node = f"ADDR:{address[:30]}"
            self.G.add_node(addr_node, type='address', value=address)
            for idx in claim_indices:
                claim_id = self.df.iloc[idx]['claim_id']
                self.G.add_edge(claim_id, addr_node, relation='lives_at')
        
        for hospital, claim_indices in hospital_groups.items():
            hosp_node = f"HOSP:{hospital}"
            self.G.add_node(hosp_node, type='hospital', value=hospital)
            for idx in claim_indices:
                claim_id = self.df.iloc[idx]['claim_id']
                self.G.add_edge(claim_id, hosp_node, relation='treated_at')
        
        for bank, claim_indices in bank_groups.items():
            bank_node = f"BANK:{bank}"
            self.G.add_node(bank_node, type='bank', value=bank)
            for idx in claim_indices:
                claim_id = self.df.iloc[idx]['claim_id']
                self.G.add_edge(claim_id, bank_node, relation='uses_bank')
        
        print(f"\nNetwork built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges")
    
    def _detect_fraud_rings(self):
        print("\n" + "="*70)
        print("DETECTING POTENTIAL FRAUD RINGS")
        print("="*70)
        
        phone_groups = self._find_shared_entities('phone')
        address_groups = self._find_shared_entities('address')
        hospital_groups = self._find_shared_entities('hospital')
        bank_groups = self._find_shared_entities('bank_account')
        
        ring_candidates = []
        
        for entity_name, groups in [('phone', phone_groups), ('address', address_groups), 
                                   ('hospital', hospital_groups), ('bank', bank_groups)]:
            for entity_value, claim_indices in groups.items():
                if len(claim_indices) >= 2:
                    claim_ids = [self.df.iloc[idx]['claim_id'] for idx in claim_indices]
                    fraud_count = sum(self.df.iloc[idx]['is_fraud'] for idx in claim_indices)
                    
                    if fraud_count >= 1:
                        ring_candidates.append({
                            'entity_type': entity_name,
                            'entity_value': entity_value,
                            'claim_ids': claim_ids,
                            'fraud_count': fraud_count,
                            'size': len(claim_ids)
                        })
        
        priority_order = {'phone': 0, 'bank': 1, 'address': 2, 'hospital': 3}
        ring_candidates.sort(key=lambda x: (priority_order.get(x['entity_type'], 99), 
                                           -x['fraud_count'] / x['size'], 
                                           -x['fraud_count']))
        
        visited_claims = set()
        ring_id = 0
        
        for candidate in ring_candidates:
            unvisited_claims = [cid for cid in candidate['claim_ids'] if cid not in visited_claims]
            
            if len(unvisited_claims) >= 2:
                fraud_ratio = candidate['fraud_count'] / candidate['size']
                
                if candidate['entity_type'] in ['phone', 'bank'] or \
                   (candidate['entity_type'] == 'address' and fraud_ratio >= 0.3) or \
                   (candidate['entity_type'] == 'hospital' and fraud_ratio >= 0.5 and candidate['size'] <= 20):
                    ring_id += 1
                    ring_data = self._analyze_ring(ring_id, unvisited_claims)
                    ring_data['shared_entity_type'] = candidate['entity_type']
                    ring_data['shared_entity_value'] = candidate['entity_value']
                    self.fraud_groups.append(ring_data)
                    
                    for cid in unvisited_claims:
                        visited_claims.add(cid)
        
        print(f"\nDetected {len(self.fraud_groups)} potential fraud rings")
        
        for i, ring in enumerate(self.fraud_groups[:10]):
            print(f"\nRing {ring['ring_id']}: {ring['size']} claims")
            entity_value = str(ring['shared_entity_value'])[:30]
            print(f"  Shared: {ring['shared_entity_type']} = {entity_value}...")
            print(f"  Total claim amount: ¥{ring['total_amount']:,.0f}")
            print(f"  Avg claim amount: ¥{ring['avg_amount']:,.0f}")
            print(f"  Known frauds: {ring['known_fraud_count']}/{ring['size']}")
            print(f"  Suspicion level: {ring['suspicion_level']}")
        
        if len(self.fraud_groups) > 10:
            print(f"\n... and {len(self.fraud_groups) - 10} more rings")
    
    def _get_connected_claims(self, start_claim):
        visited = set()
        queue = [start_claim]
        visited.add(start_claim)
        
        while queue:
            current = queue.pop(0)
            neighbors = self.G.neighbors(current)
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return [n for n in visited if self.G.nodes[n].get('type') == 'claim']
    
    def _analyze_ring(self, ring_id, claim_nodes):
        claims_data = []
        for claim_id in claim_nodes:
            node_data = self.G.nodes[claim_id]
            claims_data.append({
                'claim_id': claim_id,
                'is_fraud': node_data.get('is_fraud', 0),
                'fraud_prob': node_data.get('fraud_prob', 0.5),
                'amount': node_data.get('claim_amount', 0),
                'phone': node_data.get('phone'),
                'address': node_data.get('address'),
                'hospital': node_data.get('hospital'),
                'bank': node_data.get('bank')
            })
        
        df_ring = pd.DataFrame(claims_data)
        
        phones = df_ring['phone'].nunique()
        addresses = df_ring['address'].nunique()
        hospitals = df_ring['hospital'].nunique()
        banks = df_ring['bank'].nunique()
        
        shared = []
        if phones < len(df_ring):
            shared.append('phone')
        if addresses < len(df_ring):
            shared.append('address')
        if hospitals < len(df_ring):
            shared.append('hospital')
        if banks < len(df_ring):
            shared.append('bank')
        
        known_fraud_count = df_ring['is_fraud'].sum()
        avg_fraud_prob = df_ring['fraud_prob'].mean()
        total_amount = df_ring['amount'].sum()
        avg_amount = df_ring['amount'].mean()
        
        suspicion_score = (known_fraud_count / len(df_ring) * 0.4 + 
                          avg_fraud_prob * 0.3 + 
                          len(shared) / 4 * 0.3)
        
        if suspicion_score >= 0.7:
            suspicion_level = "🔴 极高"
        elif suspicion_score >= 0.4:
            suspicion_level = "🟡 中等"
        else:
            suspicion_level = "🟢 较低"
        
        return {
            'ring_id': ring_id,
            'size': len(df_ring),
            'claim_ids': claim_nodes,
            'claims': claims_data,
            'total_amount': total_amount,
            'avg_amount': avg_amount,
            'known_fraud_count': known_fraud_count,
            'avg_fraud_prob': avg_fraud_prob,
            'suspicion_score': suspicion_score,
            'suspicion_level': suspicion_level,
            'shared_attributes': shared
        }
    
    def visualize_network(self, output_path='plots/fraud_network.png', max_rings=3):
        print(f"\nGenerating network visualization...")
        
        plt.figure(figsize=(16, 12))
        
        pos = nx.spring_layout(self.G, k=0.3, iterations=50, seed=42)
        
        claim_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'claim']
        phone_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'phone']
        addr_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'address']
        hosp_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'hospital']
        bank_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'bank']
        
        fraud_claims = [n for n in claim_nodes if self.G.nodes[n].get('is_fraud') == 1]
        normal_claims = [n for n in claim_nodes if self.G.nodes[n].get('is_fraud') == 0]
        
        nx.draw_networkx_nodes(self.G, pos, nodelist=fraud_claims, 
                              node_color='red', node_size=200, alpha=0.8, label='Fraud Claims')
        nx.draw_networkx_nodes(self.G, pos, nodelist=normal_claims,
                              node_color='lightblue', node_size=150, alpha=0.6, label='Normal Claims')
        nx.draw_networkx_nodes(self.G, pos, nodelist=phone_nodes,
                              node_color='orange', node_size=100, alpha=0.7, label='Phone')
        nx.draw_networkx_nodes(self.G, pos, nodelist=addr_nodes,
                              node_color='green', node_size=100, alpha=0.7, label='Address')
        nx.draw_networkx_nodes(self.G, pos, nodelist=hosp_nodes,
                              node_color='purple', node_size=100, alpha=0.7, label='Hospital')
        nx.draw_networkx_nodes(self.G, pos, nodelist=bank_nodes,
                              node_color='brown', node_size=100, alpha=0.7, label='Bank')
        
        nx.draw_networkx_edges(self.G, pos, alpha=0.2, width=0.5)
        
        plt.title('Insurance Claim Fraud Detection Network', fontsize=16, fontweight='bold')
        plt.legend(scatterpoints=1, fontsize=10)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Network visualization saved to {output_path}")
    
    def generate_ring_report(self, ring_id):
        ring = next((r for r in self.fraud_groups if r['ring_id'] == ring_id), None)
        if not ring:
            return f"Ring {ring_id} not found"
        
        report = []
        report.append("="*70)
        report.append(f"FRAUD RING ANALYSIS REPORT - RING {ring_id}")
        report.append("="*70)
        report.append(f"\nRing Size: {ring['size']} claims")
        report.append(f"Shared Identifier: {ring.get('shared_entity_type', 'N/A')} = {ring.get('shared_entity_value', 'N/A')}")
        report.append(f"Total Claim Amount: ¥{ring['total_amount']:,.0f}")
        report.append(f"Average Claim Amount: ¥{ring['avg_amount']:,.0f}")
        report.append(f"Suspicion Level: {ring['suspicion_level']}")
        report.append(f"Suspicion Score: {ring['suspicion_score']:.2%}")
        report.append(f"Known Fraud Cases: {ring['known_fraud_count']}/{ring['size']}")
        report.append(f"Shared Attributes: {', '.join(ring['shared_attributes'])}")
        report.append(f"\nClaims in Ring:")
        report.append("-"*70)
        
        for claim in ring['claims']:
            fraud_status = "🔴 FRAUD" if claim['is_fraud'] else "🟢 NORMAL"
            report.append(f"  {claim['claim_id']} | {fraud_status} | ¥{claim['amount']:,.0f} | P={claim['fraud_prob']:.2%}")
        
        report.append("\n" + "="*70)
        report.append("RECOMMENDATIONS:")
        report.append("="*70)
        report.append("1. Investigate ALL claims in this ring together")
        report.append("2. Cross-reference shared identifiers across claims")
        report.append("3. Interview all claimants and look for connections")
        report.append("4. Check for organized fraud patterns")
        report.append("5. Consider involving law enforcement if confirmed")
        
        return "\n".join(report)


def analyze_network(claims_df):
    analyzer = FraudNetworkAnalyzer(claims_df)
    fraud_rings = analyzer.build_network()
    
    try:
        analyzer.visualize_network()
    except Exception as e:
        print(f"Visualization skipped: {e}")
    
    if fraud_rings:
        print("\n" + "="*70)
        print("HIGH RISK FRAUD RINGS (TOP 3)")
        print("="*70)
        
        high_risk = sorted(fraud_rings, key=lambda x: x['suspicion_score'], reverse=True)[:3]
        for ring in high_risk:
            if ring['suspicion_score'] >= 0.5:
                print(analyzer.generate_ring_report(ring['ring_id']))
    
    return analyzer, fraud_rings


if __name__ == '__main__':
    import os
    full_path = 'data/claims_full.csv'
    if not os.path.exists(full_path):
        print("Generating data with network identifiers...")
        from generate_data import generate_insurance_claims, save_data
        df = generate_insurance_claims(n_samples=10000, fraud_ratio=0.08, fraud_group_ratio=0.3)
        save_data(df)
    
    print("Loading claims data...")
    df = pd.read_csv(full_path, encoding='utf-8-sig')
    print(f"Loaded {len(df)} claims")
    
    if 'fraud_probability' not in df.columns:
        print("\nAdding dummy fraud probabilities for demo...")
        df['fraud_probability'] = df['is_fraud'].apply(lambda x: np.random.uniform(0.7, 0.99) if x == 1 else np.random.uniform(0, 0.3))
    
    analyzer, fraud_rings = analyze_network(df)
