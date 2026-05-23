import torch
import torch.nn as nn
import torch.nn.functional as F


class Encoder(nn.Module):
    def __init__(self, vocab_size, embed_size=256, hidden_size=512, latent_dim=256, num_layers=2, dropout=0.3):
        super(Encoder, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.dropout = nn.Dropout(dropout)
        
        self.gru = nn.GRU(
            embed_size,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        self.fc_mu = nn.Linear(hidden_size * 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_size * 2, latent_dim)
        
        self.hidden_size = hidden_size
        self.latent_dim = latent_dim
        self.num_layers = num_layers
    
    def forward(self, x):
        batch_size = x.size(0)
        
        x = self.embedding(x)
        x = self.dropout(x)
        
        _, h = self.gru(x)
        
        h_forward = h[-2]
        h_backward = h[-1]
        h_combined = torch.cat([h_forward, h_backward], dim=1)
        
        mu = self.fc_mu(h_combined)
        logvar = self.fc_logvar(h_combined)
        
        return mu, logvar


class Decoder(nn.Module):
    def __init__(self, vocab_size, embed_size=256, hidden_size=512, latent_dim=256, num_layers=2, dropout=0.3):
        super(Decoder, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.dropout = nn.Dropout(dropout)
        
        self.fc_z = nn.Linear(latent_dim, hidden_size * num_layers)
        
        self.gru = nn.GRU(
            embed_size,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc_out = nn.Linear(hidden_size, vocab_size)
        
        self.hidden_size = hidden_size
        self.latent_dim = latent_dim
        self.num_layers = num_layers
    
    def forward(self, x, z):
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        h = self.fc_z(z)
        h = h.view(self.num_layers, batch_size, self.hidden_size).contiguous()
        
        x = self.embedding(x)
        x = self.dropout(x)
        
        output, _ = self.gru(x, h)
        output = self.fc_out(output)
        
        return output


class MoleculeVAE(nn.Module):
    def __init__(self, vocab_size, embed_size=256, hidden_size=512, latent_dim=256, num_layers=2, dropout=0.3):
        super(MoleculeVAE, self).__init__()
        self.encoder = Encoder(vocab_size, embed_size, hidden_size, latent_dim, num_layers, dropout)
        self.decoder = Decoder(vocab_size, embed_size, hidden_size, latent_dim, num_layers, dropout)
        self.latent_dim = latent_dim
    
    def reparameterize(self, mu, logvar):
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu
    
    def forward(self, x):
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        
        input_seq = x[:, :-1]
        target_seq = x[:, 1:]
        
        output = self.decoder(input_seq, z)
        
        return output, mu, logvar, z
    
    def encode(self, x):
        mu, logvar = self.encoder(x)
        return mu, logvar
    
    def decode(self, z, max_len=120, start_token=1, end_token=2, temperature=1.0):
        batch_size = z.size(0)
        device = z.device
        
        generated = torch.zeros(batch_size, max_len, dtype=torch.long, device=device)
        generated[:, 0] = start_token
        
        h = self.decoder.fc_z(z)
        h = h.view(self.decoder.num_layers, batch_size, self.decoder.hidden_size).contiguous()
        
        for t in range(1, max_len):
            input_token = generated[:, t-1:t]
            x = self.decoder.embedding(input_token)
            x = self.decoder.dropout(x)
            
            output, h = self.decoder.gru(x, h)
            logits = self.decoder.fc_out(output)
            
            logits = logits[:, -1, :] / temperature
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, 1).squeeze(1)
            
            generated[:, t] = next_token
        
        return generated


def vae_loss(recon_x, x, mu, logvar, pad_idx=0, kl_weight=0.5):
    batch_size = x.size(0)
    
    recon_loss = F.cross_entropy(
        recon_x.view(-1, recon_x.size(-1)),
        x.view(-1),
        ignore_index=pad_idx,
        reduction='mean'
    )
    
    kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp()) / batch_size
    
    total_loss = recon_loss + kl_weight * kl_loss
    
    return total_loss, recon_loss, kl_loss


def create_model(vocab_size, embed_size=256, hidden_size=512, latent_dim=256, num_layers=2, dropout=0.3):
    model = MoleculeVAE(vocab_size, embed_size, hidden_size, latent_dim, num_layers, dropout)
    return model
