import torch
import torch.nn as nn
import torch.nn.functional as F


class ValidityDiscriminator(nn.Module):
    def __init__(self, vocab_size, embed_size=256, hidden_size=512, num_layers=3, dropout=0.3):
        super(ValidityDiscriminator, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.dropout = nn.Dropout(dropout)
        
        self.conv_layers = nn.ModuleList([
            nn.Conv1d(embed_size, hidden_size // 2, kernel_size=3, padding=1),
            nn.Conv1d(hidden_size // 2, hidden_size, kernel_size=5, padding=2),
            nn.Conv1d(hidden_size, hidden_size, kernel_size=7, padding=3),
        ])
        
        self.pool = nn.AdaptiveMaxPool1d(1)
        
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.LeakyReLU(0.2),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, hidden_size // 4),
            nn.LeakyReLU(0.2),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 4, 1),
            nn.Sigmoid()
        )
        
        self.vocab_size = vocab_size
        self.embed_size = embed_size
        self.hidden_size = hidden_size
        
    def forward(self, x):
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        x = self.embedding(x)
        x = self.dropout(x)
        
        x = x.transpose(1, 2)
        
        for conv in self.conv_layers:
            x = F.leaky_relu(conv(x), 0.2)
            x = self.dropout(x)
        
        x = self.pool(x)
        x = x.squeeze(2)
        
        validity = self.fc_layers(x)
        
        return validity


class ValidityPredictor:
    def __init__(self, discriminator, tokenizer, device='cpu'):
        self.discriminator = discriminator
        self.tokenizer = tokenizer
        self.device = device
        self.discriminator.eval()
        
    def predict_validity(self, smiles_list):
        if not smiles_list:
            return []
            
        encodings = [self.tokenizer.encode(s) for s in smiles_list]
        x = torch.tensor(encodings, dtype=torch.long, device=self.device)
        
        with torch.no_grad():
            validity_scores = self.discriminator(x).squeeze().cpu().numpy()
            
        return validity_scores.tolist()


def compute_discriminator_loss(discriminator, real_smiles, fake_smiles, tokenizer, device):
    real_encoded = [tokenizer.encode(s) for s in real_smiles]
    fake_encoded = [tokenizer.encode(s) for s in fake_smiles]
    
    real_x = torch.tensor(real_encoded, dtype=torch.long, device=device)
    fake_x = torch.tensor(fake_encoded, dtype=torch.long, device=device)
    
    real_validity = discriminator(real_x)
    fake_validity = discriminator(fake_x)
    
    real_loss = F.binary_cross_entropy(real_validity, torch.ones_like(real_validity))
    fake_loss = F.binary_cross_entropy(fake_validity, torch.zeros_like(fake_validity))
    
    total_loss = (real_loss + fake_loss) / 2
    
    return total_loss, real_loss, fake_loss, real_validity.mean(), fake_validity.mean()


def compute_generator_adversarial_loss(discriminator, fake_smiles, tokenizer, device):
    fake_encoded = [tokenizer.encode(s) for s in fake_smiles]
    fake_x = torch.tensor(fake_encoded, dtype=torch.long, device=device)
    
    fake_validity = discriminator(fake_x)
    
    adversarial_loss = F.binary_cross_entropy(fake_validity, torch.ones_like(fake_validity))
    
    return adversarial_loss, fake_validity.mean()


class AdversarialTrainer:
    def __init__(self, generator, discriminator, tokenizer, device='cpu'):
        self.generator = generator
        self.discriminator = discriminator
        self.tokenizer = tokenizer
        self.device = device
        
    def train_discriminator_step(self, real_smiles, fake_smiles, optimizer_d):
        optimizer_d.zero_grad()
        
        loss, real_loss, fake_loss, real_acc, fake_acc = compute_discriminator_loss(
            self.discriminator, real_smiles, fake_smiles, self.tokenizer, self.device
        )
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.discriminator.parameters(), max_norm=1.0)
        optimizer_d.step()
        
        return {
            'd_total_loss': loss.item(),
            'd_real_loss': real_loss.item(),
            'd_fake_loss': fake_loss.item(),
            'd_real_acc': real_acc.item(),
            'd_fake_acc': fake_acc.item()
        }
    
    def compute_adversarial_reward(self, generated_smiles):
        self.discriminator.eval()
        
        with torch.no_grad():
            validity_scores = []
            for s in generated_smiles:
                encoded = self.tokenizer.encode(s)
                x = torch.tensor([encoded], dtype=torch.long, device=self.device)
                score = self.discriminator(x).item()
                validity_scores.append(score)
                
        self.discriminator.train()
        return validity_scores
