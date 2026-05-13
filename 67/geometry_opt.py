import numpy as np
from scf import run_scf
from integral import compute_numerical_gradient


def atoms_to_flat(atoms):
    flat_coords = []
    for symbol, center in atoms:
        flat_coords.extend(center)
    return np.array(flat_coords, dtype=np.float64)


def flat_to_atoms(atoms_template, flat_coords):
    new_atoms = []
    for i, (symbol, _) in enumerate(atoms_template):
        start = i * 3
        end = start + 3
        new_atoms.append((symbol, list(flat_coords[start:end])))
    return new_atoms


def energy_function(atoms_template, charge=0, multiplicity=1, max_iter=50, tol=1e-6):
    def E(flat_coords):
        atoms = flat_to_atoms(atoms_template, flat_coords)
        results = run_scf(atoms, charge=charge, multiplicity=multiplicity,
                          max_iter=max_iter, tol=tol, use_diis=True)
        return results['energy']
    return E


def gradient_function(atoms_template, charge=0, multiplicity=1, max_iter=50, tol=1e-6, step=1e-4):
    def grad(flat_coords):
        atoms = flat_to_atoms(atoms_template, flat_coords)
        scf_func = lambda a: run_scf(a, charge=charge, multiplicity=multiplicity,
                                     max_iter=max_iter, tol=tol, use_diis=True)
        grad_tensor = compute_numerical_gradient(atoms, scf_func, step=step)
        return grad_tensor.flatten()
    return grad


def bfgs_optimize(atoms, charge=0, multiplicity=1, max_opt_iter=100,
                  grad_tol=1e-4, energy_tol=1e-6, max_step=0.2,
                  scf_max_iter=50, scf_tol=1e-6,
                  line_search=True):
    atoms_template = [(symbol, list(center)) for symbol, center in atoms]
    x0 = atoms_to_flat(atoms)
    
    n_vars = len(x0)
    
    E_func = energy_function(atoms_template, charge=charge, multiplicity=multiplicity,
                              max_iter=scf_max_iter, tol=scf_tol)
    grad_func = gradient_function(atoms_template, charge=charge, multiplicity=multiplicity,
                                   max_iter=scf_max_iter, tol=scf_tol)
    
    print("=" * 70)
    print("                     BFGS GEOMETRY OPTIMIZATION")
    print("=" * 70)
    print()
    
    print("Initial geometry:")
    for symbol, center in atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    print()
    
    print("Starting optimization...")
    print(f"{'Iteration':>10} {'Energy (Eh)':>20} {'ΔE (Eh)':>15} {'|g|':>15} {'Step':>15}")
    print("-" * 80)
    
    x = x0.copy()
    E_prev = E_func(x)
    g_prev = grad_func(x)
    
    H = np.eye(n_vars, dtype=np.float64)
    
    history = []
    history.append({'coords': x.copy(), 'energy': E_prev, 'gradient': g_prev.copy()})
    
    for iteration in range(max_opt_iter):
        p = -np.dot(H, g_prev)
        
        if np.linalg.norm(p) > max_step:
            p = p * max_step / np.linalg.norm(p)
        
        if line_search:
            alpha = wolfe_line_search(x, p, E_func, grad_func, E_prev, g_prev)
        else:
            alpha = 1.0
        
        x_new = x + alpha * p
        E_new = E_func(x_new)
        g_new = grad_func(x_new)
        
        s = x_new - x
        y = g_new - g_prev
        
        rho = 1.0 / (np.dot(y, s) + 1e-10)
        
        if np.dot(y, s) > 1e-10:
            I = np.eye(n_vars, dtype=np.float64)
            term1 = I - rho * np.outer(s, y)
            term2 = I - rho * np.outer(y, s)
            H_new = np.dot(np.dot(term1, H), term2) + rho * np.outer(s, s)
            H = H_new
        
        x = x_new
        delta_E = abs(E_new - E_prev)
        grad_norm = np.linalg.norm(g_new)
        
        print(f"{iteration+1:>10} {E_new:>20.10f} {delta_E:>15.6e} {grad_norm:>15.6e} {alpha:>15.6f}")
        
        history.append({'coords': x.copy(), 'energy': E_new, 'gradient': g_new.copy()})
        
        if grad_norm < grad_tol and delta_E < energy_tol:
            print("\nGeometry optimization converged!")
            break
        
        E_prev = E_new
        g_prev = g_new
    
    else:
        print("\nGeometry optimization did not converge within maximum iterations!")
    
    opt_atoms = flat_to_atoms(atoms_template, x)
    
    print()
    print("=" * 70)
    print("Optimized geometry:")
    for symbol, center in opt_atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    print(f"\nOptimized energy: {E_new:.10f} Eh")
    print("=" * 70)
    
    return {
        'optimized_atoms': opt_atoms,
        'optimized_energy': E_new,
        'gradient_norm': grad_norm,
        'history': history,
        'n_iterations': iteration + 1,
        'converged': grad_norm < grad_tol and delta_E < energy_tol,
    }


def wolfe_line_search(x, p, E_func, grad_func, E0, g0, c1=1e-4, c2=0.9, max_alpha=2.0, max_iter=20):
    alpha = 1.0
    alpha_prev = 0.0
    E_prev = E0
    
    for i in range(max_iter):
        x_new = x + alpha * p
        E_new = E_func(x_new)
        
        if E_new > E0 + c1 * alpha * np.dot(g0, p):
            return zoom(x, p, E_func, grad_func, E0, g0, alpha_prev, alpha, c1, c2)
        
        g_new = grad_func(x_new)
        if np.dot(g_new, p) >= c2 * np.dot(g0, p):
            return alpha
        
        if np.dot(g_new, p) <= 0:
            return zoom(x, p, E_func, grad_func, E0, g0, alpha, max_alpha, c1, c2)
        
        alpha_prev = alpha
        alpha = min(alpha * 2.0, max_alpha)
    
    return alpha


def zoom(x, p, E_func, grad_func, E0, g0, alpha_low, alpha_high, c1, c2, max_iter=20):
    for i in range(max_iter):
        alpha = (alpha_low + alpha_high) / 2.0
        x_new = x + alpha * p
        E_new = E_func(x_new)
        x_low = x + alpha_low * p
        E_low = E_func(x_low)
        
        if E_new > E0 + c1 * alpha * np.dot(g0, p) or E_new >= E_low:
            alpha_high = alpha
        else:
            g_new = grad_func(x_new)
            if np.dot(g_new, p) >= c2 * np.dot(g0, p):
                return alpha
            
            if np.dot(g_new, p) * (alpha_high - alpha_low) < 0:
                alpha_high = alpha_low
            alpha_low = alpha
    
    return (alpha_low + alpha_high) / 2.0


def steepest_descent_optimize(atoms, charge=0, multiplicity=1, max_opt_iter=100,
                              grad_tol=1e-4, energy_tol=1e-6, step_size=0.05,
                              scf_max_iter=50, scf_tol=1e-6):
    atoms_template = [(symbol, list(center)) for symbol, center in atoms]
    x0 = atoms_to_flat(atoms)
    
    E_func = energy_function(atoms_template, charge=charge, multiplicity=multiplicity,
                              max_iter=scf_max_iter, tol=scf_tol)
    grad_func = gradient_function(atoms_template, charge=charge, multiplicity=multiplicity,
                                   max_iter=scf_max_iter, tol=scf_tol)
    
    print("=" * 70)
    print("               STEEPEST DESCENT GEOMETRY OPTIMIZATION")
    print("=" * 70)
    print()
    
    print("Initial geometry:")
    for symbol, center in atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    print()
    
    print("Starting optimization...")
    print(f"{'Iteration':>10} {'Energy (Eh)':>20} {'ΔE (Eh)':>15} {'|g|':>15}")
    print("-" * 70)
    
    x = x0.copy()
    E_prev = E_func(x)
    g_prev = grad_func(x)
    
    for iteration in range(max_opt_iter):
        p = -g_prev
        if np.linalg.norm(p) > step_size:
            p = p * step_size / np.linalg.norm(p)
        
        x_new = x + p
        E_new = E_func(x_new)
        g_new = grad_func(x_new)
        
        delta_E = abs(E_new - E_prev)
        grad_norm = np.linalg.norm(g_new)
        
        print(f"{iteration+1:>10} {E_new:>20.10f} {delta_E:>15.6e} {grad_norm:>15.6e}")
        
        if E_new < E_prev:
            x = x_new
            E_prev = E_new
            g_prev = g_new
            
            if grad_norm < grad_tol and delta_E < energy_tol:
                print("\nGeometry optimization converged!")
                break
        else:
            step_size *= 0.5
            print(f"  Energy increased, reducing step size to {step_size}")
    
    else:
        print("\nGeometry optimization did not converge within maximum iterations!")
    
    opt_atoms = flat_to_atoms(atoms_template, x)
    
    print()
    print("=" * 70)
    print("Optimized geometry:")
    for symbol, center in opt_atoms:
        print(f"  {symbol:4s}  {center[0]:12.6f} {center[1]:12.6f} {center[2]:12.6f}")
    print(f"\nOptimized energy: {E_prev:.10f} Eh")
    print("=" * 70)
    
    return {
        'optimized_atoms': opt_atoms,
        'optimized_energy': E_prev,
        'gradient_norm': np.linalg.norm(g_prev),
        'n_iterations': iteration + 1,
        'converged': np.linalg.norm(g_prev) < grad_tol,
    }
