import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class PrototypicalNetwork(nn.Module):
    def __init__(self, feature_dim=64, hidden_dim=128):
        super(PrototypicalNetwork, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, feature_dim)
        )
        
    def forward(self, x):
        return self.encoder(x)

class MetaLearner(nn.Module):
    def __init__(self, grid_size=10, feature_dim=22):
        super(MetaLearner, self).__init__()
        self.grid_size = grid_size
        self.num_grids = grid_size * grid_size
        self.feature_dim = feature_dim
        self.proto_dim = 64
        
        self.spatial_encoder = nn.Sequential(
            nn.Conv2d(feature_dim, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU()
        )
        
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        
        self.origin_encoder = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, self.proto_dim)
        )
        
        self.proto_net = PrototypicalNetwork(feature_dim=self.proto_dim, hidden_dim=128)
        
        self.origin_embedding = nn.Embedding(self.num_grids, 32)
        self.dest_embedding = nn.Embedding(self.num_grids, 32)
        
        self.attention = nn.MultiheadAttention(embed_dim=self.proto_dim, num_heads=4)
        
        self.adapter = nn.Sequential(
            nn.Linear(self.proto_dim + 64, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU()
        )
        
        self.task_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, self.num_grids)
            ) for _ in range(self.num_grids)
        ])
        
        self.support_set_prototypes = None
        self.grid_similarity_matrix = None
        
    def compute_grid_similarity(self, grid_features):
        num_grids = grid_features.size(0)
        similarities = torch.zeros((num_grids, num_grids))
        
        for i in range(num_grids):
            for j in range(num_grids):
                i_idx = i // self.grid_size
                i_jdx = i % self.grid_size
                j_idx = j // self.grid_size
                j_jdx = j % self.grid_size
                
                spatial_dist = torch.sqrt(torch.tensor((i_idx - j_idx)**2 + (i_jdx - j_jdx)**2, dtype=torch.float32))
                spatial_sim = torch.exp(-spatial_dist / 3.0)
                
                feat_sim = F.cosine_similarity(
                    grid_features[i].unsqueeze(0), 
                    grid_features[j].unsqueeze(0)
                )
                
                similarities[i, j] = 0.6 * spatial_sim + 0.4 * feat_sim
        
        return similarities
    
    def find_similar_grids(self, grid_idx, top_k=5):
        if self.grid_similarity_matrix is None:
            return [grid_idx]
        
        sim_scores = self.grid_similarity_matrix[grid_idx]
        top_indices = torch.argsort(sim_scores, descending=True)[:top_k + 1]
        return [idx.item() for idx in top_indices if idx != grid_idx][:top_k]
    
    def meta_forward(self, spatial_features, origin_idx, support_indices):
        batch_size = spatial_features.size(0)
        
        spatial_features = spatial_features.permute(0, 3, 1, 2)
        spatial_encoded = self.spatial_encoder(spatial_features)
        spatial_global = self.global_pool(spatial_encoded).view(batch_size, -1)
        
        grid_prototypes = []
        for idx in range(self.num_grids):
            idx_i = idx // self.grid_size
            idx_j = idx % self.grid_size
            grid_feat = spatial_encoded[:, :, idx_i, idx_j]
            proto = self.origin_encoder(grid_feat)
            grid_prototypes.append(proto)
        
        grid_prototypes = torch.stack(grid_prototypes, dim=1)
        
        if self.training:
            self.grid_similarity_matrix = self.compute_grid_similarity(grid_prototypes[0])
        
        similar_indices = self.find_similar_grids(origin_idx, top_k=3)
        all_indices = [origin_idx] + similar_indices
        
        support_prototypes = grid_prototypes[:, all_indices, :]
        support_prototypes = support_prototypes.transpose(0, 1)
        
        attended_prototypes, _ = self.attention(
            support_prototypes, 
            support_prototypes, 
            support_prototypes
        )
        
        target_proto = attended_prototypes.mean(dim=0)
        enhanced_proto = self.proto_net(target_proto)
        
        origin_embed = self.origin_embedding(torch.tensor(origin_idx).to(spatial_features.device))
        origin_embed_expanded = origin_embed.repeat(batch_size, 1)
        
        combined = torch.cat([enhanced_proto, origin_embed_expanded], dim=1)
        adapted = self.adapter(combined)
        
        dest_embeds = self.dest_embedding.weight
        dest_embeds_expanded = dest_embeds.unsqueeze(0).repeat(batch_size, 1, 1)
        
        adapted_expanded = adapted.unsqueeze(1).repeat(1, self.num_grids, 1)
        head_input = torch.cat([adapted_expanded, dest_embeds_expanded], dim=-1)
        
        output = self.task_heads[origin_idx](adapted)
        output = output.unsqueeze(1).repeat(1, self.num_grids, 1)
        output = output.mean(dim=1)
        
        return output, enhanced_proto
    
    def forward(self, spatial_features):
        batch_size = spatial_features.size(0)
        
        spatial_features = spatial_features.permute(0, 3, 1, 2)
        spatial_encoded = self.spatial_encoder(spatial_features)
        spatial_global = self.global_pool(spatial_encoded).view(batch_size, -1)
        
        grid_prototypes = []
        for idx in range(self.num_grids):
            idx_i = idx // self.grid_size
            idx_j = idx % self.grid_size
            grid_feat = spatial_encoded[:, :, idx_i, idx_j]
            proto = self.origin_encoder(grid_feat)
            grid_prototypes.append(proto)
        
        grid_prototypes = torch.stack(grid_prototypes, dim=1)
        
        if self.grid_similarity_matrix is None:
            self.grid_similarity_matrix = self.compute_grid_similarity(grid_prototypes[0])
        
        outputs = []
        for orig_idx in range(self.num_grids):
            similar_indices = self.find_similar_grids(orig_idx, top_k=3)
            all_indices = [orig_idx] + similar_indices
            
            support_prototypes = grid_prototypes[:, all_indices, :]
            support_prototypes = support_prototypes.transpose(0, 1)
            
            attended_prototypes, _ = self.attention(
                support_prototypes, 
                support_prototypes, 
                support_prototypes
            )
            
            target_proto = attended_prototypes.mean(dim=0)
            enhanced_proto = self.proto_net(target_proto)
            
            origin_embed = self.origin_embedding(torch.tensor(orig_idx).to(spatial_features.device))
            origin_embed_expanded = origin_embed.repeat(batch_size, 1)
            
            combined = torch.cat([enhanced_proto, origin_embed_expanded], dim=1)
            adapted = self.adapter(combined)
            
            task_output = self.task_heads[orig_idx](adapted)
            outputs.append(task_output)
        
        od_matrix = torch.cat(outputs, dim=0)
        od_matrix = F.relu(od_matrix)
        
        return od_matrix
    
    def get_knowledge_transfer_weights(self):
        if self.grid_similarity_matrix is None:
            return None
        
        return self.grid_similarity_matrix.cpu().detach().numpy()

class MetaLoss(nn.Module):
    def __init__(self, base_loss_fn, proto_loss_weight=0.1):
        super(MetaLoss, self).__init__()
        self.base_loss = base_loss_fn
        self.proto_loss_weight = proto_loss_weight
        
    def forward(self, pred, target, prototypes=None):
        base_loss = self.base_loss(pred, target)
        
        if prototypes is not None:
            proto_dist = torch.cdist(prototypes, prototypes)
            proto_loss = torch.mean(torch.relu(0.5 - proto_dist))
            return base_loss + self.proto_loss_weight * proto_loss
        
        return base_loss

def meta_train_step(model, optimizer, criterion, support_data, query_data, device):
    model.train()
    
    support_features, support_targets = support_data
    query_features, query_targets = query_data
    
    support_features = support_features.to(device)
    support_targets = support_targets.to(device)
    query_features = query_features.to(device)
    query_targets = query_targets.to(device)
    
    optimizer.zero_grad()
    
    support_pred, support_protos = model.meta_forward(support_features, 0, [0])
    query_pred, _ = model.meta_forward(query_features, 0, [0])
    
    loss = criterion(support_pred, support_targets[0], support_protos)
    loss.backward(retain_graph=True)
    
    optimizer.step()
    
    optimizer.zero_grad()
    query_pred, _ = model.meta_forward(query_features, 0, [0])
    query_loss = criterion(query_pred, query_targets[0])
    
    return query_loss.item()
