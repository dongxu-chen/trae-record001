import re
import json
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ParamDependency:
    source_param: str
    target_param: str
    relation_type: str = 'direct'
    transform: Optional[Callable[[Any], Any]] = None
    condition: Optional[Dict[str, Any]] = None
    
    def __repr__(self):
        return f"{self.source_param} -> {self.target_param} ({self.relation_type})"


@dataclass
class ParamGraphNode:
    param_name: str
    param_type: str = 'string'
    default_value: Any = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    group: Optional[str] = None
    
    def __repr__(self):
        return f"Node({self.param_name}, type={self.param_type})"


@dataclass
class Dependency:
    source_step: str
    source_path: str
    target_param: str
    transform: Optional[Callable[[Any], Any]] = None
    
    def resolve(self, context: Dict[str, Any]) -> Any:
        value = self._extract_value(context.get(self.source_step, {}), self.source_path)
        if self.transform:
            value = self.transform(value)
        return value
    
    def _extract_value(self, data: Any, path: str) -> Any:
        parts = path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict):
                if '[' in part and ']' in part:
                    key, idx = part[:-1].split('[')
                    current = current.get(key, [])
                    try:
                        current = current[int(idx)]
                    except (IndexError, ValueError):
                        return None
                else:
                    current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (IndexError, ValueError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current


@dataclass
class StepResult:
    step_name: str
    success: bool
    response: Any = None
    error: Optional[str] = None
    extracted_data: Dict[str, Any] = field(default_factory=dict)


class ParameterGraph:
    def __init__(self):
        self.nodes: Dict[str, ParamGraphNode] = {}
        self.edges: List[ParamDependency] = []
    
    def add_node(self, param_name: str, param_type: str = 'string', 
                 default_value: Any = None, group: Optional[str] = None,
                 constraints: Optional[Dict[str, Any]] = None) -> None:
        if param_name not in self.nodes:
            self.nodes[param_name] = ParamGraphNode(
                param_name=param_name,
                param_type=param_type,
                default_value=default_value,
                group=group,
                constraints=constraints or {}
            )
    
    def add_dependency(self, source_param: str, target_param: str, 
                       relation_type: str = 'direct',
                       condition: Optional[Dict[str, Any]] = None,
                       transform: Optional[Callable[[Any], Any]] = None) -> None:
        if source_param not in self.nodes:
            self.add_node(source_param)
        if target_param not in self.nodes:
            self.add_node(target_param)
        
        if source_param not in self.nodes[target_param].dependencies:
            self.nodes[target_param].dependencies.append(source_param)
        if target_param not in self.nodes[source_param].dependents:
            self.nodes[source_param].dependents.append(target_param)
        
        self.edges.append(ParamDependency(
            source_param=source_param,
            target_param=target_param,
            relation_type=relation_type,
            condition=condition,
            transform=transform
        ))
    
    def get_root_params(self) -> List[str]:
        return [name for name, node in self.nodes.items() if not node.dependencies]
    
    def get_leaf_params(self) -> List[str]:
        return [name for name, node in self.nodes.items() if not node.dependents]
    
    def get_param_group(self, param_name: str) -> Set[str]:
        if param_name not in self.nodes:
            return set()
        
        group = set()
        queue = deque([param_name])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            group.add(current)
            
            node = self.nodes.get(current)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        queue.append(dep)
                for dep in node.dependents:
                    if dep not in visited:
                        queue.append(dep)
        
        return group
    
    def topological_sort(self) -> List[str]:
        in_degree = {name: len(node.dependencies) for name, node in self.nodes.items()}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for dependent in self.nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.nodes):
            cycle_params = [name for name, degree in in_degree.items() if degree > 0]
            raise ValueError(f"Circular dependency detected involving: {cycle_params}")
        
        return result
    
    def traverse_bfs(self, start_param: Optional[str] = None) -> List[str]:
        if start_param:
            if start_param not in self.nodes:
                return []
            starts = [start_param]
        else:
            starts = self.get_root_params()
        
        visited = set()
        order = []
        queue = deque(starts)
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            order.append(current)
            
            for dependent in self.nodes[current].dependents:
                if dependent not in visited:
                    queue.append(dependent)
        
        return order
    
    def traverse_dfs(self, start_param: Optional[str] = None, 
                     visited: Optional[Set[str]] = None,
                     order: Optional[List[str]] = None) -> List[str]:
        if visited is None:
            visited = set()
        if order is None:
            order = []
        
        if start_param:
            starts = [start_param]
        else:
            starts = self.get_root_params()
        
        for current in starts:
            if current in visited:
                continue
            visited.add(current)
            
            for dependent in self.nodes[current].dependents:
                self.traverse_dfs(dependent, visited, order)
            
            order.append(current)
        
        return order
    
    def generate_related_tests(self, param_name: str, test_value: Any) -> Dict[str, Any]:
        if param_name not in self.nodes:
            return {param_name: test_value}
        
        result = {param_name: test_value}
        group = self.get_param_group(param_name)
        group.discard(param_name)
        
        for related_param in group:
            node = self.nodes[related_param]
            result[related_param] = self._generate_coordinated_value(
                related_param, param_name, test_value, node
            )
        
        return result
    
    def _generate_coordinated_value(self, target_param: str, 
                                     source_param: str, source_value: Any,
                                     target_node: ParamGraphNode) -> Any:
        for edge in self.edges:
            if edge.source_param == source_param and edge.target_param == target_param:
                if edge.transform:
                    return edge.transform(source_value)
                if edge.relation_type == 'same':
                    return source_value
                if edge.relation_type == 'inverse':
                    if isinstance(source_value, bool):
                        return not source_value
                    if isinstance(source_value, (int, float)):
                        return -source_value
                if edge.relation_type == 'derived':
                    return self._apply_derived_relation(source_value, edge.condition)
                break
        
        if target_node.constraints.get('min') is not None:
            return target_node.constraints['min']
        if target_node.constraints.get('max') is not None:
            return target_node.constraints['max']
        
        return target_node.default_value
    
    def _apply_derived_relation(self, source_value: Any, condition: Optional[Dict[str, Any]]) -> Any:
        if not condition:
            return source_value
        
        if condition.get('type') == 'length':
            if isinstance(source_value, str):
                return len(source_value)
            if isinstance(source_value, (list, dict)):
                return len(source_value)
        
        if condition.get('type') == 'format':
            fmt = condition.get('format', '{}')
            return fmt.format(source_value)
        
        if condition.get('type') == 'concat':
            prefix = condition.get('prefix', '')
            suffix = condition.get('suffix', '')
            return f"{prefix}{source_value}{suffix}"
        
        return source_value
    
    def find_dependency_paths(self, source_param: str, target_param: str) -> List[List[str]]:
        if source_param not in self.nodes or target_param not in self.nodes:
            return []
        
        paths = []
        
        def dfs(current: str, path: List[str]):
            if current == target_param:
                paths.append(path.copy())
                return
            
            for dependent in self.nodes[current].dependents:
                if dependent not in path:
                    path.append(dependent)
                    dfs(dependent, path)
                    path.pop()
        
        dfs(source_param, [source_param])
        return paths
    
    def detect_cycles(self) -> List[List[str]]:
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(param: str):
            if param in rec_stack:
                idx = path.index(param)
                cycles.append(path[idx:].copy())
                return
            
            if param in visited:
                return
            
            visited.add(param)
            rec_stack.add(param)
            path.append(param)
            
            for dependent in self.nodes[param].dependents:
                dfs(dependent)
            
            path.pop()
            rec_stack.remove(param)
        
        for param in self.nodes:
            if param not in visited:
                dfs(param)
        
        return cycles
    
    def get_all_paths(self) -> List[List[str]]:
        all_paths = []
        roots = self.get_root_params()
        
        for root in roots:
            paths = []
            
            def dfs(current: str, path: List[str]):
                path.append(current)
                
                if not self.nodes[current].dependents:
                    paths.append(path.copy())
                else:
                    for dependent in self.nodes[current].dependents:
                        dfs(dependent, path)
                
                path.pop()
            
            dfs(root, [])
            all_paths.extend(paths)
        
        return all_paths
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': {
                name: {
                    'param_type': node.param_type,
                    'default_value': node.default_value,
                    'dependencies': node.dependencies,
                    'dependents': node.dependents,
                    'constraints': node.constraints,
                    'group': node.group
                }
                for name, node in self.nodes.items()
            },
            'edges': [
                {
                    'source': edge.source_param,
                    'target': edge.target_param,
                    'relation_type': edge.relation_type
                }
                for edge in self.edges
            ]
        }


class DependencyResolver:
    def __init__(self):
        self.dependencies: List[Dependency] = []
        self.context: Dict[str, StepResult] = {}
        self.extract_rules: Dict[str, str] = {}
        self.param_graph = ParameterGraph()
    
    def add_dependency(self, dependency: Dependency) -> None:
        self.dependencies.append(dependency)
    
    def add_extract_rule(self, step_name: str, json_path: str, alias: str) -> None:
        self.extract_rules[f"{step_name}.{alias}"] = json_path
    
    def set_step_result(self, step_result: StepResult) -> None:
        self.context[step_result.step_name] = step_result
        
        for rule_key, json_path in self.extract_rules.items():
            if rule_key.startswith(f"{step_result.step_name}."):
                alias = rule_key.split('.', 1)[1]
                extracted = self._extract_by_jsonpath(step_result.response, json_path)
                if extracted is not None:
                    step_result.extracted_data[alias] = extracted
    
    def _extract_by_jsonpath(self, data: Any, jsonpath: str) -> Any:
        if jsonpath.startswith('$'):
            jsonpath = jsonpath[1:]
        if jsonpath.startswith('.'):
            jsonpath = jsonpath[1:]
        
        parts = re.split(r'\.|\[', jsonpath)
        current = data
        
        for part in parts:
            if not part:
                continue
            part = part.rstrip(']')
            
            if isinstance(current, dict):
                if part.isdigit():
                    keys = list(current.keys())
                    idx = int(part)
                    if idx < len(keys):
                        current = current[keys[idx]]
                    else:
                        return None
                else:
                    current = current.get(part)
            elif isinstance(current, list):
                if part == '*':
                    return current
                try:
                    current = current[int(part)]
                except (IndexError, ValueError):
                    return None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def resolve_params(self, target_params: Dict[str, Any]) -> Dict[str, Any]:
        resolved = target_params.copy()
        
        for key, value in resolved.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                expression = value[2:-1]
                resolved[key] = self._resolve_expression(expression)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_params(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_params(item) if isinstance(item, dict)
                    else (self._resolve_expression(item[2:-1]) if isinstance(item, str) and item.startswith('${') and item.endswith('}') else item)
                    for item in value
                ]
        
        return resolved
    
    def _resolve_expression(self, expression: str) -> Any:
        if ':' in expression:
            step_ref, path = expression.split(':', 1)
        else:
            step_ref, path = expression, ''
        
        step_result = self.context.get(step_ref)
        if not step_result or not step_result.success:
            return f"__UNRESOLVED__:{expression}"
        
        if path.startswith('extracted.'):
            return step_result.extracted_data.get(path[10:], f"__UNRESOLVED__:{expression}")
        
        if path:
            return self._extract_by_jsonpath(step_result.response, path)
        
        return step_result.response
    
    def get_execution_order(self, steps: List[Dict[str, Any]]) -> List[str]:
        graph = {}
        in_degree = {}
        
        for step in steps:
            step_name = step['name']
            graph[step_name] = []
            in_degree[step_name] = 0
        
        for step in steps:
            step_name = step['name']
            params = step.get('params', {})
            deps = self._find_dependencies(params)
            
            for dep in deps:
                if dep in graph and step_name not in graph[dep]:
                    graph[dep].append(step_name)
                    in_degree[step_name] += 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(steps):
            return [step['name'] for step in steps]
        
        return result
    
    def _find_dependencies(self, params: Any, deps: set = None) -> set:
        if deps is None:
            deps = set()
        
        if isinstance(params, dict):
            for value in params.values():
                self._find_dependencies(value, deps)
        elif isinstance(params, list):
            for item in params:
                self._find_dependencies(item, deps)
        elif isinstance(params, str) and params.startswith('${') and params.endswith('}'):
            expression = params[2:-1]
            if ':' in expression:
                step_ref = expression.split(':', 1)[0]
            else:
                step_ref = expression
            deps.add(step_ref)
        
        return deps
    
    def validate_dependencies(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        errors = []
        warnings = []
        
        step_names = {step['name'] for step in steps}
        
        for step in steps:
            params = step.get('params', {})
            deps = self._find_dependencies(params)
            
            for dep in deps:
                if dep not in step_names:
                    errors.append(f"Step '{step['name']}' depends on unknown step '{dep}'")
                elif dep == step['name']:
                    errors.append(f"Step '{step['name']}' has circular dependency on itself")
        
        order = self.get_execution_order(steps)
        if len(order) != len(steps):
            errors.append("Circular dependency detected in workflow")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'execution_order': order
        }
    
    def build_param_graph(self, params_config: List[Dict[str, Any]]) -> ParameterGraph:
        graph = ParameterGraph()
        
        for param_config in params_config:
            name = param_config['name']
            ptype = param_config.get('type', 'string')
            default = param_config.get('default', '')
            group = param_config.get('group')
            constraints = param_config.get('constraints', {})
            
            graph.add_node(name, ptype, default, group, constraints)
            
            depends_on = param_config.get('depends_on', [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            for dep in depends_on:
                relation = param_config.get('relation', 'direct')
                graph.add_dependency(dep, name, relation_type=relation)
        
        self.param_graph = graph
        return graph
    
    def generate_linked_test_cases(self, params_config: List[Dict[str, Any]],
                                    base_values: Dict[str, Any],
                                    param_to_test: str,
                                    test_value: Any) -> Dict[str, Any]:
        if not self.param_graph.nodes:
            self.build_param_graph(params_config)
        
        linked_values = self.param_graph.generate_related_tests(param_to_test, test_value)
        
        result = base_values.copy()
        for param, value in linked_values.items():
            if param in result:
                result[param] = value
        
        return result
    
    def get_param_traversal_order(self, params_config: List[Dict[str, Any]],
                                   mode: str = 'bfs') -> List[str]:
        if not self.param_graph.nodes:
            self.build_param_graph(params_config)
        
        if mode == 'bfs':
            return self.param_graph.traverse_bfs()
        elif mode == 'dfs':
            return self.param_graph.traverse_dfs()
        elif mode == 'topological':
            return self.param_graph.topological_sort()
        else:
            return [p['name'] for p in params_config]
    
    def clear(self) -> None:
        self.context.clear()
        self.dependencies.clear()
        self.extract_rules.clear()
        self.param_graph = ParameterGraph()
