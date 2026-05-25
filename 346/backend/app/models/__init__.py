from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

@dataclass
class Node:
    id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    source: str
    target: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphData:
    nodes: List[Node]
    edges: List[Edge]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': [{'id': n.id, 'label': n.label, **n.properties} for n in self.nodes],
            'edges': [{'source': e.source, 'target': e.target, 'type': e.relationship_type, **e.properties} for e in self.edges]
        }

@dataclass
class Community:
    id: int
    nodes: List[str]
    size: int
    modularity: Optional[float] = None

@dataclass
class InfluenceResult:
    node_id: str
    score: float
    rank: int

@dataclass
class KeyNode:
    node_id: str
    node_type: str
    score: float
    rank: int
    description: str

@dataclass
class DiffusionStep:
    step: int
    infected: List[str]
    recovered: List[str]
    susceptible: List[str]
    new_infections: List[str]
    infection_count: int
    recovery_count: int

@dataclass
class DiffusionResult:
    steps: List[DiffusionStep]
    total_infected: int
    total_recovered: int
    peak_infected: int
    peak_step: int
    duration: int
    infection_tree: Dict[str, List[str]]
    affected_nodes: List[str]

@dataclass
class CommunityEvolutionEvent:
    window_index: int
    event_type: str
    community_id: Optional[int]
    source_communities: List[int]
    target_community: Optional[int]
    nodes_involved: List[str]
    description: str

@dataclass
class CommunityEvolutionFrame:
    window_index: int
    start_time: float
    end_time: float
    communities: List[Dict[str, Any]]
    events: List[CommunityEvolutionEvent]
    node_community_map: Dict[str, int]

@dataclass
class CommunityEvolutionResult:
    frames: List[CommunityEvolutionFrame]
    events: List[CommunityEvolutionEvent]
    total_merges: int
    total_splits: int
    total_new_communities: int
    total_dissolved_communities: int
