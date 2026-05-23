import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import Counter


AMINO_ACIDS = 'ACDEFGHIKLMNPQRSTVWY'
AA_TO_IDX = {aa: i for i, aa in enumerate(AMINO_ACIDS)}
AA_TO_IDX['<pad>'] = len(AMINO_ACIDS)
AA_TO_IDX['<unk>'] = len(AMINO_ACIDS) + 1


PROTEIN_PROPERTIES = {
    'A': {'hydrophobicity': 1.8, 'volume': 88.6, 'polarity': 0.0},
    'C': {'hydrophobicity': 2.5, 'volume': 108.5, 'polarity': 1.5},
    'D': {'hydrophobicity': -3.5, 'volume': 111.1, 'polarity': 49.7},
    'E': {'hydrophobicity': -3.5, 'volume': 138.4, 'polarity': 49.9},
    'F': {'hydrophobicity': 2.8, 'volume': 189.9, 'polarity': 0.4},
    'G': {'hydrophobicity': -0.4, 'volume': 60.1, 'polarity': 0.0},
    'H': {'hydrophobicity': -3.2, 'volume': 153.2, 'polarity': 42.1},
    'I': {'hydrophobicity': 4.5, 'volume': 166.7, 'polarity': 0.2},
    'K': {'hydrophobicity': -3.9, 'volume': 168.6, 'polarity': 49.5},
    'L': {'hydrophobicity': 3.8, 'volume': 166.7, 'polarity': 0.2},
    'M': {'hydrophobicity': 1.9, 'volume': 162.9, 'polarity': 1.4},
    'N': {'hydrophobicity': -3.5, 'volume': 114.1, 'polarity': 40.6},
    'P': {'hydrophobicity': -1.6, 'volume': 112.7, 'polarity': 1.6},
    'Q': {'hydrophobicity': -3.5, 'volume': 143.8, 'polarity': 40.7},
    'R': {'hydrophobicity': -4.5, 'volume': 173.4, 'polarity': 52.0},
    'S': {'hydrophobicity': -0.8, 'volume': 89.0, 'polarity': 29.7},
    'T': {'hydrophobicity': -0.7, 'volume': 116.1, 'polarity': 25.7},
    'V': {'hydrophobicity': 4.2, 'volume': 140.0, 'polarity': 0.2},
    'W': {'hydrophobicity': -0.9, 'volume': 227.8, 'polarity': 1.1},
    'Y': {'hydrophobicity': -1.3, 'volume': 193.6, 'polarity': 34.9},
}


def encode_protein_sequence(sequence, max_len=500):
    encoded = []
    for aa in sequence[:max_len]:
        if aa in AA_TO_IDX:
            encoded.append(AA_TO_IDX[aa])
        else:
            encoded.append(AA_TO_IDX['<unk>'])
    
    if len(encoded) < max_len:
        encoded += [AA_TO_IDX['<pad>']] * (max_len - len(encoded))
    
    return np.array(encoded)


def get_protein_properties(sequence):
    props = []
    for aa in sequence:
        if aa in PROTEIN_PROPERTIES:
            p = PROTEIN_PROPERTIES[aa]
            props.append([p['hydrophobicity'], p['volume'], p['polarity']])
        else:
            props.append([0.0, 0.0, 0.0])
    return np.array(props)


class ProteinCNNEncoder(nn.Module):
    def __init__(self, vocab_size=22, embed_size=64, hidden_size=256, output_dim=256, max_len=500):
        super(ProteinCNNEncoder, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=AA_TO_IDX['<pad>'])
        self.dropout = nn.Dropout(0.3)
        
        self.conv_layers = nn.ModuleList([
            nn.Conv1d(embed_size, hidden_size // 4, kernel_size=3, padding=1),
            nn.Conv1d(hidden_size // 4, hidden_size // 2, kernel_size=5, padding=2),
            nn.Conv1d(hidden_size // 2, hidden_size, kernel_size=7, padding=3),
        ])
        
        self.pool = nn.AdaptiveMaxPool1d(1)
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, output_dim)
        )
        
    def forward(self, x):
        x = self.embedding(x)
        x = self.dropout(x)
        x = x.transpose(1, 2)
        
        for conv in self.conv_layers:
            x = F.relu(conv(x))
            x = self.dropout(x)
        
        x = self.pool(x)
        x = x.squeeze(2)
        
        x = self.fc(x)
        
        return x


class ProteinLSTMEncoder(nn.Module):
    def __init__(self, vocab_size=22, embed_size=64, hidden_size=256, output_dim=256, num_layers=2, max_len=500):
        super(ProteinLSTMEncoder, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=AA_TO_IDX['<pad>'])
        self.dropout = nn.Dropout(0.3)
        
        self.lstm = nn.LSTM(
            embed_size,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.3
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, output_dim)
        )
        
    def forward(self, x):
        x = self.embedding(x)
        x = self.dropout(x)
        
        output, (h, c) = self.lstm(x)
        
        h_forward = h[-2]
        h_backward = h[-1]
        h_combined = torch.cat([h_forward, h_backward], dim=1)
        
        x = self.fc(h_combined)
        
        return x


class BindingPocketDetector:
    def __init__(self):
        self.hydrophobic_aas = {'A', 'V', 'L', 'I', 'F', 'M', 'W'}
        self.polar_aas = {'S', 'T', 'N', 'Q', 'Y'}
        self.charged_aas = {'R', 'H', 'K', 'D', 'E'}
        
    def predict_pocket(self, sequence, window_size=15):
        scores = []
        n = len(sequence)
        
        for i in range(n):
            start = max(0, i - window_size // 2)
            end = min(n, i + window_size // 2 + 1)
            window = sequence[start:end]
            
            aa_counts = Counter(window)
            hydro_count = sum(aa_counts[aa] for aa in self.hydrophobic_aas if aa in aa_counts)
            polar_count = sum(aa_counts[aa] for aa in self.polar_aas if aa in aa_counts)
            charged_count = sum(aa_counts[aa] for aa in self.charged_aas if aa in aa_counts)
            
            pocket_score = (hydro_count * 0.5 + polar_count * 0.3 + charged_count * 0.2) / len(window)
            scores.append(pocket_score)
        
        return np.array(scores)
    
    def get_pocket_regions(self, sequence, threshold=0.5, min_length=10):
        scores = self.predict_pocket(sequence)
        regions = []
        current_start = None
        
        for i, score in enumerate(scores):
            if score >= threshold:
                if current_start is None:
                    current_start = i
            else:
                if current_start is not None:
                    if i - current_start >= min_length:
                        regions.append((current_start, i, np.mean(scores[current_start:i])))
                    current_start = None
        
        if current_start is not None and len(scores) - current_start >= min_length:
            regions.append((current_start, len(scores), np.mean(scores[current_start:])))
        
        return sorted(regions, key=lambda x: x[2], reverse=True)


TARGET_PROTEINS = {
    'EGFR': {
        'sequence': 'MRPSGTAGAALLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCTGPRESDCLVCRKFRDEATCKDTCPPLMLYNPTTYQMDVNPEGKYSFGATCVKKCPRNYVVTDHGSCVRACGADSYEMEEDGVRKCKKCEGPCRKVCNGIGIGEFKDSLSINATNIKHFKNCTSISGDLHILPVAFRGDSFTHTPPLDPQELDILKTVKEITGFLLIQAWPENRTDLHAFENLEIIRGRTKQHGQFSLAVVSLNITSLGLRSLKEISDGDVIISGNKNLCYANTINWKKLFGTSGQKTKIISNRGENSCKATGQVCHALCSPEGCWGPEPRDCVSCRNVSRGRECVDKCNLLEGEPREFVENSECIQCHPECLPQAMNITCTGRGPDNCIQCAHYIDGPHCVKTCPAGVMGENNTLVWKYADAGHVCHLCHPNCTYGCTGPGLEGCPTNGPKIPSIATGMVGALLLLLVVALGIGLFM',
        'description': 'Epidermal Growth Factor Receptor',
        'pocket_region': (700, 800)
    },
    'HER2': {
        'sequence': 'MELAALCRWGLLLALLPPGAASTQVCTGTDMKLRLPASPETHLDMLRHLYQGCQVVQGNLELTYLPTNASLSFLQDIQEVQGYVLIAHNQVRQVPLQRLRIVRGTQLFEDNYALAVLDSNVTNGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCTGPRESDCLVCRKFRDEATCKDTCPPLMLYNPTTYQMDVNPEGKYSFGATCVKKCPRNYVVTDHGSCVRACGADSYEMEEDGVRKCKKCEGPCRKVCNGIGIGEFKDSLSINATNIKHFKNCTSISGDLHILPVAFRGDSFTHTPPLDPQELDILKTVKEITGFLLIQAWPENRTDLHAFENLEIIRGRTKQHGQFSLAVVSLNITSLGLRSLKEISDGDVIISGNKNLCYANTINWKKLFGTSGQKTKIISNRGENSCKATGQVCHALCSPEGCWGPEPRDCVSCRNVSRGRECVDKCNLLEGEPREFVENSECIQCHPECLPQAMNITCTGRGPDNCIQCAHYIDGPHCVKTCPAGVMGENNTLVWKYADAGHVCHLCHPNCTYGCTGPGLEGCPTNGPKIPSIATGMVGALLLLLVVALGIGLFM',
        'description': 'Human Epidermal Growth Factor Receptor 2',
        'pocket_region': (700, 800)
    },
    'DRD2': {
        'sequence': 'MDPLNLSWYDDDLERQNWSRPFNGSDGKADRPHYNYYATLLTLLIAVIVFGNVLVCMAVSREKALQTTTNYLIVSLAVADLLVATLVMPWVVYLEVVGEWKFSRIHCDIFVTLDVMMCTASILNLCAISIDRYTAVAMPMLYNTRYSSKRRVTVMIVISIVVVAVVSVAPVLLGWAKI',
        'description': 'Dopamine Receptor D2',
        'pocket_region': (50, 150)
    },
    'ACE2': {
        'sequence': 'MSSSSWLLLSLVAVTAAQSTIEEQAKTFLDKFNHEAEDLFYQSSLASWNYNTNITEENVQNMNNAGDKWSAFLKEQSTLAQMYPLQEIQNLTVKLQLQALQQNGSSVLSEDKSKRLNTILNTMSTIYSTGKVCNPDNPQECLLLEPGLNEIMANSLDYNERLWAWESWRSEVGKQLRPLYEEYVVLKNEMARANHYEDYGDYWRGDYEVNGVDGYDYSRGQLIEDVEHTFEEIKPLYEHLHAYVRAKLMNAYPSYISPIGCLPAHLLGDMWGRFWTNLYSLTVPFGQKPNIDVTDAMVDQAWDAQRIFKEAEKFFVSVGLPNMTQGFWENSMLTDPGNVQKAVCHPTAWDLGKGDFRILMCTKVTMDDFLTAHHEMGHIQYDMAYAAQPFLLRNGANEGFHEAVGEIMSLSAATPKHLKSIGLLSPDFQEDNETEINFLLKQALTIVGTLPFTYMLEKWRWMVFKGEIPKDQWMKKWWEMKREIVGVVEPVPHDETYCDPASLFHVSNDYSFIRYYTRTLYQFQFQEALCQAAKHEGPLHKCDISNSTEAGQKLFNMLRLGKSEPWTLALENVVGAKNMNVRPLLNYFEPLFTWLKDQNKNSFVGWSTDWSPYADQSIKVRISLKSALGDKAYEWNDNEMYLFRSSVAYAMRQYFLKVKNQMILFGEEDVRDKLKESWSSSFADDDCIEAA',
        'description': 'Angiotensin-converting enzyme 2',
        'pocket_region': (100, 300)
    }
}


def get_target_protein(target_name='EGFR'):
    if target_name in TARGET_PROTEINS:
        return TARGET_PROTEINS[target_name]
    return None


def encode_target_condition(target_name, encoder, device='cpu', max_len=500):
    target = get_target_protein(target_name)
    if target is None:
        raise ValueError(f"Unknown target: {target_name}")
    
    encoded_seq = encode_protein_sequence(target['sequence'], max_len=max_len)
    x = torch.tensor([encoded_seq], dtype=torch.long, device=device)
    
    with torch.no_grad():
        condition = encoder(x)
    
    return condition
