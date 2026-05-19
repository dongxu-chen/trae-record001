import numpy as np
from typing import Optional, List, Tuple, Union
import warnings

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("matplotlib not available. Visualization features will not work.")

from .quantum_state import QuantumState
from .noise import state_to_density_matrix, partial_trace, get_bloch_coordinates


class BlochSphere:
    def __init__(self, figsize: Tuple[int, int] = (8, 8)):
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for Bloch sphere visualization")
        
        self.fig = plt.figure(figsize=figsize)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self._setup_sphere()
        self._points = []
    
    def _setup_sphere(self):
        u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
        x = np.cos(u) * np.sin(v)
        y = np.sin(u) * np.sin(v)
        z = np.cos(v)
        
        self.ax.plot_surface(x, y, z, color='lightgray', alpha=0.1, 
                            edgecolor='gray', linewidth=0.5)
        
        self.ax.plot([-1, 1], [0, 0], [0, 0], 'k-', linewidth=1, alpha=0.5)
        self.ax.plot([0, 0], [-1, 1], [0, 0], 'k-', linewidth=1, alpha=0.5)
        self.ax.plot([0, 0], [0, 0], [-1, 1], 'k-', linewidth=1, alpha=0.5)
        
        self.ax.text(1.1, 0, 0, 'X', fontsize=12)
        self.ax.text(0, 1.1, 0, 'Y', fontsize=12)
        self.ax.text(0, 0, 1.1, 'Z', fontsize=12)
        
        self.ax.text(-1, 0, 0, '|0⟩', fontsize=14, ha='center')
        self.ax.text(1, 0, 0, '|1⟩', fontsize=14, ha='center')
        
        self.ax.set_xlim(-1.2, 1.2)
        self.ax.set_ylim(-1.2, 1.2)
        self.ax.set_zlim(-1.2, 1.2)
        
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_zticks([])
        
        self.ax.set_box_aspect([1, 1, 1])
    
    def add_point(self, x: float, y: float, z: float, 
                  color: str = 'red', label: Optional[str] = None,
                  size: int = 100):
        point = self.ax.scatter(x, y, z, color=color, s=size, alpha=0.8, 
                               edgecolor='black', linewidth=1.5)
        self._points.append((point, x, y, z, color, label))
        
        self.ax.plot([0, x], [0, y], [0, z], color=color, 
                    linestyle='--', alpha=0.5)
        
        if label:
            self.ax.text(x * 1.1, y * 1.1, z * 1.1, label, 
                       fontsize=10, color=color)
        
        return self
    
    def add_state(self, state: Union[np.ndarray, QuantumState], 
                  qubit_idx: Optional[int] = None, 
                  num_qubits: Optional[int] = None,
                  color: str = 'red', label: Optional[str] = None):
        if isinstance(state, QuantumState):
            state_vector = state.get_state_vector()
            num_qubits = state.num_qubits
        else:
            state_vector = state
            if num_qubits is None:
                num_qubits = int(np.log2(len(state_vector)))
        
        if num_qubits == 1:
            rho = state_to_density_matrix(state_vector)
        elif qubit_idx is not None:
            rho = state_to_density_matrix(state_vector)
            rho = partial_trace(rho, [qubit_idx], num_qubits)
        else:
            raise ValueError("For multi-qubit states, qubit_idx must be specified")
        
        x, y, z = get_bloch_coordinates(rho)
        return self.add_point(x, y, z, color=color, label=label)
    
    def add_trajectory(self, points: List[Tuple[float, float, float]],
                      color: str = 'blue', linewidth: float = 2):
        xs, ys, zs = zip(*points)
        self.ax.plot(xs, ys, zs, color=color, linewidth=linewidth, 
                    alpha=0.7, marker='o', markersize=4)
        return self
    
    def show(self):
        plt.tight_layout()
        plt.show()
    
    def save(self, filename: str, dpi: int = 300):
        plt.tight_layout()
        plt.savefig(filename, dpi=dpi, bbox_inches='tight')
        plt.close()


def plot_bloch_sphere(state: Union[np.ndarray, QuantumState],
                      qubit_idx: Optional[int] = None,
                      color: str = 'red',
                      label: Optional[str] = None,
                      figsize: Tuple[int, int] = (8, 8),
                      show: bool = True,
                      save_path: Optional[str] = None) -> BlochSphere:
    sphere = BlochSphere(figsize=figsize)
    sphere.add_state(state, qubit_idx=qubit_idx, color=color, label=label)
    
    if save_path:
        sphere.save(save_path)
    
    if show:
        sphere.show()
    
    return sphere


def plot_bloch_sphere_multiple(states: List[Union[np.ndarray, QuantumState]],
                               qubit_indices: Optional[List[int]] = None,
                               colors: Optional[List[str]] = None,
                               labels: Optional[List[str]] = None,
                               figsize: Tuple[int, int] = (8, 8),
                               show: bool = True,
                               save_path: Optional[str] = None) -> BlochSphere:
    if colors is None:
        colors = plt.cm.tab10(np.linspace(0, 1, len(states)))
    
    sphere = BlochSphere(figsize=figsize)
    
    for i, state in enumerate(states):
        qubit_idx = qubit_indices[i] if qubit_indices else None
        label = labels[i] if labels else None
        color = colors[i]
        
        sphere.add_state(state, qubit_idx=qubit_idx, color=color, label=label)
    
    if save_path:
        sphere.save(save_path)
    
    if show:
        sphere.show()
    
    return sphere


def plot_probability_histogram(counts: dict,
                               title: str = "Measurement Probabilities",
                               figsize: Tuple[int, int] = (10, 6),
                               color: str = 'skyblue',
                               edgecolor: str = 'black',
                               sort: bool = True,
                               show_percentages: bool = True,
                               show: bool = True,
                               save_path: Optional[str] = None):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for histogram plotting")
    
    outcomes = list(counts.keys())
    values = list(counts.values())
    
    if sort:
        sorted_indices = np.argsort(outcomes)
        outcomes = [outcomes[i] for i in sorted_indices]
        values = [values[i] for i in sorted_indices]
    
    total = sum(values)
    percentages = [v / total * 100 for v in values]
    
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(outcomes, values, color=color, edgecolor=edgecolor, alpha=0.8)
    
    if show_percentages:
        for bar, pct in zip(bars, percentages):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                   f'{pct:.1f}%',
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Measurement Outcome', fontsize=12)
    ax.set_ylabel('Counts', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig, ax


def plot_state_probabilities(state: QuantumState,
                             title: str = "State Probabilities",
                             figsize: Tuple[int, int] = (10, 6),
                             color: str = 'lightgreen',
                             edgecolor: str = 'black',
                             show_percentages: bool = True,
                             show: bool = True,
                             save_path: Optional[str] = None):
    prob_dict = state.get_probability_dict()
    
    counts = {k: int(v * 10000) for k, v in prob_dict.items()}
    
    return plot_probability_histogram(
        counts, title=title, figsize=figsize, color=color,
        edgecolor=edgecolor, show_percentages=show_percentages,
        show=show, save_path=save_path
    )


def plot_noise_comparison(circuit, noise_parameters: List[Tuple[str, float]],
                         num_shots: int = 1000,
                         figsize: Tuple[int, int] = (12, 6),
                         show: bool = True,
                         save_path: Optional[str] = None):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for noise comparison plotting")
    
    n = len(noise_parameters)
    fig, axes = plt.subplots(1, n, figsize=figsize, sharey=True)
    if n == 1:
        axes = [axes]
    
    all_outcomes = set()
    all_counts = []
    
    for noise_name, param in noise_parameters:
        test_circuit = circuit.__class__(circuit.num_qubits)
        
        for gate in circuit.gates:
            test_circuit.add_gate(gate)
        
        if 'depolarizing' in noise_name.lower():
            test_circuit.add_depolarizing_noise(param, list(range(circuit.num_qubits)))
        elif 'amplitude' in noise_name.lower():
            test_circuit.add_amplitude_damping_noise(param, list(range(circuit.num_qubits)))
        elif 'phase' in noise_name.lower():
            test_circuit.add_phase_damping_noise(param, list(range(circuit.num_qubits)))
        
        counts = test_circuit.get_counts(num_shots=num_shots)
        all_counts.append(counts)
        all_outcomes.update(counts.keys())
    
    all_outcomes = sorted(all_outcomes)
    
    for i, (ax, (noise_name, param)) in enumerate(zip(axes, noise_parameters)):
        counts = all_counts[i]
        values = [counts.get(outcome, 0) for outcome in all_outcomes]
        total = sum(values)
        percentages = [v / total * 100 for v in values]
        
        bars = ax.bar(all_outcomes, percentages, color=f'C{i}', alpha=0.7, 
                     edgecolor='black')
        
        for bar, pct in zip(bars, percentages):
            height = bar.get_height()
            if height > 1:
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                       f'{pct:.1f}%', ha='center', va='bottom', fontsize=8)
        
        ax.set_title(f'{noise_name} (param={param})', fontsize=11)
        ax.set_xlabel('Outcome', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    axes[0].set_ylabel('Probability (%)', fontsize=12)
    fig.suptitle('Noise Comparison on Bell State', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig, axes
