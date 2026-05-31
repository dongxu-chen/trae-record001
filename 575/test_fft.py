import numpy as np
from fft_water import FFTWave

def test_fft_wave():
    print("Testing FFT Wave module...")

    for spectrum_type in ['phillips', 'jonswap', 'pm']:
        print(f"\n--- {spectrum_type.upper()} Spectrum ---")
        wave = FFTWave(grid_size=64, patch_size=50.0, spectrum_type=spectrum_type)
        print(f"  Spectrum type: {wave.spectrum_type}")

        time = 1.0
        heights = wave.compute_wave_height(time)
        print(f"  Heights shape: {heights.shape}")
        print(f"  Heights range: [{heights.min():.4f}, {heights.max():.4f}]")

        dx, dz = wave.compute_choppy_displacement(time)
        print(f"  Displacement dx range: [{dx.min():.4f}, {dx.max():.4f}]")

        normals = wave.compute_normals(heights)
        print(f"  Normals shape: {normals.shape}")

        foam = wave.compute_foam(heights, time=time)
        print(f"  Foam coverage: {(foam > 0.5).mean() * 100:.1f}%")

    print("\n--- Spectrum Switching ---")
    wave = FFTWave(grid_size=64, patch_size=50.0, spectrum_type='phillips')
    h1 = wave.compute_wave_height(1.0)
    wave.set_spectrum_type('jonswap')
    h2 = wave.compute_wave_height(1.0)
    print(f"  Phillips heights range: [{h1.min():.4f}, {h1.max():.4f}]")
    print(f"  JONSWAP heights range: [{h2.min():.4f}, {h2.max():.4f}]")

    print("\nAll tests passed!")

if __name__ == '__main__':
    test_fft_wave()
