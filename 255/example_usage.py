import os
import sys
from protein_predictor import ProteinStructurePredictor, predict_protein_structure


def example_simple_prediction():
    print("=" * 60)
    print("Example 1: Simple Protein Structure Prediction")
    print("=" * 60)
    sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
    print(f"\nInput sequence (length: {len(sequence)}):")
    print(sequence)
    print("\nPredicting structure...")
    result = predict_protein_structure(sequence)
    print("\n" + "=" * 60)
    print("Prediction Results:")
    print("=" * 60)
    print(f"Job ID: {result.job_id}")
    print(f"Sequence length: {result.sequence_length}")
    print(f"Total time: {result.total_time:.2f}s")
    print(f"Success: {result.success}")
    print("\nConfidence Metrics:")
    print(f"  Mean pLDDT: {result.confidence_report.mean_plddt:.2f}")
    print(f"  Median pLDDT: {result.confidence_report.median_plddt:.2f}")
    print(f"  Overall quality: {result.confidence_report.overall_quality}")
    print(f"  pTM score: {result.confidence_report.ptm_score:.4f}"
          if result.confidence_report.ptm_score else "  pTM score: N/A")
    print("\nPLDDT Distribution:")
    for key, value in result.confidence_report.plddt_distribution.items():
        print(f"  {key:12s}: {value * 100:6.2f}%")
    print("\nMSA Information:")
    print(f"  MSA depth: {result.msa_feature.depth} sequences")
    if result.msa_feature.conservation.size > 0:
        print(f"  Mean conservation: {result.msa_feature.conservation.mean():.4f}")
    if result.pdb_path:
        print(f"\nPDB file saved to: {result.pdb_path}")
    print(f"\nOutput directory: {result.output_dir}")
    return result


def example_batch_prediction():
    print("\n" + "=" * 60)
    print("Example 2: Batch Prediction")
    print("=" * 60)
    sequences = [
        "MKWVTFISLLFLFSSAYSRGVFRR",
        "MSIKKQEIIQGLKEIENELKNLV",
        "MKTVIIFSSSQVLLAQTVKSVPE",
    ]
    print(f"\nPredicting {len(sequences)} sequences...")
    predictor = ProteinStructurePredictor()
    predictor.initialize()
    results = predictor.batch_predict(sequences)
    print(f"\nCompleted {len(results)} predictions:")
    for i, result in enumerate(results):
        print(f"  Sequence {i + 1}: length={result.sequence_length}, "
              f"mean_pLDDT={result.confidence_report.mean_plddt:.2f}, "
              f"quality={result.confidence_report.overall_quality}")
    return results


def example_custom_config():
    print("\n" + "=" * 60)
    print("Example 3: Custom Configuration")
    print("=" * 60)
    from config import Config
    config = Config()
    config.model.use_gpu = True
    config.model.num_recycles = 2
    config.prediction.save_msa = True
    config.prediction.save_pdb = True
    print("\nCustom configuration:")
    print(f"  Use GPU: {config.model.use_gpu}")
    print(f"  Number of recycles: {config.model.num_recycles}")
    print(f"  Save MSA: {config.prediction.save_msa}")
    sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
    print(f"\nPredicting sequence of length {len(sequence)}...")
    predictor = ProteinStructurePredictor(config)
    predictor.initialize()
    result = predictor.predict(sequence, job_id="custom_job")
    print(f"\nPrediction complete! Mean pLDDT: {result.confidence_report.mean_plddt:.2f}")
    return result


def example_visualization():
    print("\n" + "=" * 60)
    print("Example 4: Structure Visualization")
    print("=" * 60)
    sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
    result = predict_protein_structure(sequence)
    print(f"\nStructure predicted. Output directory: {result.output_dir}")
    print("\nGenerated files:")
    if os.path.exists(result.output_dir):
        for f in sorted(os.listdir(result.output_dir)):
            fpath = os.path.join(result.output_dir, f)
            size = os.path.getsize(fpath)
            print(f"  {f:25s} ({size:,} bytes)")
    return result


def example_result_analysis():
    print("\n" + "=" * 60)
    print("Example 5: Result Analysis")
    print("=" * 60)
    from confidence_evaluator import interpret_plddt
    sequence = "MKWVTFISLLFLFSSAYSRGVFRRDAHMKSTIVFGRCIGISMRWPTVQGLD"
    result = predict_protein_structure(sequence)
    mean_plddt = result.confidence_report.mean_plddt
    interpretation = interpret_plddt(mean_plddt)
    print(f"\nMean pLDDT: {mean_plddt:.2f}")
    print(f"Quality: {interpretation['quality']}")
    print(f"Interpretation: {interpretation['description']}")
    print("\nQuality regions:")
    for region in result.confidence_report.quality_regions:
        print(f"  Residues {region['start']:4d}-{region['end']:4d}: "
              f"{region['quality']:12s} (mean pLDDT: {region['mean_plddt']:.2f})")
    plddt = result.confidence_report.plddt_by_residue
    high_confidence = (plddt > 70).sum()
    print(f"\nResidues with pLDDT > 70: {high_confidence}/{len(plddt)} "
          f"({high_confidence / len(plddt) * 100:.1f}%)")
    return result


if __name__ == "__main__":
    print("Protein Structure Prediction - Usage Examples")
    print("=" * 60)
    print("\nAvailable examples:")
    print("  1. Simple prediction")
    print("  2. Batch prediction")
    print("  3. Custom configuration")
    print("  4. Structure visualization outputs")
    print("  5. Result analysis")
    print("  0. Run all examples")
    print()
    try:
        choice = input("Select example to run (0-5): ").strip() or "1"
        if choice == "0":
            example_simple_prediction()
            example_batch_prediction()
            example_custom_config()
            example_visualization()
            example_result_analysis()
        elif choice == "1":
            example_simple_prediction()
        elif choice == "2":
            example_batch_prediction()
        elif choice == "3":
            example_custom_config()
        elif choice == "4":
            example_visualization()
        elif choice == "5":
            example_result_analysis()
        else:
            print("Invalid choice. Running example 1.")
            example_simple_prediction()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
