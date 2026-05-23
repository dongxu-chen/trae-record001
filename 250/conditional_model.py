import torch
import torch.nn as nn
import torch.nn.functional as F


class ConditionalEncoder(nn.Module):
    def __init__(self, vocab_size, condition_dim=256, embed_size=256, hidden_size=512, 
                 latent_dim=256, num_layers=2, dropout=0.3):
        super(ConditionalEncoder, self).__init__()
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
        
        self.condition_fc = nn.Linear(condition_dim, hidden_size)
        
        self.fc_mu = nn.Linear(hidden_size * 2 + condition_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_size * 2 + condition_dim, latent_dim)
        
        self.hidden_size = hidden_size
        self.latent_dim = latent_dim
        self.condition_dim = condition_dim
        self.num_layers = num_layers
    
    def forward(self, x, condition):
        batch_size = x.size(0)
        
        x = self.embedding(x)
        x = self.dropout(x)
        
        _, h = self.gru(x)
        
        h_forward = h[-2]
        h_backward = h[-1]
        h_combined = torch.cat([h_forward, h_backward], dim=1)
        
        conditioned = torch.cat([h_combined, condition], dim=1)
        
        mu = self.fc_mu(conditioned)
        logvar = self.fc_logvar(conditioned)
        
        return mu, logvar


class ConditionalDecoder(nn.Module):
    def __init__(self, vocab_size, condition_dim=256, embed_size=256, hidden_size=512, 
                 latent_dim=256, num_layers=2, dropout=0.3):
        super(ConditionalDecoder, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.dropout = nn.Dropout(dropout)
        
        self.fc_z = nn.Linear(latent_dim + condition_dim, hidden_size * num_layers)
        
        self.gru = nn.GRU(
            embed_size + condition_dim,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc_out = nn.Linear(hidden_size, vocab_size)
        
        self.hidden_size = hidden_size
        self.latent_dim = latent_dim
        self.condition_dim = condition_dim
        self.num_layers = num_layers
    
    def forward(self, x, z, condition):
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        z_cond = torch.cat([z, condition], dim=1)
        h = self.fc_z(z_cond)
        h = h.view(self.num_layers, batch_size, self.hidden_size).contiguous()
        
        x = self.embedding(x)
        x = self.dropout(x)
        
        cond_expanded = condition.unsqueeze(1).repeat(1, seq_len, 1)
        x = torch.cat([x, cond_expanded], dim=2)
        
        output, _ = self.gru(x, h)
        output = self.fc_out(output)
        
        return output


class ConditionalMoleculeVAE(nn.Module):
    def __init__(self, vocab_size, condition_dim=256, embed_size=256, hidden_size=512, 
                 latent_dim=256, num_layers=2, dropout=0.3):
        super(ConditionalMoleculeVAE, self).__init__()
        self.encoder = ConditionalEncoder(
            vocab_size, condition_dim, embed_size, hidden_size, 
            latent_dim, num_layers, dropout
        )
        self.decoder = ConditionalDecoder(
            vocab_size, condition_dim, embed_size, hidden_size, 
            latent_dim, num_layers, dropout
        )
        self.latent_dim = latent_dim
        self.condition_dim = condition_dim
    
    def reparameterize(self, mu, logvar):
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu
    
    def forward(self, x, condition):
        mu, logvar = self.encoder(x, condition)
        z = self.reparameterize(mu, logvar)
        
        input_seq = x[:, :-1]
        
        output = self.decoder(input_seq, z, condition)
        
        return output, mu, logvar, z
    
    def encode(self, x, condition):
        mu, logvar = self.encoder(x, condition)
        return mu, logvar
    
    def decode(self, z, condition, max_len=120, start_token=1, end_token=2, temperature=1.0):
        batch_size = z.size(0)
        device = z.device
        
        generated = torch.zeros(batch_size, max_len, dtype=torch.long, device=device)
        generated[:, 0] = start_token
        
        z_cond = torch.cat([z, condition], dim=1)
        h = self.decoder.fc_z(z_cond)
        h = h.view(self.decoder.num_layers, batch_size, self.decoder.hidden_size).contiguous()
        
        for t in range(1, max_len):
            input_token = generated[:, t-1:t]
            x = self.decoder.embedding(input_token)
            x = self.decoder.dropout(x)
            
            cond_expanded = condition.unsqueeze(1)
            x = torch.cat([x, cond_expanded], dim=2)
            
            output, h = self.decoder.gru(x, h)
            logits = self.decoder.fc_out(output)
            
            logits = logits[:, -1, :] / temperature
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, 1).squeeze(1)
            
            generated[:, t] = next_token
        
        return generated


def conditional_vae_loss(recon_x, x, mu, logvar, pad_idx=0, kl_weight=0.5):
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


def create_conditional_model(vocab_size, condition_dim=256, embed_size=256, 
                              hidden_size=512, latent_dim=256, num_layers=2, dropout=0.3):
    model = ConditionalMoleculeVAE(
        vocab_size, condition_dim, embed_size, hidden_size, 
        latent_dim, num_layers, dropout
    )
    return model


class ConditionalGrammarConstrainedDecoder:
    def __init__(self, grammar):
        self.grammar = grammar
        
    def decode_constrained(self, model, z, condition, max_len=120, temperature=1.0, device='cpu'):
        batch_size = z.size(0)
        vocab_size = self.grammar.vocab_size
        
        generated = [[self.grammar.start_token] for _ in range(batch_size)]
        states = [self.grammar.get_initial_state() for _ in range(batch_size)]
        finished = [False] * batch_size
        
        z_cond = torch.cat([z, condition], dim=1)
        h = model.decoder.fc_z(z_cond)
        h = h.view(model.decoder.num_layers, batch_size, model.decoder.hidden_size).contiguous()
        
        for t in range(1, max_len):
            all_finished = all(finished)
            if all_finished:
                break
                
            input_tokens = torch.tensor(
                [[g[-1]] for g in generated], 
                dtype=torch.long, 
                device=device
            )
            
            x = model.decoder.embedding(input_tokens)
            x = model.decoder.dropout(x)
            
            cond_expanded = condition.unsqueeze(1)
            x = torch.cat([x, cond_expanded], dim=2)
            
            output, h_new = model.decoder.gru(x, h)
            logits = model.decoder.fc_out(output)
            logits = logits[:, -1, :] / temperature
            
            for i in range(batch_size):
                if finished[i]:
                    continue
                    
                mask = torch.tensor(
                    self.grammar.get_allowed_tokens(states[i]), 
                    dtype=torch.float32, 
                    device=device
                )
                
                logits[i] = logits[i] * mask - 1e9 * (1 - mask)
            
            probs = F.softmax(logits, dim=-1)
            next_tokens = torch.multinomial(probs, 1).squeeze(1)
            
            for i in range(batch_size):
                if finished[i]:
                    generated[i].append(self.grammar.pad_token)
                    continue
                    
                next_token = int(next_tokens[i])
                generated[i].append(next_token)
                
                if next_token == self.grammar.end_token:
                    finished[i] = True
                else:
                    states[i] = self.grammar.update_state(states[i], next_token)
            
            h = h_new
        
        max_gen_len = max(len(g) for g in generated)
        for i in range(batch_size):
            while len(generated[i]) < max_gen_len:
                generated[i].append(self.grammar.pad_token)
                
        return torch.tensor(generated, dtype=torch.long, device=device)
