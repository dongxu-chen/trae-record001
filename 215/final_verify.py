import sys, os
sys.path.insert(0, r'd:\Trae\project\record001\215')
os.chdir(r'd:\Trae\project\record001\215')

try:
    import numpy as np
    print('OK: numpy')
    
    from potentials import get_potential_config, compute_potential_energy, compute_force_vector
    r2 = np.array([1.0, 2.25, 4.0])
    print('LJ:', compute_potential_energy(r2, get_potential_config('lj', r_cut=3.0)))
    print('Morse:', compute_potential_energy(r2, get_potential_config('morse', r_cut=3.0)))
    print('Coulomb:', compute_potential_energy(r2, get_potential_config('coulomb', r_cut=3.0)))
    print('OK: potentials')
    
    from integrators import BerendsenThermostat, VerletIntegrator
    t = BerendsenThermostat(temperature=1.0, tau=0.1)
    v = np.random.randn(10, 3) * 0.5
    sv = t.apply(v, dt=0.001, current_temperature=0.5)
    print(f'Berendsen lambda (cold): {t.get_lambda():.4f}')
    sv2 = t.apply(v, dt=0.001, current_temperature=1.5)
    print(f'Berendsen lambda (hot): {t.get_lambda():.4f}')
    print('OK: integrators')
    
    from config import load_config, create_example_config
    create_example_config('test_cfg.json')
    cfg = load_config('test_cfg.json')
    print(f'Config loaded: N={cfg["system"]["n_particles"]}, T={cfg["system"]["temperature"]}')
    os.remove('test_cfg.json')
    print('OK: config')
    
    from trajectory import XYZWriter, read_xyz
    with XYZWriter('test.xyz', element='Ar') as w:
        w.write_frame(np.random.rand(10, 3)*10, step=0, box_length=10.0)
        w.write_frame(np.random.rand(10, 3)*10, step=100, box_length=10.0)
    frames = read_xyz('test.xyz')
    print(f'XYZ: {len(frames)} frames, {frames[0]["n_atoms"]} atoms each')
    os.remove('test.xyz')
    print('OK: trajectory')
    
    from molecular_dynamics import MolecularDynamics
    print('OK: molecular_dynamics imported')
    
    print('\n=== Running short LJ simulation ===')
    md = MolecularDynamics(
        n_particles=32, temperature=1.0, density=0.8,
        dt=0.001, n_steps=500, potential_type='lj', seed=42
    )
    hist = md.run(output_interval=100, verbose=True)
    print(f'LJ sim done: T={md.temperature:.4f}, PE={md.potential_energy:.4f}')
    
    print('\n=== Running Morse simulation ===')
    md2 = MolecularDynamics(
        n_particles=32, temperature=1.0, density=0.8,
        dt=0.001, n_steps=500, potential_type='morse',
        potential_config={'type': 'morse', 'epsilon': 1.0, 'alpha': 12.0, 'r0': 1.0, 'r_cut': 2.5},
        seed=42
    )
    hist2 = md2.run(output_interval=100, verbose=True)
    print(f'Morse sim done: T={md2.temperature:.4f}, PE={md2.potential_energy:.4f}')
    
    print('\n=== Running Berendsen thermostat simulation ===')
    md3 = MolecularDynamics(
        n_particles=32, temperature=1.0, density=0.8,
        dt=0.001, n_steps=1000, potential_type='lj',
        thermostat_enabled=True, thermostat_tau=0.1, target_temperature=1.5,
        seed=42
    )
    hist3 = md3.run(output_interval=200, verbose=True)
    temps = [h['temperature'] for h in hist3]
    print(f'Berendsen temps: {[f"{t:.3f}" for t in temps]}')
    
    print('\n=== Running with trajectory output ===')
    md4 = MolecularDynamics(
        n_particles=32, temperature=1.0, density=0.8,
        dt=0.001, n_steps=500, potential_type='lj', seed=42
    )
    hist4 = md4.run(
        output_interval=100, save_trajectory=True,
        trajectory_file='md_output.xyz', include_velocities=True,
        verbose=True
    )
    frames4 = read_xyz('md_output.xyz')
    print(f'Trajectory: {len(frames4)} frames saved to md_output.xyz')
    os.remove('md_output.xyz')
    
    print('\n' + '='*60)
    print('ALL TESTS PASSED!')
    print('='*60)
    
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
