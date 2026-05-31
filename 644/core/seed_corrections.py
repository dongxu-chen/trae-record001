import os

class SeedCorrections:
    def __init__(self, seed_path):
        self.seed_path = seed_path
        self.corrections = {}
        self.load_seed_corrections()
    
    def load_seed_corrections(self):
        if not os.path.exists(self.seed_path):
            return
        
        with open(self.seed_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    wrong = parts[0].strip()
                    correct = parts[1].strip()
                    weight = int(parts[2].strip()) if len(parts) >= 3 and parts[2].strip().isdigit() else 80
                    
                    if wrong not in self.corrections:
                        self.corrections[wrong] = []
                    self.corrections[wrong].append((correct, weight))
        
        for key in self.corrections:
            self.corrections[key].sort(key=lambda x: -x[1])
    
    def get_correction(self, query):
        if query in self.corrections:
            return self.corrections[query]
        return []
    
    def exact_match(self, query):
        return query in self.corrections
    
    def fuzzy_match(self, query, edit_distance_func, max_distance=1):
        matches = []
        for wrong, corrections in self.corrections.items():
            distance = edit_distance_func(query, wrong)
            if distance <= max_distance:
                for correct, weight in corrections:
                    matches.append((correct, distance, weight))
        matches.sort(key=lambda x: (x[1], -x[2]))
        return matches
    
    def add_correction(self, wrong, correct, weight=80):
        if wrong not in self.corrections:
            self.corrections[wrong] = []
        self.corrections[wrong].append((correct, weight))
        self.corrections[wrong].sort(key=lambda x: -x[1])
        self.save_seed_corrections()
    
    def save_seed_corrections(self):
        with open(self.seed_path, 'w', encoding='utf-8') as f:
            for wrong, corrections in self.corrections.items():
                for correct, weight in corrections:
                    f.write(f"{wrong},{correct},{weight}\n")
    
    def get_all_seeds(self):
        return self.corrections
