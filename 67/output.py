import numpy as np
from atom import ATOMIC_NUMBERS


def compute_mulliken_charges(results):
    if results.get('is_uks', False):
        Pa = results['density_matrix_alpha']
        Pb = results['density_matrix_beta']
        P = Pa + Pb
    else:
        P = results['density_matrix']
    
    S = results['overlap_matrix']
    basis = results['basis']
    atoms = results['atoms']
    
    n_basis = len(basis)
    
    PS = P @ S
    gross_charges = np.zeros(n_basis, dtype=np.float64)
    for mu in range(n_basis):
        gross_charges[mu] = 0.5 * (PS[mu, mu] + PS.T[mu, mu])
    
    atom_to_basis = {}
    for i, (symbol, center) in enumerate(atoms):
        atom_to_basis[i] = []
    
    for mu, bf in enumerate(basis):
        bf_center = tuple(bf.center)
        for i, (symbol, center) in enumerate(atoms):
            atom_center = tuple(center)
            if bf_center == atom_center:
                atom_to_basis[i].append(mu)
                break
    
    mulliken_charges = []
    for i, (symbol, center) in enumerate(atoms):
        Z = ATOMIC_NUMBERS[symbol]
        atom_gross = 0.0
        for mu in atom_to_basis[i]:
            atom_gross += gross_charges[mu]
        
        charge = Z - atom_gross
        mulliken_charges.append((symbol, center, charge, Z, atom_gross))
    
    return mulliken_charges


def print_results(results):
    print("\n" + "=" * 70)
    if results.get('is_uks', False):
        print("                  UKS/DFT-LDA CALCULATION RESULTS")
    else:
        print("                  RKS/DFT-LDA CALCULATION RESULTS")
    print("=" * 70 + "\n")
    
    print("System Information:")
    print("-" * 40)
    print(f"  Number of atoms: {len(results['atoms'])}")
    print(f"  Number of basis functions: {len(results['basis'])}")
    
    if results.get('is_uks', False):
        print(f"  Charge: {results['charge']}")
        print(f"  Multiplicity: {results['multiplicity']}")
        print(f"  Total electrons: {results['total_electrons']}")
        print(f"  Alpha electrons: {results['n_occ_alpha']}")
        print(f"  Beta electrons: {results['n_occ_beta']}")
    else:
        print(f"  Number of occupied orbitals: {results['n_occ']}")
    print()
    
    print("Molecule:")
    print("-" * 40)
    for symbol, center in results['atoms']:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    print()
    
    print("Energy Components:")
    print("-" * 40)
    print(f"  Kinetic Energy:    {results['kinetic_energy']:20.10f} Eh")
    print(f"  Coulomb Energy:    {results['coulomb_energy']:20.10f} Eh")
    print(f"  XC Energy:         {results['xc_energy']:20.10f} Eh")
    print(f"  Nuclear Energy:    {results['nuclear_energy']:20.10f} Eh")
    print("-" * 60)
    print(f"  Total Energy:      {results['energy']:20.10f} Eh")
    print()
    
    if results.get('is_uks', False):
        print("Alpha Orbital Energies:")
        print("-" * 40)
        print(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}")
        print("-" * 55)
        
        eV_conversion = 27.2114
        
        for i, energy in enumerate(results['orbital_energies_alpha']):
            occupancy = 1 if i < results['n_occ_alpha'] else 0
            print(
                f"{i+1:>8d} "
                f"{energy:>15.6f} "
                f"{energy * eV_conversion:>15.6f} "
                f"{occupancy:>10d}"
            )
        
        print()
        print("Beta Orbital Energies:")
        print("-" * 40)
        print(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}")
        print("-" * 55)
        
        for i, energy in enumerate(results['orbital_energies_beta']):
            occupancy = 1 if i < results['n_occ_beta'] else 0
            print(
                f"{i+1:>8d} "
                f"{energy:>15.6f} "
                f"{energy * eV_conversion:>15.6f} "
                f"{occupancy:>10d}"
            )
    else:
        print("Orbital Energies:")
        print("-" * 40)
        print(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}")
        print("-" * 55)
        
        eV_conversion = 27.2114
        
        for i, energy in enumerate(results['orbital_energies']):
            occupancy = 2 if i < results['n_occ'] else 0
            print(
                f"{i+1:>8d} "
                f"{energy:>15.6f} "
                f"{energy * eV_conversion:>15.6f} "
                f"{occupancy:>10d}"
            )
    
    print()
    print("Mulliken Population Analysis:")
    print("-" * 40)
    print(f"{'Atom':>6} {'Z':>6} {'Electrons':>12} {'Charge':>12}")
    print("-" * 40)
    
    mulliken_charges = compute_mulliken_charges(results)
    for symbol, center, charge, Z, electrons in mulliken_charges:
        print(f"{symbol:>6} {Z:>6d} {electrons:>12.6f} {charge:>12.6f}")
    
    total_electrons = sum(e for _, _, _, _, e in mulliken_charges)
    total_charge = sum(q for _, _, q, _, _ in mulliken_charges)
    print("-" * 40)
    print(f"{'Total':>6} {'':>6} {total_electrons:>12.6f} {total_charge:>12.6f}")
    
    print("\n" + "=" * 70)


def save_results(results, filename="dft_results.txt"):
    with open(filename, 'w') as f:
        f.write("=" * 70 + "\n")
        if results.get('is_uks', False):
            f.write("                  UKS/DFT-LDA CALCULATION RESULTS\n")
        else:
            f.write("                  RKS/DFT-LDA CALCULATION RESULTS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("System Information:\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Number of atoms: {len(results['atoms'])}\n")
        f.write(f"  Number of basis functions: {len(results['basis'])}\n")
        
        if results.get('is_uks', False):
            f.write(f"  Charge: {results['charge']}\n")
            f.write(f"  Multiplicity: {results['multiplicity']}\n")
            f.write(f"  Total electrons: {results['total_electrons']}\n")
            f.write(f"  Alpha electrons: {results['n_occ_alpha']}\n")
            f.write(f"  Beta electrons: {results['n_occ_beta']}\n")
        else:
            f.write(f"  Number of occupied orbitals: {results['n_occ']}\n")
        f.write("\n")
        
        f.write("Molecule:\n")
        f.write("-" * 40 + "\n")
        for symbol, center in results['atoms']:
            f.write(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}\n")
        f.write("\n")
        
        f.write("Energy Components:\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Kinetic Energy:    {results['kinetic_energy']:20.10f} Eh\n")
        f.write(f"  Coulomb Energy:    {results['coulomb_energy']:20.10f} Eh\n")
        f.write(f"  XC Energy:         {results['xc_energy']:20.10f} Eh\n")
        f.write(f"  Nuclear Energy:    {results['nuclear_energy']:20.10f} Eh\n")
        f.write("-" * 60 + "\n")
        f.write(f"  Total Energy:      {results['energy']:20.10f} Eh\n")
        f.write("\n")
        
        if results.get('is_uks', False):
            f.write("Alpha Orbital Energies:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}\n")
            f.write("-" * 55 + "\n")
            
            eV_conversion = 27.2114
            
            for i, energy in enumerate(results['orbital_energies_alpha']):
                occupancy = 1 if i < results['n_occ_alpha'] else 0
                f.write(
                    f"{i+1:>8d} "
                    f"{energy:>15.6f} "
                    f"{energy * eV_conversion:>15.6f} "
                    f"{occupancy:>10d}\n"
                )
            
            f.write("\n")
            f.write("Beta Orbital Energies:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}\n")
            f.write("-" * 55 + "\n")
            
            for i, energy in enumerate(results['orbital_energies_beta']):
                occupancy = 1 if i < results['n_occ_beta'] else 0
                f.write(
                    f"{i+1:>8d} "
                    f"{energy:>15.6f} "
                    f"{energy * eV_conversion:>15.6f} "
                    f"{occupancy:>10d}\n"
                )
        else:
            f.write("Orbital Energies:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Orbital':>8} {'Energy (Eh)':>15} {'Energy (eV)':>15} {'Occupancy':>10}\n")
            f.write("-" * 55 + "\n")
            
            eV_conversion = 27.2114
            
            for i, energy in enumerate(results['orbital_energies']):
                occupancy = 2 if i < results['n_occ'] else 0
                f.write(
                    f"{i+1:>8d} "
                    f"{energy:>15.6f} "
                    f"{energy * eV_conversion:>15.6f} "
                    f"{occupancy:>10d}\n"
                )
        
        f.write("\n")
        f.write("Mulliken Population Analysis:\n")
        f.write("-" * 40 + "\n")
        f.write(f"{'Atom':>6} {'Z':>6} {'Electrons':>12} {'Charge':>12}\n")
        f.write("-" * 40 + "\n")
        
        mulliken_charges = compute_mulliken_charges(results)
        for symbol, center, charge, Z, electrons in mulliken_charges:
            f.write(f"{symbol:>6} {Z:>6d} {electrons:>12.6f} {charge:>12.6f}\n")
        
        total_electrons = sum(e for _, _, _, _, e in mulliken_charges)
        total_charge = sum(q for _, _, q, _, _ in mulliken_charges)
        f.write("-" * 40 + "\n")
        f.write(f"{'Total':>6} {'':>6} {total_electrons:>12.6f} {total_charge:>12.6f}\n")
        
        f.write("\n" + "=" * 70 + "\n")
    
    print(f"\nResults saved to: {filename}")
