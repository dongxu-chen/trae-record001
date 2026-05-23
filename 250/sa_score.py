import math
import os
import pickle
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


_fscores = None


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
    }
    return common_fragments


def getFragments(mol):
    try:
        fragments = rdMolDescriptors.GetMorganFingerprint(mol, 2)
        return fragments.GetNonzeroElements()
    except:
        return {}


def calculateSAScore(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    
    readFragmentScores()
    
    try:
        fragments = getFragments(mol)
        
        if not fragments:
            return 6.0
        
        total_score = 0.0
        total_count = 0
        
        for fp, count in fragments.items():
            fp_str = str(fp)
            if fp_str in _fscores:
                total_score += _fscores[fp_str] * count
                total_count += count
            else:
                total_score += 3.0 * count
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
        
        return sa_score
        
    except Exception as e:
        return None


def calculate_average_sa_score(smiles_list):
    scores = []
    for s in smiles_list:
        score = calculateSAScore(s)
        if score is not None:
            scores.append(score)
    
    if len(scores) == 0:
        return None, 0
    
    return sum(scores) / len(scores), len(scores)


def calculate_sa_score_distribution(smiles_list, bins=None):
    if bins is None:
        bins = [1, 3, 5, 7, 9, 11]
    
    scores = []
    for s in smiles_list:
        score = calculateSAScore(s)
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
