import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import test_rtb_engine
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_rtb_engine)
    
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)
    
    with open('test_results.txt', 'r', encoding='utf-8') as f:
        print(f.read())
    
    print(f"\n{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Success: {result.wasSuccessful()}")
    print(f"{'='*60}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
