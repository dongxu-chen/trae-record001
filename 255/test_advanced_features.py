import os
import sys
import numpy as np
from protein_predictor import (
    ProteinComplexPredictor,
    ProteinAnnotator,
    FoldSearcher,
    IntegratedProteinAnalyzer,
    predict_protein_structure,
    analyze_protein,
)

TEST_SEQUENCE = "MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE"
TEST_SEQUENCE_2 = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"


def test_multimer_prediction():
    print("\n" + "=" * 70)
    print("TEST 1: MULTIMER STRUCTURE PREDICTION")
    print("=" * 70)
    try:
        predictor = ProteinComplexPredictor()
        predictor.initialize()
        print("\n--- Testing Homomer (2 copies) ---")
        homomer_result = predictor.predict_homomer(TEST_SEQUENCE, num_copies=2)
        print(f"✓ Homomer predicted: {homomer_result.num_chains} chains")
        print(f"  Stoichiometry: {homomer_result.stoichiometry}")
        print(f"  Is homomeric: {homomer_result.is_homomeric}")
        print(f"  Assembly confidence: {homomer_result.assembly_confidence:.3f}")
        print(f"  Interfaces found: {len(homomer_result.interfaces)}")
        for iface in homomer_result.interfaces:
            print(f"    - Chain {iface.chain1}:{iface.chain2} | "
                  f"Interface residues: {iface.num_residues} | "
                  f"Area: {iface.interface_area:.1f} Å² | "
                  f"Confidence: {iface.confidence:.3f}")
        print("\n--- Testing Heteromer (2 different chains) ---")
        heteromer_result = predictor.predict_heteromer({
            "A": TEST_SEQUENCE,
            "B": TEST_SEQUENCE_2
        })
        print(f"✓ Heteromer predicted: {heteromer_result.num_chains} chains")
        print(f"  Stoichiometry: {heteromer_result.stoichiometry}")
        print(f"  Is homomeric: {heteromer_result.is_homomeric}")
        print(f"  Assembly confidence: {heteromer_result.assembly_confidence:.3f}")
        print(f"  Interfaces found: {len(heteromer_result.interfaces)}")
        for iface in heteromer_result.interfaces:
            print(f"    - Chain {iface.chain1}:{iface.chain2} | "
                  f"Interface residues: {iface.num_residues} | "
                  f"Area: {iface.interface_area:.1f} Å² | "
                  f"Confidence: {iface.confidence:.3f}")
        return True
    except Exception as e:
        print(f"✗ Multimer prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_functional_annotation():
    print("\n" + "=" * 70)
    print("TEST 2: FUNCTIONAL ANNOTATION")
    print("=" * 70)
    try:
        structure_result = predict_protein_structure(TEST_SEQUENCE)
        print(f"✓ Structure predicted, now annotating...")
        annotator = ProteinAnnotator()
        annotator.initialize()
        annotation = annotator.annotate(
            TEST_SEQUENCE,
            structure_result.pdb_content,
            structure_result.confidence_report.plddt_by_residue
        )
        report = annotator.get_report(annotation)
        print(report)
        return True
    except Exception as e:
        print(f"✗ Functional annotation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fold_search():
    print("\n" + "=" * 70)
    print("TEST 3: STRUCTURE FOLD SEARCH")
    print("=" * 70)
    try:
        structure_result = predict_protein_structure(TEST_SEQUENCE)
        print(f"✓ Structure predicted, now searching folds...")
        searcher = FoldSearcher()
        searcher.initialize()
        search_result = searcher.search(
            TEST_SEQUENCE,
            structure_result.pdb_content,
            top_k=5
        )
        report = searcher.get_report(search_result)
        print(report)
        return True
    except Exception as e:
        print(f"✗ Fold search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integrated_analysis():
    print("\n" + "=" * 70)
    print("TEST 4: INTEGRATED PROTEIN ANALYSIS")
    print("=" * 70)
    try:
        result = analyze_protein(TEST_SEQUENCE)
        print(f"\n✓ Analysis completed for job: {result['job_id']}")
        print(f"  Structure confidence: {result['structure'].confidence_report.overall_quality}")
        if result['annotation']:
            print(f"  Active sites found: {len(result['annotation'].active_sites)}")
            print(f"  Binding pockets found: {len(result['annotation'].binding_pockets)}")
        if result['fold_search']:
            print(f"  Fold search hits: {result['fold_search'].num_hits}")
            if result['fold_search'].fold_prediction:
                print(f"  Predicted fold: {result['fold_search'].fold_prediction}")
        return True
    except Exception as e:
        print(f"✗ Integrated analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "#" * 70)
    print("# ADVANCED PROTEIN STRUCTURE ANALYSIS - FEATURE TEST")
    print("#" * 70)
    results = {}
    results["Multimer Prediction"] = test_multimer_prediction()
    results["Functional Annotation"] = test_functional_annotation()
    results["Fold Search"] = test_fold_search()
    results["Integrated Analysis"] = test_integrated_analysis()
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    print("-" * 70)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
