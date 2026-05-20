import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.metrics import confusion_matrix, accuracy_score, cohen_kappa_score
import time
import copy


def train_model(model, train_loader, val_loader, criterion, optimizer, 
                scheduler, num_epochs, device, patience=10):
    
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    best_loss = float('inf')
    epochs_no_improve = 0
    
    train_losses = []
    val_losses = []
    train_accs = []
    val_accs = []
    
    for epoch in range(num_epochs):
        print(f'\nEpoch {epoch+1}/{num_epochs}')
        print('-' * 50)
        
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
                dataloader = train_loader
            else:
                model.eval()
                dataloader = val_loader
                
            running_loss = 0.0
            running_corrects = 0
            total_samples = 0
            
            for inputs, labels in dataloader:
                inputs = inputs.to(device)
                labels = labels.to(device)
                
                optimizer.zero_grad()
                
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()
                        
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                total_samples += inputs.size(0)
                
            epoch_loss = running_loss / total_samples
            epoch_acc = running_corrects.double() / total_samples
            
            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')
            
            if phase == 'train':
                train_losses.append(epoch_loss)
                train_accs.append(epoch_acc.cpu().item())
            else:
                val_losses.append(epoch_loss)
                val_accs.append(epoch_acc.cpu().item())
                
                if epoch_acc > best_acc:
                    best_acc = epoch_acc
                    best_model_wts = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    
                if scheduler is not None:
                    scheduler.step(epoch_loss)
                    
        if epochs_no_improve >= patience:
            print(f'\nEarly stopping triggered after {epoch+1} epochs')
            break
            
    print(f'\nBest val Acc: {best_acc:.4f}')
    
    model.load_state_dict(best_model_wts)
    
    history = {
        'train_loss': train_losses,
        'val_loss': val_losses,
        'train_acc': train_accs,
        'val_acc': val_accs
    }
    
    return model, history


def evaluate_model(model, test_loader, device, n_classes=16):
    model.eval()
    
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    oa = accuracy_score(all_labels, all_preds)
    
    cm = confusion_matrix(all_labels, all_preds)
    class_accs = []
    for i in range(n_classes):
        if np.sum(cm[i, :]) > 0:
            class_accs.append(cm[i, i] / np.sum(cm[i, :]))
        else:
            class_accs.append(0.0)
    aa = np.mean(class_accs)
    
    kappa = cohen_kappa_score(all_labels, all_preds)
    
    metrics = {
        'OA': oa,
        'AA': aa,
        'Kappa': kappa,
        'class_accuracies': class_accs,
        'confusion_matrix': cm,
        'predictions': all_preds,
        'labels': all_labels
    }
    
    return metrics


def print_metrics(metrics, class_names=None):
    print('\n' + '='*50)
    print('Classification Results')
    print('='*50)
    print(f'Overall Accuracy (OA): {metrics["OA"]:.4f} ({metrics["OA"]*100:.2f}%)')
    print(f'Average Accuracy (AA): {metrics["AA"]:.4f} ({metrics["AA"]*100:.2f}%)')
    print(f'Kappa Coefficient: {metrics["Kappa"]:.4f}')
    print('-'*50)
    print('Class-wise Accuracies:')
    
    if class_names is None:
        class_names = [f'Class {i+1}' for i in range(len(metrics['class_accuracies']))]
    
    for i, (name, acc) in enumerate(zip(class_names, metrics['class_accuracies'])):
        print(f'  {name}: {acc:.4f} ({acc*100:.2f}%)')
    print('='*50 + '\n')
