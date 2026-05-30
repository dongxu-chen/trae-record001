from typing import Dict, List, Tuple, Set
from collections import defaultdict
from itertools import combinations
from models.schemas import Order


class AssociationRuleMiner:
    def __init__(self, orders: List[Order], min_support: float = 0.1, min_confidence: float = 0.5):
        self.orders = orders
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.transactions = self._build_transactions()
        self.frequent_itemsets = {}
        self.rules = []
    
    def _build_transactions(self) -> List[Set[str]]:
        transactions = []
        for order in self.orders:
            items = set(item.dish_id for item in order.items)
            transactions.append(items)
        return transactions
    
    def _calculate_support(self, itemset: Set[str]) -> float:
        count = 0
        for transaction in self.transactions:
            if itemset.issubset(transaction):
                count += 1
        return count / len(self.transactions) if len(self.transactions) > 0 else 0
    
    def _generate_candidates(self, itemsets: List[Set[str]], k: int) -> List[Set[str]]:
        candidates = []
        n = len(itemsets)
        for i in range(n):
            for j in range(i + 1, n):
                itemset1 = itemsets[i]
                itemset2 = itemsets[j]
                union = itemset1.union(itemset2)
                if len(union) == k and union not in candidates:
                    candidates.append(union)
        return candidates
    
    def apriori(self) -> Dict[int, List[Tuple[Set[str], float]]]:
        n_transactions = len(self.transactions)
        if n_transactions == 0:
            return {}
        
        single_items = set()
        for transaction in self.transactions:
            single_items.update(transaction)
        
        itemsets_k = []
        for item in single_items:
            itemset = {item}
            support = self._calculate_support(itemset)
            if support >= self.min_support:
                itemsets_k.append(itemset)
                self.frequent_itemsets[1] = self.frequent_itemsets.get(1, []) + [(itemset, support)]
        
        k = 2
        while itemsets_k:
            candidates = self._generate_candidates(itemsets_k, k)
            itemsets_k = []
            
            for candidate in candidates:
                support = self._calculate_support(candidate)
                if support >= self.min_support:
                    itemsets_k.append(candidate)
                    self.frequent_itemsets[k] = self.frequent_itemsets.get(k, []) + [(candidate, support)]
            
            k += 1
        
        return self.frequent_itemsets
    
    def generate_rules(self) -> List[Tuple[Set[str], Set[str], float, float]]:
        if not self.frequent_itemsets:
            self.apriori()
        
        self.rules = []
        
        for k, itemsets in self.frequent_itemsets.items():
            if k < 2:
                continue
            
            for itemset, support in itemsets:
                for i in range(1, k):
                    for antecedent in combinations(itemset, i):
                        antecedent_set = set(antecedent)
                        consequent = itemset - antecedent_set
                        
                        if len(consequent) == 0:
                            continue
                        
                        antecedent_support = 0
                        for itemset_b, supp_b in self.frequent_itemsets.get(len(antecedent_set), []):
                            if itemset_b == antecedent_set:
                                antecedent_support = supp_b
                                break
                        
                        if antecedent_support > 0:
                            confidence = support / antecedent_support
                            if confidence >= self.min_confidence:
                                lift = confidence / self._calculate_support(consequent) if self._calculate_support(consequent) > 0 else 0
                                self.rules.append((antecedent_set, consequent, confidence, lift))
        
        self.rules.sort(key=lambda x: x[2], reverse=True)
        return self.rules
    
    def get_associated_dishes(self, dish_ids: List[str], top_n: int = 5) -> List[Tuple[str, float, float]]:
        if not self.rules:
            self.generate_rules()
        
        dish_set = set(dish_ids)
        associations = []
        
        for antecedent, consequent, confidence, lift in self.rules:
            if antecedent.issubset(dish_set):
                for dish in consequent:
                    if dish not in dish_set:
                        associations.append((dish, confidence, lift))
        
        dish_scores = {}
        for dish, conf, lift in associations:
            if dish not in dish_scores or conf > dish_scores[dish][0]:
                dish_scores[dish] = (conf, lift)
        
        result = [(dish, scores[0], scores[1]) for dish, scores in dish_scores.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:top_n]
    
    def get_frequent_combinations(self, k: int = 2, top_n: int = 10) -> List[Tuple[Set[str], float]]:
        if not self.frequent_itemsets:
            self.apriori()
        
        itemsets = self.frequent_itemsets.get(k, [])
        itemsets.sort(key=lambda x: x[1], reverse=True)
        return itemsets[:top_n]
    
    def get_recommendations_for_cart(self, cart_dish_ids: List[str], top_n: int = 5) -> List[Tuple[str, float, str]]:
        if len(cart_dish_ids) == 0:
            return []
        
        associations = self.get_associated_dishes(cart_dish_ids, top_n=top_n * 2)
        
        result = []
        for dish_id, confidence, lift in associations[:top_n]:
            reason = self._generate_reason(cart_dish_ids, dish_id, confidence)
            result.append((dish_id, confidence, reason))
        
        return result
    
    def _generate_reason(self, cart_items: List[str], recommended_dish: str, confidence: float) -> str:
        confidence_pct = int(confidence * 100)
        if confidence_pct >= 80:
            strength = "非常受欢迎的"
        elif confidence_pct >= 60:
            strength = "很受欢迎的"
        else:
            strength = "常见的"
        
        return f"这是与您已选菜品{strength}搭配选择"
    
    def get_group_order_suggestions(self, num_people: int, top_n: int = 10) -> List[Tuple[Set[str], float, int]]:
        if not self.frequent_itemsets:
            self.apriori()
        
        target_size = max(2, min(int(num_people * 1.5), 6))
        suggestions = []
        
        for k in range(max(2, target_size - 1), min(target_size + 2, 7)):
            itemsets = self.frequent_itemsets.get(k, [])
            for itemset, support in itemsets:
                suggestions.append((itemset, support, k))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:top_n]
