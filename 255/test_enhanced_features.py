import os
import sys
import numpy as np


def test_msa_cache():
    print("=" * 60)
    print("Testing MSA Cache Feature")
    print("=" * 60)
    try:
        from config import Config
        from msa_features import MSAGenerator
        config = Config()
        config.cache.enable_cache = True
        config.cache.msa_cache_dir = os.path.join(os.getcwd(), "test_cache", "msa")
        os.makedirs(config.cache.msa_cache_dir, exist_ok=True)
        generator = MSAGenerator(config)
        sequence = "MKWVTFISLLFLFSSAYSRGVFRR"
        print("\nFirst prediction (should miss cache)...")
        result1 = generator.generate(sequence, job_id="cache_test_1")
        print(f"  MSA depth: {result1.feature.depth}")
        stats = generator.get_cache_stats()
        if stats:
            print(f"  Cache stats: {stats['total_entries']} entries, {stats['total_size_mb']:.2f} MB")
        print("\nSecond prediction (should hit cache)...")
        result2 = generator.generate(sequence, job_id="cache_test_2")
        print(f"  MSA depth: {result2.feature.depth}")
        stats = generator.get_cache_stats()
        if stats:
            print(f"  Cache stats: {stats['total_entries']} entries, {stats['total_size_mb']:.2f} MB")
        print("\n✓ MSA cache test passed!")
        return True
    except Exception as e:
        print(f"\n✗ MSA cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_residue_level_plddt():
    print("\n" + "=" * 60)
    print("Testing Residue-Level pLDDT")
    print("=" * 60)
    try:
        from confidence_evaluator import ConfidenceEvaluator
        evaluator = ConfidenceEvaluator()
        np.random.seed(42)
        sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
        plddt = np.concatenate([
            np.random.uniform(90, 100, 15),
            np.random.uniform(70, 90, 15),
            np.random.uniform(50, 70, 10),
            np.random.uniform(30, 50, 5),
        ])
        report = evaluator.evaluate(plddt, sequence=sequence)
        print(f"\nSequence length: {len(sequence)}")
        print(f"Mean pLDDT: {report.mean_plddt:.2f}")
        print(f"Overall quality: {report.overall_quality}")
        print(f"\nResidue confidence entries: {len(report.residue_confidence)}")
        print("\nResidue table (first 10):")
        table = evaluator.format_residue_table(report, max_rows=10)
        print(table)
        print("\nQuality summary:")
        summary = evaluator.format_quality_summary(report)
        print(summary)
        low_conf = evaluator.get_low_confidence_residues(report, 70.0)
        print(f"\nLow confidence residues (<70): {len(low_conf)}")
        high_conf = evaluator.get_high_confidence_residues(report, 90.0)
        print(f"High confidence residues (≥90): {len(high_conf)}")
        print("\n✓ Residue-level pLDDT test passed!")
        return True
    except Exception as e:
        print(f"\n✗ Residue-level pLDDT test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gpu_memory_manager():
    print("\n" + "=" * 60)
    print("Testing GPU Memory Manager")
    print("=" * 60)
    try:
        import torch
        from config import Config
        from structure_predictor import GPUMemoryManager
        config = Config()
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            print(f"GPU available: {torch.cuda.get_device_name(device)}")
            manager = GPUMemoryManager(device, config)
            status = manager.preallocate_memory()
            print(f"Preallocation status: {status.get('status', 'unknown')}")
            stats = manager.get_memory_stats()
            print(f"Memory stats: {stats}")
            print("\n✓ GPU memory manager test passed!")
        else:
            print("GPU not available, skipping GPU memory manager test")
        return True
    except Exception as e:
        print(f"\n✗ GPU memory manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamic_batcher():
    print("\n" + "=" * 60)
    print("Testing Dynamic Batcher")
    print("=" * 60)
    try:
        from config import Config
        from structure_predictor import DynamicBatcher
        config = Config()
        config.gpu.dynamic_batch = True
        config.gpu.max_batch_size = 8
        batcher = DynamicBatcher(config)
        test_cases = [
            (100, 32, 8.0, "Small protein"),
            (500, 128, 8.0, "Medium protein"),
            (1000, 256, 8.0, "Large protein"),
            (2000, 512, 8.0, "Very large protein"),
        ]
        for seq_len, msa_depth, available_gb, desc in test_cases:
            batch_size = batcher.get_optimal_batch_size(seq_len, msa_depth, available_gb)
            estimated_mem = batcher._estimate_memory_usage(seq_len, msa_depth)
            print(f"  {desc}: seq_len={seq_len}, msa_depth={msa_depth}")
            print(f"    Estimated memory per sample: {estimated_mem:.3f} GB")
            print(f"    Optimal batch size: {batch_size}")
        print("\n✓ Dynamic batcher test passed!")
        return True
    except Exception as e:
        print(f"\n✗ Dynamic batcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chunked_prediction():
    print("\n" + "=" * 60)
    print("Testing Chunked Prediction")
    print("=" * 60)
    try:
        from config import Config
        from structure_predictor import StructurePredictor
        config = Config()
        config.chunk.enable_chunking = True
        config.chunk.chunk_size = 30
        config.chunk.chunk_overlap = 10
        config.chunk.max_chunked_seq_len = 2000
        predictor = StructurePredictor(config)
        L = 100
        chunks = predictor._generate_chunks(L)
        print(f"Generated {len(chunks)} chunks for sequence length {L}")
        for chunk_idx, start, end in chunks:
            print(f"  Chunk {chunk_idx}: {start}-{end} (length={end-start})")
        weights = predictor._compute_chunk_weights(40, 30, 100)
        print(f"\nWeights for middle chunk (start=30, len=40, total=100):")
        print(f"  First 5: {weights[:5]}")
        print(f"  Last 5: {weights[-5:]}")
        print(f"  Mean: {weights.mean():.3f}, Min: {weights.min():.3f}, Max: {weights.max():.3f}")
        print("\n✓ Chunked prediction test passed!")
        return True
    except Exception as e:
        print(f"\n✗ Chunked prediction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline_with_enhancements():
    print("\n" + "=" * 60)
    print("Testing Full Pipeline with Enhancements")
    print("=" * 60)
    try:
        from protein_predictor import ProteinStructurePredictor
        from config import Config
        config = Config()
        config.cache.enable_cache = True
        config.chunk.enable_chunking = True
        config.chunk.chunk_size = 20
        config.prediction.show_residue_plddt = True
        predictor = ProteinStructurePredictor(config)
        predictor.initialize()
        sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
        print(f"\nSequence length: {len(sequence)}")
        result = predictor.predict(sequence, job_id="enhanced_test")
        print(f"\n✓ Prediction completed!")
        print(f"  Job ID: {result.job_id}")
        print(f"  Mean pLDDT: {result.confidence_report.mean_plddt:.2f}")
        print(f"  Overall quality: {result.confidence_report.overall_quality}")
        print(f"  Residue confidence entries: {len(result.confidence_report.residue_confidence)}")
        print(f"  Total time: {result.total_time:.2f}s")
        print("\n" + "-" * 40)
        print("Residue-level pLDDT (first 10 residues):")
        print("-" * 40)
        for i, res in enumerate(result.confidence_report.residue_confidence[:10]):
            print(f"  {res.amino_acid}{res.index + 1:4d}: pLDDT={res.plddt:.2f} ({res.quality})")
        print("\n✓ Full pipeline with enhancements test passed!")
        return True
    except Exception as e:
        print(f"\n✗ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("ENHANCED FEATURES TEST SUITE")
    print("=" * 60)
    print()
    results = {}
    results["msa_cache"] = test_msa_cache()
    results["residue_plddt"] = test_residue_level_plddt()
    results["gpu_memory"] = test_gpu_memory_manager()
    results["dynamic_batch"] = test_dynamic_batcher()
    results["chunked_prediction"] = test_chunked_prediction()
    results["full_pipeline"] = test_full_pipeline_with_enhancements()
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name:25s}: {status}")
    total = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total}/{total_tests} tests passed")
    if total == total_tests:
        print("\nAll enhanced feature tests passed! ✓")
        sys.exit(0)
    else:
        print(f"\n{total_tests - total} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
