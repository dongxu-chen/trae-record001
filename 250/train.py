import torch
import torch.optim as optim
import numpy as np
import os
import argparse
from tqdm import tqdm
import random

from data_utils import get_dataloaders
from model import create_model, vae_loss
from mol_utils import (
    is_valid_molecule, calculate_validity, calculate_uniqueness,
    calculate_diversity, filter_valid_molecules
)
from sa_score import calculate_average_sa_score


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_epoch(model, dataloader, optimizer, device, kl_weight=0.5):
    model.train()
    total_loss = 0
    total_recon = 0
    total_kl = 0
    count = 0
    
    pbar = tqdm(dataloader, desc='Training')
    for batch in pbar:
        batch = batch.to(device)
        
        optimizer.zero_grad()
        
        output, mu, logvar, z = model(batch)
        
        target = batch[:, 1:]
        loss, recon_loss, kl_loss = vae_loss(output, target, mu, logvar, pad_idx=0, kl_weight=kl_weight)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
        total_recon += recon_loss.item()
        total_kl += kl_loss.item()
        count += 1
        
        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'recon': f'{recon_loss.item():.4f}',
            'kl': f'{kl_loss.item():.4f}'
        })
    
    return total_loss / count, total_recon / count, total_kl / count


def validate(model, dataloader, device, kl_weight=0.5):
    model.eval()
    total_loss = 0
    total_recon = 0
    total_kl = 0
    count = 0
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Validation'):
            batch = batch.to(device)
            
            output, mu, logvar, z = model(batch)
            
            target = batch[:, 1:]
            loss, recon_loss, kl_loss = vae_loss(output, target, mu, logvar, pad_idx=0, kl_weight=kl_weight)
            
            total_loss += loss.item()
            total_recon += recon_loss.item()
            total_kl += kl_loss.item()
            count += 1
    
    return total_loss / count, total_recon / count, total_kl / count


def generate_molecules(model, tokenizer, num_samples=100, max_len=120, temperature=1.0, device='cpu'):
    model.eval()
    generated_smiles = []
    
    with torch.no_grad():
        z = torch.randn(num_samples, model.latent_dim).to(device)
        generated = model.decode(z, max_len=max_len, temperature=temperature)
        
        for seq in generated:
            smiles = tokenizer.decode(seq.cpu().numpy())
            generated_smiles.append(smiles)
    
    return generated_smiles


def evaluate_generated_molecules(generated_smiles, verbose=True):
    results = {}
    
    validity = calculate_validity(generated_smiles)
    results['validity'] = validity
    
    valid_smiles = filter_valid_molecules(generated_smiles)
    results['num_valid'] = len(valid_smiles)
    
    if len(valid_smiles) > 0:
        uniqueness = calculate_uniqueness(generated_smiles)
        results['uniqueness'] = uniqueness
        
        diversity = calculate_diversity(generated_smiles, sample_size=min(100, len(valid_smiles)))
        results['diversity'] = diversity
        
        avg_sa, sa_count = calculate_average_sa_score(valid_smiles)
        results['avg_sa_score'] = avg_sa
        results['sa_count'] = sa_count
    else:
        results['uniqueness'] = 0.0
        results['diversity'] = 0.0
        results['avg_sa_score'] = None
        results['sa_count'] = 0
    
    if verbose:
        print("\n" + "="*50)
        print("Evaluation Results")
        print("="*50)
        print(f"Total generated: {len(generated_smiles)}")
        print(f"Valid molecules: {results['num_valid']} ({results['validity']*100:.2f}%)")
        if len(valid_smiles) > 0:
            print(f"Uniqueness: {results['uniqueness']*100:.2f}%")
            print(f"Diversity: {results['diversity']:.4f}")
            if results['avg_sa_score'] is not None:
                print(f"Average SA Score: {results['avg_sa_score']:.4f}")
        print("="*50 + "\n")
        
        if len(valid_smiles) > 0:
            print("Sample valid molecules:")
            for i, smiles in enumerate(valid_smiles[:5]):
                sa = calculate_average_sa_score([smiles])[0]
                print(f"  {i+1}. {smiles}")
                if sa:
                    print(f"     SA Score: {sa:.2f}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Train Molecule VAE')
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--embed_size', type=int, default=256)
    parser.add_argument('--hidden_size', type=int, default=512)
    parser.add_argument('--latent_dim', type=int, default=256)
    parser.add_argument('--num_layers', type=int, default=2)
    parser.add_argument('--dropout', type=float, default=0.3)
    parser.add_argument('--max_len', type=int, default=120)
    parser.add_argument('--num_molecules', type=int, default=5000)
    parser.add_argument('--kl_weight', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--save_dir', type=str, default='checkpoints')
    parser.add_argument('--generate_only', action='store_true')
    parser.add_argument('--load_model', type=str, default=None)
    parser.add_argument('--num_generate', type=int, default=100)
    parser.add_argument('--temperature', type=float, default=1.0)
    
    args = parser.parse_args()
    
    set_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    os.makedirs(args.save_dir, exist_ok=True)
    
    print("Loading data...")
    train_loader, test_loader, tokenizer = get_dataloaders(
        batch_size=args.batch_size,
        max_len=args.max_len,
        num_molecules=args.num_molecules
    )
    print(f"Vocab size: {tokenizer.vocab_size}")
    print(f"Train samples: {len(train_loader.dataset)}")
    print(f"Test samples: {len(test_loader.dataset)}")
    
    model = create_model(
        vocab_size=tokenizer.vocab_size,
        embed_size=args.embed_size,
        hidden_size=args.hidden_size,
        latent_dim=args.latent_dim,
        num_layers=args.num_layers,
        dropout=args.dropout
    ).to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=3, factor=0.5)
    
    if args.load_model:
        print(f"Loading model from {args.load_model}")
        checkpoint = torch.load(args.load_model, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        print("Model loaded successfully!")
    
    if not args.generate_only:
        best_loss = float('inf')
        kl_weight_schedule = np.linspace(0.01, args.kl_weight, args.epochs)
        
        for epoch in range(args.epochs):
            print(f"\n{'='*50}")
            print(f"Epoch {epoch+1}/{args.epochs}")
            print(f"KL Weight: {kl_weight_schedule[epoch]:.4f}")
            print('='*50)
            
            train_loss, train_recon, train_kl = train_epoch(
                model, train_loader, optimizer, device, kl_weight=kl_weight_schedule[epoch]
            )
            val_loss, val_recon, val_kl = validate(
                model, test_loader, device, kl_weight=kl_weight_schedule[epoch]
            )
            
            scheduler.step(val_loss)
            
            print(f"\nTrain Loss: {train_loss:.4f} (Recon: {train_recon:.4f}, KL: {train_kl:.4f})")
            print(f"Val Loss: {val_loss:.4f} (Recon: {val_recon:.4f}, KL: {val_kl:.4f})")
            
            if val_loss < best_loss:
                best_loss = val_loss
                save_path = os.path.join(args.save_dir, 'best_model.pt')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_loss': val_loss,
                    'vocab_size': tokenizer.vocab_size,
                    'config': {
                        'embed_size': args.embed_size,
                        'hidden_size': args.hidden_size,
                        'latent_dim': args.latent_dim,
                        'num_layers': args.num_layers,
                        'max_len': args.max_len
                    }
                }, save_path)
                print(f"Saved best model to {save_path}")
            
            if (epoch + 1) % 5 == 0:
                print(f"\nGenerating molecules at epoch {epoch+1}...")
                generated = generate_molecules(
                    model, tokenizer, num_samples=50,
                    max_len=args.max_len, temperature=args.temperature, device=device
                )
                evaluate_generated_molecules(generated)
    
    print("\n" + "="*50)
    print("Final Generation and Evaluation")
    print("="*50)
    
    generated = generate_molecules(
        model, tokenizer, num_samples=args.num_generate,
        max_len=args.max_len, temperature=args.temperature, device=device
    )
    
    results = evaluate_generated_molecules(generated, verbose=True)
    
    with open('generated_smiles.txt', 'w') as f:
        for smiles in generated:
            f.write(smiles + '\n')
    print(f"\nSaved {len(generated)} generated SMILES to 'generated_smiles.txt'")
    
    return results


if __name__ == '__main__':
    main()
