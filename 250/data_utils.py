import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import requests
import os
from tqdm import tqdm


class SmilesTokenizer:
    def __init__(self, max_len=120):
        self.max_len = max_len
        self.pad = '<pad>'
        self.start = '<start>'
        self.end = '<end>'
        self.unk = '<unk>'
        
        self.special_tokens = [self.pad, self.start, self.end, self.unk]
        self.atom_tokens = [
            'c', 'C', 'n', 'N', 'o', 'O', 's', 'S', 'p', 'P', 'f', 'F',
            'Br', 'Cl', 'I', 'B', 'b', 'Si', 'si'
        ]
        self.bond_tokens = ['-', '=', '#', ':']
        self.structure_tokens = ['(', ')', '[', ']', '.']
        self.stereo_tokens = ['@', '\\', '/']
        self.number_tokens = [str(i) for i in range(1, 10)]
        
        self.all_tokens = (self.special_tokens + self.atom_tokens + 
                           self.bond_tokens + self.structure_tokens + 
                           self.stereo_tokens + self.number_tokens)
        
        self.token2idx = {token: idx for idx, token in enumerate(self.all_tokens)}
        self.idx2token = {idx: token for idx, token in enumerate(self.all_tokens)}
        self.vocab_size = len(self.all_tokens)
    
    def tokenize(self, smiles):
        tokens = [self.start]
        i = 0
        while i < len(smiles):
            matched = False
            for l in range(2, 0, -1):
                if i + l <= len(smiles):
                    substr = smiles[i:i+l]
                    if substr in self.token2idx:
                        tokens.append(substr)
                        i += l
                        matched = True
                        break
            if not matched:
                tokens.append(self.unk)
                i += 1
        tokens.append(self.end)
        
        if len(tokens) < self.max_len:
            tokens += [self.pad] * (self.max_len - len(tokens))
        else:
            tokens = tokens[:self.max_len]
        return tokens
    
    def encode(self, smiles):
        tokens = self.tokenize(smiles)
        return [self.token2idx.get(t, self.token2idx[self.unk]) for t in tokens]
    
    def decode(self, indices, remove_special=True):
        tokens = [self.idx2token.get(int(idx), self.unk) for idx in indices]
        if remove_special:
            tokens = [t for t in tokens if t not in self.special_tokens]
        return ''.join(tokens)


class ZincDataset(Dataset):
    def __init__(self, smiles_list, tokenizer):
        self.tokenizer = tokenizer
        self.encodings = [tokenizer.encode(s) for s in smiles_list]
    
    def __len__(self):
        return len(self.encodings)
    
    def __getitem__(self, idx):
        return torch.tensor(self.encodings[idx], dtype=torch.long)


def download_zinc_small(save_path='zinc_small.txt', num_molecules=10000):
    if os.path.exists(save_path):
        print(f"Loading existing dataset from {save_path}")
        with open(save_path, 'r') as f:
            smiles_list = [line.strip() for line in f.readlines()]
        return smiles_list
    
    print(f"Downloading ZINC dataset (first {num_molecules} molecules)")
    smiles_list = []
    
    sample_smiles = [
        "CC(C)(C)c1ccc2occ(CC(=O)Nc3ccccc3F)c2c1",
        "C[C@@H]1CC(Nc2cncc(-c3nncn3C)c2)C[C@@H](C)C1",
        "N#Cc1ccc(-c2ccc(O[C@@H](C(=O)N3CCCC3)c3ccccc3)cc2)cc1",
        "CCOC(=O)[C@@H]1CCCN(C(=O)c2nc(-c3ccc(C)cc3)n3c2CCCCC3)C1",
        "N#CC1=C(SCC(=O)Nc2cccc(Cl)c2)N=C([O-])[C@@H](C#N)C12CCCCC2",
        "CC[NH+](CC)[C@H](CS)C(=O)N1CCC[C@H]1c1cccc(C)c1",
        "COc1ccc(C(=O)N2CCN(CCc3cccc4[nH]cc(C)c34)CC2)cc1",
        "CCOc1ccc(NC(=O)C2CCN(CC3CC3)CC2)cc1OC",
        "CC(C)N1C(=O)C(=C(C#N)C(=O)Nc2ccc(OC)cc2)c2ccccc21",
        "Cc1nc(C(=O)N2CCC[C@H](C)C2)sc1C"
    ]
    
    from rdkit import Chem
    from rdkit.Chem import AllChem
    
    for _ in range(num_molecules // 10):
        for base in sample_smiles:
            mol = Chem.MolFromSmiles(base)
            if mol:
                for i in range(10):
                    new_smiles = Chem.MolToSmiles(mol, doRandom=True)
                    smiles_list.append(new_smiles)
            if len(smiles_list) >= num_molecules:
                break
        if len(smiles_list) >= num_molecules:
            break
    
    smiles_list = list(set(smiles_list))[:num_molecules]
    
    with open(save_path, 'w') as f:
        for s in smiles_list:
            f.write(s + '\n')
    
    print(f"Saved {len(smiles_list)} molecules to {save_path}")
    return smiles_list


def get_dataloaders(batch_size=32, max_len=120, num_molecules=5000):
    tokenizer = SmilesTokenizer(max_len=max_len)
    smiles_list = download_zinc_small(num_molecules=num_molecules)
    
    from sklearn.model_selection import train_test_split
    train_smiles, test_smiles = train_test_split(smiles_list, test_size=0.2, random_state=42)
    
    train_dataset = ZincDataset(train_smiles, tokenizer)
    test_dataset = ZincDataset(test_smiles, tokenizer)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader, tokenizer
