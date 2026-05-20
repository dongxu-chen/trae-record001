import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

from data_loader import (
    load_indian_pines, create_data_loaders, prepare_cv_data,
    create_cv_splits, create_cv_data_loaders
)
from model import Hybrid2D1DCNN, LightHybrid2D1DCNN, SpectralSpatialCNN
from augmentation import (
    get_train_transforms, get_strong_train_transforms, 
    get_spectral_transforms
)
from train import train_model, evaluate_model, print_metrics
from visualization import (
    plot_confusion_matrix, plot_training_history, 
    plot_class_distribution, visualize_data_samples,
    plot_class_accuracies, plot_pca_variance
)


INDIAN_PINES_CLASS_NAMES = [
    'Alfalfa', 'Corn-notill', 'Corn-mintill', 'Corn',
    'Grass-pasture', 'Grass-trees', 'Grass-pasture-mowed',
    'Hay-windrowed', 'Oats', 'Soybean-notill', 'Soybean-mintill',
    'Soybean-clean', 'Wheat', 'Woods', 'Buildings-Grass-Trees-Drives',
    'Stone-Steel-Towers'
]


def run_single_training(config, data, gt, device, save_results=True):
    train_transform = None
    if config['use_augmentation']:
        if config.get('strong_augmentation', False):
            train_transform = get_strong_train_transforms(p=config.get('aug_p', 0.5))
        else:
            train_transform = get_train_transforms(p=config.get('aug_p', 0.5))
    
    print('\nCreating data loaders...')
    train_loader, val_loader, test_loader, all_labels, info = create_data_loaders(
        data, gt,
        patch_size=config['patch_size'],
        n_components=config['n_components'],
        batch_size=config['batch_size'],
        train_ratio=config['train_ratio'],
        val_ratio=config['val_ratio'],
        train_transform=train_transform,
        random_state=config['random_state'],
        auto_pca=config.get('auto_pca', False),
        variance_threshold=config.get('variance_threshold', 0.99)
    )
    
    config['n_components'] = info['n_components']
    
    print(f'Train samples: {len(train_loader.dataset)}')
    print(f'Val samples: {len(val_loader.dataset)}')
    print(f'Test samples: {len(test_loader.dataset)}')
    print(f'Total labeled samples: {len(all_labels)}')
    
    if save_results:
        plot_class_distribution(all_labels, class_names=INDIAN_PINES_CLASS_NAMES,
                               save_path='results/figures/class_distribution.png')
    
    n_classes = len(np.unique(all_labels))
    
    print(f'\nInitializing {config["model_type"]} model...')
    if config['model_type'] == 'Hybrid2D1DCNN':
        model = Hybrid2D1DCNN(n_classes=n_classes, patch_size=config['patch_size'], 
                             n_bands=config['n_components'])
    elif config['model_type'] == 'LightHybrid2D1DCNN':
        model = LightHybrid2D1DCNN(n_classes=n_classes, patch_size=config['patch_size'],
                                  n_bands=config['n_components'])
    elif config['model_type'] == 'SpectralSpatialCNN':
        model = SpectralSpatialCNN(n_classes=n_classes, patch_size=config['patch_size'],
                                  n_bands=config['n_components'])
    else:
        raise ValueError(f'Unknown model type: {config["model_type"]}')
    
    model = model.to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f'Total model parameters: {total_params:,}')
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'],
                          weight_decay=config['weight_decay'])
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', 
                                                     factor=0.5, patience=5, 
                                                     verbose=True)
    
    print('\nStarting training...')
    model, history = train_model(
        model, train_loader, val_loader, criterion, optimizer, scheduler,
        num_epochs=config['num_epochs'], device=device, patience=config['patience']
    )
    
    if save_results:
        print('\nPlotting training history...')
        plot_training_history(history, save_path='results/figures/training_history.png')
    
    print('\nEvaluating on test set...')
    metrics = evaluate_model(model, test_loader, device, n_classes=n_classes)
    
    if save_results:
        print_metrics(metrics, class_names=INDIAN_PINES_CLASS_NAMES)
        
        print('\nPlotting confusion matrix...')
        plot_confusion_matrix(
            metrics['confusion_matrix'],
            class_names=INDIAN_PINES_CLASS_NAMES,
            title='Confusion Matrix (Normalized)',
            normalize=True,
            save_path='results/figures/confusion_matrix_normalized.png'
        )
        
        plot_confusion_matrix(
            metrics['confusion_matrix'],
            class_names=INDIAN_PINES_CLASS_NAMES,
            title='Confusion Matrix (Counts)',
            normalize=False,
            save_path='results/figures/confusion_matrix_counts.png'
        )
        
        print('\nPlotting class-wise accuracies...')
        plot_class_accuracies(
            metrics['class_accuracies'],
            class_names=INDIAN_PINES_CLASS_NAMES,
            save_path='results/figures/class_accuracies.png'
        )
    
    return model, metrics, history, info


def run_cross_validation(config, data, gt, device, n_splits=5):
    print(f'\n{"="*60}')
    print(f'Starting {n_splits}-fold Cross Validation')
    print(f'{"="*60}')
    
    patches, labels, info = prepare_cv_data(
        data, gt,
        patch_size=config['patch_size'],
        n_components=config['n_components'],
        auto_pca=config.get('auto_pca', False),
        variance_threshold=config.get('variance_threshold', 0.99)
    )
    config['n_components'] = info['n_components']
    n_classes = len(np.unique(labels))
    
    print(f'PCA components used: {config["n_components"]}')
    print(f'Total samples: {len(patches)}')
    print(f'Number of classes: {n_classes}')
    
    splits = create_cv_splits(labels, n_splits=n_splits, random_state=config['random_state'])
    
    train_transform = None
    if config['use_augmentation']:
        if config.get('strong_augmentation', False):
            train_transform = get_strong_train_transforms(p=config.get('aug_p', 0.5))
        else:
            train_transform = get_train_transforms(p=config.get('aug_p', 0.5))
    
    cv_metrics = []
    cv_histories = []
    
    for fold, (train_idx, val_idx, test_idx) in enumerate(splits):
        print(f'\n{"-"*60}')
        print(f'Fold {fold+1}/{n_splits}')
        print(f'{"-"*60}')
        
        train_loader, val_loader, test_loader = create_cv_data_loaders(
            patches, labels, train_idx, val_idx, test_idx,
            batch_size=config['batch_size'],
            train_transform=train_transform
        )
        
        if config['model_type'] == 'Hybrid2D1DCNN':
            model = Hybrid2D1DCNN(n_classes=n_classes, patch_size=config['patch_size'], 
                                 n_bands=config['n_components'])
        elif config['model_type'] == 'LightHybrid2D1DCNN':
            model = LightHybrid2D1DCNN(n_classes=n_classes, patch_size=config['patch_size'],
                                      n_bands=config['n_components'])
        elif config['model_type'] == 'SpectralSpatialCNN':
            model = SpectralSpatialCNN(n_classes=n_classes, patch_size=config['patch_size'],
                                      n_bands=config['n_components'])
        else:
            raise ValueError(f'Unknown model type: {config["model_type"]}')
        
        model = model.to(device)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'],
                              weight_decay=config['weight_decay'])
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', 
                                                         factor=0.5, patience=5, 
                                                         verbose=False)
        
        model, history = train_model(
            model, train_loader, val_loader, criterion, optimizer, scheduler,
            num_epochs=config['num_epochs'], device=device, patience=config['patience']
        )
        
        metrics = evaluate_model(model, test_loader, device, n_classes=n_classes)
        
        print(f'Fold {fold+1} Results: OA={metrics["OA"]:.4f}, AA={metrics["AA"]:.4f}, Kappa={metrics["Kappa"]:.4f}')
        
        cv_metrics.append(metrics)
        cv_histories.append(history)
    
    print(f'\n{"="*60}')
    print('Cross Validation Summary')
    print(f'{"="*60}')
    
    oas = [m['OA'] for m in cv_metrics]
    aas = [m['AA'] for m in cv_metrics]
    kappas = [m['Kappa'] for m in cv_metrics]
    
    print(f'OA: {np.mean(oas):.4f} ± {np.std(oas):.4f}')
    print(f'AA: {np.mean(aas):.4f} ± {np.std(aas):.4f}')
    print(f'Kappa: {np.mean(kappas):.4f} ± {np.std(kappas):.4f}')
    
    avg_cm = np.mean([m['confusion_matrix'] for m in cv_metrics], axis=0)
    
    cv_results = {
        'cv_metrics': cv_metrics,
        'cv_histories': cv_histories,
        'avg_cm': avg_cm,
        'mean_OA': np.mean(oas),
        'std_OA': np.std(oas),
        'mean_AA': np.mean(aas),
        'std_AA': np.std(aas),
        'mean_Kappa': np.mean(kappas),
        'std_Kappa': np.std(kappas),
        'config': config
    }
    
    return cv_results


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}\n')
    
    config = {
        'patch_size': 5,
        'n_components': 30,
        'batch_size': 16,
        'train_ratio': 0.15,
        'val_ratio': 0.05,
        'num_epochs': 100,
        'learning_rate': 0.001,
        'weight_decay': 1e-4,
        'patience': 15,
        'use_augmentation': True,
        'strong_augmentation': True,
        'aug_p': 0.5,
        'model_type': 'Hybrid2D1DCNN',
        'random_state': 42,
        'auto_pca': False,
        'variance_threshold': 0.99,
        'use_cv': False,
        'n_splits': 5
    }
    
    print('Configuration:')
    for k, v in config.items():
        print(f'  {k}: {v}')
    print()
    
    print('Loading Indian Pines dataset...')
    data, gt = load_indian_pines()
    print(f'Data shape: {data.shape}')
    print(f'Ground truth shape: {gt.shape}')
    print(f'Number of classes: {len(np.unique(gt)) - 1}')
    
    os.makedirs('results', exist_ok=True)
    os.makedirs('results/figures', exist_ok=True)
    
    print('\nVisualizing data samples...')
    visualize_data_samples(data, gt, class_names=INDIAN_PINES_CLASS_NAMES,
                          save_path='results/figures/data_visualization.png')
    
    if config.get('use_cv', False):
        cv_results = run_cross_validation(config, data, gt, device, n_splits=config['n_splits'])
        np.save('results/cv_results.npy', cv_results)
        
        with open('results/cv_summary.txt', 'w') as f:
            f.write('Indian Pines Cross Validation Results\n')
            f.write('='*60 + '\n\n')
            f.write(f'Model: {config["model_type"]}\n')
            f.write(f'Batch Size: {config["batch_size"]}\n')
            f.write(f'PCA Components: {config["n_components"]}\n')
            f.write(f'Number of Splits: {config["n_splits"]}\n\n')
            f.write(f'Mean OA: {cv_results["mean_OA"]:.4f} ± {cv_results["std_OA"]:.4f}\n')
            f.write(f'Mean AA: {cv_results["mean_AA"]:.4f} ± {cv_results["std_AA"]:.4f}\n')
            f.write(f'Mean Kappa: {cv_results["mean_Kappa"]:.4f} ± {cv_results["std_Kappa"]:.4f}\n')
        
        print('\nCross validation complete! Results saved to ./results/')
    else:
        model, metrics, history, info = run_single_training(config, data, gt, device, save_results=True)
        
        results = {
            'OA': metrics['OA'],
            'AA': metrics['AA'],
            'Kappa': metrics['Kappa'],
            'class_accuracies': metrics['class_accuracies'],
            'config': config,
            'history': history,
            'info': info
        }
        
        np.save('results/metrics.npy', metrics)
        np.save('results/results.npy', results)
        
        with open('results/summary.txt', 'w') as f:
            f.write('Indian Pines Hyperspectral Image Classification Results\n')
            f.write('='*60 + '\n\n')
            f.write(f'Model: {config["model_type"]}\n')
            f.write(f'Patch Size: {config["patch_size"]}\n')
            f.write(f'PCA Components: {config["n_components"]}\n')
            f.write(f'Batch Size: {config["batch_size"]}\n')
            f.write(f'Data Augmentation: {config["use_augmentation"]}\n')
            f.write(f'Strong Augmentation: {config.get("strong_augmentation", False)}\n\n')
            f.write(f'Overall Accuracy (OA): {metrics["OA"]:.4f} ({metrics["OA"]*100:.2f}%)\n')
            f.write(f'Average Accuracy (AA): {metrics["AA"]:.4f} ({metrics["AA"]*100:.2f}%)\n')
            f.write(f'Kappa Coefficient: {metrics["Kappa"]:.4f}\n\n')
            f.write('Class-wise Accuracies:\n')
            for name, acc in zip(INDIAN_PINES_CLASS_NAMES, metrics['class_accuracies']):
                f.write(f'  {name}: {acc:.4f} ({acc*100:.2f}%)\n')
        
        torch.save(model.state_dict(), 'results/model_weights.pth')
        
        print('\n' + '='*60)
        print('Training and evaluation complete!')
        print('Results saved to ./results/')
        print('='*60)
    
    return


if __name__ == '__main__':
    main()
