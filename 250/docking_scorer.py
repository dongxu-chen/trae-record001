import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski, QED
from collections import defaultdict
import pickle
import os


class DockingScorer:
    def __init__(self, cache_file='docking_cache.pkl', use_cache=True):
        self.use_cache = use_cache
        self.cache_file = cache_file
        self.cache = {}
        self.target_specific_params = defaultdict(dict)
        
        if use_cache and os.path.exists(cache_file):
            self.load_cache()
        
        self._init_target_params()
    
    def _init_target_params(self):
        self.target_specific_params['EGFR'] = {
            'preferred_mw': (400, 550),
            'preferred_logp': (3.5, 5.5),
            'preferred_hbd': (2, 4),
            'preferred_hba': (6, 10),
            'preferred_rotatable': (5, 10),
            'hydrophobic_preference': 0.7,
            'aromatic_preference': 0.8,
            'target_bias': -8.0,
        }
        
        self.target_specific_params['HER2'] = {
            'preferred_mw': (350, 500),
            'preferred_logp': (3.0, 5.0),
            'preferred_hbd': (1, 3),
            'preferred_hba': (5, 9),
            'preferred_rotatable': (4, 9),
            'hydrophobic_preference': 0.6,
            'aromatic_preference': 0.7,
            'target_bias': -7.5,
        }
        
        self.target_specific_params['DRD2'] = {
            'preferred_mw': (300, 450),
            'preferred_logp': (2.5, 4.5),
            'preferred_hbd': (1, 3),
            'preferred_hba': (4, 8),
            'preferred_rotatable': (3, 8),
            'hydrophobic_preference': 0.5,
            'aromatic_preference': 0.6,
            'target_bias': -7.0,
        }
        
        self.target_specific_params['ACE2'] = {
            'preferred_mw': (450, 600),
            'preferred_logp': (2.0, 4.0),
            'preferred_hbd': (3, 6),
            'preferred_hba': (8, 12),
            'preferred_rotatable': (6, 12),
            'hydrophobic_preference': 0.4,
            'aromatic_preference': 0.5,
            'target_bias': -8.5,
        }
        
        self.target_specific_params['default'] = {
            'preferred_mw': (350, 500),
            'preferred_logp': (2.5, 4.5),
            'preferred_hbd': (2, 5),
            'preferred_hba': (5, 10),
            'preferred_rotatable': (4, 10),
            'hydrophobic_preference': 0.5,
            'aromatic_preference': 0.5,
            'target_bias': -7.0,
        }
    
    def save_cache(self):
        if self.use_cache:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
    
    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                self.cache = pickle.load(f)
    
    def _get_cache_key(self, smiles, target_name):
        return f"{smiles}_{target_name}"
    
    def calculate_properties(self, mol):
        props = {}
        props['mw'] = Descriptors.MolWt(mol)
        props['logp'] = Descriptors.MolLogP(mol)
        props['hbd'] = Lipinski.NumHDonors(mol)
        props['hba'] = Lipinski.NumHAcceptors(mol)
        props['rotatable_bonds'] = Lipinski.NumRotatableBonds(mol)
        props['tpsa'] = Descriptors.TPSA(mol)
        props['num_rings'] = Lipinski.RingCount(mol)
        props['num_aromatic_rings'] = Lipinski.NumAromaticRings(mol)
        props['num_heavy_atoms'] = mol.GetNumHeavyAtoms()
        
        try:
            props['qed'] = QED.qed(mol)
        except:
            props['qed'] = 0.5
        
        return props
    
    def _gaussian_penalty(self, value, preferred_range):
        low, high = preferred_range
        center = (low + high) / 2
        width = (high - low) / 2
        return np.exp(-((value - center) ** 2) / (2 * width ** 2))
    
    def score_target_affinity(self, smiles, target_name='default'):
        if self.use_cache:
            cache_key = self._get_cache_key(smiles, target_name)
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        try:
            params = self.target_specific_params.get(target_name, self.target_specific_params['default'])
            props = self.calculate_properties(mol)
            
            property_scores = {}
            property_scores['mw'] = self._gaussian_penalty(props['mw'], params['preferred_mw'])
            property_scores['logp'] = self._gaussian_penalty(props['logp'], params['preferred_logp'])
            property_scores['hbd'] = self._gaussian_penalty(props['hbd'], params['preferred_hbd'])
            property_scores['hba'] = self._gaussian_penalty(props['hba'], params['preferred_hba'])
            property_scores['rotatable'] = self._gaussian_penalty(
                props['rotatable_bonds'], params['preferred_rotatable']
            )
            
            aromatic_ratio = props['num_aromatic_rings'] / max(props['num_rings'], 1)
            property_scores['aromatic'] = aromatic_ratio * params['aromatic_preference']
            
            hydrophobicity_score = (props['logp'] / 5.0) * params['hydrophobic_preference']
            hydrophobicity_score = max(0.0, min(1.0, hydrophobicity_score))
            property_scores['hydrophobic'] = hydrophobicity_score
            
            tpsa_score = 1.0 - min(1.0, props['tpsa'] / 150.0)
            property_scores['tpsa'] = tpsa_score
            
            weights = {
                'mw': 0.15,
                'logp': 0.20,
                'hbd': 0.10,
                'hba': 0.10,
                'rotatable': 0.10,
                'aromatic': 0.15,
                'hydrophobic': 0.15,
                'tpsa': 0.05,
            }
            
            total_score = sum(property_scores[k] * weights[k] for k in weights)
            
            docking_score = params['target_bias'] * (1 - total_score) - 2.0
            
            docking_score = docking_score + np.random.normal(0, 0.5)
            
            docking_score = max(-15.0, min(-3.0, docking_score))
            
            result = {
                'docking_score': docking_score,
                'property_scores': property_scores,
                'properties': props,
                'qed_score': props['qed'],
            }
            
            if self.use_cache:
                self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            return None
    
    def batch_score(self, smiles_list, target_name='default', verbose=False):
        results = []
        for i, smiles in enumerate(smiles_list):
            score = self.score_target_affinity(smiles, target_name)
            results.append(score)
            if verbose and (i + 1) % 100 == 0:
                print(f"Scored {i + 1}/{len(smiles_list)} molecules")
        
        return results
    
    def filter_by_affinity(self, smiles_list, target_name='default', threshold=-7.0):
        filtered = []
        scores = []
        
        for smiles in smiles_list:
            result = self.score_target_affinity(smiles, target_name)
            if result and result['docking_score'] <= threshold:
                filtered.append(smiles)
                scores.append(result['docking_score'])
        
        return filtered, scores
    
    def rank_molecules(self, smiles_list, target_name='default', top_k=None):
        results = []
        for smiles in smiles_list:
            result = self.score_target_affinity(smiles, target_name)
            if result:
                results.append((smiles, result['docking_score'], result))
        
        results.sort(key=lambda x: x[1])
        
        if top_k:
            results = results[:top_k]
        
        return results


class InteractionPredictor:
    def __init__(self):
        self.h_bond_donors = ['N', 'O', 'S']
        self.h_bond_acceptors = ['N', 'O', 'S', 'F', 'Cl']
        self.hydrophobic_atoms = ['C', 'F', 'Cl', 'Br', 'I']
    
    def predict_interactions(self, ligand_smiles, pocket_sequence):
        mol = Chem.MolFromSmiles(ligand_smiles)
        if mol is None:
            return None
        
        try:
            interactions = {
                'h_bond_donors': 0,
                'h_bond_acceptors': 0,
                'hydrophobic_contacts': 0,
                'aromatic_interactions': 0,
                'total_interactions': 0,
            }
            
            for atom in mol.GetAtoms():
                symbol = atom.GetSymbol()
                if symbol in self.h_bond_donors:
                    if atom.GetTotalNumHs() > 0:
                        interactions['h_bond_donors'] += 1
                if symbol in self.h_bond_acceptors:
                    interactions['h_bond_acceptors'] += 1
                if symbol in self.hydrophobic_atoms:
                    interactions['hydrophobic_contacts'] += 1
            
            aromatic_rings = 0
            for ring in mol.GetRingInfo().AtomRings():
                is_aromatic = all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring)
                if is_aromatic:
                    aromatic_rings += 1
            interactions['aromatic_interactions'] = aromatic_rings * 2
            
            pocket_hydro = sum(1 for aa in pocket_sequence if aa in 'AVLIFMWY')
            pocket_polar = sum(1 for aa in pocket_sequence if aa in 'STNQ')
            pocket_charged = sum(1 for aa in pocket_sequence if aa in 'RHKDE')
            
            pocket_bias = (pocket_hydro * 0.5 + pocket_polar * 0.3 + pocket_charged * 0.2) / max(len(pocket_sequence), 1)
            
            interactions['total_interactions'] = (
                interactions['h_bond_donors'] +
                interactions['h_bond_acceptors'] +
                interactions['hydrophobic_contacts'] * 0.3 +
                interactions['aromatic_interactions']
            ) * pocket_bias
            
            return interactions
            
        except:
            return None


def calculate_ligand_efficiency(docking_score, num_heavy_atoms):
    if num_heavy_atoms == 0:
        return 0.0
    return docking_score / num_heavy_atoms


def select_leads(smiles_list, target_name='default', num_leads=10, 
                 diversity_weight=0.3, affinity_weight=0.7):
    from rdkit.Chem import AllChem, DataStructs
    
    scorer = DockingScorer()
    results = scorer.rank_molecules(smiles_list, target_name)
    
    if len(results) == 0:
        return []
    
    mols = []
    fps = []
    for smiles, score, details in results:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            mols.append((smiles, score, details))
            fps.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024))
    
    if len(mols) == 0:
        return []
    
    selected = []
    selected_indices = []
    
    normalized_scores = np.array([s for _, s, _ in mols])
    normalized_scores = (normalized_scores - normalized_scores.min()) / (normalized_scores.max() - normalized_scores.min() + 1e-8)
    
    while len(selected) < num_leads and len(selected_indices) < len(mols):
        best_idx = -1
        best_composite = float('inf')
        
        for i in range(len(mols)):
            if i in selected_indices:
                continue
            
            diversity_penalty = 0.0
            for j in selected_indices:
                sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
                diversity_penalty = max(diversity_penalty, sim)
            
            composite_score = (
                affinity_weight * normalized_scores[i] +
                diversity_weight * diversity_penalty
            )
            
            if composite_score < best_composite:
                best_composite = composite_score
                best_idx = i
        
        if best_idx >= 0:
            selected.append(mols[best_idx])
            selected_indices.append(best_idx)
    
    return selected
