import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import List, Tuple
from config import TrainingConfig


class ContourEncoder(nn.Module):
    def __init__(self, latent_dim: int = TrainingConfig.LATENT_DIM, hidden_dim: int = TrainingConfig.HIDDEN_DIM):
        super().__init__()
        self.latent_dim = latent_dim
        
        self.conv_layers = nn.Sequential(
            nn.Conv1d(2, hidden_dim // 4, kernel_size=5, padding=2),
            nn.BatchNorm1d(hidden_dim // 4),
            nn.ReLU(),
            nn.Conv1d(hidden_dim // 4, hidden_dim // 2, kernel_size=5, padding=2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Conv1d(hidden_dim // 2, hidden_dim, kernel_size=5, padding=2),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
    
    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv_layers(x)
        x = torch.mean(x, dim=2)
        
        mu = self.fc_mu(x)
        logvar = self.fc_logvar(x)
        
        return mu, logvar


class ContourDecoder(nn.Module):
    def __init__(self, latent_dim: int = TrainingConfig.LATENT_DIM, hidden_dim: int = TrainingConfig.HIDDEN_DIM, num_points: int = 256):
        super().__init__()
        self.num_points = num_points
        
        self.fc_layers = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim * 4),
            nn.ReLU(),
        )
        
        self.conv_layers = nn.Sequential(
            nn.ConvTranspose1d(hidden_dim // 4, hidden_dim // 2, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.ConvTranspose1d(hidden_dim // 2, hidden_dim // 4, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm1d(hidden_dim // 4),
            nn.ReLU(),
            nn.Conv1d(hidden_dim // 4, 2, kernel_size=3, padding=1),
            nn.Tanh(),
        )
    
    def forward(self, z):
        batch_size = z.size(0)
        x = self.fc_layers(z)
        x = x.view(batch_size, -1, 16)
        x = self.conv_layers(x)
        x = x.transpose(1, 2)
        
        return x


class FontVAE(nn.Module):
    def __init__(self, latent_dim: int = TrainingConfig.LATENT_DIM):
        super().__init__()
        self.encoder = ContourEncoder(latent_dim)
        self.decoder = ContourDecoder(latent_dim)
    
    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def forward(self, x):
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decoder(z)
        return x_recon, mu, logvar
    
    def generate(self, z):
        return self.decoder(z)
    
    def interpolate(self, x1, x2, alpha=0.5):
        mu1, _ = self.encoder(x1)
        mu2, _ = self.encoder(x2)
        z = mu1 * (1 - alpha) + mu2 * alpha
        return self.decoder(z)


class FontStyleTransfer(nn.Module):
    def __init__(self, latent_dim: int = TrainingConfig.LATENT_DIM, style_dim: int = 64):
        super().__init__()
        self.style_encoder = ContourEncoder(latent_dim)
        self.content_encoder = ContourEncoder(latent_dim)
        
        self.decoder = ContourDecoder(latent_dim * 2)
    
    def forward(self, style_img, content_img):
        style_mu, _ = self.style_encoder(style_img)
        content_mu, _ = self.content_encoder(content_img)
        
        combined = torch.cat([style_mu, content_mu], dim=1)
        return self.decoder(combined)


class ContourDataset(Dataset):
    def __init__(self, points_list: List[np.ndarray]):
        self.points_list = []
        for points in points_list:
            if points is not None:
                self.points_list.append(torch.FloatTensor(points))
    
    def __len__(self):
        return len(self.points_list)
    
    def __getitem__(self, idx):
        return self.points_list[idx]


def vae_loss(recon_x, x, mu, logvar, kl_weight=0.001):
    recon_loss = F.mse_loss(recon_x, x, reduction='sum')
    kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + kl_weight * kl_loss, recon_loss, kl_loss


class FontTrainer:
    def __init__(self, model: FontVAE, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.model = model.to(device)
        self.optimizer = torch.optim.Adam(model.parameters(), lr=TrainingConfig.LEARNING_RATE)
        self.history = {'loss': [], 'recon_loss': [], 'kl_loss': []}
    
    def train(self, dataloader: DataLoader, epochs: int = TrainingConfig.EPOCHS):
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            total_recon = 0
            total_kl = 0
            
            for batch in dataloader:
                batch = batch.to(self.device)
                
                self.optimizer.zero_grad()
                
                recon_batch, mu, logvar = self.model(batch)
                loss, recon_loss, kl_loss = vae_loss(recon_batch, batch, mu, logvar)
                
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
                total_recon += recon_loss.item()
                total_kl += kl_loss.item()
            
            avg_loss = total_loss / len(dataloader.dataset)
            avg_recon = total_recon / len(dataloader.dataset)
            avg_kl = total_kl / len(dataloader.dataset)
            
            self.history['loss'].append(avg_loss)
            self.history['recon_loss'].append(avg_recon)
            self.history['kl_loss'].append(avg_kl)
            
            if (epoch + 1) % TrainingConfig.SAVE_INTERVAL == 0:
                print(f'Epoch {epoch+1}/{epochs}: Loss={avg_loss:.4f}, Recon={avg_recon:.4f}, KL={avg_kl:.4f}')
    
    def save_model(self, path: str):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history
        }, path)
    
    def load_model(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint['history']
    
    def generate_contour(self, style_points: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            style_tensor = torch.FloatTensor(style_points).unsqueeze(0).to(self.device)
            mu, _ = self.model.encoder(style_tensor)
            generated = self.model.decoder(mu)
            return generated.squeeze(0).cpu().numpy()


class SimpleFontGenerator:
    def __init__(self):
        self.style_vectors = {}
    
    def learn_style(self, char_points_dict: dict):
        """从样本字符中学习风格向量"""
        all_points = []
        for points in char_points_dict.values():
            if points is not None:
                all_points.append(points)
        
        if not all_points:
            return False
        
        self.mean_style = np.mean(all_points, axis=0)
        return True
    
    def generate_char(self, base_points: np.ndarray) -> np.ndarray:
        """基于基础字形和学习到的风格生成新字形"""
        if base_points is None:
            return None
        
        if hasattr(self, 'mean_style'):
            style_factor = 0.3
            generated = base_points * (1 - style_factor) + self.mean_style * style_factor
            return generated
        return base_points
