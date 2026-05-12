import sys
sys.path.insert(0, 'd:/Trae/project/record001/19')

import backend as bk
xp = bk.get_backend()

from aerosol import AerosolEffect

n_columns = 5
aerosol = AerosolEffect(n_columns=n_columns)

print("Test with list of strings per column:")
print("="*60)

# Simulate what apply_aerosol_effect_to_shortwave does
concentration = xp.array([15., 15., 15., 15., 15.])
aerosol_type = ['sulfate', 'sulfate', 'sulfate', 'sulfate', 'sulfate']
rel_hum = xp.array([70., 70., 70., 70., 70.])

print(f"concentration shape: {concentration.shape}")
print(f"aerosol_type: {aerosol_type} (len={len(aerosol_type)}, type of first: {type(aerosol_type[0])})")
print(f"rel_hum shape: {rel_hum.shape}")

# Test is check
is_correct_shape = (
    isinstance(aerosol_type, list) and 
    len(aerosol_type) == n_columns and 
    not isinstance(aerosol_type[0], list)
)
print(f"is_correct_shape: {is_correct_shape}")

if is_correct_shape:
    aerosol_type_for_indices = [[at] for at in aerosol_type]
else:
    aerosol_type_for_indices = aerosol_type

print(f"aerosol_type_for_indices: {aerosol_type_for_indices}")

ssa, g, ext_eff = aerosol._aerosol_type_to_indices(aerosol_type_for_indices, 1)
print(f"ssa shape: {ssa.shape}")
print(f"g shape: {g.shape}")
print(f"ext_eff shape: {ext_eff.shape}")

# Now test the full function
aod = aerosol.calculate_aerosol_optical_depth(concentration, aerosol_type, rel_hum)
print(f"\ncalculate_aerosol_optical_depth result:")
print(f"  aod shape: {aod.shape}")
print(f"  aod values: {aod}")
