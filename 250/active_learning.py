import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import json
from tqdm import tqdm
from collections import deque
import random

from protein_encoder import ProteinCNNEncoder, encode_protein_sequence, TARGET_PROTEINS
from conditional_model import create_conditional_model, conditional_vae_loss, ConditionalGrammarConstrainedDecoder
from grammar_constraints import SmilesGrammar
from data_utils import get_dataloaders
from mol_utils import is_valid_molecule, filter_valid_molecules
from sa_score_cached import calculateSAScoreCached, save_cache as save_sa_cache
from docking_scorer import DockingScorer, select_leads


class ActiveLearningBuffer:
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.scores = deque(maxlen=capacity)
        self.targets = deque(maxlen=capacity)
    
    def add(self, smiles, score, target_name):
        self.buffer.append(smiles)
        self.scores.append(score)
        self.targets.append(target_name)
    
    def add_batch(self, smiles_list, scores_list, target_name):
        for s, score in zip(smiles_list, scores_list):
            self.add(s, score, target_name)
    
    def sample(self, batch_size, prioritize_high_score=True):
        if len(self.buffer) < batch_size:
            return list(self.buffer), list(self.scores), list(self.targets)
        
        if prioritize_high_score:
            sorted_indices = np.argsort(self.scores)[:batch_size]
            return (
                [self.buffer[i] for i in sorted_indices],
                [self.scores[i] for i in sorted_indices],
                [self.targets[i] for i in sorted_indices]
            )
        else:
            indices = np.random.choice(len(self.buffer), batch_size, replace=False)
            return (
                [self.buffer[i] for i in indices],
                [self.scores[i] for i in indices],
                [self.targets[i] for i in indices]
            )
    
    def get_top_k(self, k, target_name=None):
        if target_name:
            filtered = [(i, s) for i, s, t in zip(self.buffer, self.scores, self.targets) if t == target_name]
            filtered.sort(key=lambda x: x[1])
            return [s for s, _ in filtered[:k]]
        else:
            indices = np.argsort(self.scores)[:k]
            return [self.buffer[i] for i in indices]
    
    def __len__(self):
        return len(self.buffer)
    
    def save(self, path='active_buffer.json'):
        data = {
            'smiles': list(self.buffer),
            'scores': list(self.scores),
            'targets': list(self.targets),
        }
        with open(path, 'w') as f:
            json.dump(data, f)
    
    def load(self, path='active_buffer.json'):
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            self.buffer = deque(data['smiles'], maxlen=self.capacity)
            self.scores = deque(data['scores'], maxlen=self.capacity)
            self.targets = deque(data['targets'], maxlen=self.capacity)
            return True
        return False


class AcquisitionFunction:
    def __init__(self, mode='expected_improvement'):
        self.mode = mode
    
    def score(self, predictions, uncertainties, best_so_far=None):
        if self.mode == 'expected_improvement':
            if best_so_far is None:
                best_so_far = np.min(predictions)
            
            ei = np.maximum(0, best_so_far - predictions)
            return ei
        
        elif self.mode == 'upper_confidence_bound':
            return predictions - 2.0 * uncertainties
        
        elif self.mode == 'uncertainty':
            return uncertainties
        
        elif self.mode == 'greedy':
            return -predictions
        
        else:
            return predictions
    
    def select(self, candidates, predictions, uncertainties, n_select, best_so_far=None):
        scores = self.score(predictions, uncertainties, best_so_far)
        top_indices = np.argsort(scores)[-n_select:]
        return [candidates[i] for i in top_indices], [predictions[i] for i in top_indices]


class ActiveLearningTrainer:
    def __init__(
        self,
        tokenizer,
        condition_dim=256,
        device='cpu',
        buffer_capacity=10000,
        docking_threshold=-7.0,
        sa_threshold=6.0
    ):
        self.tokenizer = tokenizer
        self.condition_dim = condition_dim
        self.device = device
        self.docking_threshold = docking_threshold
        self.sa_threshold = sa_threshold
        
        self.grammar = SmilesGrammar(tokenizer)
        self.grammar_decoder = ConditionalGrammarConstrainedDecoder(self.grammar)
        
        self.protein_encoder = ProteinCNNEncoder(
            vocab_size=22,
            embed_size=64,
            hidden_size=256,
            output_dim=condition_dim,
            max_len=500
        ).to(device)
        
        self.model = create_conditional_model(
            vocab_size=tokenizer.vocab_size,
            condition_dim=condition_dim,
            embed_size=256,
            hidden_size=512,
            latent_dim=256,
            num_layers=2,
            dropout=0.3
        ).to(device)
        
        self.docking_scorer = DockingScorer()
        self.buffer = ActiveLearningBuffer(capacity=buffer_capacity)
        self.acquisition = AcquisitionFunction()
        
        self.optimizer_g = optim.Adam(self.model.parameters(), lr=1e-3)
        self.optimizer_p = optim.Adam(self.protein_encoder.parameters(), lr=5e-4)
        
        self.iteration = 0
        self.best_docking_score = float('inf')
        self.training_history = []
    
    def encode_target_condition(self, target_name):
        target_info = TARGET_PROTEINS.get(target_name)
        if target_info is None:
            raise ValueError(f"Unknown target: {target_name}")
        
        encoded_seq = encode_protein_sequence(target_info['sequence'], max_len=500)
        x = torch.tensor([encoded_seq], dtype=torch.long, device=self.device)
        
        with torch.no_grad():
            condition = self.protein_encoder(x)
        
        return condition
    
    def generate_candidates(self, target_name, num_candidates=500, temperature=0.8):
        self.model.eval()
        self.protein_encoder.eval()
        
        condition = self.encode_target_condition(target_name)
        condition = condition.repeat(num_candidates, 1)
        
        with torch.no_grad():
            z = torch.randn(num_candidates, self.model.latent_dim).to(self.device)
            generated = self.grammar_decoder.decode_constrained(
                self.model, z, condition,
                max_len=120, temperature=temperature, device=self.device
            )
        
        generated_smiles = []
        for seq in generated:
            smiles = self.tokenizer.decode(seq.cpu().numpy())
            generated_smiles.append(smiles)
        
        return generated_smiles
    
    def filter_and_score(self, smiles_list, target_name):
        valid_smiles = filter_valid_molecules(smiles_list)
        
        scored = []
        for smiles in valid_smiles:
            sa_score = calculateSAScoreCached(smiles)
            if sa_score is None or sa_score > self.sa_threshold:
                continue
            
            docking_result = self.docking_scorer.score_target_affinity(smiles, target_name)
            if docking_result is None:
                continue
            
            if docking_result['docking_score'] <= self.docking_threshold:
                scored.append({
                    'smiles': smiles,
                    'docking_score': docking_result['docking_score'],
                    'sa_score': sa_score,
                    'qed': docking_result['qed_score'],
                })
        
        scored.sort(key=lambda x: x['docking_score'])
        return scored
    
    def select_for_synthesis(self, candidates, n_select=50):
        if len(candidates) == 0:
            return []
        
        smiles_list = [c['smiles'] for c in candidates]
        scores = np.array([c['docking_score'] for c in candidates])
        
        uncertainties = np.abs(scores - np.mean(scores)) / (np.std(scores) + 1e-8)
        
        selected, selected_scores = self.acquisition.select(
            smiles_list, scores, uncertainties, n_select,
            best_so_far=self.best_docking_score
        )
        
        return selected, selected_scores
    
    def simulate_synthesis_test(self, smiles_list, target_name):
        results = []
        for smiles in smiles_list:
            docking_result = self.docking_scorer.score_target_affinity(smiles, target_name)
            
            if docking_result:
                activity = np.clip(-docking_result['docking_score'] / 10.0, 0.1, 1.0)
                activity = activity + np.random.normal(0, 0.1)
                
                results.append({
                    'smiles': smiles,
                    'docking_score': docking_result['docking_score'],
                    'predicted_activity': activity,
                    'synthesis_success': np.random.random() > 0.2,
                })
            else:
                results.append({
                    'smiles': smiles,
                    'docking_score': None,
                    'predicted_activity': 0.0,
                    'synthesis_success': False,
                })
        
        return results
    
    def finetune_on_feedback(self, feedback_data, target_name, batch_size=32, epochs=3):
        self.model.train()
        self.protein_encoder.train()
        
        successful = [f for f in feedback_data if f['synthesis_success'] and f['docking_score'] is not None]
        
        if len(successful) < batch_size:
            return 0.0
        
        condition = self.encode_target_condition(target_name)
        
        total_loss = 0.0
        count = 0
        
        for epoch in range(epochs):
            random.shuffle(successful)
            
            for i in range(0, len(successful), batch_size):
                batch = successful[i:i+batch_size]
                smiles_batch = [f['smiles'] for f in batch]
                scores_batch = [f['docking_score'] for f in batch]
                
                encoded = [self.tokenizer.encode(s) for s in smiles_batch]
                x = torch.tensor(encoded, dtype=torch.long, device=self.device)
                
                batch_condition = condition.repeat(len(smiles_batch), 1)
                
                self.optimizer_g.zero_grad()
                self.optimizer_p.zero_grad()
                
                output, mu, logvar, z = self.model(x, batch_condition)
                
                target = x[:, 1:]
                vae_loss, _, _ = conditional_vae_loss(
                    output, target, mu, logvar, pad_idx=0, kl_weight=0.1
                )
                
                score_weights = torch.tensor(
                    [max(0.1, -s / 5.0) for s in scores_batch],
                    dtype=torch.float32, device=self.device
                )
                weighted_loss = (vae_loss * score_weights.mean())
                
                weighted_loss.backward()
                
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer_g.step()
                self.optimizer_p.step()
                
                total_loss += vae_loss.item()
                count += 1
        
        return total_loss / max(count, 1)
    
    def run_iteration(
        self,
        target_name='EGFR',
        num_candidates=500,
        n_select=50,
        finetune_epochs=3
    ):
        self.iteration += 1
        print(f"\n{'='*60}")
        print(f"Active Learning Iteration {self.iteration}")
        print(f"Target: {target_name}")
        print(f"{'='*60}")
        
        print(f"\n[1] Generating {num_candidates} candidates...")
        candidates = self.generate_candidates(target_name, num_candidates=num_candidates)
        print(f"   Generated {len(candidates)} molecules")
        
        print(f"\n[2] Filtering and scoring candidates...")
        scored = self.filter_and_score(candidates, target_name)
        print(f"   Valid molecules with good scores: {len(scored)}")
        
        if len(scored) == 0:
            print("   No valid candidates found. Skipping iteration.")
            return None
        
        if scored[0]['docking_score'] < self.best_docking_score:
            self.best_docking_score = scored[0]['docking_score']
            print(f"   New best docking score: {self.best_docking_score:.2f}")
        
        print(f"\n[3] Selecting {n_select} molecules for synthesis...")
        selected_smiles, selected_scores = self.select_for_synthesis(scored, n_select=n_select)
        print(f"   Selected {len(selected_smiles)} molecules")
        
        print(f"\n[4] Simulating synthesis and biological testing...")
        feedback = self.simulate_test(selected_smiles, target_name)
        
        successful = [f for f in feedback if f['synthesis_success']]
        print(f"   Successfully synthesized: {len(successful)}/{len(feedback)}")
        
        print(f"\n[5] Adding results to buffer...")
        for f in feedback:
            if f['docking_score'] is not None:
                self.buffer.add(f['smiles'], f['docking_score'], target_name)
        
        print(f"\n[6] Fine-tuning model on feedback...")
        avg_loss = self.finetune_on_feedback(feedback, target_name, epochs=finetune_epochs)
        print(f"   Average fine-tuning loss: {avg_loss:.4f}")
        
        iteration_result = {
            'iteration': self.iteration,
            'target': target_name,
            'num_candidates': num_candidates,
            'num_valid': len(scored),
            'num_selected': len(selected_smiles),
            'num_successful': len(successful),
            'best_score': self.best_docking_score,
            'avg_score': np.mean([f['docking_score'] for f in feedback if f['docking_score']]),
            'finetune_loss': avg_loss,
        }
        self.training_history.append(iteration_result)
        
        self._print_iteration_summary(iteration_result, scored[:5])
        
        return iteration_result
    
    def simulate_test(self, selected_smiles, target_name):
        return self.simulate_synthesis_test(selected_smiles, target_name)
    
    def _print_iteration_summary(self, result, top_samples):
        print(f"\n{'='*60}")
        print(f"Iteration {result['iteration']} Summary")
        print(f"{'='*60}")
        print(f"  Valid candidates: {result['num_valid']}")
        print(f"  Selected for synthesis: {result['num_selected']}")
        print(f"  Successfully synthesized: {result['num_successful']}")
        print(f"  Best docking score: {result['best_score']:.2f}")
        print(f"  Average docking score: {result['avg_score']:.2f}")
        
        if top_samples:
            print(f"\n  Top 5 molecules:")
            for i, sample in enumerate(top_samples):
                print(f"    {i+1}. Score: {sample['docking_score']:.2f}, SA: {sample['sa_score']:.2f}")
                print(f"       {sample['smiles'][:60]}..." if len(sample['smiles']) > 60 else f"       {sample['smiles']}")
        print(f"{'='*60}")
    
    def save(self, save_dir='active_checkpoints'):
        os.makedirs(save_dir, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'protein_encoder_state_dict': self.protein_encoder.state_dict(),
            'optimizer_g_state_dict': self.optimizer_g.state_dict(),
            'optimizer_p_state_dict': self.optimizer_p.state_dict(),
            'iteration': self.iteration,
            'best_docking_score': self.best_docking_score,
            'training_history': self.training_history,
        }, os.path.join(save_dir, 'active_model.pt'))
        
        self.buffer.save(os.path.join(save_dir, 'buffer.json'))
        
        self.docking_scorer.save_cache()
        save_sa_cache()
        
        with open(os.path.join(save_dir, 'history.json'), 'w') as f:
            json.dump(self.training_history, f, indent=2)
        
        print(f"\nSaved active learning state to {save_dir}")
    
    def load(self, load_dir='active_checkpoints'):
        model_path = os.path.join(load_dir, 'active_model.pt')
        if os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.protein_encoder.load_state_dict(checkpoint['protein_encoder_state_dict'])
            self.optimizer_g.load_state_dict(checkpoint['optimizer_g_state_dict'])
            self.optimizer_p.load_state_dict(checkpoint['optimizer_p_state_dict'])
            self.iteration = checkpoint['iteration']
            self.best_docking_score = checkpoint['best_docking_score']
            self.training_history = checkpoint.get('training_history', [])
            
            self.buffer.load(os.path.join(load_dir, 'buffer.json'))
            
            print(f"Loaded active learning state from {load_dir}")
            print(f"Current iteration: {self.iteration}")
            print(f"Best docking score: {self.best_docking_score:.2f}")
            return True
        return False
