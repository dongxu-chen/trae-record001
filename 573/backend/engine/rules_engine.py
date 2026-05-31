import asyncio
import yaml
import logging
from typing import Dict, List, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    description: str
    severity: str
    category: str
    passed: bool
    remediation: str

class RulesEngine:
    def __init__(self, rules_file: str):
        self.rules_file = rules_file
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.rules = config.get('rules', [])
                
            for rule in self.rules:
                try:
                    exec_globals = {}
                    exec(rule['check'], exec_globals)
                    rule['check_func'] = exec_globals.get('check')
                except Exception as e:
                    logger.warning(f"Failed to load rule {rule['id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")

    async def evaluate_image(self, image_config: Dict, image_name: str = "") -> Dict[str, Any]:
        results = []
        image_config = image_config or {}
        
        if isinstance(image_config, dict) and 'Config' in image_config:
            config_data = image_config
        else:
            config_data = {'Config': image_config or {}, 'history': []}

        for rule in self.rules:
            try:
                check_func = rule.get('check_func')
                if check_func:
                    has_issue = check_func(config_data)
                    
                    results.append({
                        "rule_id": rule['id'],
                        "rule_name": rule['name'],
                        "description": rule['description'],
                        "severity": rule['severity'].upper(),
                        "category": rule['category'],
                        "passed": not has_issue,
                        "remediation": rule.get('remediation', ''),
                        "has_issue": has_issue
                    })
            except Exception as e:
                logger.error(f"Error evaluating rule {rule['id']}: {e}")
                results.append({
                    "rule_id": rule['id'],
                    "rule_name": rule['name'],
                    "description": rule['description'],
                    "severity": rule['severity'].upper(),
                    "category": rule['category'],
                    "passed": True,
                    "remediation": rule.get('remediation', ''),
                    "error": str(e)
                })

        return {
            "results": results,
            "summary": self._summarize_results(results)
        }

    def _summarize_results(self, results: List[Dict]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        failed = total - passed
        
        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        by_category = {}
        
        for r in results:
            if not r['passed']:
                sev = r['severity'].upper()
                if sev in by_severity:
                    by_severity[sev] += 1
                else:
                    by_severity["LOW"] += 1
                
                cat = r['category']
                by_category[cat] = by_category.get(cat, 0) + 1

        risk_score = self._calculate_risk_score(results)

        return {
            "total_rules": total,
            "passed": passed,
            "failed": failed,
            "by_severity": by_severity,
            "by_category": by_category,
            "risk_score": risk_score
        }

    def _calculate_risk_score(self, results: List[Dict]) -> float:
        weights = {
            "CRITICAL": 10,
            "HIGH": 5,
            "MEDIUM": 2,
            "LOW": 1
        }
        
        score = 0.0
        max_score = 0.0
        
        for r in results:
            sev = r['severity'].upper()
            weight = weights.get(sev, 1)
            max_score += weight
            if not r['passed']:
                score += weight
        
        if max_score > 0:
            return round((score / max_score) * 100, 2)
        return 0.0

    def get_rule(self, rule_id: str) -> Dict:
        for rule in self.rules:
            if rule['id'] == rule_id:
                return rule
        return None

    def list_rules(self) -> List[Dict]:
        return [
            {
                "id": r['id'],
                "name": r['name'],
                "description": r['description'],
                "severity": r['severity'],
                "category": r['category']
            }
            for r in self.rules
        ]

class ImageAnalyzer:
    @staticmethod
    def check_latest_tag(config: Dict) -> bool:
        history = config.get('history', [])
        for layer in history:
            cmd = layer.get('CreatedBy', '')
            if 'FROM' in cmd and ':latest' in cmd:
                return True
        return False

    @staticmethod
    def extract_base_image(config: Dict) -> str:
        history = config.get('history', [])
        for layer in history:
            cmd = layer.get('CreatedBy', '')
            if cmd.startswith('FROM '):
                return cmd.split(' ')[1]
        return "unknown"

    @staticmethod
    def get_layer_count(config: Dict) -> int:
        return len(config.get('history', []))
