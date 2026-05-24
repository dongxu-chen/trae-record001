import os
import sys
import numpy as np


def test_imports():
    print("Testing imports...")
    try:
        from config import Config
        print("  ✓ config")
        from msa_features import MSAGenerator, validate_sequence, build_msa_feature
        print("  ✓ msa_features")
        from structure_predictor import StructurePredictor, AlphaFold2Lite
        print("  ✓ structure_predictor")
        from confidence_evaluator import ConfidenceEvaluator, compute_plddt_stats
        print("  ✓ confidence_evaluator")
        from protein_predictor import ProteinStructurePredictor, predict_protein_structure
        print("  ✓ protein_predictor")
        from utils import PDBUtils, SequenceUtils
        print("  ✓ utils")
        print("All imports successful!\n")
        return True
    except Exception as e:
        print(f"Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sequence_validation():
    print("Testing sequence validation...")
    from msa_features import validate_sequence
    test_cases = [
        ("MKWVTFISLLFLFSSAYSRGVFRR", True, "Valid sequence"),
        ("", False, "Empty sequence"),
        ("ABCXYZ123", False, "Invalid characters"),
        ("ACDEFGHIKLMNPQRSTVWY", True, "All amino acids"),
    ]
    for seq, expected_valid, desc in test_cases:
        valid, msg = validate_sequence(seq)
        status = "✓" if valid == expected_valid else "✗"
        print(f"  {status} {desc}: valid={valid}")
    print()


def test_msa_generation():
    print("Testing MSA generation...")
    try:
        from config import Config
        from msa_features import MSAGenerator, build_msa_feature
        config = Config()
        generator = MSAGenerator(config)
        sequence = "MKWVTFISLLFLFSSAYSRGVFRR"
        msa_output = generator.generate(sequence, job_id="test_job")
        print(f"  ✓ MSA generated with {msa_output.feature.depth} sequences")
        print(f"  ✓ Sequence length: {len(sequence)}")
        print(f"  ✓ Alignment matrix shape: {msa_output.feature.alignment_matrix.shape}")
        if msa_output.feature.pssm is not None:
            print(f"  ✓ PSSM shape: {msa_output.feature.pssm.shape}")
        print()
        return msa_output
    except Exception as e:
        print(f"  ✗ MSA generation failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return None


def test_model_creation():
    print("Testing model creation...")
    try:
        from config import Config
        from structure_predictor import AlphaFold2Lite
        model_config = type('ModelConfig', (), {
            'msa_channels': 256,
            'pair_channels': 128,
            'struct_channels': 384,
            'num_evo_blocks': 2,
        })
        model = AlphaFold2Lite(model_config)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"  ✓ Model created with {total_params:,} parameters")
        batch_size = 1
        N, L = 16, 50
        msa = torch.randint(0, 21, (batch_size, N, L))
        seq = torch.randint(0, 21, (batch_size, L))
        with torch.no_grad():
            outputs = model({"msa": msa, "sequence": seq})
        print(f"  ✓ Forward pass successful")
        print(f"  ✓ Output keys: {list(outputs.keys())}")
        print(f"  ✓ Positions shape: {outputs['positions'].shape}")
        print(f"  ✓ PLDDT shape: {outputs['plddt'].shape}")
        print()
        return True
    except ImportError as e:
        print(f"  ✗ PyTorch not available: {e}")
        print()
        return False
    except Exception as e:
        print(f"  ✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_confidence_evaluation():
    print("Testing confidence evaluation...")
    try:
        from confidence_evaluator import ConfidenceEvaluator, compute_plddt_stats, interpret_plddt
        evaluator = ConfidenceEvaluator()
        np.random.seed(42)
        plddt = np.random.uniform(40, 95, size=50)
        pae = np.random.uniform(0, 20, size=(50, 50))
        report = evaluator.evaluate(plddt, pae, ptm=0.85, iptm=0.75)
        print(f"  ✓ Report generated")
        print(f"  ✓ Mean pLDDT: {report.mean_plddt:.2f}")
        print(f"  ✓ Overall quality: {report.overall_quality}")
        print(f"  ✓ Quality regions: {len(report.quality_regions)} regions")
        print(f"  ✓ PAE stats computed: {report.pae_stats is not None}")
        stats = compute_plddt_stats(plddt)
        print(f"  ✓ PLDDT stats: {len(stats)} metrics")
        interpretation = interpret_plddt(report.mean_plddt)
        print(f"  ✓ Interpretation: {interpretation['quality']}")
        print()
        return True
    except Exception as e:
        print(f"  ✗ Confidence evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_utils():
    print("Testing utilities...")
    try:
        from utils import SequenceUtils, PDBUtils, compute_rmsd, compute_contact_map
        sequence = "MKWVTFISLLFLFSSAYSRGVFRR"
        valid, msg = SequenceUtils.validate(sequence)
        print(f"  ✓ Sequence validation: {valid}")
        props = SequenceUtils.properties(sequence)
        print(f"  ✓ Sequence properties: {len(props)} properties")
        coords1 = np.random.randn(10, 3)
        coords2 = coords1 + np.random.randn(10, 3) * 0.1
        rmsd = compute_rmsd(coords1, coords2)
        print(f"  ✓ RMSD computation: {rmsd:.4f}")
        contact_map = compute_contact_map(coords1, threshold=8.0)
        print(f"  ✓ Contact map shape: {contact_map.shape}")
        print()
        return True
    except Exception as e:
        print(f"  ✗ Utils test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_full_prediction():
    print("Testing full prediction pipeline...")
    try:
        from protein_predictor import ProteinStructurePredictor
        from config import Config
        config = Config()
        config.prediction.save_pdb = True
        predictor = ProteinStructurePredictor(config)
        predictor.initialize()
        sequence = "MKWVTFISLLFLFSSAYSRGVFRR"
        result = predictor.predict(sequence, job_id="test_full")
        print(f"  ✓ Prediction successful")
        print(f"  ✓ Job ID: {result.job_id}")
        print(f"  ✓ Sequence length: {result.sequence_length}")
        print(f"  ✓ Mean pLDDT: {result.confidence_report.mean_plddt:.2f}")
        print(f"  ✓ PDB generated: {len(result.pdb_content) > 0}")
        print(f"  ✓ Total time: {result.total_time:.2f}s")
        print()
        return result
    except Exception as e:
        print(f"  ✗ Full prediction failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return None


def main():
    print("=" * 60)
    print("Protein Structure Predictor - Test Suite")
    print("=" * 60)
    print()
    results = {}
    results["imports"] = test_imports()
    if not results["imports"]:
        print("Critical: Imports failed. Exiting.")
        sys.exit(1)
    global torch
    try:
        import torch
    except ImportError:
        torch = None
    test_sequence_validation()
    results["msa"] = test_msa_generation() is not None
    if torch is not None:
        results["model"] = test_model_creation()
    else:
        print("Skipping model test (PyTorch not available)\n")
        results["model"] = False
    results["confidence"] = test_confidence_evaluation()
    results["utils"] = test_utils()
    results["full_prediction"] = test_full_prediction() is not None
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name:20s}: {status}")
    total = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total}/{total_tests} tests passed")
    if total == total_tests:
        print("\nAll tests passed! ✓")
        sys.exit(0)
    else:
        print(f"\n{total_tests - total} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
