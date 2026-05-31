import random
from typing import Dict, List, Any, Optional, Iterator
from config import (
    EDGE_CASE_VALUES,
    SQL_INJECTION_PAYLOADS,
    XSS_PAYLOADS,
    COMMAND_INJECTION_PAYLOADS,
    PATH_TRAVERSAL_PAYLOADS
)


class ParameterGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.injection_payloads = {
            'sql': SQL_INJECTION_PAYLOADS,
            'xss': XSS_PAYLOADS,
            'command': COMMAND_INJECTION_PAYLOADS,
            'path': PATH_TRAVERSAL_PAYLOADS,
            'all': (SQL_INJECTION_PAYLOADS + XSS_PAYLOADS + 
                    COMMAND_INJECTION_PAYLOADS + PATH_TRAVERSAL_PAYLOADS)
        }
        
        self.edge_cases = EDGE_CASE_VALUES

    def generate_edge_cases(self, param_type: str) -> List[Any]:
        return self.edge_cases.get(param_type, self.edge_cases['string']).copy()

    def generate_injection_payloads(self, injection_type: str = 'all') -> List[str]:
        return self.injection_payloads.get(injection_type, []).copy()

    def generate_type_mismatch(self, param_type: str) -> List[Any]:
        mismatch_map = {
            'string': [123, 0, None, True, [], {}, 3.14],
            'integer': ["abc", "", None, True, [], {}, "123abc"],
            'number': ["abc", "", None, True, [], {}, "123.45abc"],
            'boolean': ["true", 123, None, [], {}, "yes"],
            'array': ["string", 123, None, True, {}, "[]"],
            'object': ["string", 123, None, True, [], "{}"],
            'date': ["not-a-date", 123, None, True, [], {}],
            'email': [123, None, True, [], {}],
            'url': [123, None, True, [], {}]
        }
        return mismatch_map.get(param_type, self.edge_cases['string']).copy()

    def generate_values(
        self,
        param_name: str,
        param_type: str = 'string',
        include_edge_cases: bool = True,
        include_injections: bool = True,
        include_type_mismatch: bool = True,
        injection_types: List[str] = None,
        custom_values: List[Any] = None,
        max_values: int = 50
    ) -> List[Dict[str, Any]]:
        values = []
        
        if custom_values:
            for val in custom_values:
                values.append({
                    'param_name': param_name,
                    'value': val,
                    'type': 'custom',
                    'description': f'Custom value: {val}'
                })
        
        if include_edge_cases:
            for val in self.generate_edge_cases(param_type):
                values.append({
                    'param_name': param_name,
                    'value': val,
                    'type': 'edge_case',
                    'description': f'Edge case for {param_type}: {repr(val)}'
                })
        
        if include_type_mismatch:
            for val in self.generate_type_mismatch(param_type):
                values.append({
                    'param_name': param_name,
                    'value': val,
                    'type': 'type_mismatch',
                    'description': f'Type mismatch: {repr(val)} expected {param_type}'
                })
        
        if include_injections:
            injection_types = injection_types or ['all']
            for inj_type in injection_types:
                for payload in self.generate_injection_payloads(inj_type):
                    values.append({
                        'param_name': param_name,
                        'value': payload,
                        'type': f'injection_{inj_type}',
                        'description': f'{inj_type.upper()} injection payload'
                    })
        
        if len(values) > max_values:
            values = values[:max_values]
        
        return values

    def generate_param_combinations(
        self,
        api_params: List[Dict[str, Any]],
        test_mode: str = 'single',
        max_combinations: int = 100
    ) -> Iterator[Dict[str, Any]]:
        if test_mode == 'single':
            for param_config in api_params:
                name = param_config['name']
                ptype = param_config.get('type', 'string')
                default = param_config.get('default', '')
                required = param_config.get('required', False)
                
                base_params = {}
                for p in api_params:
                    if p['name'] != name:
                        base_params[p['name']] = p.get('default', '')
                
                test_values = self.generate_values(
                    param_name=name,
                    param_type=ptype,
                    custom_values=param_config.get('custom_values')
                )
                
                for val_info in test_values:
                    params = base_params.copy()
                    params[name] = val_info['value']
                    yield {
                        'params': params,
                        'tested_param': name,
                        'value_info': val_info
                    }
        
        elif test_mode == 'exhaustive':
            all_values = []
            for param_config in api_params:
                name = param_config['name']
                ptype = param_config.get('type', 'string')
                vals = self.generate_values(
                    param_name=name,
                    param_type=ptype,
                    custom_values=param_config.get('custom_values'),
                    max_values=5
                )
                all_values.append([(name, v['value'], v) for v in vals])
            
            from itertools import product
            count = 0
            for combo in product(*all_values):
                if count >= max_combinations:
                    break
                params = {}
                tested_params = []
                value_infos = []
                for name, val, info in combo:
                    params[name] = val
                    tested_params.append(name)
                    value_infos.append(info)
                
                yield {
                    'params': params,
                    'tested_param': ', '.join(tested_params),
                    'value_info': value_infos[0] if value_infos else None
                }
                count += 1
        
        elif test_mode == 'targeted':
            for param_config in api_params:
                name = param_config['name']
                ptype = param_config.get('type', 'string')
                injection_type = param_config.get('injection_type', 'all')
                
                base_params = {}
                for p in api_params:
                    if p['name'] != name:
                        base_params[p['name']] = p.get('default', '')
                
                injections = self.generate_injection_payloads(injection_type)
                for payload in injections:
                    params = base_params.copy()
                    params[name] = payload
                    yield {
                        'params': params,
                        'tested_param': name,
                        'value_info': {
                            'param_name': name,
                            'value': payload,
                            'type': f'injection_{injection_type}',
                            'description': f'Targeted {injection_type} injection'
                        }
                    }

    def generate_random_value(self, param_type: str = 'string') -> Any:
        edge_cases = self.generate_edge_cases(param_type)
        return random.choice(edge_cases) if edge_cases else ''
