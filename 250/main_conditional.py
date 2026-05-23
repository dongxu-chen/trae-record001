import torch
import torch.optim as optim
import numpy as np
import os
import argparse
from tqdm import tqdm
import random

from data_utils import get_dataloaders
from protein_encoder import ProteinCNNEncoder, encode_protein_sequence, TARGET_PROTEINS
from conditional_model import (
    create_conditional_model, conditional_vae_loss, 
    ConditionalGrammarConstrainedDecoder
)
from grammar_constraints import SmilesGrammar
from discriminator import ValidityDiscriminator, compute_discriminator_loss
from mol_utils import (
    is_valid_molecule, calculate_validity, calculate_uniqueness,
    calculate_diversity, filter_valid_molecules
)
from sa_score_cached import (
    calculate_average_sa_score_cached, calculateSAScoreCached,
    load_cache, save_cache, get_cache_stats
)
from docking_scorer import DockingScorer
from active_learning import ActiveLearningTrainer


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def pre_train_vae(
    model, protein_encoder, train_loader, test_loader, 
    optimizer_g, optimizer_p, device, tokenizer,
    epochs=20, kl_weight=0.1, target_name='EGFR', save_dir='checkpoints'
):
    print("\n" + "="*60)
    print("Phase 1: Pre-training Conditional VAE")
    print("="*60)
    
    target_info = TARGET_PROTEINS.get(target_name)
    if target_info is None:
        raise ValueError(f"Unknown target: {target_name}")
    
    encoded_seq = encode_protein_sequence(target_info['sequence'], max_len=500)
    condition_tensor = torch.tensor([encoded_seq], dtype=torch.long, device=device)
    
    best_loss = float('inf')
    kl_weight_schedule = np.linspace(0.01, kl_weight, epochs)
    
    for epoch in range(epochs):
        model.train()
        protein_encoder.train()
        
        total_loss = 0
        total_recon = 0
        total_kl = 0
        count = 0
        
        pbar = tqdm(train_loader, desc=f'VAE Epoch {epoch+1}/{epochs}')
        for batch in pbar:
            batch = batch.to(device)
            batch_size = batch.size(0)
            
            condition = protein_encoder(condition_tensor.repeat(batch_size, 1))
            
            optimizer_g.zero_grad()
            optimizer_p.zero_grad()
            
            output, mu, logvar, z = model(batch, condition)
            
            target = batch[:, 1:]
            loss, recon_loss, kl_loss = conditional_vae_loss(
                output, target, mu, logvar, pad_idx=0, kl_weight=kl_weight_schedule[epoch]
            )
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            torch.nn.utils.clip_grad_norm_(protein_encoder.parameters(), max_norm=1.0)
            optimizer_g.step()
            optimizer_p.step()
            
            total_loss += loss.item()
            total_recon += recon_loss.item()
            total_kl += kl_loss.item()
            count += 1
            
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'recon': f'{recon_loss.item():.4f}',
                'kl': f'{kl_loss.item():.4f}'
            })
        
        avg_loss = total_loss / count
        print(f"Epoch {epoch+1}: Train Loss={avg_loss:.4f}")
        
        if avg_loss < best_loss:
            best_loss = avg_loss
            save_path = os.path.join(save_dir, 'conditional_vae_pretrained.pt')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'protein_encoder_state_dict': protein_encoder.state_dict(),
                'optimizer_g_state_dict': optimizer_g.state_dict(),
                'optimizer_p_state_dict': optimizer_p.state_dict(),
                'train_loss': avg_loss,
            }, save_path)
            print(f"Saved best model to {save_path}")
        
        if (epoch + 1) % 5 == 0:
            evaluate_conditional_generation(
                model, protein_encoder, tokenizer, target_name, 
                device, num_samples=100
            )
    
    return best_loss


def adversarial_training_phase(
    model, protein_encoder, discriminator, tokenizer, 
    train_smiles, target_name, device,
    epochs=30, adv_interval=2, adv_weight=0.05, save_dir='checkpoints'
):
    print("\n" + "="*60)
    print("Phase 2: Adversarial Training")
    print("="*60)
    
    grammar = SmilesGrammar(tokenizer)
    grammar_decoder = ConditionalGrammarConstrainedDecoder(grammar)
    
    optimizer_d = optim.Adam(discriminator.parameters(), lr=1e-4)
    
    target_info = TARGET_PROTEINS.get(target_name)
    encoded_seq = encode_protein_sequence(target_info['sequence'], max_len=500)
    condition_tensor = torch.tensor([encoded_seq], dtype=torch.long, device=device)
    
    for epoch in range(epochs):
        print(f"\nAdversarial Epoch {epoch+1}/{epochs}")
        
        model.train()
        protein_encoder.train()
        
        if (epoch + 1) % adv_interval == 0:
            print("  Generating fake samples...")
            model.eval()
            protein_encoder.eval()
            
            with torch.no_grad():
                condition = protein_encoder(condition_tensor.repeat(200, 1))
                z = torch.randn(200, model.latent_dim).to(device)
                generated = grammar_decoder.decode_constrained(
                    model, z, condition, max_len=120, temperature=0.8, device=device
                )
            
            fake_smiles = [tokenizer.decode(seq.cpu().numpy()) for seq in generated]
            fake_smiles = [s for s in fake_smiles if is_valid_molecule(s)]
            
            if len(fake_smiles) > 0:
                print(f"  Training discriminator on {len(fake_smiles)} samples...")
                discriminator.train()
                
                real_batch = random.sample(train_smiles, min(len(train_smiles), len(fake_smiles)))
                
                optimizer_d.zero_grad()
                d_loss, _, _, _, _ = compute_discriminator_loss(
                    discriminator, real_batch, fake_smiles, tokenizer, device
                )
                d_loss.backward()
                optimizer_d.step()
                
                print(f"  Discriminator loss: {d_loss.item():.4f}")
            
            model.train()
            protein_encoder.train()
        
        if (epoch + 1) % 5 == 0:
            evaluate_conditional_generation(
                model, protein_encoder, tokenizer, target_name,
                device, num_samples=100, use_docking=True
            )
    
    save_path = os.path.join(save_dir, 'conditional_adversarial.pt')
    torch.save({
        'model_state_dict': model.state_dict(),
        'protein_encoder_state_dict': protein_encoder.state_dict(),
        'discriminator_state_dict': discriminator.state_dict(),
    }, save_path)
    print(f"Saved adversarial model to {save_path}")


def active_learning_phase(
    active_trainer, target_name, num_iterations=10,
    num_candidates=500, n_select=50, save_dir='active_checkpoints'
):
    print("\n" + "="*60)
    print("Phase 3: Active Learning Loop")
    print("="*60)
    print(f"Target: {target_name}")
    print(f"Number of iterations: {num_iterations}")
    print(f"Candidates per iteration: {num_candidates}")
    print(f"Selected per iteration: {n_select}")
    
    all_results = []
    
    for iteration in range(num_iterations):
        result = active_trainer.run_iteration(
            target_name=target_name,
            num_candidates=num_candidates,
            n_select=n_select,
            finetune_epochs=3
        )
        
        if result:
            all_results.append(result)
        
        if (iteration + 1) % 5 == 0:
            active_trainer.save(save_dir)
            print(f"\nSaved checkpoint at iteration {iteration + 1}")
    
    active_trainer.save(save_dir)
    
    print("\n" + "="*60)
    print("Active Learning Complete!")
    print("="*60)
    if all_results:
        print(f"Best docking score: {min(r['best_score'] for r in all_results):.2f}")
        print(f"Final buffer size: {len(active_trainer.buffer)}")
    
    return all_results


def evaluate_conditional_generation(
    model, protein_encoder, tokenizer, target_name,
    device, num_samples=100, temperature=0.8, use_docking=False
):
    model.eval()
    protein_encoder.eval()
    
    print(f"\nEvaluating conditional generation for target: {target_name}")
    
    grammar = SmilesGrammar(tokenizer)
    grammar_decoder = ConditionalGrammarConstrainedDecoder(grammar)
    
    target_info = TARGET_PROTEINS.get(target_name)
    encoded_seq = encode_protein_sequence(target_info['sequence'], max_len=500)
    condition_tensor = torch.tensor([encoded_seq], dtype=torch.long, device=device)
    
    with torch.no_grad():
        condition = protein_encoder(condition_tensor.repeat(num_samples, 1))
        z = torch.randn(num_samples, model.latent_dim).to(device)
        generated = grammar_decoder.decode_constrained(
            model, z, condition, max_len=120, temperature=temperature, device=device
        )
    
    generated_smiles = [tokenizer.decode(seq.cpu().numpy()) for seq in generated]
    
    validity = calculate_validity(generated_smiles)
    valid_smiles = filter_valid_molecules(generated_smiles)
    
    print(f"  Generated: {len(generated_smiles)}")
    print(f"  Valid: {len(valid_smiles)} ({validity*100:.2f}%)")
    
    if len(valid_smiles) > 0:
        uniqueness = calculate_uniqueness(generated_smiles)
        diversity = calculate_diversity(generated_smiles, sample_size=min(50, len(valid_smiles)))
        avg_sa, _ = calculate_average_sa_score_cached(valid_smiles)
        
        print(f"  Uniqueness: {uniqueness*100:.2f}%")
        print(f"  Diversity: {diversity:.4f}")
        if avg_sa:
            print(f"  Avg SA Score: {avg_sa:.2f}")
        
        if use_docking:
            scorer = DockingScorer()
            ranked = scorer.rank_molecules(valid_smiles, target_name, top_k=5)
            if ranked:
                print(f"\n  Top 5 by docking score ({target_name}):")
                for i, (smiles, score, details) in enumerate(ranked):
                    print(f"    {i+1}. Score: {score:.2f}, QED: {details['qed_score']:.3f}")
                    print(f"       {smiles[:50]}..." if len(smiles) > 50 else f"       {smiles}")
    
    return generated_smiles


def main():
    parser = argparse.ArgumentParser(description='Conditional Molecule Generation with Active Learning')
    parser.add_argument('--target', type=str, default='EGFR', 
                       choices=['EGFR', 'HER2', 'DRD2', 'ACE2'])
    parser.add_argument('--phase', type=str, default='all',
                       choices=['pretrain', 'adversarial', 'active', 'all', 'generate'])
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--pretrain_epochs', type=int, default=20)
    parser.add_argument('--adv_epochs', type=int, default=30)
    parser.add_argument('--active_iterations', type=int, default=10)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--condition_dim', type=int, default=256)
    parser.add_argument('--latent_dim', type=int, default=256)
    parser.add_argument('--num_candidates', type=int, default=500)
    parser.add_argument('--n_select', type=int, default=50)
    parser.add_argument('--num_generate', type=int, default=200)
    parser.add_argument('--temperature', type=float, default=0.8)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--save_dir', type=str, default='checkpoints')
    parser.add_argument('--load_model', type=str, default=None)
    parser.add_argument('--sa_cache_file', type=str, default='sa_score_cache.pkl')
    
    args = parser.parse_args()
    
    set_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    print(f"Target protein: {args.target}")
    
    os.makedirs(args.save_dir, exist_ok=True)
    
    if os.path.exists(args.sa_cache_file):
        print(f"Loading SA Score cache from {args.sa_cache_file}")
        load_cache(args.sa_cache_file)
    
    print("\nLoading data and initializing tokenizer...")
    train_loader, test_loader, tokenizer = get_dataloaders(
        batch_size=args.batch_size, max_len=120, num_molecules=5000
    )
    all_train_smiles = [tokenizer.decode(enc) for enc in train_loader.dataset.encodings]
    print(f"Vocab size: {tokenizer.vocab_size}")
    
    print("\nInitializing models...")
    protein_encoder = ProteinCNNEncoder(
        vocab_size=22, embed_size=64, hidden_size=256,
        output_dim=args.condition_dim, max_len=500
    ).to(device)
    
    model = create_conditional_model(
        vocab_size=tokenizer.vocab_size,
        condition_dim=args.condition_dim,
        embed_size=256, hidden_size=512,
        latent_dim=args.latent_dim, num_layers=2, dropout=0.3
    ).to(device)
    
    discriminator = ValidityDiscriminator(
        vocab_size=tokenizer.vocab_size,
        embed_size=256, hidden_size=512, num_layers=3, dropout=0.3
    ).to(device)
    
    optimizer_g = optim.Adam(model.parameters(), lr=args.lr)
    optimizer_p = optim.Adam(protein_encoder.parameters(), lr=5e-4)
    
    if args.load_model:
        print(f"\nLoading model from {args.load_model}")
        checkpoint = torch.load(args.load_model, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        if 'protein_encoder_state_dict' in checkpoint:
            protein_encoder.load_state_dict(checkpoint['protein_encoder_state_dict'])
        if 'discriminator_state_dict' in checkpoint:
            discriminator.load_state_dict(checkpoint['discriminator_state_dict'])
        print("Model loaded successfully!")
    
    if args.phase == 'pretrain' or args.phase == 'all':
        pre_train_vae(
            model, protein_encoder, train_loader, test_loader,
            optimizer_g, optimizer_p, device, tokenizer,
            epochs=args.pretrain_epochs, target_name=args.target, save_dir=args.save_dir
        )
    
    if args.phase == 'adversarial' or args.phase == 'all':
        adversarial_training_phase(
            model, protein_encoder, discriminator, tokenizer,
            all_train_smiles, args.target, device,
            epochs=args.adv_epochs, save_dir=args.save_dir
        )
    
    if args.phase == 'active' or args.phase == 'all':
        print("\n" + "="*60)
        print("Initializing Active Learning Trainer")
        print("="*60)
        
        active_trainer = ActiveLearningTrainer(
            tokenizer=tokenizer,
            condition_dim=args.condition_dim,
            device=device,
            buffer_capacity=10000,
            docking_threshold=-7.0,
            sa_threshold=6.0
        )
        
        active_trainer.model.load_state_dict(model.state_dict())
        active_trainer.protein_encoder.load_state_dict(protein_encoder.state_dict())
        
        active_learning_phase(
            active_trainer, args.target,
            num_iterations=args.active_iterations,
            num_candidates=args.num_candidates,
            n_select=args.n_select
        )
        
        model = active_trainer.model
        protein_encoder = active_trainer.protein_encoder
    
    if args.phase == 'generate' or args.phase == 'all':
        print("\n" + "="*60)
        print("Final Generation and Evaluation")
        print("="*60)
        
        generated = evaluate_conditional_generation(
            model, protein_encoder, tokenizer, args.target,
            device, num_samples=args.num_generate,
            temperature=args.temperature, use_docking=True
        )
        
        output_file = f'generated_{args.target.lower()}_molecules.txt'
        with open(output_file, 'w') as f:
            for smiles in generated:
                f.write(smiles + '\n')
        print(f"\nSaved {len(generated)} molecules to {output_file}")
        
        save_cache(args.sa_cache_file)
        
        cache_stats = get_cache_stats()
        print(f"\nSA Score Cache Statistics:")
        print(f"  Hits: {cache_stats['hits']}")
        print(f"  Misses: {cache_stats['misses']}")
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
            print(f"  Hit Rate: {hit_rate*100:.2f}%")
    
    print("\n" + "="*60)
    print("Pipeline complete!")
    print("="*60)


if __name__ == '__main__':
    main()
