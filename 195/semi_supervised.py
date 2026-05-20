import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import Dataset, DataLoader
import copy

from augmentation import get_strong_train_transforms, get_train_transforms


class FixMatchLoss(nn.Module):
    def __init__(self, threshold=0.95, lambda_u=1.0, temperature=1.0):
        super(FixMatchLoss, self).__init__()
        self.threshold = threshold
        self.lambda_u = lambda_u
        self.temperature = temperature
        self.ce_loss = nn.CrossEntropyLoss()
        
    def forward(self, logits_x, labels_x, logits_u_w, logits_u_s):
        loss_x = self.ce_loss(logits_x, labels_x)
        
        pseudo_labels = torch.softmax(logits_u_w / self.temperature, dim=1)
        max_probs, pseudo_targets = torch.max(pseudo_labels, dim=1)
        mask = max_probs.ge(self.threshold).float()
        
        loss_u = (F.cross_entropy(logits_u_s, pseudo_targets, reduction='none') * mask).mean()
        
        total_loss = loss_x + self.lambda_u * loss_u
        
        return total_loss, loss_x, loss_u, mask.mean().item()


class UnsupervisedDataset(Dataset):
    def __init__(self, patches, weak_transform=None, strong_transform=None):
        self.patches = patches
        self.weak_transform = weak_transform
        self.strong_transform = strong_transform
        
    def __len__(self):
        return len(self.patches)
    
    def __getitem__(self, idx):
        patch = self.patches[idx]
        
        if self.weak_transform:
            patch_weak = self.weak_transform(patch.copy())
        else:
            patch_weak = patch.copy()
            
        if self.strong_transform:
            patch_strong = self.strong_transform(patch.copy())
        else:
            patch_strong = patch.copy()
        
        patch_weak = np.transpose(patch_weak, (2, 0, 1))
        patch_weak = np.expand_dims(patch_weak, axis=0)
        
        patch_strong = np.transpose(patch_strong, (2, 0, 1))
        patch_strong = np.expand_dims(patch_strong, axis=0)
        
        return torch.FloatTensor(patch_weak), torch.FloatTensor(patch_strong)


class SemiSupervisedTrainer:
    def __init__(self, model, device, labeled_loader, unlabeled_loader, val_loader,
                 optimizer, scheduler, num_epochs, patience=15,
                 threshold=0.95, lambda_u=1.0, temperature=1.0):
        
        self.model = model.to(device)
        self.device = device
        self.labeled_loader = labeled_loader
        self.unlabeled_loader = unlabeled_loader
        self.val_loader = val_loader
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.num_epochs = num_epochs
        self.patience = patience
        
        self.criterion = FixMatchLoss(threshold=threshold, lambda_u=lambda_u, temperature=temperature)
        self.ce_loss = nn.CrossEntropyLoss()
        
    def train_epoch(self):
        self.model.train()
        
        total_loss = 0.0
        total_loss_x = 0.0
        total_loss_u = 0.0
        total_mask = 0.0
        total_correct = 0
        total_samples = 0
        
        labeled_iter = iter(self.labeled_loader)
        
        for batch_idx, (u_weak, u_strong) in enumerate(self.unlabeled_loader):
            try:
                x, labels_x = next(labeled_iter)
            except StopIteration:
                labeled_iter = iter(self.labeled_loader)
                x, labels_x = next(labeled_iter)
            
            x = x.to(self.device)
            labels_x = labels_x.to(self.device)
            u_weak = u_weak.to(self.device)
            u_strong = u_strong.to(self.device)
            
            self.optimizer.zero_grad()
            
            logits_x = self.model(x)
            
            with torch.no_grad():
                logits_u_w = self.model(u_weak)
            
            logits_u_s = self.model(u_strong)
            
            loss, loss_x, loss_u, mask_ratio = self.criterion(
                logits_x, labels_x, logits_u_w, logits_u_s
            )
            
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item() * x.size(0)
            total_loss_x += loss_x.item() * x.size(0)
            total_loss_u += loss_u.item() * x.size(0)
            total_mask += mask_ratio
            
            _, preds = torch.max(logits_x, 1)
            total_correct += torch.sum(preds == labels_x.data)
            total_samples += x.size(0)
        
        avg_loss = total_loss / total_samples
        avg_loss_x = total_loss_x / total_samples
        avg_loss_u = total_loss_u / total_samples
        avg_mask = total_mask / len(self.unlabeled_loader)
        accuracy = total_correct.double() / total_samples
        
        return avg_loss, avg_loss_x, avg_loss_u, avg_mask, accuracy.item()
    
    def validate(self):
        self.model.eval()
        
        running_loss = 0.0
        running_corrects = 0
        total_samples = 0
        
        with torch.no_grad():
            for inputs, labels in self.val_loader:
                inputs = inputs.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.model(inputs)
                _, preds = torch.max(outputs, 1)
                loss = self.ce_loss(outputs, labels)
                
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                total_samples += inputs.size(0)
        
        epoch_loss = running_loss / total_samples
        epoch_acc = running_corrects.double() / total_samples
        
        return epoch_loss, epoch_acc.item()
    
    def train(self):
        best_model_wts = copy.deepcopy(self.model.state_dict())
        best_acc = 0.0
        epochs_no_improve = 0
        
        history = {
            'train_loss': [],
            'train_loss_x': [],
            'train_loss_u': [],
            'train_mask': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }
        
        for epoch in range(self.num_epochs):
            print(f'\nEpoch {epoch+1}/{self.num_epochs}')
            print('-' * 60)
            
            train_loss, loss_x, loss_u, mask_ratio, train_acc = self.train_epoch()
            
            print(f'Train - Loss: {train_loss:.4f} (X: {loss_x:.4f}, U: {loss_u:.4f}), '
                  f'Mask: {mask_ratio:.4f}, Acc: {train_acc:.4f}')
            
            val_loss, val_acc = self.validate()
            print(f'Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}')
            
            history['train_loss'].append(train_loss)
            history['train_loss_x'].append(loss_x)
            history['train_loss_u'].append(loss_u)
            history['train_mask'].append(mask_ratio)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)
            
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_wts = copy.deepcopy(self.model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            
            if self.scheduler is not None:
                self.scheduler.step(val_loss)
            
            if epochs_no_improve >= self.patience:
                print(f'\nEarly stopping triggered after {epoch+1} epochs')
                break
        
        print(f'\nBest val Acc: {best_acc:.4f}')
        self.model.load_state_dict(best_model_wts)
        
        return self.model, history


class MeanTeacherLoss(nn.Module):
    def __init__(self, alpha=0.999, consistency_weight=10.0, consistency_rampup=5):
        super(MeanTeacherLoss, self).__init__()
        self.alpha = alpha
        self.consistency_weight = consistency_weight
        self.consistency_rampup = consistency_rampup
        self.ce_loss = nn.CrossEntropyLoss()
        
    def update_ema(self, student_model, teacher_model, epoch):
        alpha = min(1 - 1 / (epoch + 1), self.alpha)
        for param_t, param_s in zip(teacher_model.parameters(), student_model.parameters()):
            param_t.data.mul_(alpha).add_(param_s.data, alpha=1 - alpha)
            
    def get_consistency_weight(self, epoch):
        if epoch < self.consistency_rampup:
            return self.consistency_weight * (epoch / self.consistency_rampup)
        return self.consistency_weight
        
    def forward(self, logits_student, labels, logits_teacher, epoch):
        loss_x = self.ce_loss(logits_student, labels)
        
        consistency_loss = F.mse_loss(
            torch.softmax(logits_student, dim=1),
            torch.softmax(logits_teacher, dim=1)
        )
        
        weight = self.get_consistency_weight(epoch)
        total_loss = loss_x + weight * consistency_loss
        
        return total_loss, loss_x, consistency_loss, weight


class MeanTeacherTrainer:
    def __init__(self, student_model, teacher_model, device, labeled_loader, unlabeled_loader,
                 val_loader, optimizer, scheduler, num_epochs, patience=15,
                 alpha=0.999, consistency_weight=10.0, consistency_rampup=5):
        
        self.student = student_model.to(device)
        self.teacher = teacher_model.to(device)
        self.teacher.load_state_dict(student_model.state_dict())
        for param in self.teacher.parameters():
            param.requires_grad = False
            
        self.device = device
        self.labeled_loader = labeled_loader
        self.unlabeled_loader = unlabeled_loader
        self.val_loader = val_loader
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.num_epochs = num_epochs
        self.patience = patience
        
        self.criterion = MeanTeacherLoss(alpha, consistency_weight, consistency_rampup)
        self.ce_loss = nn.CrossEntropyLoss()
        
    def train_epoch(self, epoch):
        self.student.train()
        self.teacher.eval()
        
        total_loss = 0.0
        total_loss_x = 0.0
        total_loss_cons = 0.0
        total_correct = 0
        total_samples = 0
        
        labeled_iter = iter(self.labeled_loader)
        
        for batch_idx, (u_weak, u_strong) in enumerate(self.unlabeled_loader):
            try:
                x, labels_x = next(labeled_iter)
            except StopIteration:
                labeled_iter = iter(self.labeled_loader)
                x, labels_x = next(labeled_iter)
            
            x = x.to(self.device)
            labels_x = labels_x.to(self.device)
            u_weak = u_weak.to(self.device)
            
            self.optimizer.zero_grad()
            
            all_inputs = torch.cat([x, u_weak], dim=0)
            logits_student = self.student(all_inputs)
            logits_x_s = logits_student[:x.size(0)]
            logits_u_s = logits_student[x.size(0):]
            
            with torch.no_grad():
                logits_teacher = self.teacher(all_inputs)
                logits_x_t = logits_teacher[:x.size(0)]
                logits_u_t = logits_teacher[x.size(0):]
            
            loss, loss_x, loss_cons, weight = self.criterion(
                logits_x_s, labels_x, 
                torch.cat([logits_x_t, logits_u_t], dim=0),
                epoch
            )
            
            loss.backward()
            self.optimizer.step()
            
            self.criterion.update_ema(self.student, self.teacher, epoch)
            
            total_loss += loss.item() * x.size(0)
            total_loss_x += loss_x.item() * x.size(0)
            total_loss_cons += loss_cons.item() * x.size(0)
            
            _, preds = torch.max(logits_x_s, 1)
            total_correct += torch.sum(preds == labels_x.data)
            total_samples += x.size(0)
        
        avg_loss = total_loss / total_samples
        avg_loss_x = total_loss_x / total_samples
        avg_loss_cons = total_loss_cons / total_samples
        accuracy = total_correct.double() / total_samples
        
        return avg_loss, avg_loss_x, avg_loss_cons, accuracy.item()
    
    def validate(self):
        self.teacher.eval()
        
        running_loss = 0.0
        running_corrects = 0
        total_samples = 0
        
        with torch.no_grad():
            for inputs, labels in self.val_loader:
                inputs = inputs.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.teacher(inputs)
                _, preds = torch.max(outputs, 1)
                loss = self.ce_loss(outputs, labels)
                
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                total_samples += inputs.size(0)
        
        epoch_loss = running_loss / total_samples
        epoch_acc = running_corrects.double() / total_samples
        
        return epoch_loss, epoch_acc.item()
    
    def train(self):
        best_model_wts = copy.deepcopy(self.teacher.state_dict())
        best_acc = 0.0
        epochs_no_improve = 0
        
        history = {
            'train_loss': [],
            'train_loss_x': [],
            'train_loss_cons': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }
        
        for epoch in range(self.num_epochs):
            print(f'\nEpoch {epoch+1}/{self.num_epochs}')
            print('-' * 60)
            
            train_loss, loss_x, loss_cons, train_acc = self.train_epoch(epoch)
            
            print(f'Train - Loss: {train_loss:.4f} (X: {loss_x:.4f}, Cons: {loss_cons:.4f}), '
                  f'Acc: {train_acc:.4f}')
            
            val_loss, val_acc = self.validate()
            print(f'Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}')
            
            history['train_loss'].append(train_loss)
            history['train_loss_x'].append(loss_x)
            history['train_loss_cons'].append(loss_cons)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)
            
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_wts = copy.deepcopy(self.teacher.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            
            if self.scheduler is not None:
                self.scheduler.step(val_loss)
            
            if epochs_no_improve >= self.patience:
                print(f'\nEarly stopping triggered after {epoch+1} epochs')
                break
        
        print(f'\nBest val Acc: {best_acc:.4f}')
        self.teacher.load_state_dict(best_model_wts)
        
        return self.teacher, history


def create_semisupervised_loaders(patches, labels, labeled_ratio=0.05, 
                                  unlabeled_ratio=0.5, batch_size=16, 
                                  train_transform=None, random_state=42):
    from sklearn.model_selection import train_test_split
    
    n_samples = len(patches)
    indices = np.arange(n_samples)
    
    labeled_indices, rest_indices = train_test_split(
        indices, train_size=labeled_ratio, stratify=labels, random_state=random_state
    )
    
    n_unlabeled = int(n_samples * unlabeled_ratio)
    unlabeled_indices = rest_indices[:n_unlabeled]
    
    print(f'Semi-supervised setup:')
    print(f'  Labeled samples: {len(labeled_indices)}')
    print(f'  Unlabeled samples: {len(unlabeled_indices)}')
    
    from data_loader import HyperSpectralDataset
    
    labeled_dataset = HyperSpectralDataset(
        patches[labeled_indices], labels[labeled_indices], transform=train_transform
    )
    
    weak_tf = get_train_transforms(p=0.5)
    strong_tf = get_strong_train_transforms(p=0.5)
    
    unlabeled_dataset = UnsupervisedDataset(
        patches[unlabeled_indices], 
        weak_transform=weak_tf,
        strong_transform=strong_tf
    )
    
    val_indices, test_indices = train_test_split(
        rest_indices[n_unlabeled:], test_size=0.5, 
        stratify=labels[rest_indices[n_unlabeled:]], random_state=random_state
    )
    
    val_dataset = HyperSpectralDataset(patches[val_indices], labels[val_indices])
    test_dataset = HyperSpectralDataset(patches[test_indices], labels[test_indices])
    
    labeled_loader = DataLoader(labeled_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    unlabeled_loader = DataLoader(unlabeled_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    return labeled_loader, unlabeled_loader, val_loader, test_loader
