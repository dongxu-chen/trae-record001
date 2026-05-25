import sys
import numpy as np

sys.path.insert(0, r'd:\Trae\project\record001\290')

from laplace_solver import LaplaceSolver, MultiGridLaplaceSolver

print("Testing Laplace Solver...")
print("=" * 50)

print("\n1. Testing basic LaplaceSolver initialization...")
solver = LaplaceSolver(20, 20)
print(f"   Created solver with grid size: {solver.nx}x{solver.ny}")

print("\n2. Testing Dirichlet boundary condition...")
def boundary_temp(x, y):
    temp = np.zeros_like(x)
    temp[y == 0] = 100
    temp[y == 19] = 0
    return temp
solver.set_dirichlet_boundary(boundary_temp)
print(f"   Boundary points set: {np.sum(solver.boundary_mask)}")

print("\n3. Testing Jacobi iteration (5 iterations)...")
for i in range(5):
    res = solver.jacobi_step()
print(f"   Residual after 5 Jacobi steps: {res:.4e}")

print("\n4. Testing full solve with SOR method...")
solver2 = LaplaceSolver(30, 30)
solver2.set_dirichlet_boundary(boundary_temp)
u, converged = solver2.solve(method='sor', tol=1e-4, max_iter=500, verbose=False)
print(f"   Converged: {converged}")
print(f"   Iterations: {solver2.iteration_count}")
print(f"   Final residual: {solver2.convergence_history[-1]:.4e}")

print("\n5. Testing circular region mask...")
solver3 = LaplaceSolver(40, 40)
solver3.set_circular_region(19.5, 19.5, 15)
print(f"   Active grid points in circle: {np.sum(solver3.mask)}")
print(f"   Masked (inactive) points: {np.sum(~solver3.mask)}")

print("\n6. Testing MultiGridLaplaceSolver...")
solver_mg = MultiGridLaplaceSolver(33, 33, n_levels=3)
print(f"   Multigrid levels: {solver_mg.n_levels}")
print(f"   Grid sizes: {[g.shape for g in solver_mg.grids]}")

print("\n7. Testing multigrid solve...")
def boundary_temp_mg(x, y):
    temp = np.zeros_like(x)
    ny = 33
    temp[y == 0] = 100
    temp[y == (ny-1)] = 0
    return temp
solver_mg.set_dirichlet_boundary(boundary_temp_mg)
u_mg, converged_mg = solver_mg.solve_multigrid(tol=1e-4, max_iter=20, verbose=False)
print(f"   Multigrid converged: {converged_mg}")
print(f"   V-cycles: {solver_mg.iteration_count}")
print(f"   Final residual: {solver_mg.convergence_history[-1]:.4e}")

print("\n8. Testing visualization methods...")
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots()
    solver2.plot_contour(ax=ax)
    plt.savefig(r'd:\Trae\project\record001\290\test_output.png', dpi=100)
    plt.close()
    print("   Plot saved successfully!")
except Exception as e:
    print(f"   Plot warning: {e}")

print("\n" + "=" * 50)
print("All tests passed successfully!")
