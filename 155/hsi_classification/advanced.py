import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from sklearn.cluster import KMeans
from scipy.stats import entropy


class HSIDataset3D(Dataset):
    def __init__(self, X, y=None, patch_size=7):
        self.X = X
        self.y = y
        self.patch_size = patch_size
        self.pad = patch_size // 2
        
        self.height, self.width, self.bands = X.shape
        
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
        patch = patch[np.newaxis, ...]
        
        if self.y is not None:
            label = int(self.y[i, j]) - 1
            return torch.FloatTensor(patch), torch.LongTensor([label])[0]
        
        return torch.FloatTensor(patch)


class HSICNN3D(nn.Module):
    def __init__(self, input_bands, num_classes, patch_size=7):
        super(HSICNN3D, self).__init__()
        
        self.conv3d_1 = nn.Sequential(
            nn.Conv3d(1, 32, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(32),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(1, 1, 1))
        )
        
        self.conv3d_2 = nn.Sequential(
            nn.Conv3d(32, 64, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(64),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(1, 1, 1))
        )
        
        self.conv3d_3 = nn.Sequential(
            nn.Conv3d(64, 128, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(128),
            nn.ReLU()
        )
        
        with torch.no_grad():
            dummy = torch.randn(1, 1, input_bands, patch_size, patch_size)
            features = self.conv3d_1(dummy)
            features = self.conv3d_2(features)
            features = self.conv3d_3(features)
            feature_size = features.view(1, -1).size(1)
        
        self.fc = nn.Sequential(
            nn.Linear(feature_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.conv3d_1(x)
        x = self.conv3d_2(x)
        x = self.conv3d_3(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


class CNN3DClassifier:
    def __init__(self, input_bands, num_classes, patch_size=7, device=None,
                 learning_rate=0.001, batch_size=32, random_state=42):
        self.input_bands = input_bands
        self.num_classes = num_classes
        self.patch_size = patch_size
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.random_state = random_state
        
        torch.manual_seed(random_state)
        
        self.model = HSICNN3D(input_bands, num_classes, patch_size).to(self.device)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        self.train_losses = []
        self.train_accuracies = []

    def _normalize_data(self, X):
        mean = np.mean(X, axis=(0, 1), keepdims=True)
        std = np.std(X, axis=(0, 1), keepdims=True)
        std[std == 0] = 1.0
        return (X - mean) / std

    def fit(self, X_train, y_train, epochs=100, verbose=True):
        X_train = self._normalize_data(X_train.astype(np.float32))
        
        dataset = HSIDataset3D(X_train, y_train, self.patch_size)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        for epoch in range(epochs):
            self.model.train()
            running_loss = 0.0
            correct = 0
            total = 0
            
            for patches, labels in dataloader:
                patches = patches.to(self.device)
                labels = labels.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(patches)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()
                
                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
            
            train_loss = running_loss / len(dataloader)
            train_acc = 100. * correct / total
            self.train_losses.append(train_loss)
            self.train_accuracies.append(train_acc)
            
            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        
        return self

    def predict(self, X):
        X = self._normalize_data(X.astype(np.float32))
        height, width = X.shape[0], X.shape[1]
        
        dataset = HSIDataset3D(X, patch_size=self.patch_size)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=False)
        
        self.model.eval()
        predictions = np.zeros((height, width), dtype=np.int32)
        idx = 0
        
        with torch.no_grad():
            for patches in dataloader:
                patches = patches.to(self.device)
                outputs = self.model(patches)
                _, predicted = torch.max(outputs.data, 1)
                predicted = predicted.cpu().numpy()
                
                for pred in predicted:
                    i, j = dataset.valid_indices[idx]
                    predictions[i, j] = pred + 1
                    idx += 1
        
        return predictions

    def save_model(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'input_bands': self.input_bands,
            'num_classes': self.num_classes,
            'patch_size': self.patch_size
        }, path)

    def load_model(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        self.model = HSICNN3D(
            checkpoint['input_bands'],
            checkpoint['num_classes'],
            checkpoint['patch_size']
        ).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return self


class TransferLearningClassifier:
    def __init__(self, num_classes, backbone='resnet18', device=None,
                 learning_rate=0.001, batch_size=32, freeze_backbone=True, random_state=42):
        self.num_classes = num_classes
        self.backbone = backbone
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.freeze_backbone = freeze_backbone
        self.random_state = random_state
        
        torch.manual_seed(random_state)
        
        if backbone == 'resnet18':
            self.model = models.resnet18(pretrained=True)
            num_ftrs = self.model.fc.in_features
            self.model.fc = nn.Linear(num_ftrs, num_classes)
        elif backbone == 'resnet50':
            self.model = models.resnet50(pretrained=True)
            num_ftrs = self.model.fc.in_features
            self.model.fc = nn.Linear(num_ftrs, num_classes)
        elif backbone == 'vgg16':
            self.model = models.vgg16(pretrained=True)
            num_ftrs = self.model.classifier[6].in_features
            self.model.classifier[6] = nn.Linear(num_ftrs, num_classes)
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
        
        self.model = self.model.to(self.device)
        
        if freeze_backbone:
            for param in self.model.parameters():
                param.requires_grad = False
            for param in self.model.fc.parameters():
                param.requires_grad = True
        
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(filter(lambda p: p.requires_grad, self.model.parameters()), lr=learning_rate)
        
        self.train_losses = []
        self.train_accuracies = []

    def _normalize_data(self, X):
        mean = np.mean(X, axis=(0, 1), keepdims=True)
        std = np.std(X, axis=(0, 1), keepdims=True)
        std[std == 0] = 1.0
        return (X - mean) / std

    def _prepare_patches(self, X, y=None):
        X = self._normalize_data(X.astype(np.float32))
        height, width, bands = X.shape
        
        if bands < 3:
            X_padded = np.pad(X, ((0, 0), (0, 0), (0, 3 - bands)), mode='reflect')
        else:
            step = bands // 3
            X_padded = np.stack([
                X[:, :, 0],
                X[:, :, step],
                X[:, :, 2 * step]
            ], axis=-1)
        
        patches = []
        labels = []
        indices = []
        
        patch_size = 224
        
        for i in range(0, height, patch_size // 2):
            for j in range(0, width, patch_size // 2):
                patch = np.zeros((patch_size, patch_size, 3), dtype=np.float32)
                
                for pi in range(patch_size):
                    for pj in range(patch_size):
                        ni = i + pi - patch_size // 2
                        nj = j + pj - patch_size // 2
                        
                        ni = max(0, min(ni, height - 1))
                        nj = max(0, min(nj, width - 1))
                        
                        patch[pi, pj] = X_padded[ni, nj]
                
                patch = np.transpose(patch, (2, 0, 1))
                patches.append(patch)
                indices.append((i, j))
                
                if y is not None:
                    labels.append(y[min(i, height - 1), min(j, width - 1)])
        
        if y is not None:
            return np.array(patches), np.array(labels), indices
        return np.array(patches), indices

    def fit(self, X_train, y_train, epochs=50, verbose=True):
        patches, labels, _ = self._prepare_patches(X_train, y_train)
        
        valid_mask = labels > 0
        patches = patches[valid_mask]
        labels = labels[valid_mask] - 1
        
        class CustomDataset(Dataset):
            def __init__(self, patches, labels):
                self.patches = patches
                self.labels = labels
            
            def __len__(self):
                return len(self.patches)
            
            def __getitem__(self, idx):
                return torch.FloatTensor(self.patches[idx]), torch.LongTensor([self.labels[idx]])[0]
        
        dataset = CustomDataset(patches, labels)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        for epoch in range(epochs):
            self.model.train()
            running_loss = 0.0
            correct = 0
            total = 0
            
            for patches_batch, labels_batch in dataloader:
                patches_batch = patches_batch.to(self.device)
                labels_batch = labels_batch.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(patches_batch)
                loss = self.criterion(outputs, labels_batch)
                loss.backward()
                self.optimizer.step()
                
                running_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels_batch.size(0)
                correct += (predicted == labels_batch).sum().item()
            
            train_loss = running_loss / len(dataloader)
            train_acc = 100. * correct / total
            self.train_losses.append(train_loss)
            self.train_accuracies.append(train_acc)
            
            if verbose and (epoch + 1) % 5 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        
        return self

    def predict(self, X):
        patches, indices = self._prepare_patches(X)
        
        self.model.eval()
        predictions = np.zeros((X.shape[0], X.shape[1]), dtype=np.int32)
        counts = np.zeros((X.shape[0], X.shape[1]), dtype=np.int32)
        
        with torch.no_grad():
            for idx in range(0, len(patches), self.batch_size):
                batch_patches = torch.FloatTensor(patches[idx:idx + self.batch_size]).to(self.device)
                outputs = self.model(batch_patches)
                _, predicted = torch.max(outputs.data, 1)
                predicted = predicted.cpu().numpy() + 1
                
                for i, pred in enumerate(predicted):
                    patch_i, patch_j = indices[idx + i]
                    for di in range(-112, 112):
                        for dj in range(-112, 112):
                            ni, nj = patch_i + di, patch_j + dj
                            if 0 <= ni < X.shape[0] and 0 <= nj < X.shape[1]:
                                predictions[ni, nj] += pred
                                counts[ni, nj] += 1
        
        counts[counts == 0] = 1
        predictions = predictions // counts
        
        return predictions

    def unfreeze_backbone(self):
        for param in self.model.parameters():
            param.requires_grad = True
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate * 0.1)
        self.freeze_backbone = False


class ActiveLearning:
    def __init__(self, strategy='uncertainty', random_state=42):
        self.strategy = strategy
        self.random_state = random_state
        np.random.seed(random_state)

    def select_samples(self, X, y, model, n_samples=50, method=None):
        method = method or self.strategy
        
        if method == 'uncertainty':
            return self._uncertainty_sampling(X, y, model, n_samples)
        elif method == 'entropy':
            return self._entropy_sampling(X, y, model, n_samples)
        elif method == 'margin':
            return self._margin_sampling(X, y, model, n_samples)
        elif method == 'random':
            return self._random_sampling(X, y, n_samples)
        elif method == 'diversity':
            return self._diversity_sampling(X, y, n_samples)
        else:
            raise ValueError(f"Unsupported strategy: {method}")

    def _uncertainty_sampling(self, X, y, model, n_samples):
        if hasattr(model, 'predict_proba'):
            probas = model.predict_proba(X)
        else:
            predictions = model.predict(X)
            probas = np.zeros((X.shape[0], X.shape[1], len(np.unique(y[y > 0]))))
            for i in range(predictions.shape[0]):
                for j in range(predictions.shape[1]):
                    if predictions[i, j] > 0:
                        probas[i, j, predictions[i, j] - 1] = 1.0
        
        if probas.ndim == 3:
            probas_flat = probas.reshape(-1, probas.shape[-1])
        else:
            probas_flat = probas
        
        unlabeled_mask = (y.flatten() == 0)
        probas_unlabeled = probas_flat[unlabeled_mask]
        
        max_probas = np.max(probas_unlabeled, axis=1)
        uncertainty = 1 - max_probas
        
        top_indices = np.argsort(uncertainty)[-n_samples:]
        
        flat_indices = np.arange(len(y.flatten()))[unlabeled_mask][top_indices]
        row_indices = flat_indices // y.shape[1]
        col_indices = flat_indices % y.shape[1]
        
        return list(zip(row_indices, col_indices))

    def _entropy_sampling(self, X, y, model, n_samples):
        if hasattr(model, 'predict_proba'):
            probas = model.predict_proba(X)
        else:
            predictions = model.predict(X)
            probas = np.zeros((X.shape[0], X.shape[1], len(np.unique(y[y > 0]))))
            for i in range(predictions.shape[0]):
                for j in range(predictions.shape[1]):
                    if predictions[i, j] > 0:
                        probas[i, j, predictions[i, j] - 1] = 1.0
        
        if probas.ndim == 3:
            probas_flat = probas.reshape(-1, probas.shape[-1])
        else:
            probas_flat = probas
        
        unlabeled_mask = (y.flatten() == 0)
        probas_unlabeled = probas_flat[unlabeled_mask]
        
        entropies = entropy(probas_unlabeled.T)
        
        top_indices = np.argsort(entropies)[-n_samples:]
        
        flat_indices = np.arange(len(y.flatten()))[unlabeled_mask][top_indices]
        row_indices = flat_indices // y.shape[1]
        col_indices = flat_indices % y.shape[1]
        
        return list(zip(row_indices, col_indices))

    def _margin_sampling(self, X, y, model, n_samples):
        if hasattr(model, 'predict_proba'):
            probas = model.predict_proba(X)
        else:
            predictions = model.predict(X)
            probas = np.zeros((X.shape[0], X.shape[1], len(np.unique(y[y > 0]))))
            for i in range(predictions.shape[0]):
                for j in range(predictions.shape[1]):
                    if predictions[i, j] > 0:
                        probas[i, j, predictions[i, j] - 1] = 1.0
        
        if probas.ndim == 3:
            probas_flat = probas.reshape(-1, probas.shape[-1])
        else:
            probas_flat = probas
        
        unlabeled_mask = (y.flatten() == 0)
        probas_unlabeled = probas_flat[unlabeled_mask]
        
        sorted_probas = np.sort(probas_unlabeled, axis=1)[:, ::-1]
        margins = sorted_probas[:, 0] - sorted_probas[:, 1]
        
        top_indices = np.argsort(margins)[:n_samples]
        
        flat_indices = np.arange(len(y.flatten()))[unlabeled_mask][top_indices]
        row_indices = flat_indices // y.shape[1]
        col_indices = flat_indices % y.shape[1]
        
        return list(zip(row_indices, col_indices))

    def _random_sampling(self, X, y, n_samples):
        unlabeled_coords = np.argwhere(y == 0)
        selected = np.random.choice(len(unlabeled_coords), n_samples, replace=False)
        return [tuple(coord) for coord in unlabeled_coords[selected]]

    def _diversity_sampling(self, X, y, n_samples):
        X_flat = X.reshape(-1, X.shape[-1])
        unlabeled_mask = (y.flatten() == 0)
        X_unlabeled = X_flat[unlabeled_mask]
        
        kmeans = KMeans(n_clusters=n_samples, random_state=self.random_state, n_init=10)
        kmeans.fit(X_unlabeled)
        
        selected_indices = []
        for cluster_idx in range(n_samples):
            cluster_mask = kmeans.labels_ == cluster_idx
            if np.any(cluster_mask):
                distances = np.linalg.norm(X_unlabeled[cluster_mask] - kmeans.cluster_centers_[cluster_idx], axis=1)
                closest_in_cluster = np.argwhere(cluster_mask).flatten()[np.argmin(distances)]
                selected_indices.append(closest_in_cluster)
        
        flat_indices = np.arange(len(y.flatten()))[unlabeled_mask][selected_indices]
        row_indices = flat_indices // y.shape[1]
        col_indices = flat_indices % y.shape[1]
        
        return list(zip(row_indices, col_indices))

    def active_learning_cycle(self, X, y, model_class, model_params,
                              n_cycles=5, n_samples_per_cycle=20, strategy='uncertainty'):
        y_train = y.copy()
        labeled_counts = []
        accuracies = []
        
        num_classes = len(np.unique(y[y > 0]))
        
        for cycle in range(n_cycles):
            print(f"\nActive Learning Cycle {cycle + 1}/{n_cycles}")
            print(f"Current labeled samples: {np.sum(y_train > 0)}")
            
            model = model_class(**model_params)
            if hasattr(model, 'input_channels'):
                pass
            elif 'num_classes' not in model_params:
                model = model_class(num_classes=num_classes, **model_params)
            
            if hasattr(model, 'fit'):
                model.fit(X, y_train, verbose=False)
                predictions = model.predict(X)
            else:
                model.fit(X.reshape(-1, X.shape[-1])[y_train.flatten() > 0],
                         y_train.flatten()[y_train.flatten() > 0])
                predictions = model.predict(X.reshape(-1, X.shape[-1])).reshape(y_train.shape)
            
            valid_mask = y > 0
            acc = np.mean(predictions[valid_mask] == y[valid_mask])
            accuracies.append(acc)
            labeled_counts.append(np.sum(y_train > 0))
            
            print(f"Current Accuracy: {acc * 100:.2f}%")
            
            if cycle < n_cycles - 1:
                selected_coords = self.select_samples(X, y_train, model, n_samples_per_cycle, strategy)
                
                for i, j in selected_coords:
                    y_train[i, j] = y[i, j]
        
        return y_train, labeled_counts, accuracies


class ClassificationVisualizer:
    def __init__(self, figsize=(12, 8), dpi=100):
        self.figsize = figsize
        self.dpi = dpi
        self.colormaps = {
            'standard': plt.cm.tab20,
            'earth': ListedColormap(['#000000', '#8B4513', '#228B22', '#32CD32', '#006400',
                                     '#FFD700', '#FFA500', '#FF4500', '#0000FF', '#1E90FF',
                                     '#8B008B', '#FF1493', '#808080', '#FFFFFF', '#00FFFF']),
            'remote_sensing': ListedColormap(['#000000', '#0000FF', '#00FF00', '#FFFF00',
                                               '#FF0000', '#FF00FF', '#00FFFF', '#808080',
                                               '#800000', '#808000', '#008000', '#800080',
                                               '#008080', '#000080', '#FFA500'])
        }

    def plot_classification_map(self, y_pred, y_true=None, title='Classification Map',
                                cmap='remote_sensing', save_path=None, show=True):
        fig, axes = plt.subplots(1, 2 if y_true is not None else 1, figsize=self.figsize)
        
        if y_true is not None:
            axes = axes.flatten()
            
            im1 = axes[0].imshow(y_true, cmap=self.colormaps[cmap])
            axes[0].set_title('Ground Truth', fontsize=14, fontweight='bold')
            axes[0].axis('off')
            plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
            
            im2 = axes[1].imshow(y_pred, cmap=self.colormaps[cmap])
            axes[1].set_title(title, fontsize=14, fontweight='bold')
            axes[1].axis('off')
            plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
        else:
            im = axes.imshow(y_pred, cmap=self.colormaps[cmap])
            axes.set_title(title, fontsize=14, fontweight='bold')
            axes.axis('off')
            plt.colorbar(im, ax=axes, fraction=0.046, pad=0.04)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_pseudocolor_image(self, X, bands=[0, 1, 2], title='Pseudocolor Image',
                               enhance_contrast=True, save_path=None, show=True):
        if X.ndim == 3:
            rgb = np.zeros((X.shape[0], X.shape[1], 3), dtype=np.float32)
            
            for i in range(min(3, len(bands))):
                band = X[:, :, bands[i]] if bands[i] < X.shape[-1] else X[:, :, 0]
                
                if enhance_contrast:
                    p2, p98 = np.percentile(band, (2, 98))
                    band = np.clip((band - p2) / (p98 - p2 + 1e-8), 0, 1)
                else:
                    band = (band - band.min()) / (band.max() - band.min() + 1e-8)
                
                rgb[:, :, i] = band
            
            plt.figure(figsize=self.figsize)
            plt.imshow(rgb)
            plt.title(title, fontsize=14, fontweight='bold')
            plt.axis('off')
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            
            if show:
                plt.show()
            else:
                plt.close()
            
            return rgb

    def plot_spectral_signature(self, X, coords, labels=None, title='Spectral Signatures',
                                save_path=None, show=True):
        plt.figure(figsize=self.figsize)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(coords)))
        
        for idx, (i, j) in enumerate(coords):
            spectrum = X[i, j, :]
            label = labels[idx] if labels else f'Pixel ({i}, {j})'
            plt.plot(spectrum, color=colors[idx], label=label, linewidth=2)
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel('Band Number', fontsize=12)
        plt.ylabel('Reflectance', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_uncertainty_map(self, probas, title='Prediction Uncertainty',
                             cmap='RdYlGn_r', save_path=None, show=True):
        if probas.ndim == 3:
            max_proba = np.max(probas, axis=-1)
            uncertainty = 1 - max_proba
        else:
            uncertainty = 1 - probas
        
        plt.figure(figsize=self.figsize)
        im = plt.imshow(uncertainty, cmap=cmap, vmin=0, vmax=1)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.axis('off')
        cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
        cbar.set_label('Uncertainty', fontsize=12)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return uncertainty

    def plot_comparison_panel(self, X, y_true, y_pred, probas=None,
                              rgb_bands=[30, 20, 10], save_path=None, show=True):
        fig = plt.figure(figsize=(15, 10))
        
        gs = fig.add_gridspec(2, 3, hspace=0.1, wspace=0.1)
        
        ax1 = fig.add_subplot(gs[0, 0])
        rgb = self.plot_pseudocolor_image(X, bands=rgb_bands, show=False, enhance_contrast=True)
        ax1.imshow(rgb)
        ax1.set_title('RGB Composite', fontsize=12, fontweight='bold')
        ax1.axis('off')
        
        ax2 = fig.add_subplot(gs[0, 1])
        im2 = ax2.imshow(y_true, cmap=self.colormaps['remote_sensing'])
        ax2.set_title('Ground Truth', fontsize=12, fontweight='bold')
        ax2.axis('off')
        fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        
        ax3 = fig.add_subplot(gs[0, 2])
        im3 = ax3.imshow(y_pred, cmap=self.colormaps['remote_sensing'])
        ax3.set_title('Prediction', fontsize=12, fontweight='bold')
        ax3.axis('off')
        fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
        
        error_map = (y_true != y_pred).astype(float)
        error_map[y_true == 0] = np.nan
        ax4 = fig.add_subplot(gs[1, 0])
        im4 = ax4.imshow(error_map, cmap='Reds', vmin=0, vmax=1)
        ax4.set_title('Classification Errors', fontsize=12, fontweight='bold')
        ax4.axis('off')
        cbar4 = fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)
        cbar4.set_ticks([0, 1])
        cbar4.set_ticklabels(['Correct', 'Error'])
        
        if probas is not None:
            uncertainty = 1 - np.max(probas, axis=-1)
            ax5 = fig.add_subplot(gs[1, 1])
            im5 = ax5.imshow(uncertainty, cmap='RdYlGn_r', vmin=0, vmax=1)
            ax5.set_title('Prediction Uncertainty', fontsize=12, fontweight='bold')
            ax5.axis('off')
            cbar5 = fig.colorbar(im5, ax=ax5, fraction=0.046, pad=0.04)
            cbar5.set_label('Uncertainty')
        else:
            ax5 = fig.add_subplot(gs[1, 1])
            ax5.text(0.5, 0.5, 'No probability data', ha='center', va='center',
                     transform=ax5.transAxes, fontsize=12)
            ax5.set_title('Prediction Uncertainty', fontsize=12, fontweight='bold')
            ax5.axis('off')
        
        ax6 = fig.add_subplot(gs[1, 2])
        correct = np.sum((y_true == y_pred) & (y_true > 0))
        total = np.sum(y_true > 0)
        accuracy = correct / total * 100 if total > 0 else 0
        
        stats_text = f"Overall Accuracy: {accuracy:.2f}%\n"
        stats_text += f"Correct: {correct}\n"
        stats_text += f"Total: {total}\n"
        stats_text += f"Errors: {total - correct}"
        
        ax6.text(0.5, 0.5, stats_text, ha='center', va='center',
                transform=ax6.transAxes, fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax6.set_title('Statistics', fontsize=12, fontweight='bold')
        ax6.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
