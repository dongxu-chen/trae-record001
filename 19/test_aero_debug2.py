import sys
sys.path.insert(0, 'd:/Trae/project/record001/19')

import backend as bk
xp = bk.get_backend()

from aerosol import AerosolEffect

n_columns = 5
aerosol = AerosolEffect(n_columns=n_columns)

print("Detailed debugging...")
print("="*60)

concentration = xp.array([15., 15., 15., 15., 15.])
aerosol_type = ['sulfate', 'sulfate', 'sulfate', 'sulfate', 'sulfate']
rel_hum = xp.array([70., 70., 70., 70., 70.])
scale_height = 2.0

# Step by step trace
aerosol_mass_concentration = xp.asarray(concentration)
print(f"Step 1: aerosol_mass_concentration ndim={aerosol_mass_concentration.ndim}, shape={aerosol_mass_concentration.shape}")

if aerosol_mass_concentration.ndim == 0:
    print("  -> ndim == 0 branch")
    n_layers = 1
    mc = xp.full((n_columns, n_layers), float(aerosol_mass_concentration))
elif aerosol_mass_concentration.ndim == 1:
    print(f"  -> ndim == 1 branch, shape[0]={aerosol_mass_concentration.shape[0]}, n_columns={n_columns}")
    if aerosol_mass_concentration.shape[0] == n_columns:
        print("    -> shape[0] == n_columns, n_layers=1")
        n_layers = 1
        mc = aerosol_mass_concentration.reshape(-1, 1)
    else:
        print("    -> shape[0] != n_columns, using as n_layers")
        n_layers = aerosol_mass_concentration.shape[0]
        mc = xp.broadcast_to(aerosol_mass_concentration, (n_columns, n_layers))
else:
    print("  -> ndim == 2+ branch")
    n_layers = aerosol_mass_concentration.shape[1]
    mc = aerosol_mass_concentration

print(f"Step 2: n_layers={n_layers}, mc shape={mc.shape}")

# Check aerosol type handling
print(f"\nStep 3: aerosol_type isinstance(list)={isinstance(aerosol_type, list)}")
print(f"         len(aerosol_type)={len(aerosol_type)}")
print(f"         isinstance(aerosol_type[0], list)={isinstance(aerosol_type[0], list)}")

if isinstance(aerosol_type, list) and len(aerosol_type) == n_columns and not isinstance(aerosol_type[0], list):
    aerosol_type_for_indices = [[at] for at in aerosol_type]
    print(f"         -> Converting to 2D list: {aerosol_type_for_indices}")
else:
    aerosol_type_for_indices = aerosol_type
    print(f"         -> No conversion needed")

ssa, g, ext_eff = aerosol._aerosol_type_to_indices(aerosol_type_for_indices, n_layers)
print(f"\nStep 4: ssa shape={ssa.shape}, g shape={g.shape}, ext_eff shape={ext_eff.shape}")

rh_factor = 1.0 + 0.01 * (rel_hum / 100.0) ** 3
print(f"\nStep 5: rh_factor shape={rh_factor.shape}")

mass_extinction = ext_eff * rh_factor
print(f"         mass_extinction shape={mass_extinction.shape}")
print(f"         mc shape={mc.shape}")

aod = mass_extinction * mc * scale_height * 1e-3
print(f"\nStep 6: aod shape={aod.shape}")

aod = xp.where(mc > 0, xp.maximum(0.0, aod), 0.0)
print(f"Step 7: aod shape after where={aod.shape}")

print(f"\nStep 8: aod.shape[1]={aod.shape[1]}")
if aod.shape[1] == 1:
    print("         -> Returning aod[:, 0]")
    result = aod[:, 0]
else:
    print("         -> Returning full aod")
    result = aod
    
print(f"\nFinal result shape={result.shape}")
