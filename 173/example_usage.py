import numpy as np
from ase import Atoms
from ase.spacegroup import crystal
from phonon_calculator import PhononCalculator


def example_simple_cubic():
    print("=" * 60)
    print("Example 1: Simple Cubic Lattice")
    print("=" * 60)
    
    a = 3.0
    atoms = Atoms(
        symbols=['Na'],
        cell=[[a, 0, 0], [0, a, 0], [0, 0, a]],
        scaled_positions=[[0, 0, 0]],
        pbc=True
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    path = [
        (np.array([0, 0, 0]), np.array([0.5, 0, 0]), 50),
        (np.array([0.5, 0, 0]), np.array([0.5, 0.5, 0]), 50),
        (np.array([0.5, 0.5, 0]), np.array([0, 0, 0]), 50),
        (np.array([0, 0, 0]), np.array([0, 0, 0.5]), 50)
    ]
    labels = ['Γ', 'X', 'M', 'Γ', 'R']
    
    calculator.calculate_band_structure(path=path, labels=labels)
    calculator.calculate_dos(mesh=(15, 15, 15))
    
    fig = calculator.plot_band_and_dos(save_path='simple_cubic_phonon.png', show=False)
    calculator.save_results(prefix='simple_cubic')
    
    print(f"Number of phonon bands: {calculator.frequencies[0].shape[1]}")
    print(f"Max frequency: {np.max(np.concatenate(calculator.frequencies)):.3f} THz")
    print(f"Results saved to simple_cubic_phonon.png")
    print()


def example_graphene():
    print("=" * 60)
    print("Example 2: Graphene (2D Hexagonal Lattice)")
    print("=" * 60)
    
    a = 2.46
    c = 20.0
    atoms = Atoms(
        symbols=['C', 'C'],
        cell=[[a, 0, 0], [a/2, a*np.sqrt(3)/2, 0], [0, 0, c]],
        scaled_positions=[[0, 0, 0], [1/3, 2/3, 0]],
        pbc=[True, True, False]
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    path = [
        (np.array([0, 0, 0]), np.array([1/3, 1/3, 0]), 50),
        (np.array([1/3, 1/3, 0]), np.array([0.5, 0, 0]), 50),
        (np.array([0.5, 0, 0]), np.array([0, 0, 0]), 50)
    ]
    labels = ['Γ', 'K', 'M', 'Γ']
    
    calculator.calculate_band_structure(path=path, labels=labels)
    calculator.calculate_dos(mesh=(20, 20, 1))
    
    fig = calculator.plot_band_and_dos(save_path='graphene_phonon.png', show=False)
    calculator.save_results(prefix='graphene')
    
    print(f"Number of phonon bands: {calculator.frequencies[0].shape[1]}")
    print(f"Max frequency: {np.max(np.concatenate(calculator.frequencies)):.3f} THz")
    print(f"Results saved to graphene_phonon.png")
    print()


def example_nacl():
    print("=" * 60)
    print("Example 3: NaCl Structure (Rock Salt)")
    print("=" * 60)
    
    a = 5.64
    atoms = crystal(
        symbols=['Na', 'Cl'],
        basis=[[0, 0, 0], [0.5, 0.5, 0.5]],
        spacegroup=225,
        cellpar=[a, a, a, 90, 90, 90]
    )
    
    supercell_matrix = np.eye(3, dtype=int) * 2
    calculator = PhononCalculator(atoms, supercell_matrix=supercell_matrix)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, supercell_matrix)
    calculator.set_force_constants(force_constants)
    
    path = [
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 50),
        (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 50),
        (np.array([1, 1, 1]), np.array([0, 0, 0]), 50),
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0.5]), 50)
    ]
    labels = ['Γ', 'X', 'L', 'Γ', 'K']
    
    calculator.calculate_band_structure(path=path, labels=labels)
    calculator.calculate_dos(mesh=(15, 15, 15))
    
    fig = calculator.plot_band_and_dos(save_path='nacl_phonon.png', show=False)
    calculator.save_results(prefix='nacl')
    
    print(f"Number of atoms in unit cell: {len(atoms)}")
    print(f"Number of phonon bands: {calculator.frequencies[0].shape[1]}")
    print(f"Max frequency: {np.max(np.concatenate(calculator.frequencies)):.3f} THz")
    print(f"Results saved to nacl_phonon.png")
    print()


def example_interpolation_comparison():
    print("=" * 60)
    print("Example 4: Interpolation Method Comparison")
    print("=" * 60)
    
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
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 20),
        (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 20),
    ]
    labels = ['Γ', 'X', 'L']
    
    calculator.calculate_band_structure(path=path, labels=labels, npoints=20)
    
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    calculator.plot_band_structure(ax=axes[0], show=False, interpolate=False)
    axes[0].set_title('Original (20 points)', fontsize=12)
    
    q_linear, freq_linear = calculator.interpolate_bands(
        calculator.qpoints, calculator.frequencies, factor=3, method='linear'
    )
    calculator.qpoints, calculator.frequencies = q_linear, freq_linear
    calculator.plot_band_structure(ax=axes[1], show=False, interpolate=False)
    axes[1].set_title('Linear Interpolation (60 points)', fontsize=12)
    
    calculator.calculate_band_structure(path=path, labels=labels, npoints=20)
    q_cubic, freq_cubic = calculator.interpolate_bands(
        calculator.qpoints, calculator.frequencies, factor=3, method='cubic'
    )
    calculator.qpoints, calculator.frequencies = q_cubic, freq_cubic
    calculator.plot_band_structure(ax=axes[2], show=False, interpolate=False)
    axes[2].set_title('Cubic Spline Interpolation (60 points)', fontsize=12)
    
    plt.tight_layout()
    plt.savefig('interpolation_comparison.png', dpi=300)
    print(f"Comparison plot saved to interpolation_comparison.png")
    print()


def example_from_structure_file():
    print("=" * 60)
    print("Example 5: Loading Structure from File")
    print("=" * 60)
    
    from ase.io import write
    
    a = 4.05
    atoms = Atoms(
        symbols=['Al'],
        cell=[[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]],
        scaled_positions=[[0, 0, 0]],
        pbc=True
    )
    
    write('Al_fcc.vasp', atoms, format='vasp')
    print("Created example structure file: Al_fcc.vasp")
    
    calculator = PhononCalculator.from_file('Al_fcc.vasp', supercell_matrix=np.eye(3, dtype=int) * 2)
    
    force_constants = PhononCalculator.generate_example_force_constants(atoms, np.eye(3, dtype=int) * 2)
    calculator.set_force_constants(force_constants)
    
    path = [
        (np.array([0, 0, 0]), np.array([0.5, 0.5, 0]), 50),
        (np.array([0.5, 0.5, 0]), np.array([1, 1, 1]), 50),
        (np.array([1, 1, 1]), np.array([0, 0, 0]), 50),
    ]
    labels = ['Γ', 'X', 'L', 'Γ']
    
    calculator.calculate_band_structure(path=path, labels=labels)
    calculator.calculate_dos(mesh=(15, 15, 15))
    
    fig = calculator.plot_band_and_dos(save_path='al_fcc_phonon.png', show=False)
    calculator.save_results(prefix='al_fcc')
    
    print(f"Material: Aluminum (FCC)")
    print(f"Number of phonon bands: {calculator.frequencies[0].shape[1]}")
    print(f"Max frequency: {np.max(np.concatenate(calculator.frequencies)):.3f} THz")
    print(f"Results saved to al_fcc_phonon.png")
    print()


if __name__ == '__main__':
    print("Running all examples...")
    print()
    
    try:
        example_simple_cubic()
    except Exception as e:
        print(f"Simple cubic example failed: {e}")
        print()
    
    try:
        example_graphene()
    except Exception as e:
        print(f"Graphene example failed: {e}")
        print()
    
    try:
        example_nacl()
    except Exception as e:
        print(f"NaCl example failed: {e}")
        print()
    
    try:
        example_interpolation_comparison()
    except Exception as e:
        print(f"Interpolation comparison failed: {e}")
        print()
    
    try:
        example_from_structure_file()
    except Exception as e:
        print(f"Structure file example failed: {e}")
        print()
    
    print("All examples completed!")
