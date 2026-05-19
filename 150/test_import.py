#!/usr/bin/env python
# -*- coding: utf-8 -*-

print("Testing MS Peak Detector imports...")

try:
    from ms_peak_detector.core import MSPeakProcessor
    print("✓ MSPeakProcessor imported successfully")
except Exception as e:
    print(f"✗ MSPeakProcessor import failed: {e}")

try:
    from ms_peak_detector.baseline_correction import BaselineCorrector
    print("✓ BaselineCorrector imported successfully")
except Exception as e:
    print(f"✗ BaselineCorrector import failed: {e}")

try:
    from ms_peak_detector.peak_detection import PeakDetector
    print("✓ PeakDetector imported successfully")
except Exception as e:
    print(f"✗ PeakDetector import failed: {e}")

try:
    from ms_peak_detector.peak_alignment import PeakAligner, SpectrumAligner
    print("✓ PeakAligner, SpectrumAligner imported successfully")
except Exception as e:
    print(f"✗ PeakAligner import failed: {e}")

try:
    from ms_peak_detector.isotope_detection import IsotopeDetector
    print("✓ IsotopeDetector imported successfully")
except Exception as e:
    print(f"✗ IsotopeDetector import failed: {e}")

try:
    from ms_peak_detector.processor import MSPeakAnalysisPipeline
    print("✓ MSPeakAnalysisPipeline imported successfully")
except Exception as e:
    print(f"✗ MSPeakAnalysisPipeline import failed: {e}")

try:
    from ms_peak_detector import (
        MSPeakProcessor,
        BaselineCorrector,
        PeakDetector,
        PeakAligner,
        SpectrumAligner,
        IsotopeDetector,
        MSPeakAnalysisPipeline
    )
    print("\n✓ All main imports successful!")
except Exception as e:
    print(f"\n✗ Main imports failed: {e}")

print("\nTesting basic functionality...")

try:
    import numpy as np
    pipeline = MSPeakAnalysisPipeline()
    
    mz, intensity = pipeline.generate_test_spectrum(num_peaks=5, mz_range=(100, 500))
    print(f"✓ Generated test spectrum: {len(mz)} points")
    
    corrector = BaselineCorrector(method="rolling_min")
    corrected = corrector.correct(mz, intensity)
    print(f"✓ Baseline correction completed")
    
    detector = PeakDetector(method="local_max")
    peaks = detector.detect(mz, corrected, threshold=0.1)
    print(f"✓ Detected {len(peaks)} peaks")
    
    isotope_detector = IsotopeDetector()
    theoretical = isotope_detector.calculate_theoretical_isotope_distribution("C6H12O6")
    print(f"✓ Calculated theoretical isotope distribution")
    
    print("\n" + "="*50)
    print("All tests passed successfully! ✓")
    print("="*50)
    
except Exception as e:
    print(f"\n✗ Functionality test failed: {e}")
    import traceback
    traceback.print_exc()
