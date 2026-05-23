from collections import deque
import torch
import torch.nn.functional as F


class SmilesGrammar:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.token2idx = tokenizer.token2idx
        self.idx2token = tokenizer.idx2token
        self.vocab_size = tokenizer.vocab_size
        
        self.atom_tokens = set()
        self.bond_tokens = set()
        self.number_tokens = set()
        self.special_tokens = set()
        
        for token in tokenizer.atom_tokens:
            if token in self.token2idx:
                self.atom_tokens.add(self.token2idx[token])
        
        for token in tokenizer.bond_tokens:
            if token in self.token2idx:
                self.bond_tokens.add(self.token2idx[token])
        
        for token in tokenizer.number_tokens:
            if token in self.token2idx:
                self.number_tokens.add(self.token2idx[token])
        
        for token in tokenizer.special_tokens:
            if token in self.token2idx:
                self.special_tokens.add(self.token2idx[token])
        
        self.lparen = self.token2idx.get('(', -1)
        self.rparen = self.token2idx.get(')', -1)
        self.lbracket = self.token2idx.get('[', -1)
        self.rbracket = self.token2idx.get(']', -1)
        self.start_token = self.token2idx.get('<start>', 1)
        self.end_token = self.token2idx.get('<end>', 2)
        self.pad_token = self.token2idx.get('<pad>', 0)
        
        self.branch_tokens = {self.lparen, self.rparen}
        self.bracket_tokens = {self.lbracket, self.rbracket}
        
    def get_initial_mask(self):
        mask = [0.0] * self.vocab_size
        
        for token_idx in self.atom_tokens:
            mask[token_idx] = 1.0
        
        if self.lbracket >= 0:
            mask[self.lbracket] = 1.0
        
        return mask
    
    def update_state(self, state, next_token):
        new_state = state.copy()
        
        token = self.idx2token.get(int(next_token), '<unk>')
        
        if next_token == self.lparen:
            new_state['paren_stack'].append('(')
            new_state['expect_atom'] = True
            new_state['expect_bond'] = False
            
        elif next_token == self.rparen:
            if new_state['paren_stack']:
                new_state['paren_stack'].pop()
            new_state['expect_atom'] = False
            new_state['expect_bond'] = True
            
        elif next_token == self.lbracket:
            new_state['in_bracket'] = True
            new_state['bracket_stack'].append('[')
            new_state['expect_atom'] = True
            new_state['expect_bond'] = False
            
        elif next_token == self.rbracket:
            if new_state['bracket_stack']:
                new_state['bracket_stack'].pop()
            new_state['in_bracket'] = False
            new_state['expect_atom'] = False
            new_state['expect_bond'] = True
            
        elif next_token in self.atom_tokens:
            new_state['last_was_atom'] = True
            new_state['last_was_bond'] = False
            new_state['last_was_number'] = False
            new_state['expect_atom'] = False
            new_state['expect_bond'] = True
            new_state['num_atoms'] += 1
            
        elif next_token in self.bond_tokens:
            new_state['last_was_atom'] = False
            new_state['last_was_bond'] = True
            new_state['last_was_number'] = False
            new_state['expect_atom'] = True
            new_state['expect_bond'] = False
            
        elif next_token in self.number_tokens:
            num = int(token)
            if num in new_state['open_rings']:
                new_state['open_rings'].remove(num)
            else:
                new_state['open_rings'].add(num)
            new_state['last_was_number'] = True
            new_state['expect_atom'] = False
            new_state['expect_bond'] = True
            
        return new_state
    
    def get_allowed_tokens(self, state):
        mask = [0.0] * self.vocab_size
        
        mask[self.end_token] = 1.0
        
        if state['expect_atom']:
            for token_idx in self.atom_tokens:
                mask[token_idx] = 1.0
            if self.lbracket >= 0 and not state['in_bracket']:
                mask[self.lbracket] = 1.0
                
        elif state['in_bracket']:
            for token_idx in self.atom_tokens:
                mask[token_idx] = 1.0
            if self.rbracket >= 0 and len(state['bracket_stack']) > 0:
                mask[self.rbracket] = 1.0
            if state.get('bracket_has_atom', False):
                if self.rbracket >= 0 and len(state['bracket_stack']) > 0:
                    mask[self.rbracket] = 1.0
                    
        elif state['last_was_atom'] or state['last_was_number']:
            for token_idx in self.bond_tokens:
                mask[token_idx] = 1.0
            
            if self.lparen >= 0 and len(state['paren_stack']) < 5:
                mask[self.lparen] = 1.0
            
            if self.rparen >= 0 and len(state['paren_stack']) > 0:
                mask[self.rparen] = 1.0
            
            if len(state['open_rings']) < 3 and state['num_atoms'] > 1:
                for token_idx in self.number_tokens:
                    mask[token_idx] = 1.0
                    
        elif state['last_was_bond']:
            for token_idx in self.atom_tokens:
                mask[token_idx] = 1.0
            if self.lbracket >= 0:
                mask[self.lbracket] = 1.0
                
        if state['num_atoms'] == 0:
            for token_idx in self.atom_tokens:
                mask[token_idx] = 1.0
            if self.lbracket >= 0:
                mask[self.lbracket] = 1.0
            mask[self.end_token] = 0.0
            
        if state['num_atoms'] >= 60:
            for token_idx in self.atom_tokens:
                mask[token_idx] = 0.0
            for token_idx in self.bond_tokens:
                mask[token_idx] = 0.0
            if self.lparen >= 0:
                mask[self.lparen] = 0.0
            if self.lbracket >= 0:
                mask[self.lbracket] = 0.0
            mask[self.end_token] = 1.0
            
        if len(state['open_rings']) > 0 and state['num_atoms'] > 2:
            for num in state['open_rings']:
                num_str = str(num)
                if num_str in self.token2idx:
                    mask[self.token2idx[num_str]] = 1.0
                    
        mask[self.pad_token] = 0.0
        mask[self.start_token] = 0.0
        
        return mask
    
    def get_initial_state(self):
        return {
            'paren_stack': deque(),
            'bracket_stack': deque(),
            'open_rings': set(),
            'in_bracket': False,
            'last_was_atom': False,
            'last_was_bond': False,
            'last_was_number': False,
            'expect_atom': True,
            'expect_bond': False,
            'num_atoms': 0,
            'bracket_has_atom': False
        }


class GrammarConstrainedDecoder:
    def __init__(self, grammar):
        self.grammar = grammar
        
    def decode_constrained(self, model, z, max_len=120, temperature=1.0, device='cpu'):
        batch_size = z.size(0)
        vocab_size = self.grammar.vocab_size
        
        generated = [[self.grammar.start_token] for _ in range(batch_size)]
        states = [self.grammar.get_initial_state() for _ in range(batch_size)]
        finished = [False] * batch_size
        
        h = model.decoder.fc_z(z)
        h = h.view(model.decoder.num_layers, batch_size, model.decoder.hidden_size).contiguous()
        
        for t in range(1, max_len):
            all_finished = all(finished)
            if all_finished:
                break
                
            input_tokens = torch.tensor(
                [[g[-1]] for g in generated], 
                dtype=torch.long, 
                device=device
            )
            
            x = model.decoder.embedding(input_tokens)
            x = model.decoder.dropout(x)
            
            output, h_new = model.decoder.gru(x, h)
            logits = model.decoder.fc_out(output)
            logits = logits[:, -1, :] / temperature
            
            for i in range(batch_size):
                if finished[i]:
                    continue
                    
                mask = torch.tensor(
                    self.grammar.get_allowed_tokens(states[i]), 
                    dtype=torch.float32, 
                    device=device
                )
                
                logits[i] = logits[i] * mask - 1e9 * (1 - mask)
            
            probs = F.softmax(logits, dim=-1)
            next_tokens = torch.multinomial(probs, 1).squeeze(1)
            
            for i in range(batch_size):
                if finished[i]:
                    generated[i].append(self.grammar.pad_token)
                    continue
                    
                next_token = int(next_tokens[i])
                generated[i].append(next_token)
                
                if next_token == self.grammar.end_token:
                    finished[i] = True
                else:
                    states[i] = self.grammar.update_state(states[i], next_token)
            
            h = h_new
        
        max_gen_len = max(len(g) for g in generated)
        for i in range(batch_size):
            while len(generated[i]) < max_len:
                generated[i].append(self.grammar.pad_token)
                
        return torch.tensor(generated, dtype=torch.long, device=device)
