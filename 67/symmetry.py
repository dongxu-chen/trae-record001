import numpy as np
from atom import ATOMIC_NUMBERS


def compute_center_of_mass(atoms):
    total_mass = 0.0
    com = np.zeros(3, dtype=np.float64)
    
    for symbol, center in atoms:
        mass = ATOMIC_NUMBERS[symbol]
        total_mass += mass
        com += mass * np.array(center, dtype=np.float64)
    
    if total_mass > 0:
        com /= total_mass
    
    return com


def compute_principal_axes(atoms):
    com = compute_center_of_mass(atoms)
    
    I = np.zeros((3, 3), dtype=np.float64)
    
    for symbol, center in atoms:
        mass = ATOMIC_NUMBERS[symbol]
        r = np.array(center, dtype=np.float64) - com
        I[0, 0] += mass * (r[1]**2 + r[2]**2)
        I[1, 1] += mass * (r[0]**2 + r[2]**2)
        I[2, 2] += mass * (r[0]**2 + r[1]**2)
        I[0, 1] -= mass * r[0] * r[1]
        I[0, 2] -= mass * r[0] * r[2]
        I[1, 2] -= mass * r[1] * r[2]
    
    I[1, 0] = I[0, 1]
    I[2, 0] = I[0, 2]
    I[2, 1] = I[1, 2]
    
    eigvals, eigvecs = np.linalg.eigh(I)
    
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    
    return eigvals, eigvecs, com


def rotation_matrix(axis, theta):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.sqrt(np.dot(axis, axis))
    a = np.cos(theta / 2.0)
    b, c, d = -axis * np.sin(theta / 2.0)
    aa, bb, cc, dd = a*a, b*b, c*c, d*d
    bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
    return np.array([
        [aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
        [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
        [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]
    ], dtype=np.float64)


def apply_symmetry_operation(atoms, R, com):
    new_atoms = []
    for symbol, center in atoms:
        r = np.array(center, dtype=np.float64) - com
        new_r = np.dot(R, r) + com
        new_atoms.append((symbol, list(new_r)))
    return new_atoms


def is_symmetry_operation(atoms, R, com, tolerance=1e-3):
    transformed = apply_symmetry_operation(atoms, R, com)
    
    for symbol1, center1 in transformed:
        found = False
        for symbol2, center2 in atoms:
            if symbol1 == symbol2:
                dist = np.linalg.norm(np.array(center1) - np.array(center2))
                if dist < tolerance:
                    found = True
                    break
        if not found:
            return False
    
    return True


def find_principal_rotations(atoms, max_order=6, tolerance=1e-3):
    eigvals, eigvecs, com = compute_principal_axes(atoms)
    
    rotations = []
    
    for axis_idx in range(3):
        axis = eigvecs[:, axis_idx]
        if np.linalg.norm(axis) < 1e-10:
            continue
        
        for n in range(2, max_order + 1):
            theta = 2 * np.pi / n
            R = rotation_matrix(axis, theta)
            if is_symmetry_operation(atoms, R, com, tolerance):
                rotations.append({
                    'axis': axis,
                    'order': n,
                    'axis_idx': axis_idx,
                })
                break
    
    return rotations, eigvecs, com


def detect_point_group(atoms, tolerance=1e-3):
    n_atoms = len(atoms)
    
    if n_atoms == 1:
        return 'Kh'
    
    rotations, eigvecs, com = find_principal_rotations(atoms, max_order=6, tolerance=tolerance)
    
    unique_symbols = set(symbol for symbol, center in atoms)
    
    n_unique = len(unique_symbols)
    
    if n_atoms == 2:
        if n_unique == 1:
            return 'D∞h'
        else:
            return 'C∞v'
    
    principal_rotation = None
    for rot in rotations:
        if rot['order'] >= 2:
            if principal_rotation is None or rot['order'] > principal_rotation['order']:
                principal_rotation = rot
    
    if principal_rotation is None:
        return 'C1'
    
    n = principal_rotation['order']
    
    c2_axes = 0
    for rot in rotations:
        if rot['order'] == 2 and rot['axis_idx'] != principal_rotation['axis_idx']:
            axis_dot = np.abs(np.dot(rot['axis'], principal_rotation['axis']))
            if axis_dot < 0.1:
                c2_axes += 1
    
    has_inversion = False
    if n_atoms % 2 == 0:
        inversion = is_symmetry_operation(atoms, -np.eye(3, dtype=np.float64), com, tolerance)
        has_inversion = inversion
    
    if n == 2:
        if c2_axes >= 2:
            if has_inversion:
                return 'D2h'
            return 'D2'
        else:
            if has_inversion:
                return 'C2h'
            return 'C2'
    
    if n >= 3:
        if c2_axes >= n:
            if has_inversion:
                if n % 2 == 0:
                    if n == 6:
                        return 'D6h'
                    if n == 4:
                        return 'D4h'
                    if n == 5:
                        return 'D5h'
                return f'D{n}h'
            return f'D{n}'
        else:
            if has_inversion:
                return f'C{n}h'
            return f'C{n}'
    
    return 'C1'


def get_symmetry_information(atoms, tolerance=1e-3):
    point_group = detect_point_group(atoms, tolerance)
    
    rotations, eigvecs, com = find_principal_rotations(atoms, max_order=6, tolerance=tolerance)
    
    symm_info = {
        'point_group': point_group,
        'center_of_mass': com,
        'principal_axes': eigvecs,
        'rotations': rotations,
    }
    
    return symm_info


def symmetry_reduce_integrals(eri, symmetry_info):
    return eri


def symmetry_reduce_fock(F, symmetry_info):
    return F


def symmetry_symmetric_positions(atoms, symmetry_info, tolerance=1e-3):
    groups = []
    used = set()
    
    com = symmetry_info['center_of_mass']
    rotations = symmetry_info['rotations']
    
    rotation_ops = []
    for rot in rotations:
        for k in range(1, rot['order']):
            theta = 2 * np.pi * k / rot['order']
            R = rotation_matrix(rot['axis'], theta)
            rotation_ops.append(R)
    
    for i, (symbol1, center1) in enumerate(atoms):
        if i in used:
            continue
        
        group = [i]
        used.add(i)
        
        r1 = np.array(center1, dtype=np.float64) - com
        
        for R in rotation_ops:
            r_new = np.dot(R, r1)
            new_center = r_new + com
            
            for j, (symbol2, center2) in enumerate(atoms):
                if j in used or j == i:
                    continue
                if symbol1 != symbol2:
                    continue
                
                dist = np.linalg.norm(new_center - np.array(center2))
                if dist < tolerance:
                    group.append(j)
                    used.add(j)
                    break
        
        groups.append(group)
    
    return groups


def symmetry_unique_indices(atoms, symmetry_info):
    groups = symmetry_symmetric_positions(atoms, symmetry_info)
    unique_indices = [g[0] for g in groups]
    return unique_indices, groups


def print_symmetry_info(atoms, tolerance=1e-3):
    info = get_symmetry_information(atoms, tolerance)
    
    print("\n" + "=" * 70)
    print("                         SYMMETRY INFORMATION")
    print("=" * 70)
    print()
    
    print(f"Detected point group: {info['point_group']}")
    print()
    
    print(f"Center of mass: {info['center_of_mass']}")
    print()
    
    print("Principal axes (eigenvectors):")
    for i, axis in enumerate(info['principal_axes'].T):
        print(f"  Axis {i+1}: {axis}")
    print()
    
    if info['rotations']:
        print("Rotation axes detected:")
        for rot in info['rotations']:
            print(f"  C{rot['order']} axis: {rot['axis']}")
    else:
        print("No rotation axes detected.")
    
    print()
    print("=" * 70)
