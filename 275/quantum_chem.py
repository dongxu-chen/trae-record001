import numpy as np
from pyscf import gto, scf, dft, grad, hessian
from pyscf.geomopt.berny_solver import optimize
from pyscf import solvent, tddft
from rdkit import Chem
from rdkit.Chem import AllChem
import warnings
warnings.filterwarnings('ignore')


class DIIS:
    def __init__(self, n_diis=8, start_iter=3):
        self.n_diis = n_diis
        self.start_iter = start_iter
        self.fock_list = []
        self.error_list = []
        self.coeff_list = []

    def update(self, fock, error, cycle):
        if cycle < self.start_iter:
            return fock

        self.fock_list.append(fock.copy())
        self.error_list.append(error.copy())

        if len(self.fock_list) > self.n_diis:
            self.fock_list.pop(0)
            self.error_list.pop(0)

        if len(self.fock_list) < 2:
            return fock

        n = len(self.fock_list)
        B = np.zeros((n + 1, n + 1))
        B[n, :] = -1
        B[:, n] = -1
        B[n, n] = 0

        for i in range(n):
            for j in range(i, n):
                B[i, j] = np.einsum('ij,ij->', self.error_list[i], self.error_list[j])
                B[j, i] = B[i, j]

        rhs = np.zeros(n + 1)
        rhs[n] = -1

        try:
            coeff = np.linalg.solve(B, rhs)
            fock_new = np.zeros_like(fock)
            for i in range(n):
                fock_new += coeff[i] * self.fock_list[i]
            return fock_new
        except np.linalg.LinAlgError:
            return fock


class SolventPCM:
    SOLVENTS = {
        'water': {'eps': 78.39, 'epsinf': 1.78},
        'methanol': {'eps': 32.63, 'epsinf': 1.76},
        'ethanol': {'eps': 24.55, 'epsinf': 1.85},
        'acetone': {'eps': 20.49, 'epsinf': 1.85},
        'dichloromethane': {'eps': 8.93, 'epsinf': 2.03},
        'chloroform': {'eps': 4.81, 'epsinf': 2.09},
        'hexane': {'eps': 1.88, 'epsinf': 1.37},
        'toluene': {'eps': 2.38, 'epsinf': 1.55},
        'thf': {'eps': 7.58, 'epsinf': 1.98},
        'dmso': {'eps': 46.7, 'epsinf': 2.01},
        'acetonitrile': {'eps': 35.94, 'epsinf': 1.81},
    }

    def __init__(self, solvent='water', method='pcm'):
        if solvent.lower() not in self.SOLVENTS:
            raise ValueError(f"Unsupported solvent. Choose from: {list(self.SOLVENTS.keys())}")
        self.solvent = solvent.lower()
        self.method = method
        self.eps = self.SOLVENTS[self.solvent]['eps']
        self.epsinf = self.SOLVENTS[self.solvent]['epsinf']

    def apply(self, mf):
        try:
            mf_sol = solvent.ddCOSMO(mf)
            mf_sol.with_solvent.eps = self.eps
            mf_sol.with_solvent.epsinf = self.epsinf
            return mf_sol
        except:
            try:
                mf_sol = solvent.PCM(mf)
                mf_sol.with_solvent.eps = self.eps
                return mf_sol
            except:
                return mf


class QuantumChemistry:
    VALID_BASIS = {'sto-3g', '6-31g', 'cc-pvdz'}
    VALID_METHODS = {'hf', 'dft'}
    VALID_DFT_FUNCTIONALS = {'b3lyp', 'pbe', 'bp86', 'blyp', 'cam-b3lyp'}

    def __init__(self, basis='sto-3g', method='hf', functional='b3lyp', verbose=0,
                 use_diis=True, diis_n=8, diis_start=3,
                 conv_tol_init=1e-6, conv_tol_final=1e-10, conv_tightening_start=10,
                 freq_imag_threshold=-50.0,
                 solvent=None, solvent_method='pcm'):
        if basis.lower() not in self.VALID_BASIS:
            raise ValueError(f"Invalid basis set. Choose from {self.VALID_BASIS}")
        if method.lower() not in self.VALID_METHODS:
            raise ValueError(f"Invalid method. Choose from {self.VALID_METHODS}")
        if functional.lower() not in self.VALID_DFT_FUNCTIONALS:
            raise ValueError(f"Invalid DFT functional. Choose from {self.VALID_DFT_FUNCTIONALS}")

        self.basis = basis.lower()
        self.method = method.lower()
        self.functional = functional.lower()
        self.verbose = verbose
        
        self.use_diis = use_diis
        self.diis_n = diis_n
        self.diis_start = diis_start
        
        self.conv_tol_init = conv_tol_init
        self.conv_tol_final = conv_tol_final
        self.conv_tightening_start = conv_tightening_start
        
        self.freq_imag_threshold = freq_imag_threshold
        
        self.solvent = solvent
        self.solvent_method = solvent_method
        self.solvent_obj = None
        if solvent is not None:
            self.solvent_obj = SolventPCM(solvent, solvent_method)
        
        self.mol = None
        self.mf = None
        self.results = {}
        self.scf_convergence_history = []

    def _dynamic_conv_tol(self, cycle):
        if cycle < self.conv_tightening_start:
            return self.conv_tol_init
        else:
            factor = (cycle - self.conv_tightening_start + 1) / 10.0
            factor = min(factor, 1.0)
            return self.conv_tol_init * (1 - factor) + self.conv_tol_final * factor

    def load_molecule_from_xyz(self, xyz_string):
        lines = xyz_string.strip().split('\n')
        if len(lines) < 2:
            raise ValueError("Invalid XYZ format")
        
        atom_list = []
        for line in lines[2:]:
            parts = line.split()
            if len(parts) >= 4:
                symbol = parts[0]
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                atom_list.append(f"{symbol} {x} {y} {z}")
        
        mol_str = '; '.join(atom_list)
        self.mol = gto.M(
            atom=mol_str,
            basis=self.basis,
            verbose=self.verbose
        )
        return self

    def load_molecule_from_xyz_file(self, filepath):
        with open(filepath, 'r') as f:
            xyz_content = f.read()
        return self.load_molecule_from_xyz(xyz_content)

    def load_molecule_from_smiles(self, smiles, generate_3d=True):
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smiles}")
        
        mol = Chem.AddHs(mol)
        
        if generate_3d:
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)
        
        conf = mol.GetConformer()
        atom_list = []
        
        for i in range(mol.GetNumAtoms()):
            atom = mol.GetAtomWithIdx(i)
            pos = conf.GetAtomPosition(i)
            atom_list.append(f"{atom.GetSymbol()} {pos.x} {pos.y} {pos.z}")
        
        mol_str = '; '.join(atom_list)
        self.mol = gto.M(
            atom=mol_str,
            basis=self.basis,
            verbose=self.verbose
        )
        return self

    def _setup_mf(self):
        if self.method == 'hf':
            self.mf = scf.RHF(self.mol)
        elif self.method == 'dft':
            self.mf = dft.RKS(self.mol)
            self.mf.xc = self.functional

        if self.use_diis:
            self.mf.diis = scf.diis.DIIS()
            self.mf.diis_space = self.diis_n
            self.mf.diis_start_cycle = self.diis_start

        if self.solvent_obj is not None:
            self.mf = self.solvent_obj.apply(self.mf)

        self.mf.conv_tol = self.conv_tol_final
        return self.mf

    def run_single_point(self, max_cycles=100):
        if self.mol is None:
            raise ValueError("Molecule not loaded. Call load_molecule first.")

        self._setup_mf()
        self.mf.max_cycle = max_cycles

        self.scf_convergence_history = []
        
        def callback(envs):
            cycle = envs['cycle']
            current_tol = self._dynamic_conv_tol(cycle)
            if 'e_delta' in envs:
                self.scf_convergence_history.append({
                    'cycle': cycle,
                    'energy': envs['e_tot'],
                    'e_delta': envs['e_delta'],
                    'conv_tol': current_tol
                })
        
        if hasattr(self.mf, 'callback'):
            self.mf.callback = callback
        
        self.mf.kernel()
        
        self._extract_results()
        return self.results

    def _extract_results(self):
        if self.mf is None or not hasattr(self.mf, 'e_tot'):
            return

        self.results['total_energy'] = self.mf.e_tot
        self.results['scf_converged'] = self.mf.converged
        
        if self.solvent is not None:
            self.results['solvent'] = self.solvent
            if hasattr(self.mf, 'e_solvent'):
                self.results['solvent_energy'] = self.mf.e_solvent
        
        if self.scf_convergence_history:
            self.results['scf_history'] = self.scf_convergence_history
        
        if hasattr(self.mf, 'mo_energy'):
            self.results['orbital_energies'] = self.mf.mo_energy
            self.results['homo_energy'] = self.mf.mo_energy[self.mol.nelectron // 2 - 1]
            self.results['lumo_energy'] = self.mf.mo_energy[self.mol.nelectron // 2]
            self.results['homo_lumo_gap'] = self.results['lumo_energy'] - self.results['homo_energy']
        
        if hasattr(self.mf, 'mo_occ'):
            self.results['orbital_occupancies'] = self.mf.mo_occ

        try:
            dm = self.mf.make_rdm1()
            self.results['density_matrix'] = dm
        except:
            pass

        try:
            dip = self.mf.dip_moment()
            self.results['dipole_moment'] = dip
            self.results['dipole_magnitude'] = np.linalg.norm(dip)
        except:
            pass

        if hasattr(self.mol, 'atom_coords'):
            self.results['atomic_coordinates'] = self.mol.atom_coords()
            self.results['atomic_symbols'] = [self.mol.atom_pure_symbol(i) for i in range(self.mol.natm)]

    def _trust_radius_optimize(self, max_cycles=50, trust_radius_init=0.3, 
                                trust_radius_min=0.01, trust_radius_max=1.0,
                                energy_tol=1e-6, grad_tol=1e-4):
        if self.mf is None:
            self.run_single_point()

        coords = self.mol.atom_coords().copy()
        trust_radius = trust_radius_init
        energy_prev = self.mf.e_tot
        
        self.results['opt_history'] = []
        
        for cycle in range(max_cycles):
            grad_obj = grad.RHF(self.mf) if self.method == 'hf' else grad.RKS(self.mf)
            gradient = grad_obj.kernel()
            grad_norm = np.linalg.norm(gradient)
            
            step = -gradient * min(trust_radius / max(grad_norm, 1e-8), 1.0)
            
            mol_new = gto.M(
                atom=[(self.mol.atom_pure_symbol(i), 
                       coords[i, 0] + step[i, 0],
                       coords[i, 1] + step[i, 1],
                       coords[i, 2] + step[i, 2]) 
                      for i in range(self.mol.natm)],
                basis=self.basis,
                verbose=self.verbose
            )
            
            if self.method == 'hf':
                mf_new = scf.RHF(mol_new)
            else:
                mf_new = dft.RKS(mol_new)
                mf_new.xc = self.functional
            
            if self.use_diis:
                mf_new.diis = scf.diis.DIIS()
                mf_new.diis_space = self.diis_n
                mf_new.diis_start_cycle = self.diis_start
            
            if self.solvent_obj is not None:
                mf_new = self.solvent_obj.apply(mf_new)
            
            mf_new.conv_tol = self.conv_tol_final
            mf_new.max_cycle = 50
            mf_new.kernel()
            
            energy_new = mf_new.e_tot
            energy_change = energy_new - energy_prev
            
            rho = -energy_change / max(0.5 * grad_norm * np.linalg.norm(step), 1e-10)
            
            if rho > 0.75:
                trust_radius = min(2.0 * trust_radius, trust_radius_max)
                coords += step
                energy_prev = energy_new
                self.mol = mol_new
                self.mf = mf_new
            elif rho > 0.25:
                coords += step
                energy_prev = energy_new
                self.mol = mol_new
                self.mf = mf_new
            else:
                trust_radius = max(0.25 * trust_radius, trust_radius_min)
            
            self.results['opt_history'].append({
                'cycle': cycle + 1,
                'energy': energy_prev,
                'grad_norm': grad_norm,
                'trust_radius': trust_radius,
                'energy_change': energy_change
            })
            
            if self.verbose >= 1:
                print(f"Cycle {cycle+1}: E = {energy_prev:.8f}, |g| = {grad_norm:.6f}, "
                      f"trust = {trust_radius:.4f}, dE = {energy_change:.2e}")
            
            if abs(energy_change) < energy_tol and grad_norm < grad_tol:
                if self.verbose >= 1:
                    print(f"Converged in {cycle + 1} cycles!")
                break
        
        return self.results

    def optimize_geometry(self, max_cycles=50, method='adaptive', **kwargs):
        if self.mol is None:
            raise ValueError("Molecule not loaded. Call load_molecule first.")

        if self.mf is None:
            self.run_single_point()

        if method.lower() == 'adaptive' or method.lower() == 'trust_radius':
            self._trust_radius_optimize(max_cycles=max_cycles, **kwargs)
        else:
            mol_eq = optimize(self.mf, maxsteps=max_cycles)
            self.mol = mol_eq
            self._setup_mf()
            self.mf.kernel()
        
        self._extract_results()
        return self.results

    def run_frequency_analysis(self, imag_threshold=None):
        if self.mf is None or self.mol is None:
            raise ValueError("Run single point or geometry optimization first.")

        if imag_threshold is None:
            imag_threshold = self.freq_imag_threshold

        if self.method == 'hf':
            hess_obj = hessian.RHF(self.mf)
        else:
            hess_obj = hessian.RKS(self.mf)
        
        h = hess_obj.kernel()
        
        mass = self.mol.atom_mass_list()
        mass = np.sqrt(np.repeat(mass, 3))
        
        h = h.reshape(self.mol.natm * 3, self.mol.natm * 3)
        h = h / mass[:, None] / mass[None, :]
        
        e, v = np.linalg.eigh(h)
        
        freq = np.sqrt(np.abs(e)) * 219474.63 * np.sign(e)
        
        self.results['frequencies'] = freq
        self.results['force_constants'] = e
        self.results['frequency_normal_modes'] = v
        
        translations = freq[:3]
        rotations = freq[3:6]
        vibrations = freq[6:]
        
        self.results['translational_freq'] = translations
        self.results['rotational_freq'] = rotations
        self.results['vibrational_freq'] = vibrations
        
        imaginary_freqs = vibrations[vibrations < imag_threshold]
        n_imaginary = len(imaginary_freqs)
        
        self.results['imaginary_frequencies'] = imaginary_freqs
        self.results['n_imaginary_frequencies'] = n_imaginary
        self.results['is_stable'] = n_imaginary == 0
        self.results['imag_threshold'] = imag_threshold
        
        if n_imaginary > 0:
            self.results['small_imag_freqs'] = vibrations[(vibrations >= imag_threshold) & (vibrations < 0)]
        
        return self.results

    def run_tddft(self, nstates=10, singlet=True, oscillator_strength=True):
        if self.mf is None:
            raise ValueError("Run single point calculation first.")
        
        if self.method != 'dft':
            print("Warning: TD-DFT requires DFT method. Switching to TD-HF.")
        
        try:
            mytd = tddft.TDA(self.mf) if singlet else tddft.UFC(self.mf)
            mytd.nstates = nstates
            mytd.kernel()
            
            energies_eV = mytd.e * 27.2114
            wavelengths_nm = 1240.0 / energies_eV
            
            self.results['excited_states'] = {
                'energies_hartree': mytd.e,
                'energies_eV': energies_eV,
                'wavelengths_nm': wavelengths_nm,
                'nstates': nstates
            }
            
            if oscillator_strength and hasattr(mytd, 'oscillator_strength'):
                osc = mytd.oscillator_strength()
                self.results['excited_states']['oscillator_strengths'] = osc
            
            if hasattr(mytd, 'transition_dipole'):
                self.results['excited_states']['transition_dipoles'] = mytd.transition_dipole
            
            return self.results['excited_states']
        except Exception as e:
            print(f"TD-DFT calculation failed: {e}")
            return None

    def predict_absorption_spectrum(self, nstates=10, broadening='gaussian', 
                                     fwhm=0.3, energy_range=(1.5, 6.0), npoints=200):
        if 'excited_states' not in self.results:
            self.run_tddft(nstates=nstates)
        
        exc = self.results['excited_states']
        energies = exc['energies_eV']
        osc = exc.get('oscillator_strengths', np.ones_like(energies))
        
        x = np.linspace(energy_range[0], energy_range[1], npoints)
        y = np.zeros_like(x)
        
        sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
        
        for e, o in zip(energies, osc):
            if broadening == 'gaussian':
                y += o * np.exp(-(x - e)**2 / (2 * sigma**2))
            elif broadening == 'lorentzian':
                y += o * (fwhm / 2) / ((x - e)**2 + (fwhm / 2)**2)
        
        wavelengths = 1240.0 / x
        
        self.results['absorption_spectrum'] = {
            'energies_eV': x,
            'wavelengths_nm': wavelengths,
            'intensity': y,
            'peak_energies_eV': energies,
            'peak_wavelengths_nm': 1240.0 / energies,
            'oscillator_strengths': osc
        }
        
        return self.results['absorption_spectrum']

    def calculate_hirshfeld_charges(self):
        if self.mf is None:
            raise ValueError("Run single point calculation first.")
        
        try:
            from pyscf import lo
            dm = self.mf.make_rdm1()
            hirshfeld = lo.hirshfeld.Hirshfeld(self.mol)
            charges = hirshfeld.kernel(dm)
            self.results['hirshfeld_charges'] = charges
            return charges
        except:
            return None

    def get_results_summary(self):
        summary = []
        summary.append("=" * 60)
        summary.append("Quantum Chemistry Calculation Results")
        summary.append("=" * 60)
        summary.append(f"Method: {self.method.upper()}")
        if self.method == 'dft':
            summary.append(f"Functional: {self.functional.upper()}")
        summary.append(f"Basis Set: {self.basis}")
        summary.append(f"DIIS acceleration: {'Enabled' if self.use_diis else 'Disabled'}")
        if self.solvent is not None:
            summary.append(f"Solvent (PCM): {self.solvent}")
        summary.append("-" * 60)

        if 'scf_converged' in self.results:
            summary.append(f"SCF Converged: {self.results['scf_converged']}")

        if 'total_energy' in self.results:
            summary.append(f"Total Energy: {self.results['total_energy']:.8f} Hartree")
            summary.append(f"              {self.results['total_energy'] * 27.2114:.4f} eV")
            if 'solvent_energy' in self.results:
                summary.append(f"Solvent Energy: {self.results['solvent_energy']:.8f} Hartree")
        
        if 'homo_energy' in self.results:
            summary.append(f"HOMO Energy: {self.results['homo_energy']:.6f} Hartree")
            summary.append(f"LUMO Energy: {self.results['lumo_energy']:.6f} Hartree")
            summary.append(f"HOMO-LUMO Gap: {self.results['homo_lumo_gap']:.6f} Hartree")
            summary.append(f"                {self.results['homo_lumo_gap'] * 27.2114:.4f} eV")

        if 'dipole_moment' in self.results:
            dip = self.results['dipole_moment']
            summary.append(f"Dipole Moment (x,y,z): [{dip[0]:.4f}, {dip[1]:.4f}, {dip[2]:.4f}] a.u.")
            summary.append(f"Dipole Moment Magnitude: {self.results['dipole_magnitude']:.4f} a.u.")

        if 'excited_states' in self.results:
            exc = self.results['excited_states']
            summary.append("-" * 60)
            summary.append("Excited States (TD-DFT):")
            n_show = min(5, exc['nstates'])
            for i in range(n_show):
                line = f"  S{i+1}: {exc['energies_eV'][i]:.3f} eV"
                line += f" ({exc['wavelengths_nm'][i]:.1f} nm)"
                if 'oscillator_strengths' in exc:
                    line += f", f = {exc['oscillator_strengths'][i]:.4f}"
                summary.append(line)

        if 'vibrational_freq' in self.results:
            vib_freq = self.results['vibrational_freq']
            summary.append("-" * 60)
            summary.append(f"Frequency Analysis (imag. threshold: {self.results.get('imag_threshold', -50):.1f} cm⁻¹)")
            summary.append("Vibrational Frequencies (cm^-1):")
            
            n_imag = self.results.get('n_imaginary_frequencies', 0)
            if n_imag > 0:
                imag_freqs = self.results.get('imaginary_frequencies', [])
                summary.append(f"  WARNING: {n_imag} imaginary frequency(ies) detected!")
                for f in imag_freqs[:5]:
                    summary.append(f"    Imaginary: {f:.2f} cm⁻¹")
            
            for i, f in enumerate(vib_freq[:10]):
                if f >= 0:
                    summary.append(f"  Mode {i+1}: {f:.2f}")
                else:
                    summary.append(f"  Mode {i+1}: {f:.2f} (imaginary)")
            if len(vib_freq) > 10:
                summary.append(f"  ... and {len(vib_freq) - 10} more modes")
            summary.append(f"Structure is stable: {self.results['is_stable']}")

        if 'opt_history' in self.results:
            hist = self.results['opt_history']
            summary.append("-" * 60)
            summary.append(f"Geometry Optimization: {len(hist)} cycles")
            if hist:
                summary.append(f"  Initial energy: {hist[0]['energy']:.8f} Hartree")
                summary.append(f"  Final energy:   {hist[-1]['energy']:.8f} Hartree")
                summary.append(f"  Final |grad|:   {hist[-1]['grad_norm']:.6f}")

        if 'hirshfeld_charges' in self.results:
            summary.append("-" * 60)
            summary.append("Hirshfeld Charges:")
            symbols = self.results.get('atomic_symbols', [])
            for i, (sym, q) in enumerate(zip(symbols, self.results['hirshfeld_charges'])):
                summary.append(f"  {sym}{i}: {q:.4f}")

        summary.append("=" * 60)
        return "\n".join(summary)

    def save_results(self, filepath):
        save_dict = {}
        for k, v in self.results.items():
            if isinstance(v, np.ndarray):
                save_dict[k] = v
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                pass
            elif isinstance(v, (int, float, str, bool)):
                save_dict[k] = np.array([v])
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, np.ndarray):
                        save_dict[f"{k}_{k2}"] = v2
        
        np.savez(filepath, **save_dict)
        
        with open(filepath.replace('.npz', '.txt'), 'w') as f:
            f.write(self.get_results_summary())
            
            if 'atomic_coordinates' in self.results and 'atomic_symbols' in self.results:
                f.write("\n\nAtomic Coordinates:\n")
                coords = self.results['atomic_coordinates']
                symbols = self.results['atomic_symbols']
                for sym, coord in zip(symbols, coords):
                    f.write(f"{sym:4s} {coord[0]:10.6f} {coord[1]:10.6f} {coord[2]:10.6f}\n")


class ReactionPathFinder:
    def __init__(self, basis='sto-3g', method='dft', functional='b3lyp', verbose=0):
        self.basis = basis
        self.method = method
        self.functional = functional
        self.verbose = verbose

    def _create_calculator(self, **kwargs):
        return QuantumChemistry(
            basis=self.basis,
            method=self.method,
            functional=self.functional,
            verbose=self.verbose,
            **kwargs
        )

    def calculate_reaction_energy(self, reactant_smiles, product_smiles):
        qc_r = self._create_calculator()
        qc_r.load_molecule_from_smiles(reactant_smiles)
        qc_r.optimize_geometry(max_cycles=30, method='adaptive')
        e_reactant = qc_r.results['total_energy']
        
        qc_p = self._create_calculator()
        qc_p.load_molecule_from_smiles(product_smiles)
        qc_p.optimize_geometry(max_cycles=30, method='adaptive')
        e_product = qc_p.results['total_energy']
        
        delta_e = (e_product - e_reactant) * 27.2114
        
        return {
            'reactant_energy_Hartree': e_reactant,
            'product_energy_Hartree': e_product,
            'reaction_energy_eV': delta_e,
            'reaction_energy_kJmol': delta_e * 96.485
        }

    def linear_transit_search(self, reactant_coords, product_coords, atoms, nimages=10):
        images = []
        energies = []
        
        for i in range(nimages):
            alpha = i / (nimages - 1)
            coords = (1 - alpha) * reactant_coords + alpha * product_coords
            
            mol_str = '; '.join([f"{atoms[j]} {coords[j,0]} {coords[j,1]} {coords[j,2]}" 
                                for j in range(len(atoms))])
            
            mol = gto.M(atom=mol_str, basis=self.basis, verbose=self.verbose)
            
            if self.method == 'hf':
                mf = scf.RHF(mol)
            else:
                mf = dft.RKS(mol)
                mf.xc = self.functional
            
            mf.conv_tol = 1e-8
            mf.kernel()
            
            images.append(coords.copy())
            energies.append(mf.e_tot)
        
        return {
            'images': images,
            'energies_Hartree': np.array(energies),
            'energies_eV': (np.array(energies) - min(energies)) * 27.2114,
            'barrier_eV': (max(energies) - min(energies)) * 27.2114
        }

    def find_transition_state_guess(self, reactant_smiles, product_smiles, nimages=12):
        qc_r = self._create_calculator()
        qc_r.load_molecule_from_smiles(reactant_smiles)
        qc_r.optimize_geometry(max_cycles=30, method='adaptive')
        coords_r = qc_r.results['atomic_coordinates'].copy()
        atoms = qc_r.results['atomic_symbols']
        
        qc_p = self._create_calculator()
        qc_p.load_molecule_from_smiles(product_smiles)
        qc_p.optimize_geometry(max_cycles=30, method='adaptive')
        coords_p = qc_p.results['atomic_coordinates'].copy()
        
        if len(atoms) != len(qc_p.results['atomic_symbols']):
            raise ValueError("Reactant and product must have same number of atoms")
        
        path = self.linear_transit_search(coords_r, coords_p, atoms, nimages=nimages)
        ts_idx = np.argmax(path['energies_Hartree'])
        ts_coords = path['images'][ts_idx]
        
        return {
            'ts_guess_coords': ts_coords,
            'atoms': atoms,
            'energy_profile': path,
            'reactant_coords': coords_r,
            'product_coords': coords_p
        }

    def approximate_barrier(self, reactant_smiles, product_smiles, solvent=None):
        qc_r = self._create_calculator(solvent=solvent)
        qc_r.load_molecule_from_smiles(reactant_smiles)
        qc_r.run_single_point()
        e_reactant = qc_r.results['total_energy']
        
        qc_p = self._create_calculator(solvent=solvent)
        qc_p.load_molecule_from_smiles(product_smiles)
        qc_p.run_single_point()
        e_product = qc_p.results['total_energy']
        
        delta_e = (e_product - e_reactant) * 27.2114
        approx_barrier = abs(delta_e) * 0.5 + 1.0
        
        return {
            'reaction_energy_eV': delta_e,
            'approximate_barrier_eV': approx_barrier,
            'solvent': solvent
        }


def example_usage():
    print("Example 1: PCM Solvent Effect (Water)")
    print("-" * 60)
    qc = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp', 
                          verbose=0, use_diis=True, solvent='water')
    qc.load_molecule_from_smiles('O')
    qc.run_single_point()
    print(qc.get_results_summary())
    
    print("\n\nExample 2: TD-DFT Excited States")
    print("-" * 60)
    qc2 = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                          verbose=0, use_diis=True)
    qc2.load_molecule_from_smiles('C=C')
    qc2.run_single_point()
    qc2.run_tddft(nstates=5)
    qc2.predict_absorption_spectrum(nstates=5)
    print(qc2.get_results_summary())
    
    print("\n\nExample 3: Reaction Energy Calculation")
    print("-" * 60)
    rf = ReactionPathFinder(basis='sto-3g', method='dft', functional='b3lyp', verbose=0)
    result = rf.approximate_barrier('C=C', 'C1CC1')
    print(f"Reaction Energy: {result['reaction_energy_eV']:.3f} eV")
    print(f"Approximate Barrier: {result['approximate_barrier_eV']:.3f} eV")
    
    print("\n\nExample 4: Solvent Comparison")
    print("-" * 60)
    print("Solvent effects on formaldehyde:")
    for solv in [None, 'water', 'ethanol', 'hexane']:
        qc_solv = QuantumChemistry(basis='sto-3g', method='hf', solvent=solv, verbose=0)
        qc_solv.load_molecule_from_smiles('C=O')
        qc_solv.run_single_point()
        solv_name = solv if solv else 'Gas phase'
        print(f"  {solv_name:12s}: E = {qc_solv.results['total_energy']:.6f} Hartree")


if __name__ == "__main__":
    example_usage()
