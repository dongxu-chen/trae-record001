import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import torch.nn.functional as F


class HSICNN(nn.Module):
    def __init__(self, input_channels, num_classes):
        super(HSICNN, self).__init__()
        
        self.conv1 = nn.Sequential(
            nn.Conv2d(input_channels, 64, kernel_size=3, padding=1, padding_mode='reflect'),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Dropout2d(0.3)
        )
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, padding_mode='reflect'),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Dropout2d(0.3)
        )
        
        self.conv3 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1, padding_mode='reflect'),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Dropout2d(0.3)
        )
        
        self.classifier = nn.Sequential(
            nn.Conv2d(256, 128, kernel_size=1),
            nn.ReLU(),
            nn.Dropout2d(0.5),
            nn.Conv2d(128, num_classes, kernel_size=1)
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.classifier(x)
        return x


class HSIDataset(Dataset):
    def __init__(self, X, y=None, patch_size=5):
        self.X = X
        self.y = y
        self.patch_size = patch_size
        self.pad = patch_size // 2
        
        if X.ndim == 3:
            self.height, self.width, self.bands = X.shape
        else:
            self.height, self.width = 1, X.shape[0]
            self.bands = X.shape[1]
        
        if y is not None:
            valid_mask = y > 0
            self.valid_indices = np.argwhere(valid_mask)
        else:
            self.valid_indices = np.argwhere(np.ones((self.height, self.width), dtype=bool))

    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, idx):
        i, j = self.valid_indices[idx]
        
        patch = np.zeros((self.patch_size, self.patch_size, self.bands), dtype=np.float32)
        
        for pi in range(self.patch_size):
            for pj in range(self.patch_size):
                ni = i - self.pad + pi
                nj = j - self.pad + pj
                
                ni = max(0, min(ni, self.height - 1))
                nj = max(0, min(nj, self.width - 1))
                
                patch[pi, pj] = self.X[ni, nj]
        
        patch = np.transpose(patch, (2, 0, 1))
        
        if self.y is not None:
            label = int(self.y[i, j]) - 1
            return torch.FloatTensor(patch), torch.LongTensor([label])[0]
        
        return torch.FloatTensor(patch)


class CNNClassifier:
    def __init__(self, input_channels, num_classes, device=None, 
                 learning_rate=0.001, batch_size=64, random_state=42):
        self.input_channels = input_channels
        self.num_classes = num_classes
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.random_state = random_state
        
        torch.manual_seed(random_state)
        
        self.model = HSICNN(input_channels, num_classes).to(self.device)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        self.train_losses = []
        self.val_losses = []
        self.train_accuracies = []
        self.val_accuracies = []

    def _normalize_data(self, X):
        mean = np.mean(X, axis=(0, 1), keepdims=True)
        std = np.std(X, axis=(0, 1), keepdims=True)
        std[std == 0] = 1.0
        return (X - mean) / std

    def _prepare_batch(self, X, y=None):
        X = self._normalize_data(X.astype(np.float32))
        X = np.transpose(X, (2, 0, 1))
        X = torch.FloatTensor(X).unsqueeze(0).to(self.device)
        
        if y is not None:
            y = torch.LongTensor(y.astype(np.int32) - 1).to(self.device)
            return X, y
        return X

    def fit(self, X_train, y_train, X_val=None, y_val=None, epochs=100, verbose=True):
        height, width = y_train.shape
        
        X_tensor, y_tensor = self._prepare_batch(X_train, y_train)
        train_mask = torch.BoolTensor(y_train > 0).to(self.device)
        
        val_tensor = None
        val_mask = None
        if X_val is not None and y_val is not None:
            X_val_tensor, y_val_tensor = self._prepare_batch(X_val, y_val)
            val_mask = torch.BoolTensor(y_val > 0).to(self.device)
        
        for epoch in range(epochs):
            self.model.train()
            self.optimizer.zero_grad()
            
            outputs = self.model(X_tensor)
            outputs = outputs.squeeze(0).permute(1, 2, 0)
            
            loss = self.criterion(outputs[train_mask], y_tensor[train_mask])
            loss.backward()
            self.optimizer.step()
            
            _, predicted = torch.max(outputs[train_mask], 1)
            train_acc = (predicted == y_tensor[train_mask]).float().mean().item() * 100
            
            self.train_losses.append(loss.item())
            self.train_accuracies.append(train_acc)
            
            if verbose and (epoch + 1) % 10 == 0:
                log_str = f"Epoch [{epoch+1}/{epochs}], Train Loss: {loss.item():.4f}, Train Acc: {train_acc:.2f}%"
                
                if val_tensor is not None:
                    self.model.eval()
                    with torch.no_grad():
                        val_outputs = self.model(X_val_tensor)
                        val_outputs = val_outputs.squeeze(0).permute(1, 2, 0)
                        val_loss = self.criterion(val_outputs[val_mask], y_val_tensor[val_mask])
                        
                        _, val_predicted = torch.max(val_outputs[val_mask], 1)
                        val_acc = (val_predicted == y_val_tensor[val_mask]).float().mean().item() * 100
                        
                        self.val_losses.append(val_loss.item())
                        self.val_accuracies.append(val_acc)
                        
                        log_str += f", Val Loss: {val_loss.item():.4f}, Val Acc: {val_acc:.2f}%"
                
                print(log_str)
        
        return self

    def predict(self, X):
        self.model.eval()
        
        X_tensor = self._prepare_batch(X)
        
        with torch.no_grad():
            outputs = self.model(X_tensor)
            outputs = outputs.squeeze(0).permute(1, 2, 0)
            _, predicted = torch.max(outputs, 2)
            predictions = predicted.cpu().numpy() + 1
        
        return predictions

    def predict_proba(self, X):
        self.model.eval()
        
        X_tensor = self._prepare_batch(X)
        
        with torch.no_grad():
            outputs = self.model(X_tensor)
            outputs = outputs.squeeze(0).permute(1, 2, 0)
            probas = torch.softmax(outputs, dim=2).cpu().numpy()
        
        return probas

    def save_model(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'input_channels': self.input_channels,
            'num_classes': self.num_classes
        }, path)

    def load_model(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        self.model = HSICNN(
            checkpoint['input_channels'], 
            checkpoint['num_classes']
        ).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return self
