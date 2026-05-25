from quantum_chem import QuantumChemistry, ReactionPathFinder, SolventPCM

def example_pcm_solvent():
    print("=" * 70)
    print("Example 1: PCM Solvent Effect Comparison")
    print("=" * 70)
    
    print("Solvent effects on water molecule:\n")
    
    solvents = [None, 'water', 'methanol', 'ethanol', 'acetonitrile', 'hexane']
    
    results = []
    for solv in solvents:
        solv_name = solv if solv else 'Gas phase'
        qc = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                              solvent=solv, verbose=0, use_diis=True)
        qc.load_molecule_from_smiles('O')
        qc.run_single_point()
        
        e = qc.results['total_energy']
        dip = qc.results.get('dipole_magnitude', 0)
        results.append((solv_name, e, dip))
        print(f"  {solv_name:15s}: E = {e:.6f} Hartree, μ = {dip:.4f} a.u.")
    
    gas_e = results[0][1]
    print(f"\nSolvation energies (relative to gas phase):")
    for solv_name, e, dip in results[1:]:
        solv_energy = (e - gas_e) * 27.2114
        print(f"  {solv_name:15s}: ΔG_solv = {solv_energy:.4f} eV")
    print()


def example_tddft_absorption():
    print("=" * 70)
    print("Example 2: TD-DFT Excited States & Absorption Spectrum")
    print("=" * 70)
    
    qc = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                          verbose=0, use_diis=True)
    
    print("Calculating excited states for formaldehyde (H2CO)...\n")
    qc.load_molecule_from_smiles('C=O')
    qc.run_single_point()
    qc.run_tddft(nstates=8)
    
    print(qc.get_results_summary())
    
    print("\nGenerating absorption spectrum...")
    spectrum = qc.predict_absorption_spectrum(
        nstates=8,
        broadening='gaussian',
        fwhm=0.3,
        energy_range=(2.0, 10.0)
    )
    
    print(f"\nSpectrum range: {spectrum['energies_eV'][0]:.1f} - {spectrum['energies_eV'][-1]:.1f} eV")
    print(f"                    {spectrum['wavelengths_nm'][0]:.1f} - {spectrum['wavelengths_nm'][-1]:.1f} nm")
    
    peak_idx = np.argmax(spectrum['intensity'])
    print(f"Maximum absorption: {spectrum['wavelengths_nm'][peak_idx]:.1f} nm")
    print()


def example_solvent_tddft():
    print("=" * 70)
    print("Example 3: Solvent Effect on Absorption Spectrum")
    print("=" * 70)
    
    print("Solvent effect on ethylene excitation energy:\n")
    
    for solv in [None, 'water']:
        solv_name = solv if solv else 'Gas phase'
        qc = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                              solvent=solv, verbose=0, use_diis=True)
        qc.load_molecule_from_smiles('C=C')
        qc.run_single_point()
        qc.run_tddft(nstates=5)
        
        exc = qc.results['excited_states']
        print(f"  {solv_name}:")
        print(f"    S0->S1: {exc['energies_eV'][0]:.2f} eV ({exc['wavelengths_nm'][0]:.1f} nm)")
        print(f"    S0->S2: {exc['energies_eV'][1]:.2f} eV ({exc['wavelengths_nm'][1]:.1f} nm)")
    print()


def example_reaction_path():
    print("=" * 70)
    print("Example 4: Reaction Path & Barrier Calculation")
    print("=" * 70)
    
    rf = ReactionPathFinder(basis='sto-3g', method='dft', functional='b3lyp', verbose=0)
    
    print("Reaction: H2CO -> H2 + CO (simplified)\n")
    
    result = rf.approximate_barrier('C=O', '[H][H]C#O')
    
    print(f"Reaction Energy: {result['reaction_energy_eV']:.3f} eV")
    print(f"Approximate Barrier: {result['approximate_barrier_eV']:.3f} eV")
    print()
    
    print("Solvent effect on reaction barrier:")
    for solv in [None, 'water']:
        solv_name = solv if solv else 'Gas phase'
        res = rf.approximate_barrier('C=O', '[H][H]C#O', solvent=solv)
        print(f"  {solv_name:12s}: E_reac = {res['reaction_energy_eV']:+.3f} eV, "
              f"E_barr ≈ {res['approximate_barrier_eV']:.3f} eV")
    print()


def example_linear_transit():
    print("=" * 70)
    print("Example 5: Linear Transit Search for Transition State")
    print("=" * 70)
    
    rf = ReactionPathFinder(basis='sto-3g', method='hf', verbose=0)
    
    print("Finding approximate TS along reaction path...\n")
    
    try:
        ts_guess = rf.find_transition_state_guess('O', 'O', nimages=8)
        
        print(f"Number of images: {len(ts_guess['energy_profile']['images'])}")
        print(f"Energy profile (eV relative to minimum):")
        for i, e in enumerate(ts_guess['energy_profile']['energies_eV']):
            marker = " *" if i == np.argmax(ts_guess['energy_profile']['energies_eV']) else ""
            print(f"  Image {i}: {e:.3f} eV{marker}")
        
        print(f"\nEstimated barrier: {ts_guess['energy_profile']['barrier_eV']:.3f} eV")
        print("* = TS guess structure")
    except Exception as e:
        print(f"Note: Linear transit requires matching atom counts in reactant/product")
        print(f"Reason: {e}")
    print()


def example_solvent_list():
    print("=" * 70)
    print("Example 6: Available Solvents in PCM Model")
    print("=" * 70)
    
    print("Supported solvents:")
    for i, (solv, props) in enumerate(SolventPCM.SOLVENTS.items()):
        print(f"  {i+1:2d}. {solv:18s} ε = {props['eps']:6.2f}, "
              f"ε_∞ = {props['epsinf']:.2f}")
    print()


def example_full_workflow():
    print("=" * 70)
    print("Example 7: Full Workflow - Excited State in Solution")
    print("=" * 70)
    
    print("Step 1: Optimize geometry in gas phase")
    qc = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                          verbose=1, use_diis=True)
    qc.load_molecule_from_smiles('C=O')
    qc.optimize_geometry(max_cycles=20, method='adaptive')
    print(f"  Optimized energy: {qc.results['total_energy']:.6f} Hartree\n")
    
    print("Step 2: TD-DFT in gas phase")
    qc.run_tddft(nstates=3)
    print(f"  S1 energy: {qc.results['excited_states']['energies_eV'][0]:.2f} eV\n")
    
    print("Step 3: Single point with solvent (PCM)")
    qc_solv = QuantumChemistry(basis='sto-3g', method='dft', functional='b3lyp',
                                solvent='water', verbose=0, use_diis=True)
    qc_solv.mol = qc.mol
    qc_solv.run_single_point()
    qc_solv.run_tddft(nstates=3)
    print(f"  S1 energy (water): {qc_solv.results['excited_states']['energies_eV'][0]:.2f} eV")
    print()


if __name__ == "__main__":
    import numpy as np
    
    example_pcm_solvent()
    example_tddft_absorption()
    example_solvent_tddft()
    example_reaction_path()
    example_linear_transit()
    example_solvent_list()
    example_full_workflow()
