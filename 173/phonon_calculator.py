import numpy as np
from typing import Optional, Tuple, List, Dict
import warnings
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from phonopy import Phonopy
from phonopy.phonon.band_structure import get_band_qpoints_and_path_connections
from phonopy.structure.atoms import PhonopyAtoms
from ase import Atoms
from ase.io import read, write
try:
    import seekpath
    SEEKPATH_AVAILABLE = True
except ImportError:
    SEEKPATH_AVAILABLE = False

plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class PhononCalculator:
    def __init__(self, atoms: Atoms, supercell_matrix: Optional[np.ndarray] = None):
        if supercell_matrix is None:
            supercell_matrix = np.eye(3, dtype=int) * 2
        
        self.atoms = atoms
        self.supercell_matrix = supercell_matrix
        self.phonon = self._init_phonopy()
        self.frequencies = None
        self.qpoints = None
        self.path_connections = None
        self.labels = None
        self.dos = None
        self.dos_frequencies = None
        self.force_constants = None
        self._has_imaginary_frequencies = False

    def _init_phonopy(self) -> Phonopy:
        phonopy_atoms = PhonopyAtoms(
            symbols=self.atoms.get_chemical_symbols(),
            cell=self.atoms.get_cell(),
            positions=self.atoms.get_scaled_positions(),
            masses=self.atoms.get_masses()
        )
        return Phonopy(phonopy_atoms, supercell_matrix=self.supercell_matrix, primitive_matrix='P')

    def set_force_constants(self, force_constants: np.ndarray, check_stability: bool = True):
        self.force_constants = force_constants
        self.phonon.force_constants = force_constants
        
        if check_stability:
            self._check_force_constants_stability(force_constants)

    def _check_force_constants_stability(self, force_constants: np.ndarray, threshold: float = -1e-3):
        n_atoms = force_constants.shape[0]
        fc_matrix = force_constants.reshape(n_atoms * 3, n_atoms * 3)
        
        try:
            eigenvalues = np.linalg.eigvalsh(fc_matrix)
            
            n_negative = np.sum(eigenvalues < threshold)
            min_eig = np.min(eigenvalues)
            
            if n_negative > 0:
                self._has_imaginary_frequencies = True
                warnings.warn(
                    f"⚠️  检测到力常数矩阵存在 {n_negative} 个负本征值！\n"
                    f"最小本征值: {min_eig:.6e}\n"
                    f"这可能导致声子谱出现虚频（imaginary frequencies）。\n"
                    f"建议检查：\n"
                    f"  1. 晶体结构是否充分弛豫\n"
                    f"  2. 超胞大小是否足够\n"
                    f"  3. DFT计算参数是否收敛\n"
                    f"  4. 位移大小是否合适",
                    UserWarning
                )
            else:
                self._has_imaginary_frequencies = False
                print(f"✅ 力常数矩阵稳定性检查通过：最小本征值 = {min_eig:.6e}")
                
        except Exception as e:
            warnings.warn(f"力常数矩阵本征值计算失败: {e}", UserWarning)

    def generate_displacements(self, distance: float = 0.01):
        self.phonon.generate_displacements(distance=distance)
        return self.phonon.get_supercells_with_displacements()

    def set_forces(self, forces_list: List[np.ndarray], check_stability: bool = True):
        self.phonon.forces = forces_list
        self.phonon.produce_force_constants()
        self.force_constants = self.phonon.force_constants
        
        if check_stability and self.force_constants is not None:
            self._check_force_constants_stability(self.force_constants)

    def calculate_band_structure(
        self,
        path: Optional[List[Tuple[np.ndarray, np.ndarray, int]]] = None,
        labels: Optional[List[str]] = None,
        npoints: int = 101,
        use_seekpath: bool = True
    ):
        if path is None:
            if use_seekpath and SEEKPATH_AVAILABLE:
                path, labels = self._get_seekpath_path(npoints_per_segment=npoints)
                print(f"🔍 使用Seekpath自动生成布里渊区路径: {' → '.join(labels)}")
            else:
                if SEEKPATH_AVAILABLE:
                    warnings.warn("Seekpath可用但未使用，将使用默认路径", UserWarning)
                path, labels = self._get_default_path()
        
        qpoints, path_connections = get_band_qpoints_and_path_connections(
            path, npoints=npoints
        )
        
        try:
            self.phonon.run_band_structure(
                qpoints, path_connections=path_connections, labels=labels, is_band_connection=False
            )
        except TypeError:
            self.phonon.run_band_structure(
                qpoints, path_connections=path_connections, labels=labels
            )
        
        band_dict = self.phonon.get_band_structure_dict()
        self.frequencies = band_dict['frequencies']
        self.qpoints = band_dict['qpoints']
        self.path_connections = path_connections
        self.labels = labels
        
        self._check_imaginary_frequencies()
        
        return self.frequencies, self.qpoints

    def _check_imaginary_frequencies(self, threshold: float = -1e-2):
        if self.frequencies is None:
            return
        
        all_freqs = np.concatenate(self.frequencies)
        n_imag = np.sum(all_freqs < threshold)
        
        if n_imag > 0:
            min_freq = np.min(all_freqs)
            warnings.warn(
                f"⚠️  声子谱检测到 {n_imag} 个虚频模式！\n"
                f"最小频率: {min_freq:.6f} THz\n"
                f"这表明晶体结构可能是动力学不稳定的。",
                UserWarning
            )
            self._has_imaginary_frequencies = True

    def _get_seekpath_path(self, npoints_per_segment: int = 50) -> Tuple[List, List]:
        cell = (
            self.atoms.get_cell(),
            self.atoms.get_scaled_positions(),
            self.atoms.get_atomic_numbers()
        )
        
        seekpath_result = seekpath.get_path(cell, with_time_reversal=True)
        
        path = seekpath_result['path']
        point_coords = seekpath_result['point_coords']
        
        path_tuples = []
        labels = []
        
        for i, (start_label, end_label) in enumerate(path):
            start_q = np.array(point_coords[start_label])
            end_q = np.array(point_coords[end_label])
            path_tuples.append((start_q, end_q, npoints_per_segment))
            
            if i == 0:
                labels.append(start_label)
            labels.append(end_label)
        
        labels = [self._format_label(l) for l in labels]
        
        return path_tuples, labels

    @staticmethod
    def _format_label(label: str) -> str:
        label_map = {
            'GAMMA': 'Γ',
            'Gamma': 'Γ',
            'gamma': 'Γ',
            'G': 'Γ',
        }
        
        if label in label_map:
            return label_map[label]
        
        if len(label) == 1:
            return label
        
        if '_' in label:
            parts = label.split('_')
            base = parts[0]
            sub = parts[1] if len(parts) > 1 else ''
            if base in label_map:
                base = label_map[base]
            return f'{base}$_{{{sub}}}$'
        
        return label

    def _get_default_path(self) -> Tuple[List, List]:
        cell = self.atoms.get_cell()
        lattice = cell.get_bravais_lattice()
        
        if lattice.name == 'FCC':
            path = [
                (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 50),
                (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 50),
                (np.array([1, 1, 1]), np.array([0, 0, 0]), 50),
                (np.array([0, 0, 0]), np.array([0.5, 0.5, 0.5]), 50)
            ]
            labels = ['Γ', 'X', 'L', 'Γ', 'K']
        elif lattice.name == 'BCC':
            path = [
                (np.array([0, 0, 0]), np.array([0.5, 0, 0.5]), 50),
                (np.array([0.5, 0, 0.5]), np.array([0.25, 0.25, 0.25]), 50),
                (np.array([0.25, 0.25, 0.25]), np.array([0, 0, 0]), 50),
                (np.array([0, 0, 0]), np.array([0.5, 0.5, 0.5]), 50)
            ]
            labels = ['Γ', 'H', 'P', 'Γ', 'N']
        else:
            path = [
                (np.array([0, 0, 0]), np.array([0.5, 0, 0]), 50),
                (np.array([0.5, 0, 0]), np.array([0.5, 0.5, 0]), 50),
                (np.array([0.5, 0.5, 0]), np.array([0, 0, 0]), 50),
                (np.array([0, 0, 0]), np.array([0, 0, 0.5]), 50)
            ]
            labels = ['Γ', 'X', 'M', 'Γ', 'R']
        
        return path, labels

    def calculate_dos(
        self,
        mesh: Tuple[int, int, int] = (20, 20, 20),
        sigma: Optional[float] = None,
        freq_min: float = 0,
        freq_max: float = 20,
        freq_pitch: float = 0.1
    ):
        self.phonon.run_mesh(mesh, is_mesh_symmetry=False)
        self.phonon.run_total_dos(
            sigma=sigma,
            freq_min=freq_min,
            freq_max=freq_max,
            freq_pitch=freq_pitch
        )
        
        dos_dict = self.phonon.get_total_dos_dict()
        self.dos = dos_dict['total_dos']
        self.dos_frequencies = dos_dict['frequency_points']
        
        return self.dos, self.dos_frequencies

    def interpolate_bands(
        self,
        original_qpoints: np.ndarray,
        original_frequencies: np.ndarray,
        factor: int = 3,
        method: str = 'cubic'
    ) -> Tuple[np.ndarray, np.ndarray]:
        from scipy.interpolate import interp1d
        
        n_segments = len(original_qpoints)
        interp_qpoints = []
        interp_frequencies = []
        
        for i in range(n_segments):
            q_segment = original_qpoints[i]
            freq_segment = original_frequencies[i]
            
            n_original = len(q_segment)
            n_new = n_original * factor
            
            distances = np.linalg.norm(np.diff(q_segment, axis=0), axis=1)
            cumulative_dist = np.concatenate([[0], np.cumsum(distances)])
            
            new_distances = np.linspace(0, cumulative_dist[-1], n_new)
            
            new_q = np.zeros((n_new, 3))
            for j in range(3):
                interp_q = interp1d(cumulative_dist, q_segment[:, j], kind='linear')
                new_q[:, j] = interp_q(new_distances)
            
            new_freq = np.zeros((n_new, freq_segment.shape[1]))
            for j in range(freq_segment.shape[1]):
                try:
                    interp_f = interp1d(cumulative_dist, freq_segment[:, j], kind=method)
                    new_freq[:, j] = interp_f(new_distances)
                except Exception as e:
                    warnings.warn(f"三次样条插值失败，使用线性插值替代: {e}", UserWarning)
                    interp_f = interp1d(cumulative_dist, freq_segment[:, j], kind='linear')
                    new_freq[:, j] = interp_f(new_distances)
            
            interp_qpoints.append(new_q)
            interp_frequencies.append(new_freq)
        
        return interp_qpoints, interp_frequencies

    def plot_band_structure(
        self,
        ax: Optional[plt.Axes] = None,
        show: bool = True,
        save_path: Optional[str] = None,
        interpolate: bool = True,
        interpolation_factor: int = 3,
        interpolation_method: str = 'cubic',
        highlight_imaginary: bool = True,
        **kwargs
    ) -> plt.Axes:
        if self.frequencies is None:
            raise RuntimeError("Band structure not calculated. Call calculate_band_structure first.")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
        
        freq_data = self.frequencies
        q_data = self.qpoints
        
        if interpolate:
            q_data, freq_data = self.interpolate_bands(
                self.qpoints, self.frequencies, 
                factor=interpolation_factor, 
                method=interpolation_method
            )
        
        all_distances = []
        all_frequencies = []
        segment_ends = [0]
        
        for i, (q_seg, freq_seg) in enumerate(zip(q_data, freq_data)):
            distances = np.linalg.norm(np.diff(q_seg, axis=0), axis=1)
            cumulative = np.concatenate([[0], np.cumsum(distances)])
            if i > 0:
                cumulative += segment_ends[-1]
            
            all_distances.extend(cumulative)
            all_frequencies.append(freq_seg)
            segment_ends.append(cumulative[-1])
        
        all_distances = np.array(all_distances)
        all_frequencies = np.vstack(all_frequencies)
        
        for i in range(all_frequencies.shape[1]):
            freq_band = all_frequencies[:, i]
            
            if highlight_imaginary:
                mask = freq_band < 0
                if np.any(mask):
                    ax.plot(all_distances[~mask], freq_band[~mask], 'b-', linewidth=1.5, alpha=0.8)
                    ax.plot(all_distances[mask], freq_band[mask], 'r--', linewidth=1.5, alpha=0.9, 
                            label='虚频' if i == 0 else "")
                else:
                    ax.plot(all_distances, freq_band, 'b-', linewidth=1.5, alpha=0.8)
            else:
                ax.plot(all_distances, freq_band, 'b-', linewidth=1.5, alpha=0.8)
        
        for end in segment_ends[1:-1]:
            ax.axvline(x=end, color='gray', linestyle='--', linewidth=0.8)
        
        if self.labels is not None:
            label_positions = [segment_ends[i] for i in range(len(self.labels)) if i < len(segment_ends)]
            ax.set_xticks(label_positions)
            ax.set_xticklabels(self.labels, fontsize=12)
        
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        
        ax.set_xlabel('Wave Vector', fontsize=14)
        ax.set_ylabel('Frequency (THz)', fontsize=14)
        
        title = 'Phonon Band Structure'
        if self._has_imaginary_frequencies:
            title += ' (⚠️ 存在虚频)'
        ax.set_title(title, fontsize=16)
        
        ax.grid(True, alpha=0.3)
        
        if highlight_imaginary and self._has_imaginary_frequencies:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(loc='upper right')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return ax

    def plot_dos(
        self,
        ax: Optional[plt.Axes] = None,
        show: bool = True,
        save_path: Optional[str] = None
    ) -> plt.Axes:
        if self.dos is None:
            raise RuntimeError("DOS not calculated. Call calculate_dos first.")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))
        
        ax.plot(self.dos, self.dos_frequencies, 'r-', linewidth=2)
        ax.fill_betweenx(self.dos_frequencies, 0, self.dos, alpha=0.3, color='red')
        
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        
        ax.set_xlabel('Density of States', fontsize=14)
        ax.set_ylabel('Frequency (THz)', fontsize=14)
        ax.set_title('Phonon Density of States', fontsize=16)
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return ax

    def plot_band_and_dos(
        self,
        save_path: Optional[str] = None,
        show: bool = True,
        interpolate: bool = True,
        interpolation_factor: int = 3,
        interpolation_method: str = 'cubic'
    ):
        if self.frequencies is None or self.dos is None:
            raise RuntimeError("Calculate band structure and DOS first.")
        
        fig = plt.figure(figsize=(12, 6))
        gs = GridSpec(1, 2, width_ratios=[3, 1], wspace=0.05)
        
        ax_band = fig.add_subplot(gs[0])
        ax_dos = fig.add_subplot(gs[1], sharey=ax_band)
        
        self.plot_band_structure(
            ax=ax_band, show=False, interpolate=interpolate,
            interpolation_factor=interpolation_factor,
            interpolation_method=interpolation_method
        )
        self.plot_dos(ax=ax_dos, show=False)
        
        ax_dos.set_ylabel('')
        ax_dos.set_yticklabels([])
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return fig

    def save_results(self, prefix: str = 'phonon'):
        if self.frequencies is not None:
            np.save(f'{prefix}_frequencies.npy', self.frequencies)
            np.save(f'{prefix}_qpoints.npy', self.qpoints)
        
        if self.dos is not None:
            np.save(f'{prefix}_dos.npy', self.dos)
            np.save(f'{prefix}_dos_frequencies.npy', self.dos_frequencies)
        
        try:
            self.phonon.write_yaml_band_structure(filename=f'{prefix}_band.yaml')
        except AttributeError:
            try:
                self.phonon.write_band_structure(filename=f'{prefix}_band.yaml')
            except:
                pass
        
        if self.dos is not None:
            try:
                self.phonon.write_yaml_total_dos(filename=f'{prefix}_dos.yaml')
            except AttributeError:
                try:
                    self.phonon.write_total_dos(filename=f'{prefix}_dos.yaml')
                except:
                    pass

    @classmethod
    def from_file(cls, filename: str, supercell_matrix: Optional[np.ndarray] = None):
        atoms = read(filename)
        return cls(atoms, supercell_matrix=supercell_matrix)

    @staticmethod
    def generate_example_force_constants(atoms: Atoms, supercell_matrix: np.ndarray) -> np.ndarray:
        n_atoms = len(atoms)
        supercell = atoms * np.diag(supercell_matrix)
        n_supercell = len(supercell)
        
        force_constants = np.zeros((n_supercell, n_supercell, 3, 3))
        
        k = 10.0
        for i in range(n_supercell):
            force_constants[i, i] = np.eye(3) * k * 2
        
        for i in range(n_supercell):
            for j in range(max(0, i-1), min(n_supercell, i+2)):
                if i != j:
                    force_constants[i, j] = -np.eye(3) * k
        
        return force_constants

    @staticmethod
    def generate_unstable_force_constants(atoms: Atoms, supercell_matrix: np.ndarray) -> np.ndarray:
        n_atoms = len(atoms)
        supercell = atoms * np.diag(supercell_matrix)
        n_supercell = len(supercell)
        
        force_constants = np.zeros((n_supercell, n_supercell, 3, 3))
        
        k = 10.0
        for i in range(n_supercell):
            force_constants[i, i] = -np.eye(3) * k * 0.5
        
        for i in range(n_supercell):
            for j in range(max(0, i-1), min(n_supercell, i+2)):
                if i != j:
                    force_constants[i, j] = -np.eye(3) * k
        
        return force_constants


def run_example_fcc():
    print("=" * 70)
    print("Running FCC Silicon example with Seekpath")
    print("=" * 70)
    
    a = 5.431
    atoms = Atoms(
        symbols=['Si', 'Si'],
        cell=[[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]],
        scaled_positions=[[0, 0, 0], [0.25, 0.25, 0.25]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    print("\n📦 生成示例力常数...")
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    print("\n🎯 计算声子色散关系（使用Seekpath自动路径）...")
    calculator.calculate_band_structure(use_seekpath=True)
    
    print("\n📊 计算态密度...")
    calculator.calculate_dos(mesh=(20, 20, 20))
    
    print("\n🎨 绘制结果（三次样条插值）...")
    calculator.plot_band_and_dos(
        save_path='phonon_fcc_si_seekpath.png', 
        show=False,
        interpolate=True,
        interpolation_factor=3,
        interpolation_method='cubic'
    )
    
    print("\n💾 保存结果...")
    calculator.save_results(prefix='fcc_si_seekpath')
    
    print("\n✅ 完成！结果已保存到 phonon_fcc_si_seekpath.png")
    return calculator


def run_example_bcc():
    print("=" * 70)
    print("Running BCC Iron example with Seekpath")
    print("=" * 70)
    
    a = 2.87
    atoms = Atoms(
        symbols=['Fe'],
        cell=[[-a/2, a/2, a/2], [a/2, -a/2, a/2], [a/2, a/2, -a/2]],
        scaled_positions=[[0, 0, 0]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    print("\n📦 生成示例力常数...")
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    print("\n🎯 计算声子色散关系...")
    calculator.calculate_band_structure(use_seekpath=True)
    
    print("\n📊 计算态密度...")
    calculator.calculate_dos(mesh=(20, 20, 20))
    
    print("\n🎨 绘制结果...")
    calculator.plot_band_and_dos(save_path='phonon_bcc_fe_seekpath.png', show=False)
    
    print("\n💾 保存结果...")
    calculator.save_results(prefix='bcc_fe_seekpath')
    
    print("\n✅ 完成！结果已保存到 phonon_bcc_fe_seekpath.png")
    return calculator


def run_example_unstable():
    print("=" * 70)
    print("示例：检测虚频（不稳定结构）")
    print("=" * 70)
    
    a = 3.0
    atoms = Atoms(
        symbols=['Na'],
        cell=[[a, 0, 0], [0, a, 0], [0, 0, a]],
        scaled_positions=[[0, 0, 0]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    print("\n📦 生成不稳定力常数（含负对角元）...")
    force_constants = PhononCalculator.generate_unstable_force_constants(atoms, supercell_matrix)
    
    print("\n🔍 设置力常数并检查稳定性...")
    calculator.set_force_constants(force_constants)
    
    print("\n🎯 计算声子色散关系...")
    calculator.calculate_band_structure(use_seekpath=True)
    
    print("\n📊 计算态密度...")
    calculator.calculate_dos(mesh=(15, 15, 15))
    
    print("\n🎨 绘制结果（虚频将用红色虚线标记）...")
    calculator.plot_band_and_dos(
        save_path='phonon_unstable_example.png', 
        show=False,
        interpolate=True,
        interpolation_method='cubic'
    )
    
    print("\n💾 保存结果...")
    calculator.save_results(prefix='unstable_example')
    
    print("\n✅ 完成！注意图中的红色虚线表示虚频模式")
    return calculator


def run_example_interpolation_comparison():
    print("=" * 70)
    print("示例：插值方法对比（默认使用三次样条）")
    print("=" * 70)
    
    a = 5.431
    atoms = Atoms(
        symbols=['Si', 'Si'],
        cell=[[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]],
        scaled_positions=[[0, 0, 0], [0.25, 0.25, 0.25]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    path = [
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 10),
        (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 10),
    ]
    labels = ['Γ', 'X', 'L']
    
    print("\n🎯 使用稀疏q点计算（10点/段）...")
    calculator.calculate_band_structure(path=path, labels=labels, npoints=10)
    
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    calculator.plot_band_structure(ax=axes[0], show=False, interpolate=False)
    axes[0].set_title('原始数据 (10 points/segment)', fontsize=12)
    
    calculator.plot_band_structure(
        ax=axes[1], show=False, interpolate=True,
        interpolation_factor=3, interpolation_method='linear'
    )
    axes[1].set_title('线性插值 (30 points/segment)', fontsize=12)
    
    calculator.plot_band_structure(
        ax=axes[2], show=False, interpolate=True,
        interpolation_factor=3, interpolation_method='cubic'
    )
    axes[2].set_title('三次样条插值 (30 points/segment) [默认]', fontsize=12)
    
    plt.tight_layout()
    plt.savefig('interpolation_comparison.png', dpi=300, bbox_inches='tight')
    
    print("\n✅ 插值对比图已保存到 interpolation_comparison.png")
    print("   观察三次样条插值如何提供最平滑的曲线")
    return calculator


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Phonon Spectrum Calculator')
    parser.add_argument('--structure', type=str, help='Path to structure file')
    parser.add_argument('--force_constants', type=str, help='Path to force constants file (.npy)')
    parser.add_argument('--example', type=str, choices=['fcc', 'bcc', 'unstable', 'interp'], 
                        help='Run example')
    parser.add_argument('--supercell', type=int, default=2, help='Supercell size')
    parser.add_argument('--mesh', type=int, default=20, help='k-point mesh for DOS')
    parser.add_argument('--npoints', type=int, default=101, help='Number of q-points per segment')
    parser.add_argument('--no-seekpath', action='store_true', help='Disable seekpath auto path')
    parser.add_argument('--no-check', action='store_true', help='Disable force constants stability check')
    
    args = parser.parse_args()
    
    if args.example == 'fcc':
        run_example_fcc()
    elif args.example == 'bcc':
        run_example_bcc()
    elif args.example == 'unstable':
        run_example_unstable()
    elif args.example == 'interp':
        run_example_interpolation_comparison()
    elif args.structure:
        print(f"Loading structure from {args.structure}...")
        supercell_matrix = np.eye(3, dtype=int) * args.supercell
        calculator = PhononCalculator.from_file(args.structure, supercell_matrix=supercell_matrix)
        
        if args.force_constants:
            print(f"Loading force constants from {args.force_constants}...")
            force_constants = np.load(args.force_constants)
            calculator.set_force_constants(force_constants, check_stability=not args.no_check)
        else:
            print("Generating example force constants...")
            force_constants = PhononCalculator.generate_example_force_constants(
                calculator.atoms, supercell_matrix
            )
            calculator.set_force_constants(force_constants, check_stability=not args.no_check)
        
        print("Calculating band structure...")
        calculator.calculate_band_structure(npoints=args.npoints, use_seekpath=not args.no_seekpath)
        
        print("Calculating DOS...")
        calculator.calculate_dos(mesh=(args.mesh, args.mesh, args.mesh))
        
        print("Plotting...")
        calculator.plot_band_and_dos(save_path='phonon_result.png')
        
        print("Saving results...")
        calculator.save_results()
        print("Done!")
    else:
        print("Running FCC example by default...")
        run_example_fcc()
