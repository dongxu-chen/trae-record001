import numpy as np
from typing import Optional, Tuple, List, Dict, Callable
import warnings
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.interpolate import interp1d
from scipy.integrate import simpson
from phonon_calculator import PhononCalculator

try:
    from phonopy import Phonopy
    from phonopy.structure.atoms import PhonopyAtoms
    PHONOPY_AVAILABLE = True
except ImportError:
    PHONOPY_AVAILABLE = False

try:
    from ase import Atoms
    ASE_AVAILABLE = True
except ImportError:
    ASE_AVAILABLE = False

kB = 8.617333262145e-5  # eV/K
hbar = 6.582119569e-16   # eV·s
THz_to_eV = 4.13566733e-3  # THz to eV
eV_to_J = 1.602176634e-19   # eV to J


class QuasiHarmonicApproximation:
    def __init__(
        self,
        calculator: PhononCalculator,
        volume_scales: Optional[List[float]] = None
    ):
        self.calculator = calculator
        self.atoms = calculator.atoms
        self.volume_scales = volume_scales or [0.98, 0.99, 1.00, 1.01, 1.02]
        
        self.volumes = []
        self.frequencies_by_volume = []
        self.qpoints_by_volume = []
        self.gruneisen_parameters = None
        self.thermal_expansion_coeff = None
        
    def calculate_frequencies_at_volumes(
        self,
        npoints: int = 101,
        use_seekpath: bool = True,
        path: Optional[List] = None,
        labels: Optional[List[str]] = None
    ):
        print("📊 准谐近似：计算不同体积下的声子频率...")
        
        original_cell = self.atoms.get_cell()
        original_positions = self.atoms.get_scaled_positions()
        
        if path is None and not use_seekpath:
            path = [
                (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 20),
                (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 20),
                (np.array([1, 1, 1]), np.array([0, 0, 0]), 20),
            ]
            labels = ['Γ', 'X', 'L', 'Γ']
        
        for scale in self.volume_scales:
            print(f"  体积比例: {scale:.2f}x")
            
            scaling_factor = scale ** (1/3)
            scaled_cell_arr = np.array(original_cell) * scaling_factor
            scaled_atoms = Atoms(
                symbols=self.atoms.get_chemical_symbols(),
                cell=scaled_cell_arr,
                scaled_positions=original_positions,
                pbc=True
            )
            
            vol_calculator = PhononCalculator(
                scaled_atoms, 
                supercell_matrix=self.calculator.supercell_matrix
            )
            
            fc_scale = scale ** (-5/3)
            force_constants = PhononCalculator.generate_example_force_constants(
                scaled_atoms, self.calculator.supercell_matrix
            )
            force_constants = force_constants * fc_scale
            
            vol_calculator.set_force_constants(force_constants, check_stability=False)
            
            if path is not None:
                vol_calculator.calculate_band_structure(
                    path=path, labels=labels, npoints=npoints, use_seekpath=False
                )
            else:
                vol_calculator.calculate_band_structure(
                    npoints=npoints, use_seekpath=use_seekpath
                )
            
            volume = scaled_atoms.get_cell().volume
            self.volumes.append(volume)
            self.frequencies_by_volume.append(vol_calculator.frequencies)
            self.qpoints_by_volume.append(vol_calculator.qpoints)
        
        self.volumes = np.array(self.volumes)
        print(f"✅ 完成 {len(self.volumes)} 个体积点的声子计算")
        
        return self.volumes, self.frequencies_by_volume
    
    def calculate_gruneisen_parameters(self) -> np.ndarray:
        if len(self.frequencies_by_volume) < 2:
            raise RuntimeError("需要至少2个体积点来计算Grüneisen参数")
        
        print("🔬 计算Grüneisen参数...")
        
        ref_idx = len(self.volumes) // 2
        V0 = self.volumes[ref_idx]
        freqs_ref = self.frequencies_by_volume[ref_idx]
        
        self.gruneisen_parameters = []
        
        for seg_idx, freq_seg in enumerate(freqs_ref):
            gamma_seg = np.zeros_like(freq_seg)
            
            for q_idx in range(freq_seg.shape[0]):
                for band_idx in range(freq_seg.shape[1]):
                    omega0 = freq_seg[q_idx, band_idx]
                    
                    if abs(omega0) < 1e-6:
                        gamma_seg[q_idx, band_idx] = 0
                        continue
                    
                    freq_vs_V = np.array([
                        self.frequencies_by_volume[v_idx][seg_idx][q_idx, band_idx]
                        for v_idx in range(len(self.volumes))
                    ])
                    
                    valid_mask = freq_vs_V > 1e-6
                    if np.sum(valid_mask) < 2:
                        gamma_seg[q_idx, band_idx] = 0
                        continue
                    
                    log_omega = np.log(freq_vs_V[valid_mask])
                    log_V = np.log(self.volumes[valid_mask])
                    
                    try:
                        coeffs = np.polyfit(log_V, log_omega, 1)
                        dlog_omega_dlog_V = coeffs[0]
                        gamma = -dlog_omega_dlog_V
                        gamma_seg[q_idx, band_idx] = gamma
                    except:
                        gamma_seg[q_idx, band_idx] = 0
            
            self.gruneisen_parameters.append(gamma_seg)
        
        avg_gamma = np.mean([np.mean(g[g > -10]) for g in self.gruneisen_parameters])
        print(f"✅ 平均Grüneisen参数: {avg_gamma:.3f}")
        
        return self.gruneisen_parameters
    
    def calculate_thermal_expansion(
        self,
        temperatures: np.ndarray,
        bulk_modulus: float = 100.0  # GPa
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self.gruneisen_parameters is None:
            self.calculate_gruneisen_parameters()
        
        print("🔥 计算热膨胀系数...")
        
        ref_idx = len(self.volumes) // 2
        V0 = self.volumes[ref_idx]
        freqs_ref = self.frequencies_by_volume[ref_idx]
        
        alpha = np.zeros_like(temperatures)
        Cv_total = np.zeros_like(temperatures)
        
        for T_idx, T in enumerate(temperatures):
            if T < 1e-6:
                alpha[T_idx] = 0
                Cv_total[T_idx] = 0
                continue
            
            Cv_weighted = 0
            gamma_weighted = 0
            
            for seg_idx, freq_seg in enumerate(freqs_ref):
                gamma_seg = self.gruneisen_parameters[seg_idx]
                
                for q_idx in range(freq_seg.shape[0]):
                    for band_idx in range(freq_seg.shape[1]):
                        omega = freq_seg[q_idx, band_idx]
                        gamma = gamma_seg[q_idx, band_idx]
                        
                        if omega < 1e-6:
                            continue
                        
                        omega_eV = omega * THz_to_eV
                        x = hbar * omega * 2 * np.pi / (kB * T)
                        x = np.clip(x, 1e-6, 100)
                        
                        Cv_mode = 3 * kB * (x ** 2 * np.exp(x)) / (np.exp(x) - 1) ** 2
                        
                        Cv_weighted += Cv_mode
                        gamma_weighted += gamma * Cv_mode
            
            if Cv_weighted > 0:
                gamma_avg = gamma_weighted / Cv_weighted
                Cv_total[T_idx] = Cv_weighted
                Cv_weighted_J = Cv_weighted * eV_to_J
                alpha[T_idx] = gamma_avg * Cv_weighted_J / (bulk_modulus * 1e9 * V0 * 1e-30)
        
        self.thermal_expansion_coeff = alpha
        print(f"✅ 热膨胀系数计算完成")
        print(f"   300K时 α = {alpha[np.argmin(np.abs(temperatures - 300))]:.2e} K⁻¹")
        
        return alpha, Cv_total
    
    def plot_gruneisen_band_structure(
        self,
        save_path: Optional[str] = None,
        show: bool = True
    ):
        if self.gruneisen_parameters is None:
            self.calculate_gruneisen_parameters()
        
        ref_idx = len(self.volumes) // 2
        freqs_ref = self.frequencies_by_volume[ref_idx]
        qpoints_ref = self.qpoints_by_volume[ref_idx]
        
        all_distances = []
        all_gammas = []
        all_freqs = []
        segment_ends = [0]
        
        for i, (q_seg, gamma_seg, freq_seg) in enumerate(zip(
            qpoints_ref, self.gruneisen_parameters, freqs_ref
        )):
            distances = np.linalg.norm(np.diff(q_seg, axis=0), axis=1)
            cumulative = np.concatenate([[0], np.cumsum(distances)])
            if i > 0:
                cumulative += segment_ends[-1]
            
            all_distances.extend(cumulative)
            all_gammas.append(gamma_seg)
            all_freqs.append(freq_seg)
            segment_ends.append(cumulative[-1])
        
        all_distances = np.array(all_distances)
        all_gammas = np.vstack(all_gammas)
        all_freqs = np.vstack(all_freqs)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        for i in range(all_freqs.shape[1]):
            ax1.plot(all_distances, all_freqs[:, i], 'b-', linewidth=1.5, alpha=0.8)
        
        for end in segment_ends[1:-1]:
            ax1.axvline(x=end, color='gray', linestyle='--', linewidth=0.8)
        
        ax1.set_ylabel('Frequency (THz)', fontsize=12)
        ax1.set_title('Phonon Band Structure', fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        gamma_mesh = ax2.pcolormesh(
            all_distances, 
            np.arange(all_gammas.shape[1]), 
            all_gammas.T,
            cmap='RdBu_r', 
            shading='auto',
            vmin=-3, vmax=3
        )
        fig.colorbar(gamma_mesh, ax=ax2, label='Grüneisen Parameter γ')
        
        for end in segment_ends[1:-1]:
            ax2.axvline(x=end, color='gray', linestyle='--', linewidth=0.8)
        
        if self.calculator.labels is not None:
            label_positions = [segment_ends[i] for i in range(len(self.calculator.labels)) 
                             if i < len(segment_ends)]
            ax2.set_xticks(label_positions)
            ax2.set_xticklabels(self.calculator.labels, fontsize=10)
        
        ax2.set_xlabel('Wave Vector', fontsize=12)
        ax2.set_ylabel('Band Index', fontsize=12)
        ax2.set_title('Grüneisen Parameters', fontsize=14)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return fig


class PhononLifetime:
    def __init__(
        self,
        calculator: PhononCalculator,
        gruneisen_params: Optional[List[np.ndarray]] = None,
        average_gamma: float = 1.5
    ):
        self.calculator = calculator
        self.gruneisen_params = gruneisen_params
        self.average_gamma = average_gamma
        self.lifetimes = None
        self.thermal_conductivity = None
        
    def calculate_lifetimes(
        self,
        temperature: float = 300.0,
        tau0: float = 1e-12,  # ps
        use_gruneisen: bool = True
    ) -> List[np.ndarray]:
        print(f"⏱️  计算 {temperature}K 下的声子寿命...")
        
        if self.calculator.frequencies is None:
            raise RuntimeError("请先计算声子频率")
        
        self.lifetimes = []
        
        for seg_idx, freq_seg in enumerate(self.calculator.frequencies):
            tau_seg = np.zeros_like(freq_seg)
            
            for q_idx in range(freq_seg.shape[0]):
                for band_idx in range(freq_seg.shape[1]):
                    omega = freq_seg[q_idx, band_idx]
                    
                    if omega < 0.1:
                        tau_seg[q_idx, band_idx] = tau0 * 10
                        continue
                    
                    if use_gruneisen and self.gruneisen_params is not None:
                        try:
                            if (seg_idx < len(self.gruneisen_params) and 
                                q_idx < len(self.gruneisen_params[seg_idx]) and
                                band_idx < len(self.gruneisen_params[seg_idx][q_idx])):
                                gamma = self.gruneisen_params[seg_idx][q_idx, band_idx]
                                gamma = np.clip(abs(gamma), 0.1, 5.0)
                            else:
                                gamma = self.average_gamma
                        except (IndexError, TypeError):
                            gamma = self.average_gamma
                    else:
                        gamma = self.average_gamma
                    
                    omega_rad = omega * 2 * np.pi * 1e12
                    
                    if temperature < 10:
                        tau = tau0 * 100
                    else:
                        tau = 1.0 / (gamma ** 2 * omega_rad ** 2 * temperature / 300 * 1e12)
                        tau = np.clip(tau, 1e-14, 1e-10)
                    
                    tau_seg[q_idx, band_idx] = tau
            
            self.lifetimes.append(tau_seg)
        
        avg_tau = np.mean([np.mean(t) for t in self.lifetimes]) * 1e12
        print(f"✅ 平均声子寿命: {avg_tau:.3f} ps")
        
        return self.lifetimes
    
    def calculate_thermal_conductivity(
        self,
        temperatures: np.ndarray,
        vsound: float = 5000.0,  # m/s
        n_modes: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        print("🔥 计算晶格热导率...")
        
        if self.calculator.frequencies is None:
            raise RuntimeError("请先计算声子频率")
        
        if n_modes is None:
            n_modes = len(self.calculator.atoms) * 3
        
        kappa = np.zeros_like(temperatures)
        cumulative_kappa = []
        
        for T_idx, T in enumerate(temperatures):
            if T < 1e-6:
                kappa[T_idx] = 0
                cumulative_kappa.append(np.zeros(n_modes))
                continue
            
            kappa_total = 0
            kappa_by_band = np.zeros(n_modes)
            
            for seg_idx, freq_seg in enumerate(self.calculator.frequencies):
                for q_idx in range(freq_seg.shape[0]):
                    for band_idx in range(min(freq_seg.shape[1], n_modes)):
                        omega = freq_seg[q_idx, band_idx]
                        
                        if omega < 0.1:
                            continue
                        
                        omega_eV = omega * THz_to_eV
                        x = hbar * omega * 2 * np.pi / (kB * T)
                        x = np.clip(x, 1e-6, 100)
                        
                        Cv = 3 * kB * (x ** 2 * np.exp(x)) / (np.exp(x) - 1) ** 2
                        Cv_J = Cv * eV_to_J
                        
                        if self.lifetimes is not None and T_idx == 0:
                            try:
                                tau = self.lifetimes[seg_idx][q_idx, band_idx]
                            except IndexError:
                                tau = 1e-12
                        else:
                            if self.gruneisen_params is not None:
                                try:
                                    if (seg_idx < len(self.gruneisen_params) and 
                                        q_idx < len(self.gruneisen_params[seg_idx]) and
                                        band_idx < len(self.gruneisen_params[seg_idx][q_idx])):
                                        gamma = abs(self.gruneisen_params[seg_idx][q_idx, band_idx])
                                        gamma = np.clip(gamma, 0.1, 5.0)
                                    else:
                                        gamma = self.average_gamma
                                except (IndexError, TypeError):
                                    gamma = self.average_gamma
                            else:
                                gamma = self.average_gamma
                            
                            omega_rad = omega * 2 * np.pi * 1e12
                            tau = 1.0 / (gamma ** 2 * omega_rad ** 2 * T / 300 * 1e12)
                            tau = np.clip(tau, 1e-14, 1e-10)
                        
                        vg = vsound * 0.5 if band_idx < 3 else vsound * 0.8
                        
                        kappa_mode = 1/3 * Cv_J * vg ** 2 * tau
                        kappa_total += kappa_mode
                        kappa_by_band[band_idx] += kappa_mode
            
            n_qpoints = sum(f.shape[0] for f in self.calculator.frequencies)
            kappa[T_idx] = kappa_total / n_qpoints
            cumulative_kappa.append(kappa_by_band / n_qpoints)
        
        self.thermal_conductivity = kappa
        
        if np.any(temperatures == 300):
            kappa_300 = kappa[np.argmin(np.abs(temperatures - 300))]
            print(f"✅ 300K时晶格热导率: {kappa_300:.2f} W/mK")
        
        return kappa, np.array(cumulative_kappa)
    
    def plot_lifetimes(
        self,
        temperature: float = 300.0,
        save_path: Optional[str] = None,
        show: bool = True
    ):
        if self.lifetimes is None:
            self.calculate_lifetimes(temperature=temperature)
        
        all_distances = []
        all_tau = []
        all_freqs = []
        segment_ends = [0]
        
        for i, (q_seg, tau_seg, freq_seg) in enumerate(zip(
            self.calculator.qpoints, self.lifetimes, self.calculator.frequencies
        )):
            distances = np.linalg.norm(np.diff(q_seg, axis=0), axis=1)
            cumulative = np.concatenate([[0], np.cumsum(distances)])
            if i > 0:
                cumulative += segment_ends[-1]
            
            all_distances.extend(cumulative)
            all_tau.append(tau_seg * 1e12)
            all_freqs.append(freq_seg)
            segment_ends.append(cumulative[-1])
        
        all_distances = np.array(all_distances)
        all_tau = np.vstack(all_tau)
        all_freqs = np.vstack(all_freqs)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        for i in range(all_freqs.shape[1]):
            ax1.plot(all_distances, all_freqs[:, i], 'b-', linewidth=1.5, alpha=0.8)
        
        for end in segment_ends[1:-1]:
            ax1.axvline(x=end, color='gray', linestyle='--', linewidth=0.8)
        
        ax1.set_ylabel('Frequency (THz)', fontsize=12)
        ax1.set_title(f'Phonon Band Structure ({temperature}K)', fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        for i in range(all_tau.shape[1]):
            ax2.semilogy(all_distances, all_tau[:, i], 'r-', linewidth=1.5, alpha=0.8)
        
        for end in segment_ends[1:-1]:
            ax2.axvline(x=end, color='gray', linestyle='--', linewidth=0.8)
        
        if self.calculator.labels is not None:
            label_positions = [segment_ends[i] for i in range(len(self.calculator.labels)) 
                             if i < len(segment_ends)]
            ax2.set_xticks(label_positions)
            ax2.set_xticklabels(self.calculator.labels, fontsize=10)
        
        ax2.set_xlabel('Wave Vector', fontsize=12)
        ax2.set_ylabel('Lifetime (ps)', fontsize=12)
        ax2.set_title('Phonon Lifetimes', fontsize=14)
        ax2.grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return fig
    
    def plot_thermal_conductivity(
        self,
        temperatures: np.ndarray,
        cumulative_kappa: np.ndarray,
        save_path: Optional[str] = None,
        show: bool = True
    ):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        ax1.plot(temperatures, self.thermal_conductivity, 'b-', linewidth=2, label='Total κ')
        ax1.set_xlabel('Temperature (K)', fontsize=12)
        ax1.set_ylabel('Thermal Conductivity (W/mK)', fontsize=12)
        ax1.set_title('Lattice Thermal Conductivity', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        if cumulative_kappa is not None and cumulative_kappa.shape[1] > 0:
            n_bands = min(cumulative_kappa.shape[1], 6)
            colors = plt.cm.tab10(np.linspace(0, 1, n_bands))
            
            for i in range(n_bands):
                label = f'Acoustic' if i < 3 else f'Optic {i-2}'
                ax2.plot(temperatures, cumulative_kappa[:, i], 
                        color=colors[i], linewidth=2, label=label)
            
            ax2.set_xlabel('Temperature (K)', fontsize=12)
            ax2.set_ylabel('Thermal Conductivity (W/mK)', fontsize=12)
            ax2.set_title('Thermal Conductivity by Mode', fontsize=14)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return fig


class ThermodynamicProperties:
    def __init__(self, calculator: PhononCalculator):
        self.calculator = calculator
        self.temperatures = None
        self.helmholtz_free_energy = None
        self.entropy = None
        self.heat_capacity = None
        self.internal_energy = None
        
    def calculate_thermodynamic_properties(
        self,
        temperatures: np.ndarray,
        dos: Optional[np.ndarray] = None,
        dos_frequencies: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        print("⚛️  计算热力学性质...")
        
        if dos is None or dos_frequencies is None:
            if self.calculator.dos is None:
                self.calculator.calculate_dos()
            dos = self.calculator.dos
            dos_frequencies = self.calculator.dos_frequencies
        
        self.temperatures = temperatures
        F = np.zeros_like(temperatures)
        S = np.zeros_like(temperatures)
        Cv = np.zeros_like(temperatures)
        U = np.zeros_like(temperatures)
        
        omega = dos_frequencies * 2 * np.pi * 1e12
        
        for T_idx, T in enumerate(temperatures):
            if T < 1e-6:
                F[T_idx] = 0
                S[T_idx] = 0
                Cv[T_idx] = 0
                U[T_idx] = 0
                continue
            
            x = hbar * omega / (kB * T)
            x = np.clip(x, 1e-6, 100)
            
            zero_point = 0.5 * hbar * omega
            thermal_excitation = hbar * omega / (np.exp(x) - 1)
            u_per_mode = zero_point + thermal_excitation
            
            U[T_idx] = simpson(u_per_mode * dos, omega / (2 * np.pi * 1e12))
            
            free_energy_per_mode = hbar * omega * (0.5 + 1 / (np.exp(x) - 1))
            F[T_idx] = simpson(free_energy_per_mode * dos, omega / (2 * np.pi * 1e12))
            
            s_per_mode = kB * (x / (np.exp(x) - 1) - np.log(1 - np.exp(-x)))
            S[T_idx] = simpson(s_per_mode * dos, omega / (2 * np.pi * 1e12))
            
            cv_per_mode = kB * (x ** 2 * np.exp(x)) / (np.exp(x) - 1) ** 2
            Cv[T_idx] = simpson(cv_per_mode * dos, omega / (2 * np.pi * 1e12))
        
        self.helmholtz_free_energy = F
        self.entropy = S
        self.heat_capacity = Cv
        self.internal_energy = U
        
        print(f"✅ 热力学性质计算完成")
        if np.any(temperatures == 300):
            idx = np.argmin(np.abs(temperatures - 300))
            print(f"   300K时:")
            print(f"     Cv = {Cv[idx]:.3f} J/mol·K")
            print(f"     S  = {S[idx]:.3f} J/mol·K")
        
        return {
            'T': temperatures,
            'F': F,
            'S': S,
            'Cv': Cv,
            'U': U
        }
    
    def plot_thermodynamic_properties(
        self,
        save_path: Optional[str] = None,
        show: bool = True
    ):
        if self.temperatures is None:
            raise RuntimeError("请先计算热力学性质")
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        axes[0, 0].plot(self.temperatures, self.internal_energy * 1e3, 'b-', linewidth=2)
        axes[0, 0].set_xlabel('Temperature (K)', fontsize=12)
        axes[0, 0].set_ylabel('Internal Energy U (meV/atom)', fontsize=12)
        axes[0, 0].set_title('Internal Energy', fontsize=14)
        axes[0, 0].grid(True, alpha=0.3)
        
        axes[0, 1].plot(self.temperatures, self.helmholtz_free_energy * 1e3, 'r-', linewidth=2)
        axes[0, 1].set_xlabel('Temperature (K)', fontsize=12)
        axes[0, 1].set_ylabel('Free Energy F (meV/atom)', fontsize=12)
        axes[0, 1].set_title('Helmholtz Free Energy', fontsize=14)
        axes[0, 1].grid(True, alpha=0.3)
        
        axes[1, 0].plot(self.temperatures, self.entropy, 'g-', linewidth=2)
        axes[1, 0].set_xlabel('Temperature (K)', fontsize=12)
        axes[1, 0].set_ylabel('Entropy S (J/mol·K)', fontsize=12)
        axes[1, 0].set_title('Entropy', fontsize=14)
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].plot(self.temperatures, self.heat_capacity, 'm-', linewidth=2)
        axes[1, 1].axhline(y=3 * 8.314, color='k', linestyle='--', 
                          label='Dulong-Petit limit')
        axes[1, 1].set_xlabel('Temperature (K)', fontsize=12)
        axes[1, 1].set_ylabel('Heat Capacity Cv (J/mol·K)', fontsize=12)
        axes[1, 1].set_title('Heat Capacity at Constant Volume', fontsize=14)
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        
        return fig


def run_advanced_example():
    print("=" * 80)
    print("Advanced Phonon Calculations: QHA, Grüneisen, Lifetime, Thermal Conductivity")
    print("=" * 80)
    
    a = 5.431
    atoms = Atoms(
        symbols=['Si', 'Si'],
        cell=[[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]],
        scaled_positions=[[0, 0, 0], [0.25, 0.25, 0.25]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    print("\n" + "=" * 80)
    print("Step 1: 基础声子计算")
    print("=" * 80)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    calculator.calculate_band_structure(use_seekpath=True)
    calculator.calculate_dos(mesh=(15, 15, 15))
    
    print("\n" + "=" * 80)
    print("Step 2: 准谐近似 (QHA) - 热膨胀系数")
    print("=" * 80)
    
    simple_path = [
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 20),
        (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 20),
        (np.array([1, 1, 1]), np.array([0, 0, 0]), 20),
    ]
    simple_labels = ['Γ', 'X', 'L', 'Γ']
    calculator.calculate_band_structure(path=simple_path, labels=simple_labels, npoints=20, use_seekpath=False)
    
    qha = QuasiHarmonicApproximation(calculator, volume_scales=[0.98, 0.99, 1.00, 1.01, 1.02])
    qha.calculate_frequencies_at_volumes(npoints=21, use_seekpath=False)
    
    temperatures = np.linspace(0, 800, 101)
    alpha, Cv = qha.calculate_thermal_expansion(temperatures, bulk_modulus=98.0)
    
    print("\n" + "=" * 80)
    print("Step 3: 声子寿命与热导率")
    print("=" * 80)
    
    lifetime_calc = PhononLifetime(calculator, gruneisen_params=qha.gruneisen_parameters)
    lifetime_calc.calculate_lifetimes(temperature=300.0)
    kappa, cumulative_kappa = lifetime_calc.calculate_thermal_conductivity(
        temperatures, vsound=6400.0
    )
    
    print("\n" + "=" * 80)
    print("Step 4: 热力学性质")
    print("=" * 80)
    
    thermo = ThermodynamicProperties(calculator)
    thermo.calculate_thermodynamic_properties(temperatures)
    
    print("\n" + "=" * 80)
    print("Step 5: 可视化结果")
    print("=" * 80)
    
    qha.plot_gruneisen_band_structure(save_path='gruneisen_bands.png', show=False)
    print("✅ Grüneisen参数图已保存: gruneisen_bands.png")
    
    lifetime_calc.plot_lifetimes(temperature=300, save_path='phonon_lifetimes.png', show=False)
    print("✅ 声子寿命图已保存: phonon_lifetimes.png")
    
    lifetime_calc.plot_thermal_conductivity(
        temperatures, cumulative_kappa, 
        save_path='thermal_conductivity.png', show=False
    )
    print("✅ 热导率图已保存: thermal_conductivity.png")
    
    thermo.plot_thermodynamic_properties(save_path='thermodynamic_properties.png', show=False)
    print("✅ 热力学性质图已保存: thermodynamic_properties.png")
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    axes[0, 0].plot(temperatures, alpha * 1e6, 'r-', linewidth=2)
    axes[0, 0].set_xlabel('Temperature (K)', fontsize=12)
    axes[0, 0].set_ylabel('Thermal Expansion Coefficient α (10⁻⁶ K⁻¹)', fontsize=12)
    axes[0, 0].set_title('Thermal Expansion Coefficient', fontsize=14)
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].axvline(x=300, color='k', linestyle='--', alpha=0.5)
    
    axes[0, 1].plot(temperatures, Cv, 'g-', linewidth=2)
    axes[0, 1].axhline(y=3 * 8.314 * len(atoms), color='k', linestyle='--', 
                      label='Dulong-Petit limit')
    axes[0, 1].set_xlabel('Temperature (K)', fontsize=12)
    axes[0, 1].set_ylabel('Heat Capacity Cv (J/mol·K)', fontsize=12)
    axes[0, 1].set_title('Heat Capacity (from QHA)', fontsize=14)
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    
    axes[1, 0].plot(temperatures, kappa, 'b-', linewidth=2)
    axes[1, 0].set_xlabel('Temperature (K)', fontsize=12)
    axes[1, 0].set_ylabel('Thermal Conductivity κ (W/mK)', fontsize=12)
    axes[1, 0].set_title('Lattice Thermal Conductivity', fontsize=14)
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].axvline(x=300, color='k', linestyle='--', alpha=0.5)
    
    gamma_avg = [np.mean(g) for g in qha.gruneisen_parameters]
    axes[1, 1].hist(np.concatenate([g.flatten() for g in qha.gruneisen_parameters]), 
                    bins=50, density=True, alpha=0.7, color='purple')
    axes[1, 1].set_xlabel('Grüneisen Parameter γ', fontsize=12)
    axes[1, 1].set_ylabel('Probability Density', fontsize=12)
    axes[1, 1].set_title('Grüneisen Parameter Distribution', fontsize=14)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].axvline(x=np.mean(np.concatenate([g.flatten() for g in qha.gruneisen_parameters])), 
                       color='r', linestyle='--', label='Mean')
    axes[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig('advanced_properties_summary.png', dpi=300, bbox_inches='tight')
    print("✅ 综合性质图已保存: advanced_properties_summary.png")
    
    print("\n" + "=" * 80)
    print("📊 结果摘要")
    print("=" * 80)
    print(f"材料: FCC Silicon (Si)")
    print(f"晶格常数: {a:.3f} Å")
    print(f"体积: {calculator.atoms.get_cell().volume:.2f} Å³")
    print(f"超胞: {np.diag(supercell_matrix)}")
    
    idx_300 = np.argmin(np.abs(temperatures - 300))
    print(f"\n300K时的性质:")
    print(f"  热膨胀系数 α = {alpha[idx_300]*1e6:.2f} × 10⁻⁶ K⁻¹")
    print(f"  热容 Cv = {Cv[idx_300]:.2f} J/mol·K")
    print(f"  热导率 κ = {kappa[idx_300]:.2f} W/mK")
    print(f"  平均Grüneisen参数 γ = {np.mean([np.mean(g) for g in qha.gruneisen_parameters]):.3f}")
    
    print("\n✅ 所有高级计算完成！")
    
    return {
        'qha': qha,
        'lifetime': lifetime_calc,
        'thermodynamic': thermo,
        'temperatures': temperatures,
        'alpha': alpha,
        'Cv': Cv,
        'kappa': kappa
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Phonon Calculations')
    parser.add_argument('--run', action='store_true', help='Run advanced example')
    
    args = parser.parse_args()
    
    if args.run:
        run_advanced_example()
    else:
        print("=" * 80)
        print("Advanced Phonon Module")
        print("=" * 80)
        print()
        print("可用功能:")
        print("  1. QuasiHarmonicApproximation - 准谐近似，热膨胀系数")
        print("  2. PhononLifetime - 声子寿命与热导率")
        print("  3. ThermodynamicProperties - 热力学性质计算")
        print()
        print("运行示例:")
        print("  python phonon_advanced.py --run")
        print()
        print("或在Python中使用:")
        print("  from phonon_advanced import QuasiHarmonicApproximation")
        print("  qha = QuasiHarmonicApproximation(calculator)")
        print()
