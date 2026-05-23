import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski
from collections import Counter


VALENCE_RULES = {
    'C': [4],
    'N': [3, 5],
    'O': [2],
    'S': [2, 4, 6],
    'F': [1],
    'Cl': [1],
    'Br': [1],
    'I': [1],
    'P': [3, 5],
    'B': [3],
    'Si': [4],
}


def check_valency(mol):
    if mol is None:
        return False
    
    try:
        for atom in mol.GetAtoms():
            symbol = atom.GetSymbol()
            if symbol not in VALENCE_RULES:
                continue
            
            explicit_valence = atom.GetExplicitValence()
            implicit_valence = atom.GetImplicitValence()
            total_valence = explicit_valence + implicit_valence
            
            allowed_valences = VALENCE_RULES[symbol]
            if total_valence not in allowed_valences:
                return False
        return True
    except:
        return False


def check_ring_sizes(mol, min_ring=3, max_ring=8):
    if mol is None:
        return False
    
    try:
        ring_info = mol.GetRingInfo()
        atom_rings = ring_info.AtomRings()
        
        for ring in atom_rings:
            ring_size = len(ring)
            if ring_size < min_ring or ring_size > max_ring:
                return False
        return True
    except:
        return False


def check_aromaticity(mol):
    if mol is None:
        return False
    
    try:
        for atom in mol.GetAtoms():
            if atom.GetIsAromatic():
                symbol = atom.GetSymbol()
                if symbol not in ['C', 'N', 'O', 'S', 'B', 'P']:
                    return False
        return True
    except:
        return False


def is_valid_molecule(smiles):
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        
        if not check_valency(mol):
            return False
        
        if not check_ring_sizes(mol):
            return False
        
        if not check_aromaticity(mol):
            return False
        
        try:
            Chem.SanitizeMol(mol)
        except:
            return False
        
        return True
    except:
        return False


def filter_valid_molecules(smiles_list):
    valid_smiles = []
    for s in smiles_list:
        if is_valid_molecule(s):
            valid_smiles.append(s)
    return valid_smiles


def calculate_validity(smiles_list):
    if len(smiles_list) == 0:
        return 0.0
    
    valid_count = sum(1 for s in smiles_list if is_valid_molecule(s))
    return valid_count / len(smiles_list)


def calculate_uniqueness(smiles_list):
    if len(smiles_list) == 0:
        return 0.0
    
    valid_smiles = [s for s in smiles_list if is_valid_molecule(s)]
    if len(valid_smiles) == 0:
        return 0.0
    
    unique_smiles = set(valid_smiles)
    return len(unique_smiles) / len(valid_smiles)


def calculate_diversity(smiles_list, sample_size=None):
    valid_smiles = [s for s in smiles_list if is_valid_molecule(s)]
    if len(valid_smiles) < 2:
        return 0.0
    
    if sample_size and len(valid_smiles) > sample_size:
        indices = np.random.choice(len(valid_smiles), sample_size, replace=False)
        valid_smiles = [valid_smiles[i] for i in indices]
    
    mols = [Chem.MolFromSmiles(s) for s in valid_smiles]
    mols = [m for m in mols if m is not None]
    
    if len(mols) < 2:
        return 0.0
    
    fps = [AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=1024) for m in mols]
    
    pairwise_sims = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            sim = AllChem.DataStructs.TanimotoSimilarity(fps[i], fps[j])
            pairwise_sims.append(sim)
    
    if len(pairwise_sims) == 0:
        return 0.0
    
    avg_sim = np.mean(pairwise_sims)
    diversity = 1.0 - avg_sim
    
    return diversity


def calculate_diversity_fast(smiles_list):
    valid_smiles = [s for s in smiles_list if is_valid_molecule(s)]
    if len(valid_smiles) == 0:
        return 0.0
    
    unique_smiles = list(set(valid_smiles))
    return len(unique_smiles) / len(valid_smiles)


def get_molecular_properties(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    
    props = {
        'mw': Descriptors.MolWt(mol),
        'logp': Descriptors.MolLogP(mol),
        'h_donors': Lipinski.NumHDonors(mol),
        'h_acceptors': Lipinski.NumHAcceptors(mol),
        'rotatable_bonds': Lipinski.NumRotatableBonds(mol),
        'tpsa': Descriptors.TPSA(mol),
        'num_rings': Lipinski.RingCount(mol),
        'num_atoms': mol.GetNumAtoms(),
    }
    return props


def check_lipinski_rule_of_five(smiles):
    props = get_molecular_properties(smiles)
    if props is None:
        return False
    
    violations = 0
    if props['mw'] > 500: violations += 1
    if props['logp'] > 5: violations += 1
    if props['h_donors'] > 5: violations += 1
    if props['h_acceptors'] > 10: violations += 1
    
    return violations <= 1
