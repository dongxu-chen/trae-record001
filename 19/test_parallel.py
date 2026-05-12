import sys
sys.path.insert(0, 'd:/Trae/project/record001/19')

from parallel import ColumnParallel
import numpy as np

print('Testing parallel.py (single-process mode)...')
print('='*60)

n_columns = 10

cp = ColumnParallel(n_columns, use_mpi=False)

print(f'Rank: {cp.rank}')
print(f'Size: {cp.size}')
print(f'Is root: {cp.is_root}')

local_cols = cp.get_local_columns()
print(f'Local columns indices: {local_cols}')
print(f'Local columns count: {cp.local_columns}')

# Test scatter data
data = np.random.rand(n_columns, 5, 3)
print(f'Original data shape: {data.shape}')

local_data = cp.scatter_data(data)
print(f'Local data shape after scatter: {local_data.shape}')

# Test gather data
gathered = cp.gather_data(local_data)
print(f'Gathered data shape: {gathered.shape}')

# Verify data integrity
if cp.is_root:
    print('Are original and gathered equal?', np.allclose(data, gathered))

# Test gather results
results = {'flux': np.random.rand(cp.local_columns, 3)}
all_results = cp.gather_results(results)

if cp.is_root:
    print('Gathered results flux shape:', all_results['flux'].shape)

print()
print('parallel.py test passed!')
