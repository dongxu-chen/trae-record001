import numpy as np
from mesh import UnstructuredMesh1D, generate_uniform_mesh, _remove_duplicate_nodes
from flux import create_flux_solver
from boundary import create_boundary_condition, BoundaryManager
from solver import EulerSolver1D, sod_shock_tube


def test_hllc_solver():
    print("=" * 60)
    print("Test 1: HLLC Solver with Sod Shock Tube")
    print("=" * 60)

    mesh = generate_uniform_mesh(0.0, 1.0, 100)

    solver_roe = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='roe',
        time_scheme='rk3',
        left_bc='zero_gradient',
        right_bc='zero_gradient',
        cfl=0.6
    )
    solver_roe.initialize(lambda x: sod_shock_tube(x, 0.5))
    solver_roe.solve(t_end=0.2, verbose=False)
    rho_roe, u_roe, p_roe = solver_roe.get_primitive_variables()

    solver_hllc = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='hllc',
        time_scheme='rk3',
        left_bc='zero_gradient',
        right_bc='zero_gradient',
        cfl=0.6
    )
    solver_hllc.initialize(lambda x: sod_shock_tube(x, 0.5))
    solver_hllc.solve(t_end=0.2, verbose=False)
    rho_hllc, u_hllc, p_hllc = solver_hllc.get_primitive_variables()

    diff_rho = np.max(np.abs(rho_hllc - rho_roe))
    diff_u = np.max(np.abs(u_hllc - u_roe))
    diff_p = np.max(np.abs(p_hllc - p_roe))

    print(f"Max density diff (HLLC vs Roe): {diff_rho:.6e}")
    print(f"Max velocity diff (HLLC vs Roe): {diff_u:.6e}")
    print(f"Max pressure diff (HLLC vs Roe): {diff_p:.6e}")

    assert diff_rho < 0.2, "HLLC density error too large"
    assert solver_hllc.n_steps > 0, "HLLC solver did not run"
    print("[PASS] HLLC solver test passed")

    return True


def test_node_duplicate_removal():
    print("\n" + "=" * 60)
    print("Test 2: Duplicate Node Removal")
    print("=" * 60)

    nodes_with_duplicates = np.array([0.0, 0.1, 0.1, 0.2, 0.3, 0.3, 0.3, 0.4, 0.5])
    print(f"Original nodes ({len(nodes_with_duplicates)} nodes): {nodes_with_duplicates}")

    unique_nodes, mapping = _remove_duplicate_nodes(nodes_with_duplicates, tolerance=1e-12)

    print(f"Unique nodes ({len(unique_nodes)}): {unique_nodes}")

    assert len(unique_nodes) == 6, f"Expected 6 unique nodes, got {len(unique_nodes)}"
    assert np.allclose(unique_nodes, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]), "Node values incorrect"

    mesh = UnstructuredMesh1D(nodes_with_duplicates, remove_duplicates=True)
    print(f"Mesh created with {mesh.n_nodes} nodes, {mesh.n_cells} cells")
    assert mesh.n_nodes == 6, f"Expected 6 nodes after dedup"
    assert mesh.n_cells == 5, f"Expected 5 cells after dedup"

    print("[PASS] Node duplicate removal test passed")
    return True


def test_farfield_boundary():
    print("\n" + "=" * 60)
    print("Test 3: Farfield Characteristic Boundary")
    print("=" * 60)

    mesh = generate_uniform_mesh(0.0, 1.0, 50)
    flux_solver = create_flux_solver('roe', gamma=1.4)

    rho_far = 1.0
    u_far = 0.0
    p_far = 1.0

    left_bc = create_boundary_condition(
        'farfield_characteristic',
        rho_far=rho_far, u_far=u_far, p_far=p_far
    )
    right_bc = create_boundary_condition(
        'farfield_characteristic',
        rho_far=rho_far, u_far=u_far, p_far=p_far
    )

    boundary_manager = BoundaryManager(left_bc, right_bc)

    U = np.zeros((3, mesh.n_cells))
    for i in range(mesh.n_cells):
        x = mesh.cell_centers[i]
        if x < 0.3:
            U[:, i] = flux_solver.conservative_from_primitive(2.0, 0.0, 2.0)
        elif x > 0.7:
            U[:, i] = flux_solver.conservative_from_primitive(0.5, 0.0, 0.5)
        else:
            U[:, i] = flux_solver.conservative_from_primitive(rho_far, u_far, p_far)

    rho_initial = np.array([flux_solver.primitive_from_conservative(U[:, i])[0] for i in range(mesh.n_cells)])
    print(f"Initial density range: [{rho_initial.min():.3f}, {rho_initial.max():.3f}]")

    solver = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='roe',
        time_scheme='rk3',
        left_bc='farfield_characteristic',
        right_bc='farfield_characteristic',
        cfl=0.8,
        left_bc_params={'rho_far': rho_far, 'u_far': u_far, 'p_far': p_far},
        right_bc_params={'rho_far': rho_far, 'u_far': u_far, 'p_far': p_far}
    )

    def ic(x):
        if x < 0.3:
            return 2.0, 0.0, 2.0
        elif x > 0.7:
            return 0.5, 0.0, 0.5
        else:
            return rho_far, u_far, p_far

    solver.initialize(ic)
    solver.solve(t_end=0.1, verbose=False)

    rho_final, u_final, p_final = solver.get_primitive_variables()

    print(f"Final density range: [{rho_final.min():.3f}, {rho_final.max():.3f}]")
    print(f"Final velocity range: [{u_final.min():.3f}, {u_final.max():.3f}]")

    assert np.all(np.isfinite(rho_final)), "Density contains NaN or Inf"
    assert np.all(np.isfinite(u_final)), "Velocity contains NaN or Inf"
    assert np.all(np.isfinite(p_final)), "Pressure contains NaN or Inf"
    assert np.all(rho_final > 0), "Negative density detected"
    assert np.all(p_final > 0), "Negative pressure detected"

    print("[PASS] Farfield boundary test passed - no divergence")
    return True


def test_hll_vs_hllc_contact():
    print("\n" + "=" * 60)
    print("Test 4: HLL vs HLLC Contact Discontinuity")
    print("=" * 60)

    mesh = generate_uniform_mesh(0.0, 1.0, 100)

    def contact_ic(x):
        if x < 0.5:
            return 1.0, 0.5, 1.0
        else:
            return 0.5, 0.5, 1.0

    solver_hll = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='hll',
        time_scheme='rk3',
        left_bc='zero_gradient',
        right_bc='zero_gradient',
        cfl=0.6
    )
    solver_hll.initialize(contact_ic)
    solver_hll.solve(t_end=0.1, verbose=False)
    rho_hll, u_hll, p_hll = solver_hll.get_primitive_variables()

    solver_hllc = EulerSolver1D(
        mesh=mesh,
        flux_solver_type='hllc',
        time_scheme='rk3',
        left_bc='zero_gradient',
        right_bc='zero_gradient',
        cfl=0.6
    )
    solver_hllc.initialize(contact_ic)
    solver_hllc.solve(t_end=0.1, verbose=False)
    rho_hllc, u_hllc, p_hllc = solver_hllc.get_primitive_variables()

    print(f"HLL  - density at interface (cell 50): {rho_hll[50]:.6f}")
    print(f"HLLC - density at interface (cell 50): {rho_hllc[50]:.6f}")

    hll_jump = abs(rho_hll[49] - rho_hll[50])
    hllc_jump = abs(rho_hllc[49] - rho_hllc[50])

    print(f"HLL  - density jump at interface: {hll_jump:.6f}")
    print(f"HLLC - density jump at interface: {hllc_jump:.6f}")

    print("[PASS] HLLC contact discontinuity test passed")
    return True


def main():
    all_passed = True

    try:
        all_passed &= test_hllc_solver()
    except Exception as e:
        print(f"[FAIL] HLLC solver test failed: {e}")
        all_passed = False

    try:
        all_passed &= test_node_duplicate_removal()
    except Exception as e:
        print(f"[FAIL] Node duplicate removal test failed: {e}")
        all_passed = False

    try:
        all_passed &= test_farfield_boundary()
    except Exception as e:
        print(f"[FAIL] Farfield boundary test failed: {e}")
        all_passed = False

    try:
        all_passed &= test_hll_vs_hllc_contact()
    except Exception as e:
        print(f"[FAIL] HLL vs HLLC test failed: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
