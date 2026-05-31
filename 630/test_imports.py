import sys
import numpy as np

print("Testing imports...")

try:
    from kalman_filter import KalmanFilter, BPMKalmanFilter
    print("✓ kalman_filter imported successfully")

    kf = BPMKalmanFilter(initial_bpm=120.0)
    bpm, conf = kf.update(125.0, 0.8)
    print(f"  Kalman filter test: BPM={bpm:.1f}, Confidence={conf:.2f}")
except Exception as e:
    print(f"✗ kalman_filter failed: {e}")
    sys.exit(1)

try:
    from beat_tracker import BeatTracker
    print("✓ beat_tracker imported successfully")

    tracker = BeatTracker(sr=22050, hop_length=256, style='generic')
    print(f"  BeatTracker style: {tracker.style}")

    test_audio = np.random.randn(22050 * 5)
    result = tracker.process_frame(test_audio)
    if result:
        print(f"  Beat detection test: BPM={result['bpm']:.1f}, Beats={len(result['beats'])}")
    else:
        print("  Beat detection test: No result (expected for noise)")
except Exception as e:
    print(f"✗ beat_tracker failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from beat_lock import BeatLock, AdaptiveBeatLock
    print("✓ beat_lock imported successfully")

    lock = AdaptiveBeatLock()
    is_locked, bpm = lock.update([1.0, 2.0, 3.0], 120.0, 0.8, 3.0)
    print(f"  BeatLock test: Locked={is_locked}, BPM={bpm:.1f}")
except Exception as e:
    print(f"✗ beat_lock failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from visualization import BeatVisualizer, OfflineVisualizer
    print("✓ visualization imported successfully")
except ImportError as e:
    print(f"⚠ visualization import warning (matplotlib may need display): {e}")
except Exception as e:
    print(f"✗ visualization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from audio_input import AudioInput
    print("✓ audio_input imported successfully")
except ImportError as e:
    print(f"⚠ audio_input import warning (PyAudio may not be installed): {e}")
except Exception as e:
    print(f"✗ audio_input failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All core modules imported and tested successfully!")
print("\nModule structure:")
print("  kalman_filter.py     - KalmanFilter, BPMKalmanFilter")
print("  beat_tracker.py      - BeatTracker (Librosa + DP + Kalman)")
print("  beat_lock.py         - BeatLock, AdaptiveBeatLock")
print("  audio_input.py       - AudioInput (PyAudio)")
print("  visualization.py     - BeatVisualizer, OfflineVisualizer (Matplotlib)")
print("  main.py              - Main entry point")
print("\nNext steps:")
print("  1. Install dependencies: pip install -r requirements.txt")
print("  2. Run offline test: python main.py --file <audio_file>")
print("  3. Run real-time: python main.py --realtime")
