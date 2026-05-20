import torch
import torch.nn as nn
import torch.nn.functional as F


class Hybrid2D1DCNN(nn.Module):
    def __init__(self, in_channels=1, n_classes=16, patch_size=5, n_bands=30):
        super(Hybrid2D1DCNN, self).__init__()
        
        self.patch_size = patch_size
        self.n_bands = n_bands
        
        self.conv2d_1 = nn.Conv2d(n_bands, 64, kernel_size=3, stride=1, padding=1)
        self.conv2d_2 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv2d_3 = nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        
        self.bn2d_1 = nn.BatchNorm2d(64)
        self.bn2d_2 = nn.BatchNorm2d(128)
        self.bn2d_3 = nn.BatchNorm2d(256)
        
        self.pool2d = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        
        self.dropout2d = nn.Dropout2d(0.3)
        
        self.spatial_features = self._get_spatial_features_size()
        
        self.conv1d_1 = nn.Conv1d(1, 32, kernel_size=3, stride=1, padding=1)
        self.conv1d_2 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        
        self.bn1d_1 = nn.BatchNorm1d(32)
        self.bn1d_2 = nn.BatchNorm1d(64)
        
        self.pool1d = nn.MaxPool1d(kernel_size=2, stride=2)
        
        self.dropout1d = nn.Dropout(0.3)
        
        self.spectral_features = self._get_spectral_features_size()
        
        combined_features = self.spatial_features + self.spectral_features
        
        self.fc1 = nn.Linear(combined_features, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, n_classes)
        
        self.dropout_fc = nn.Dropout(0.5)
        
    def _get_spatial_features_size(self):
        x = torch.randn(1, self.n_bands, self.patch_size, self.patch_size)
        x = self.pool2d(F.relu(self.bn2d_1(self.conv2d_1(x))))
        x = self.pool2d(F.relu(self.bn2d_2(self.conv2d_2(x))))
        x = F.relu(self.bn2d_3(self.conv2d_3(x)))
        return x.numel()
    
    def _get_spectral_features_size(self):
        x = torch.randn(1, 1, self.n_bands)
        x = self.pool1d(F.relu(self.bn1d_1(self.conv1d_1(x))))
        x = F.relu(self.bn1d_2(self.conv1d_2(x)))
        return x.numel()
        
    def forward(self, x):
        batch_size = x.size(0)
        
        x_2d = x.squeeze(1)
        
        x_2d = F.relu(self.bn2d_1(self.conv2d_1(x_2d)))
        x_2d = self.pool2d(x_2d)
        x_2d = self.dropout2d(x_2d)
        
        x_2d = F.relu(self.bn2d_2(self.conv2d_2(x_2d)))
        x_2d = self.pool2d(x_2d)
        x_2d = self.dropout2d(x_2d)
        
        x_2d = F.relu(self.bn2d_3(self.conv2d_3(x_2d)))
        
        x_2d = x_2d.view(batch_size, -1)
        
        x_1d = x.squeeze(1)
        h, w = x_1d.size(2), x_1d.size(3)
        x_1d = F.adaptive_avg_pool2d(x_1d, (1, 1)).squeeze(-1).squeeze(-1)
        x_1d = x_1d.unsqueeze(1)
        
        x_1d = F.relu(self.bn1d_1(self.conv1d_1(x_1d)))
        x_1d = self.pool1d(x_1d)
        x_1d = self.dropout1d(x_1d)
        
        x_1d = F.relu(self.bn1d_2(self.conv1d_2(x_1d)))
        
        x_1d = x_1d.view(batch_size, -1)
        
        x_combined = torch.cat([x_2d, x_1d], dim=1)
        
        x = self.dropout_fc(F.relu(self.fc1(x_combined)))
        x = self.dropout_fc(F.relu(self.fc2(x)))
        x = self.fc3(x)
        
        return x


class LightHybrid2D1DCNN(nn.Module):
    def __init__(self, in_channels=1, n_classes=16, patch_size=5, n_bands=30):
        super(LightHybrid2D1DCNN, self).__init__()
        
        self.patch_size = patch_size
        self.n_bands = n_bands
        
        self.conv2d_1 = nn.Conv2d(n_bands, 32, kernel_size=3, stride=1, padding=1)
        self.conv2d_2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        
        self.bn2d_1 = nn.BatchNorm2d(32)
        self.bn2d_2 = nn.BatchNorm2d(64)
        
        self.pool2d = nn.MaxPool2d(kernel_size=2, stride=2)
        
        self.dropout2d = nn.Dropout2d(0.4)
        
        self.spatial_features = self._get_spatial_features_size()
        
        self.conv1d_1 = nn.Conv1d(1, 16, kernel_size=3, stride=1, padding=1)
        self.conv1d_2 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        
        self.bn1d_1 = nn.BatchNorm1d(16)
        self.bn1d_2 = nn.BatchNorm1d(32)
        
        self.pool1d = nn.MaxPool1d(kernel_size=2, stride=2)
        
        self.dropout1d = nn.Dropout(0.4)
        
        self.spectral_features = self._get_spectral_features_size()
        
        combined_features = self.spatial_features + self.spectral_features
        
        self.fc1 = nn.Linear(combined_features, 128)
        self.fc2 = nn.Linear(128, n_classes)
        
        self.dropout_fc = nn.Dropout(0.5)
        
    def _get_spatial_features_size(self):
        x = torch.randn(1, self.n_bands, self.patch_size, self.patch_size)
        x = self.pool2d(F.relu(self.bn2d_1(self.conv2d_1(x))))
        x = F.relu(self.bn2d_2(self.conv2d_2(x)))
        return x.numel()
    
    def _get_spectral_features_size(self):
        x = torch.randn(1, 1, self.n_bands)
        x = self.pool1d(F.relu(self.bn1d_1(self.conv1d_1(x))))
        x = F.relu(self.bn1d_2(self.conv1d_2(x)))
        return x.numel()
        
    def forward(self, x):
        batch_size = x.size(0)
        
        x_2d = x.squeeze(1)
        
        x_2d = F.relu(self.bn2d_1(self.conv2d_1(x_2d)))
        x_2d = self.pool2d(x_2d)
        x_2d = self.dropout2d(x_2d)
        
        x_2d = F.relu(self.bn2d_2(self.conv2d_2(x_2d)))
        
        x_2d = x_2d.view(batch_size, -1)
        
        x_1d = x.squeeze(1)
        x_1d = F.adaptive_avg_pool2d(x_1d, (1, 1)).squeeze(-1).squeeze(-1)
        x_1d = x_1d.unsqueeze(1)
        
        x_1d = F.relu(self.bn1d_1(self.conv1d_1(x_1d)))
        x_1d = self.pool1d(x_1d)
        x_1d = self.dropout1d(x_1d)
        
        x_1d = F.relu(self.bn1d_2(self.conv1d_2(x_1d)))
        
        x_1d = x_1d.view(batch_size, -1)
        
        x_combined = torch.cat([x_2d, x_1d], dim=1)
        
        x = self.dropout_fc(F.relu(self.fc1(x_combined)))
        x = self.fc2(x)
        
        return x


class SpectralSpatialCNN(nn.Module):
    def __init__(self, in_channels=1, n_classes=16, patch_size=5, n_bands=30):
        super(SpectralSpatialCNN, self).__init__()
        
        self.patch_size = patch_size
        self.n_bands = n_bands
        
        self.conv2d_1 = nn.Conv2d(n_bands, 64, kernel_size=3, padding=1)
        self.conv2d_2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        
        self.bn2d_1 = nn.BatchNorm2d(64)
        self.bn2d_2 = nn.BatchNorm2d(128)
        
        self.pool2d = nn.MaxPool2d(2, 2)
        
        self.fc_spectral_1 = nn.Linear(n_bands, 128)
        self.fc_spectral_2 = nn.Linear(128, 64)
        
        self.bn_spectral_1 = nn.BatchNorm1d(128)
        self.bn_spectral_2 = nn.BatchNorm1d(64)
        
        self.spatial_features = self._get_spatial_features_size()
        
        combined_features = self.spatial_features + 64
        
        self.fc1 = nn.Linear(combined_features, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, n_classes)
        
        self.dropout = nn.Dropout(0.5)
        
    def _get_spatial_features_size(self):
        x = torch.randn(1, self.n_bands, self.patch_size, self.patch_size)
        x = self.pool2d(F.relu(self.bn2d_1(self.conv2d_1(x))))
        x = F.relu(self.bn2d_2(self.conv2d_2(x)))
        return x.numel()
        
    def forward(self, x):
        batch_size = x.size(0)
        
        x_2d = x.squeeze(1)
        
        x_2d = F.relu(self.bn2d_1(self.conv2d_1(x_2d)))
        x_2d = self.pool2d(x_2d)
        x_2d = F.relu(self.bn2d_2(self.conv2d_2(x_2d)))
        x_2d = x_2d.view(batch_size, -1)
        
        x_spectral = x.squeeze(1)
        x_spectral = F.adaptive_avg_pool2d(x_spectral, (1, 1)).squeeze(-1).squeeze(-1)
        x_spectral = F.relu(self.bn_spectral_1(self.fc_spectral_1(x_spectral)))
        x_spectral = self.dropout(x_spectral)
        x_spectral = F.relu(self.bn_spectral_2(self.fc_spectral_2(x_spectral)))
        
        x_combined = torch.cat([x_2d, x_spectral], dim=1)
        
        x = self.dropout(F.relu(self.fc1(x_combined)))
        x = self.dropout(F.relu(self.fc2(x)))
        x = self.fc3(x)
        
        return x
