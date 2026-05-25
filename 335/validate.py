import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_import_test():
    print("\n" + "=" * 60)
    print("Running Import Test")
    print("=" * 60)
    from tests.test_imports import test_imports
    return test_imports()


def run_post_processing_test():
    print("\n" + "=" * 60)
    print("Running Post-Processing Test")
    print("=" * 60)
    from tests.test_post_processing import main as run_post_tests
    return run_post_tests()


def run_point_cloud_test():
    print("\n" + "=" * 60)
    print("Running Point Cloud Test")
    print("=" * 60)
    from tests.test_point_cloud import main as run_pc_tests
    return run_pc_tests()


def check_dependencies():
    print("\n" + "=" * 60)
    print("Checking Dependencies")
    print("=" * 60)
    
    core_dependencies = [
        ("numpy", "NumPy"),
        ("cv2", "OpenCV"),
        ("torch", "PyTorch"),
        ("matplotlib", "Matplotlib"),
        ("PIL", "Pillow"),
        ("tqdm", "tqdm"),
        ("scipy", "SciPy"),
    ]
    
    optional_dependencies = [
        ("open3d", "Open3D"),
        ("onnxruntime", "ONNX Runtime"),
    ]
    
    core_ok = True
    print("Core dependencies:")
    for module, name in core_dependencies:
        try:
            __import__(module)
            print(f"  ✓ {name} is installed")
        except ImportError:
            print(f"  ✗ {name} is NOT installed")
            core_ok = False
    
    print("\nOptional dependencies:")
    optional_warning = False
    for module, name in optional_dependencies:
        try:
            __import__(module)
            print(f"  ✓ {name} is installed")
        except ImportError:
            print(f"  ⚠️  {name} is NOT installed (optional)")
            optional_warning = True
    
    if optional_warning:
        print("\n  Note: Some optional features will use fallback implementations.")
        print("  Install optional dependencies for full functionality.")
    
    return core_ok


def show_project_structure():
    print("\n" + "=" * 60)
    print("Project Structure")
    print("=" * 60)
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "__pycache__" in dirpath or ".git" in dirpath:
            continue
        
        level = dirpath.replace(root_dir, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(dirpath)}/")
        
        subindent = " " * 2 * (level + 1)
        for filename in filenames:
            if filename.endswith(".py"):
                print(f"{subindent}{filename}")


def main():
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#" + " " * 15 + "DEPTH ESTIMATION PROJECT" + " " * 18 + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    
    show_project_structure()
    
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\n⚠️  Some dependencies are missing. Install them with:")
        print("   pip install -r requirements.txt")
        print("\n   Trying to run tests anyway...\n")
    
    import_ok = run_import_test()
    
    if not import_ok:
        print("\n❌ Import tests failed. Cannot proceed with other tests.")
        return False
    
    post_ok = run_post_processing_test()
    pc_ok = run_point_cloud_test()
    
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#" + " " * 20 + "VALIDATION SUMMARY" + " " * 23 + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    
    results = [
        ("Dependencies", deps_ok),
        ("Imports", import_ok),
        ("Post-Processing", post_ok),
        ("Point Cloud", pc_ok),
    ]
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name:25s}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "#" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! The project is ready to use.")
        print("\n📖 Quick Start Guide:")
        print("   1. Process a single image:")
        print("      python main.py --mode image --input your_image.jpg --output output")
        print("\n   2. Real-time webcam depth estimation:")
        print("      python main.py --mode webcam --model-type MiDaS_small")
        print("\n   3. Generate point cloud:")
        print("      python main.py --mode pointcloud --input your_image.jpg --output cloud.ply")
        print("\n   4. Process a video file:")
        print("      python main.py --mode video --input video.mp4 --output output.mp4")
        print("\n   5. Export model to ONNX:")
        print("      python main.py --mode export_onnx --model-type MiDaS_small --output model.onnx")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
