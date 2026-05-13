from scf import run_scf
from output import print_results, save_results
from geometry_opt import bfgs_optimize
from symmetry import print_symmetry_info


def test_h2_rks():
    print("\n" + "=" * 70)
    print("                         TEST: H2 RKS")
    print("=" * 70)
    
    h2_atoms = [
        ('H', [0.0, 0.0, 0.0]),
        ('H', [0.0, 0.0, 0.74]),
    ]
    
    results = run_scf(h2_atoms, charge=0, multiplicity=1, max_iter=50, tol=1e-8, use_diis=True)
    print_results(results)
    save_results(results, "h2_rks_results.txt")
    return results


def test_h2_uks():
    print("\n" + "=" * 70)
    print("                         TEST: H2 UKS")
    print("=" * 70)
    
    h2_atoms = [
        ('H', [0.0, 0.0, 0.0]),
        ('H', [0.0, 0.0, 0.74]),
    ]
    
    results = run_scf(h2_atoms, charge=0, multiplicity=1, max_iter=50, tol=1e-8, use_diis=True, force_uks=True)
    print_results(results)
    save_results(results, "h2_uks_results.txt")
    return results


def test_symmetry():
    print("\n" + "=" * 70)
    print("                       TEST: SYMMETRY")
    print("=" * 70)
    
    h2_atoms = [
        ('H', [0.0, 0.0, -0.37]),
        ('H', [0.0, 0.0, 0.37]),
    ]
    
    print("\nH2 molecule:")
    for symbol, center in h2_atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    
    print_symmetry_info(h2_atoms)
    
    co2_atoms = [
        ('C', [0.0, 0.0, 0.0]),
        ('O', [0.0, 0.0, -1.16]),
        ('O', [0.0, 0.0, 1.16]),
    ]
    
    print("\n\nCO2 molecule:")
    for symbol, center in co2_atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    
    print_symmetry_info(co2_atoms)
    
    water_atoms = [
        ('O', [0.0, 0.0, 0.0]),
        ('H', [0.0, 0.757, 0.586]),
        ('H', [0.0, -0.757, 0.586]),
    ]
    
    print("\n\nWater molecule:")
    for symbol, center in water_atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    
    print_symmetry_info(water_atoms)


def test_geometry_optimization():
    print("\n" + "=" * 70)
    print("                  TEST: H2 GEOMETRY OPTIMIZATION (BFGS)")
    print("=" * 70)
    
    h2_atoms = [
        ('H', [0.0, 0.0, 0.0]),
        ('H', [0.0, 0.0, 1.0]),
    ]
    
    opt_results = bfgs_optimize(
        h2_atoms,
        charge=0,
        multiplicity=1,
        max_opt_iter=10,
        grad_tol=1e-2,
        energy_tol=1e-4,
        max_step=0.1,
        scf_max_iter=30,
        scf_tol=1e-6,
        line_search=False
    )
    
    return opt_results


def test_li_uks():
    print("\n" + "=" * 70)
    print("                       TEST: Li Atom (UKS)")
    print("=" * 70)
    
    li_atoms = [
        ('Li', [0.0, 0.0, 0.0]),
    ]
    
    results = run_scf(li_atoms, charge=0, multiplicity=2, max_iter=50, tol=1e-8, use_diis=True)
    print_results(results)
    save_results(results, "li_uks_results.txt")
    return results


def main():
    print("=" * 70)
    print("           OPEN-SOURCE QUANTUM CHEMISTRY PACKAGE - EXTENDED TEST")
    print("               DFT/LDA with STO-3G, UKS, BFGS, Symmetry")
    print("=" * 70)
    print()
    
    results_h2_rks = test_h2_rks()
    
    results_h2_uks = test_h2_uks()
    
    try:
        results_li = test_li_uks()
    except Exception as e:
        print(f"Li test failed: {e}")
    
    test_symmetry()
    
    try:
        opt_results = test_geometry_optimization()
    except Exception as e:
        print(f"Geometry optimization test failed: {e}")
    
    print("\n" + "=" * 70)
    print("                             ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
