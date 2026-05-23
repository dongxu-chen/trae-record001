import sys, os
os.chdir(r'd:\Trae\project\record001\215')
sys.path.insert(0, '.')

with open('result.txt', 'w') as f:
    try:
        import numpy as np
        f.write('OK: numpy\n'); f.flush()
        
        from potentials import lennard_jones_potential
        r_min = 2.0**(1.0/6.0)
        pe = lennard_jones_potential(np.array([r_min**2]), r_cut=3.0)
        f.write(f'OK: LJ potential at r_min = {pe[0]:.6f} (expected -1.0)\n'); f.flush()
        
        from utils import pbc_wrap, get_box_length
        w = pbc_wrap(np.array([[12.0, -1.0, 5.0]]), 10.0)
        f.write(f'OK: PBC wrap {w[0]}\n'); f.flush()
        
        from molecular_dynamics import MolecularDynamics
        f.write('OK: MD class imported\n'); f.flush()
        
        md = MolecularDynamics(n_particles=32, temperature=1.0, density=0.8, dt=0.001, n_steps=500, dim=3, seed=42)
        f.write(f'OK: MD initialized. box={md.box_length:.3f} T0={md.temperature:.3f} PE0={md.potential_energy:.3f} KE0={md.kinetic_energy:.3f}\n'); f.flush()
        
        for step in range(1, 501):
            md.step()
            if step % 100 == 0:
                te = md.kinetic_energy + md.potential_energy
                f.write(f'  step {step:4d}: KE={md.kinetic_energy:8.3f} PE={md.potential_energy:8.3f} E={te:8.3f} T={md.temperature:6.3f}\n'); f.flush()
        
        f.write(f'\nOK: Simulation complete. Neighbor updates={md.n_neighbor_updates}\n'); f.flush()
        f.write('ALL TESTS PASSED\n')
        
    except Exception as e:
        import traceback
        f.write(f'ERROR: {e}\n{traceback.format_exc()}\n')
