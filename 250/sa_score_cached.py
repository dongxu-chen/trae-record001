import math
import os
import pickle
import hashlib
from functools import lru_cache
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors, AllChem


_fscores = None
_fragment_cache = {}
_molecule_cache = {}
_sa_score_cache = {}
_cache_stats = {'hits': 0, 'misses': 0}


def get_cache_stats():
    return _cache_stats.copy()


def reset_cache_stats():
    global _cache_stats
    _cache_stats = {'hits': 0, 'misses': 0}


def clear_cache():
    global _fragment_cache, _molecule_cache, _sa_score_cache
    _fragment_cache.clear()
    _molecule_cache.clear()
    _sa_score_cache.clear()
    reset_cache_stats()


def save_cache(cache_file='sa_score_cache.pkl'):
    cache_data = {
        'fragment_cache': _fragment_cache,
        'sa_score_cache': _sa_score_cache
    }
    with open(cache_file, 'wb') as f:
        pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"Cache saved to {cache_file}. Entries: {len(_sa_score_cache)}")


def load_cache(cache_file='sa_score_cache.pkl'):
    global _fragment_cache, _sa_score_cache
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        _fragment_cache.update(cache_data.get('fragment_cache', {}))
        _sa_score_cache.update(cache_data.get('sa_score_cache', {}))
        print(f"Cache loaded from {cache_file}. Entries: {len(_sa_score_cache)}")
        return True
    return False


def smiles_fingerprint(smiles, radius=2, nBits=2048):
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nBits)
        return fp.ToBase64()
    except:
        return None


def substructure_key(mol_fragment):
    try:
        smi = Chem.MolToSmiles(mol_fragment, canonical=True)
        return smi
    except:
        return None


def readFragmentScores(name='fpscores'):
    global _fscores
    if _fscores is not None:
        return
    
    try:
        data_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(data_dir, f'{name}.pkl.gz')
        
        if os.path.exists(filename):
            import gzip
            with gzip.open(filename, 'rb') as f:
                _fscores = pickle.load(f)
        else:
            _fscores = generateDefaultFragmentScores()
    except:
        _fscores = generateDefaultFragmentScores()


def generateDefaultFragmentScores():
    common_fragments = {
        'c1ccccc1': -2.0,
        'C1CCCCC1': -1.5,
        'c1ccncc1': -1.8,
        'c1ccccc1C': -1.0,
        'C1CCNCC1': -1.2,
        'c1ccc(O)cc1': -1.0,
        'c1ccc(Cl)cc1': -0.8,
        'c1ccc(F)cc1': -0.9,
        'C1CC1': -0.5,
        'C1CCC1': -0.7,
        'c1ccco1': -1.2,
        'c1cccs1': -1.3,
        'c1cncnc1': -1.5,
        'O=C(O)': -0.5,
        'O=C(N)': -0.6,
        'C(=O)O': -0.5,
        'C(=O)N': -0.6,
        'CN': -0.3,
        'CO': -0.4,
        'CF': -0.3,
        'CCl': -0.3,
        'CBr': -0.4,
        'c1cc(Cl)ccc1': -0.8,
        'c1cc(F)ccc1': -0.9,
        'C1CCNC1': -0.8,
        'C1CNCC1': -0.9,
        'c1ccc(C)cc1': -0.8,
        'c1ccc(Oc)cc1': -0.7,
        'n1cccnc1': -1.4,
        'n1ccncc1': -1.5,
        'c1ccc(NC)cc1': -0.6,
        'c1ccc(CO)cc1': -0.6,
        'c1ccc(CN)cc1': -0.6,
        'C1=CCCCC1': -1.0,
        'c1ccc2ccccc2c1': -2.5,
        'c1ccc2c(c1)cccc2': -2.5,
        'O=Cc1ccccc1': -0.7,
        'N#Cc1ccccc1': -0.8,
        'c1ccc(C#N)cc1': -0.8,
        'c1ccc(C(=O)O)cc1': -1.0,
        'c1ccc(C(=O)N)cc1': -0.9,
        'c1ccc(OCC)cc1': -0.8,
    }
    return common_fragments


def getFragmentsCached(mol):
    global _cache_stats
    
    mol_key = Chem.MolToSmiles(mol, canonical=True) if mol else None
    
    if mol_key and mol_key in _fragment_cache:
        _cache_stats['hits'] += 1
        return _fragment_cache[mol_key]
    
    _cache_stats['misses'] += 1
    
    try:
        fragments = rdMolDescriptors.GetMorganFingerprint(mol, 2)
        frag_dict = fragments.GetNonzeroElements()
        
        if mol_key:
            _fragment_cache[mol_key] = frag_dict
            
        return frag_dict
    except:
        return {}


def getFragmentScoreCached(fp, count=1):
    global _cache_stats, _fscores
    
    fp_key = str(fp)
    
    if fp_key in _fscores:
        return _fscores[fp_key] * count
    
    return 3.0 * count


def calculateSAScoreCached(smiles, use_cache=True):
    global _cache_stats, _sa_score_cache
    
    if use_cache and smiles in _sa_score_cache:
        _cache_stats['hits'] += 1
        return _sa_score_cache[smiles]
    
    _cache_stats['misses'] += 1
    
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    
    readFragmentScores()
    
    try:
        fragments = getFragmentsCached(mol)
        
        if not fragments:
            return 6.0
        
        total_score = 0.0
        total_count = 0
        
        for fp, count in fragments.items():
            total_score += getFragmentScoreCached(fp, count)
            total_count += count
        
        if total_count > 0:
            avg_score = total_score / total_count
        else:
            avg_score = 3.0
        
        num_atoms = mol.GetNumAtoms()
        num_rings = rdMolDescriptors.CalcNumRings(mol)
        num_macrocycles = sum(1 for ring in mol.GetRingInfo().AtomRings() if len(ring) > 8)
        
        complexity_penalty = 0.0
        if num_atoms > 50:
            complexity_penalty += (num_atoms - 50) * 0.1
        if num_rings > 5:
            complexity_penalty += (num_rings - 5) * 0.2
        complexity_penalty += num_macrocycles * 1.0
        
        stereo_centers = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
        complexity_penalty += stereo_centers * 0.1
        
        sa_score = 5.0 + avg_score + complexity_penalty
        sa_score = max(1.0, min(10.0, sa_score))
        
        if use_cache:
            _sa_score_cache[smiles] = sa_score
        
        return sa_score
        
    except Exception as e:
        return None


def calculate_average_sa_score_cached(smiles_list, use_cache=True):
    scores = []
    for s in smiles_list:
        score = calculateSAScoreCached(s, use_cache=use_cache)
        if score is not None:
            scores.append(score)
    
    if len(scores) == 0:
        return None, 0
    
    return sum(scores) / len(scores), len(scores)


def precompute_sa_scores(smiles_list, batch_size=1000, use_cache=True, save_interval=5000):
    print(f"Precomputing SA Scores for {len(smiles_list)} molecules...")
    
    from tqdm import tqdm
    
    for i in tqdm(range(0, len(smiles_list), batch_size)):
        batch = smiles_list[i:i+batch_size]
        for s in batch:
            calculateSAScoreCached(s, use_cache=use_cache)
        
        if (i + batch_size) % save_interval == 0:
            save_cache()
    
    save_cache()
    
    stats = get_cache_stats()
    print(f"Precomputation complete. Cache hits: {stats['hits']}, misses: {stats['misses']}")
    print(f"Total cached entries: {len(_sa_score_cache)}")


class SAScoreScorer:
    def __init__(self, cache_file=None, use_cache=True):
        self.use_cache = use_cache
        readFragmentScores()
        
        if cache_file and use_cache:
            load_cache(cache_file)
    
    def score(self, smiles):
        return calculateSAScoreCached(smiles, use_cache=self.use_cache)
    
    def score_batch(self, smiles_list):
        return [self.score(s) for s in smiles_list]
    
    def save(self, cache_file='sa_score_cache.pkl'):
        if self.use_cache:
            save_cache(cache_file)
    
    def get_stats(self):
        return get_cache_stats()
    
    def clear(self):
        clear_cache()


def calculate_sa_score_distribution_cached(smiles_list, bins=None, use_cache=True):
    if bins is None:
        bins = [1, 3, 5, 7, 9, 11]
    
    scores = []
    for s in smiles_list:
        score = calculateSAScoreCached(s, use_cache=use_cache)
        if score is not None:
            scores.append(score)
    
    if len(scores) == 0:
        return {}
    
    distribution = {}
    for i in range(len(bins) - 1):
        low, high = bins[i], bins[i + 1]
        count = sum(1 for s in scores if low <= s < high)
        distribution[f'{low}-{high}'] = count / len(scores)
    
    return distribution
