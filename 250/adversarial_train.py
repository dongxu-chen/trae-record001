import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import os
import argparse
from tqdm import tqdm
import random

from data_utils import get_dataloaders
from model import create_model, vae_loss
from discriminator import ValidityDiscriminator, compute_discriminator_loss, compute_generator_adversarial_loss
from grammar_constraints import SmilesGrammar, GrammarConstrainedDecoder
from mol_utils import (
    is_valid_molecule, calculate_validity, calculate_uniqueness,
    calculate_diversity, filter_valid_molecules
)
from sa_score_cached import (
    calculate_average_sa_score_cached, calculateSAScoreCached,
    load_cache, save_cache, get_cache_stats
)


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def generate_with_grammar(model, grammar_decoder, num_samples, max_len, temperature, device):
    model.eval()
    with torch.no_grad():
        z = torch.randn(num_samples, model.latent_dim).to(device)
        generated = grammar_decoder.decode_constrained(
            model, z, max_len=max_len, temperature=temperature, device=device
        )
    return generated


def train_vae_epoch(model, dataloader, optimizer, device, kl_weight=0.5):
    model.train()
    total_loss = 0
    total_recon = 0
    total_kl = 0
    count = 0
    
    pbar = tqdm(dataloader, desc='VAE Training')
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


def train_discriminator_epoch(discriminator, real_smiles, fake_smiles_list, tokenizer, optimizer_d, device, batch_size=64):
    discriminator.train()
    total_loss = 0
    count = 0
    
    num_batches = max(1, len(fake_smiles_list) // batch_size)
    
    pbar = tqdm(range(num_batches), desc='Discriminator Training')
    for i in pbar:
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(fake_smiles_list))
        
        fake_batch = fake_smiles_list[start_idx:end_idx]
        real_batch = random.sample(real_smiles, min(len(real_smiles), len(fake_batch)))
        
        if len(real_batch) == 0 or len(fake_batch) == 0:
            continue
        
        optimizer_d.zero_grad()
        
        loss, real_loss, fake_loss, real_acc, fake_acc = compute_discriminator_loss(
            discriminator, real_batch, fake_batch, tokenizer, device
        )
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(discriminator.parameters(), max_norm=1.0)
        optimizer_d.step()
        
        total_loss += loss.item()
        count += 1
        
        pbar.set_postfix({
            'd_loss': f'{loss.item():.4f}',
            'real_acc': f'{real_acc.item():.2f}',
            'fake_acc': f'{fake_acc.item():.2f}'
        })
    
    return total_loss / count if count > 0 else 0


def adversarial_generator_step(model, discriminator, tokenizer, grammar_decoder, optimizer_g, 
                                device, batch_size=64, max_len=120, temperature=1.0, adv_weight=0.1):
    model.train()
    discriminator.eval()
    
    optimizer_g.zero_grad()
    
    z = torch.randn(batch_size, model.latent_dim).to(device)
    generated = grammar_decoder.decode_constrained(
        model, z, max_len=max_len, temperature=temperature, device=device
    )
    
    generated_smiles = [tokenizer.decode(seq.cpu().numpy()) for seq in generated]
    
    valid_smiles = []
    valid_indices = []
    for i, s in enumerate(generated_smiles):
        if is_valid_molecule(s):
            valid_smiles.append(s)
            valid_indices.append(i)
    
    if len(valid_smiles) == 0:
        return 0.0, 0.0, 0
    
    valid_encoded = [tokenizer.encode(s) for s in valid_smiles]
    valid_x = torch.tensor(valid_encoded, dtype=torch.long, device=device)
    
    fake_validity = discriminator(valid_x)
    
    adversarial_loss = F.binary_cross_entropy(fake_validity, torch.ones_like(fake_validity))
    
    loss = adv_weight * adversarial_loss
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer_g.step()
    
    return adversarial_loss.item(), fake_validity.mean().item(), len(valid_smiles)


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


def generate_molecules(model, grammar_decoder, tokenizer, num_samples=100, max_len=120, temperature=1.0, device='cpu'):
    model.eval()
    
    generated = generate_with_grammar(model, grammar_decoder, num_samples, max_len, temperature, device)
    
    generated_smiles = []
    for seq in generated:
        smiles = tokenizer.decode(seq.cpu().numpy())
        generated_smiles.append(smiles)
    
    return generated_smiles


def evaluate_generated_molecules(generated_smiles, verbose=True, use_sa_cache=True):
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
        
        avg_sa, sa_count = calculate_average_sa_score_cached(valid_smiles, use_cache=use_sa_cache)
        results['avg_sa_score'] = avg_sa
        results['sa_count'] = sa_count
    else:
        results['uniqueness'] = 0.0
        results['diversity'] = 0.0
        results['avg_sa_score'] = None
        results['sa_count'] = 0
    
    if verbose:
        print("\n" + "="*60)
        print("Evaluation Results")
        print("="*60)
        print(f"Total generated: {len(generated_smiles)}")
        print(f"Valid molecules: {results['num_valid']} ({results['validity']*100:.2f}%)")
        if len(valid_smiles) > 0:
            print(f"Uniqueness: {results['uniqueness']*100:.2f}%")
            print(f"Diversity: {results['diversity']:.4f}")
            if results['avg_sa_score'] is not None:
                print(f"Average SA Score: {results['avg_sa_score']:.4f}")
        print("="*60 + "\n")
        
        if len(valid_smiles) > 0:
            print("Sample valid molecules:")
            for i, smiles in enumerate(valid_smiles[:5]):
                sa = calculateSAScoreCached(smiles, use_cache=use_sa_cache)
                print(f"  {i+1}. {smiles}")
                if sa:
                    print(f"     SA Score: {sa:.2f}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Adversarial Training for Molecule VAE')
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--vae_epochs', type=int, default=10)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--d_lr', type=float, default=1e-4)
    parser.add_argument('--embed_size', type=int, default=256)
    parser.add_argument('--hidden_size', type=int, default=512)
    parser.add_argument('--latent_dim', type=int, default=256)
    parser.add_argument('--num_layers', type=int, default=2)
    parser.add_argument('--dropout', type=float, default=0.3)
    parser.add_argument('--max_len', type=int, default=120)
    parser.add_argument('--num_molecules', type=int, default=5000)
    parser.add_argument('--kl_weight', type=float, default=0.1)
    parser.add_argument('--adv_weight', type=float, default=0.05)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--save_dir', type=str, default='checkpoints')
    parser.add_argument('--generate_only', action='store_true')
    parser.add_argument('--load_model', type=str, default=None)
    parser.add_argument('--num_generate', type=int, default=200)
    parser.add_argument('--temperature', type=float, default=0.8)
    parser.add_argument('--adv_interval', type=int, default=2)
    parser.add_argument('--use_grammar', action='store_true', default=True)
    parser.add_argument('--sa_cache_file', type=str, default='sa_score_cache.pkl')
    
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
    
    all_train_smiles = train_loader.dataset.encodings
    all_train_smiles = [tokenizer.decode(enc) for enc in all_train_smiles]
    
    print("Creating grammar...")
    grammar = SmilesGrammar(tokenizer)
    grammar_decoder = GrammarConstrainedDecoder(grammar)
    print("Grammar created successfully!")
    
    print("Creating models...")
    model = create_model(
        vocab_size=tokenizer.vocab_size,
        embed_size=args.embed_size,
        hidden_size=args.hidden_size,
        latent_dim=args.latent_dim,
        num_layers=args.num_layers,
        dropout=args.dropout
    ).to(device)
    
    discriminator = ValidityDiscriminator(
        vocab_size=tokenizer.vocab_size,
        embed_size=args.embed_size,
        hidden_size=args.hidden_size,
        num_layers=3,
        dropout=args.dropout
    ).to(device)
    
    optimizer_g = optim.Adam(model.parameters(), lr=args.lr)
    optimizer_d = optim.Adam(discriminator.parameters(), lr=args.d_lr)
    
    scheduler_g = optim.lr_scheduler.ReduceLROnPlateau(optimizer_g, 'min', patience=3, factor=0.5)
    
    if args.load_model:
        print(f"Loading model from {args.load_model}")
        checkpoint = torch.load(args.load_model, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer_g.load_state_dict(checkpoint['optimizer_state_dict'])
        if 'discriminator_state_dict' in checkpoint:
            discriminator.load_state_dict(checkpoint['discriminator_state_dict'])
        print("Model loaded successfully!")
    
    if os.path.exists(args.sa_cache_file):
        print("Loading SA Score cache...")
        load_cache(args.sa_cache_file)
    
    if not args.generate_only:
        print("\n" + "="*60)
        print("Phase 1: Pre-training VAE")
        print("="*60)
        
        best_loss = float('inf')
        kl_weight_schedule = np.linspace(0.01, args.kl_weight, args.vae_epochs)
        
        for epoch in range(args.vae_epochs):
            print(f"\nVAE Epoch {epoch+1}/{args.vae_epochs}")
            
            train_loss, train_recon, train_kl = train_vae_epoch(
                model, train_loader, optimizer_g, device, kl_weight=kl_weight_schedule[epoch]
            )
            val_loss, val_recon, val_kl = validate(
                model, test_loader, device, kl_weight=kl_weight_schedule[epoch]
            )
            
            scheduler_g.step(val_loss)
            
            print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
            
            if val_loss < best_loss:
                best_loss = val_loss
                save_path = os.path.join(args.save_dir, 'vae_pretrained.pt')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer_g.state_dict(),
                    'val_loss': val_loss,
                }, save_path)
                print(f"Saved VAE model to {save_path}")
            
            if (epoch + 1) % 5 == 0:
                generated = generate_molecules(
                    model, grammar_decoder, tokenizer, 
                    num_samples=50, max_len=args.max_len, 
                    temperature=args.temperature, device=device
                )
                evaluate_generated_molecules(generated, verbose=True)
        
        print("\n" + "="*60)
        print("Phase 2: Adversarial Training")
        print("="*60)
        
        for epoch in range(args.epochs):
            print(f"\n{'='*60}")
            print(f"Adversarial Epoch {epoch+1}/{args.epochs}")
            print('='*60)
            
            print("\n[1] Training VAE...")
            vae_loss_epoch, _, _ = train_vae_epoch(
                model, train_loader, optimizer_g, device, kl_weight=args.kl_weight
            )
            
            if (epoch + 1) % args.adv_interval == 0:
                print("\n[2] Generating samples for discriminator training...")
                fake_smiles = generate_molecules(
                    model, grammar_decoder, tokenizer,
                    num_samples=min(500, args.batch_size * 5),
                    max_len=args.max_len,
                    temperature=args.temperature,
                    device=device
                )
                
                print(f"\n[3] Training discriminator on {len(fake_smiles)} samples...")
                d_loss = train_discriminator_epoch(
                    discriminator, all_train_smiles, fake_smiles,
                    tokenizer, optimizer_d, device, batch_size=args.batch_size
                )
                
                print(f"\n[4] Adversarial generator update...")
                adv_losses = []
                adv_accs = []
                num_valid_total = 0
                for _ in range(3):
                    adv_loss, adv_acc, num_valid = adversarial_generator_step(
                        model, discriminator, tokenizer, grammar_decoder,
                        optimizer_g, device, batch_size=args.batch_size,
                        max_len=args.max_len, temperature=args.temperature,
                        adv_weight=args.adv_weight
                    )
                    adv_losses.append(adv_loss)
                    adv_accs.append(adv_acc)
                    num_valid_total += num_valid
                
                avg_adv_loss = np.mean(adv_losses)
                avg_adv_acc = np.mean(adv_accs)
                
                print(f"VAE Loss: {vae_loss_epoch:.4f}")
                print(f"Discriminator Loss: {d_loss:.4f}")
                print(f"Adversarial Loss: {avg_adv_loss:.4f}")
                print(f"Average validity prediction: {avg_adv_acc:.4f}")
            
            if (epoch + 1) % 5 == 0 or epoch == args.epochs - 1:
                print(f"\n[5] Evaluation at epoch {epoch+1}...")
                generated = generate_molecules(
                    model, grammar_decoder, tokenizer,
                    num_samples=100, max_len=args.max_len,
                    temperature=args.temperature, device=device
                )
                results = evaluate_generated_molecules(generated, verbose=True)
                
                save_path = os.path.join(args.save_dir, f'adversarial_model_epoch{epoch+1}.pt')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'discriminator_state_dict': discriminator.state_dict(),
                    'optimizer_state_dict': optimizer_g.state_dict(),
                    'optimizer_d_state_dict': optimizer_d.state_dict(),
                    'results': results,
                }, save_path)
                
                save_cache(args.sa_cache_file)
    
    print("\n" + "="*60)
    print("Final Generation and Evaluation")
    print("="*60)
    
    generated = generate_molecules(
        model, grammar_decoder, tokenizer,
        num_samples=args.num_generate, max_len=args.max_len,
        temperature=args.temperature, device=device
    )
    
    results = evaluate_generated_molecules(generated, verbose=True, use_sa_cache=True)
    
    with open('generated_smiles_adversarial.txt', 'w') as f:
        for smiles in generated:
            f.write(smiles + '\n')
    print(f"\nSaved {len(generated)} generated SMILES to 'generated_smiles_adversarial.txt'")
    
    save_cache(args.sa_cache_file)
    
    cache_stats = get_cache_stats()
    print(f"\nCache Statistics: Hits={cache_stats['hits']}, Misses={cache_stats['misses']}")
    
    return results


if __name__ == '__main__':
    main()
