import sys
sys.path.insert(0, 'd:/Trae/project/record001/19')

from flux_storage import FluxStorage, BatchFluxWriter
import numpy as np

print('Testing flux_storage.py...')
print('='*60)

storage = FluxStorage('test_fluxes.h5', mode='w')

results = {
    'shortwave': {
        'downward_flux': np.random.rand(5, 3, 10),
        'upward_flux': np.random.rand(5, 3, 10),
        'net_flux': np.random.rand(5, 3, 10),
        'n_columns': 5,
        'n_bands': 3,
        'n_levels': 10
    },
    'longwave': {
        'downward_flux': np.random.rand(5, 3, 10),
        'upward_flux': np.random.rand(5, 3, 10),
        'net_flux': np.random.rand(5, 3, 10)
    },
    'net': {
        'net_flux': np.random.rand(5, 3, 10)
    },
    'heating_rate': np.random.rand(5, 3, 9)
}

storage.save_radiation_results(results, timestep=0)
storage.save_metadata({'model': 'test', 'n_columns': 5})
storage.close()

print('Data saved successfully!')

storage2 = FluxStorage('test_fluxes.h5', mode='r')
loaded = storage2.load_radiation_results(timestep=0)
print('Loaded downward_flux shape:', loaded['shortwave']['downward_flux'].shape)
meta = storage2.load_metadata()
print('Metadata:', meta)
storage2.close()

print()
print('Testing BatchFluxWriter...')
print('-'*60)

batch_storage = FluxStorage('test_batch.h5', mode='w')
batch_writer = BatchFluxWriter(batch_storage, batch_size=3)

for t in range(5):
    batch_results = {
        'shortwave': {
            'downward_flux': np.random.rand(5, 3, 10) + t,
            'upward_flux': np.random.rand(5, 3, 10),
            'net_flux': np.random.rand(5, 3, 10)
        },
        'longwave': {
            'upward_flux': np.random.rand(5, 3, 10),
        },
    }
    batch_writer.add_results(batch_results, timestep=t)
    print(f'Added timestep {t}, cached: {len(batch_writer.cache)}')

batch_writer.flush()
batch_writer.close()
print('Batch data written!')

storage3 = FluxStorage('test_batch.h5', mode='r')
keys = storage3.file.keys()
print('Timesteps in batch file:', list(keys))
storage3.close()

print()
print('flux_storage.py all tests passed!')
