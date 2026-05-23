import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class SpatialAttention(nn.Module):
    def __init__(self, in_channels):
        super(SpatialAttention, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, in_channels // 8, kernel_size=1)
        self.conv2 = nn.Conv2d(in_channels // 8, 1, kernel_size=1)
        
    def forward(self, x):
        attn = F.relu(self.conv1(x))
        attn = torch.sigmoid(self.conv2(attn))
        return x * attn

class TemporalAttention(nn.Module):
    def __init__(self, hidden_size):
        super(TemporalAttention, self).__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1)
        )
        
    def forward(self, x):
        weights = self.attention(x)
        weights = F.softmax(weights, dim=1)
        weighted_x = x * weights
        return weighted_x.sum(dim=1)

class MultiTaskODPredictor(nn.Module):
    def __init__(self, grid_size=10, feature_dim=22):
        super(MultiTaskODPredictor, self).__init__()
        self.grid_size = grid_size
        self.num_grids = grid_size * grid_size
        self.feature_dim = feature_dim
        
        self.spatial_encoder = nn.Sequential(
            nn.Conv2d(feature_dim, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            SpatialAttention(128)
        )
        
        self.spatial_attention = SpatialAttention(128)
        
        self.origin_embedding = nn.Embedding(self.num_grids, 32)
        self.dest_embedding = nn.Embedding(self.num_grids, 32)
        
        self.shared_fc = nn.Sequential(
            nn.Linear(128 + 64, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.task_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, self.num_grids)
            ) for _ in range(self.num_grids)
        ])
        
    def forward(self, spatial_features):
        batch_size = spatial_features.size(0)
        
        spatial_features = spatial_features.permute(0, 3, 1, 2)
        spatial_encoded = self.spatial_encoder(spatial_features)
        spatial_encoded = self.spatial_attention(spatial_encoded)
        spatial_encoded = F.adaptive_avg_pool2d(spatial_encoded, (1, 1)).view(batch_size, -1)
        
        origin_indices = torch.arange(self.num_grids).to(spatial_features.device)
        origin_embeds = self.origin_embedding(origin_indices)
        
        dest_indices = torch.arange(self.num_grids).to(spatial_features.device)
        dest_embeds = self.dest_embedding(dest_indices)
        
        outputs = []
        for orig_idx in range(self.num_grids):
            orig_embed = origin_embeds[orig_idx:orig_idx+1]
            
            orig_embed_expanded = orig_embed.repeat(self.num_grids, 1)
            combined = torch.cat([orig_embed_expanded, dest_embeds], dim=1)
            
            spatial_expanded = spatial_encoded.repeat(self.num_grids, 1)
            full_features = torch.cat([spatial_expanded, combined], dim=1)
            
            shared = self.shared_fc(full_features)
            task_output = self.task_heads[orig_idx](shared.mean(dim=0, keepdim=True))
            outputs.append(task_output)
        
        od_matrix = torch.cat(outputs, dim=0)
        od_matrix = F.relu(od_matrix)
        
        return od_matrix

class SimpleODPredictor(nn.Module):
    def __init__(self, grid_size=10, feature_dim=22):
        super(SimpleODPredictor, self).__init__()
        self.grid_size = grid_size
        self.num_grids = grid_size * grid_size
        self.feature_dim = feature_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(feature_dim * grid_size * grid_size, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, self.num_grids * self.num_grids)
        )
        
    def forward(self, spatial_features):
        batch_size = spatial_features.size(0)
        flattened = spatial_features.view(batch_size, -1)
        encoded = self.encoder(flattened)
        output = self.decoder(encoded)
        output = output.view(batch_size, self.num_grids, self.num_grids)
        output = F.relu(output)
        return output.squeeze(0)

def train_model(model, train_loader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    
    for batch_idx, (features, targets) in enumerate(train_loader):
        features = features.to(device)
        targets = targets.to(device)
        
        optimizer.zero_grad()
        outputs = model(features)
        
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(train_loader)

def predict(model, features, device):
    model.eval()
    with torch.no_grad():
        features = features.to(device)
        outputs = model(features)
    return outputs.cpu().numpy()
