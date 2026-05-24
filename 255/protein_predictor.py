import os
import uuid
import time
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union
import numpy as np
from config import Config
from msa_features import MSAGenerator, MSAFeature, MSAOutput, extract_msa_features
from structure_predictor import StructurePredictor, StructurePrediction
from confidence_evaluator import ConfidenceEvaluator, ConfidenceReport


@dataclass
class PredictionResult:
    job_id: str
    sequence: str
    sequence_length: int
    pdb_content: str
    pdb_path: Optional[str]
    msa_feature: MSAFeature
    structure_prediction: StructurePrediction
    confidence_report: ConfidenceReport
    output_dir: str
    total_time: float
    error_message: Optional[str] = None
    success: bool = True


@dataclass
class JobStatus:
    job_id: str
    status: str
    progress: float
    message: str
    start_time: float
    end_time: Optional[float] = None


class ProteinStructurePredictor:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.msa_generator = MSAGenerator(self.config)
        self.structure_predictor = StructurePredictor(self.config)
        self.confidence_evaluator = ConfidenceEvaluator(self.config)
        self._jobs: Dict[str, JobStatus] = {}
        self._initialized = False

    def initialize(self) -> bool:
        if self._initialized:
            return True
        print("Initializing Protein Structure Predictor...")
        model_loaded = self.structure_predictor.load_model()
        if not model_loaded:
            print("Warning: Model loading failed, using fallback mode")
        self._initialized = True
        print(f"Predictor initialized. GPU available: {self.structure_predictor.device.type == 'cuda'}")
        return True

    def predict(self, sequence: str, job_id: Optional[str] = None,
               save_outputs: bool = True) -> PredictionResult:
        sequence = sequence.upper().strip()
        job_id = job_id or str(uuid.uuid4())[:8]
        start_time = time.time()
        self._jobs[job_id] = JobStatus(
            job_id=job_id, status="starting", progress=0.0,
            message="Starting prediction...", start_time=start_time,
        )
        try:
            self._update_job(job_id, "msa", 0.1, "Generating MSA features...")
            msa_output = self.msa_generator.generate(sequence, job_id)
            self._update_job(job_id, "predicting", 0.4, "Predicting structure...")
            structure_pred = self.structure_predictor.predict(
                sequence, msa_output.feature,
            )
            self._update_job(job_id, "evaluating", 0.8, "Evaluating confidence...")
            confidence_report = self.confidence_evaluator.evaluate(
                structure_pred.plddt, structure_pred.pae,
                structure_pred.ptm, structure_pred.iptm, sequence,
            )
            output_dir = os.path.join(self.config.prediction.output_dir, job_id)
            os.makedirs(output_dir, exist_ok=True)
            pdb_path = None
            if save_outputs and self.config.prediction.save_pdb:
                pdb_path = os.path.join(output_dir, "prediction.pdb")
                with open(pdb_path, "w") as f:
                    f.write(structure_pred.pdb_content)
                self._save_outputs(job_id, output_dir, sequence, msa_output,
                                  structure_pred, confidence_report)
            total_time = time.time() - start_time
            self._update_job(job_id, "completed", 1.0, "Prediction completed", total_time)
            return PredictionResult(
                job_id=job_id,
                sequence=sequence,
                sequence_length=len(sequence),
                pdb_content=structure_pred.pdb_content,
                pdb_path=pdb_path,
                msa_feature=msa_output.feature,
                structure_prediction=structure_pred,
                confidence_report=confidence_report,
                output_dir=output_dir,
                total_time=total_time,
                success=True,
            )
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Prediction failed: {str(e)}"
            self._update_job(job_id, "failed", 0.0, error_msg, total_time)
            raise RuntimeError(error_msg) from e

    def _save_outputs(self, job_id: str, output_dir: str, sequence: str,
                     msa_output: MSAOutput, structure_pred: StructurePrediction,
                     confidence_report: ConfidenceReport) -> None:
        plddt_plot_path = os.path.join(output_dir, "plddt_plot.png")
        self.confidence_evaluator.plot_plddt(confidence_report, plddt_plot_path, sequence)
        if structure_pred.pae is not None:
            pae_plot_path = os.path.join(output_dir, "pae_plot.png")
            self.confidence_evaluator.plot_pae(structure_pred.pae, pae_plot_path)
        report_path = os.path.join(output_dir, "confidence_report.txt")
        self.confidence_evaluator.generate_report(confidence_report, report_path)
        if self.config.prediction.save_msa and msa_output.a3m_path:
            import shutil
            msa_save_path = os.path.join(output_dir, "msa.a3m")
            if os.path.exists(msa_output.a3m_path):
                shutil.copy2(msa_output.a3m_path, msa_save_path)
        metadata = {
            "job_id": job_id,
            "sequence": sequence,
            "sequence_length": len(sequence),
            "model_name": structure_pred.model_name,
            "inference_time": float(structure_pred.inference_time),
            "num_recycles": int(structure_pred.num_recycles),
            "mean_plddt": float(confidence_report.mean_plddt),
            "overall_quality": confidence_report.overall_quality,
            "msa_depth": int(msa_output.feature.depth),
            "ptm_score": float(structure_pred.ptm) if structure_pred.ptm is not None else None,
            "iptm_score": float(structure_pred.iptm) if structure_pred.iptm is not None else None,
        }
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _update_job(self, job_id: str, status: str, progress: float,
                   message: str, total_time: Optional[float] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            self._jobs[job_id].progress = progress
            self._jobs[job_id].message = message
            if total_time is not None:
                self._jobs[job_id].end_time = self._jobs[job_id].start_time + total_time

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        return self._jobs.get(job_id)

    def predict_from_fasta(self, fasta_path: str, job_id: Optional[str] = None) -> PredictionResult:
        from msa_features import read_fasta
        sequence, _ = read_fasta(fasta_path)
        return self.predict(sequence, job_id)

    def batch_predict(self, sequences: List[str]) -> List[PredictionResult]:
        results = []
        for i, seq in enumerate(sequences):
            job_id = f"batch_{i}_{str(uuid.uuid4())[:4]}"
            try:
                result = self.predict(seq, job_id)
                results.append(result)
            except Exception as e:
                print(f"Batch prediction failed for sequence {i}: {e}")
        return results


class ProteinPredictorAPI:
    def __init__(self, config: Optional[Config] = None):
        self.predictor = ProteinStructurePredictor(config)
        self.predictor.initialize()

    def predict_structure(self, sequence: str) -> Dict[str, Any]:
        result = self.predictor.predict(sequence)
        return self._result_to_dict(result)

    def predict_from_file(self, file_path: str, file_type: str = "fasta") -> Dict[str, Any]:
        if file_type == "fasta":
            result = self.predictor.predict_from_fasta(file_path)
            return self._result_to_dict(result)
        elif file_type == "txt":
            with open(file_path) as f:
                sequence = f.read().strip()
            return self.predict_structure(sequence)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def get_confidence_report(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_status = self.predictor.get_job_status(job_id)
        if not job_status or job_status.status != "completed":
            return None
        output_dir = os.path.join(self.predictor.config.prediction.output_dir, job_id)
        metadata_path = os.path.join(output_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                return json.load(f)
        return None

    def _result_to_dict(self, result: PredictionResult) -> Dict[str, Any]:
        return {
            "job_id": result.job_id,
            "sequence": result.sequence,
            "sequence_length": result.sequence_length,
            "pdb_content": result.pdb_content,
            "pdb_path": result.pdb_path,
            "output_dir": result.output_dir,
            "total_time": result.total_time,
            "success": result.success,
            "confidence": {
                "mean_plddt": result.confidence_report.mean_plddt,
                "median_plddt": result.confidence_report.median_plddt,
                "overall_quality": result.confidence_report.overall_quality,
                "distribution": result.confidence_report.plddt_distribution,
                "ptm_score": result.confidence_report.ptm_score,
                "iptm_score": result.confidence_report.iptm_score,
            },
            "msa_info": {
                "depth": result.msa_feature.depth,
                "mean_conservation": float(np.mean(result.msa_feature.conservation))
                if result.msa_feature.conservation.size > 0 else 0.0,
            },
        }


class ProteinComplexPredictor:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.multimer_predictor = None

    def initialize(self) -> bool:
        try:
            from multimer_prediction import MultimerPredictor
            self.multimer_predictor = MultimerPredictor(self.config)
            return True
        except Exception as e:
            print(f"Failed to initialize complex predictor: {e}")
            return False

    def predict_homomer(self, sequence: str, num_copies: int = 2) -> Any:
        if not self.multimer_predictor:
            self.initialize()
        return self.multimer_predictor.predict_homomer(sequence, num_copies)

    def predict_heteromer(self, sequences: Dict[str, str]) -> Any:
        if not self.multimer_predictor:
            self.initialize()
        return self.multimer_predictor.predict_heteromer(sequences)

    def predict_complex(self, sequences: Union[str, List[str], Dict[str, str]]) -> Any:
        if not self.multimer_predictor:
            self.initialize()
        return self.multimer_predictor.predict_multimer(sequences)


class ProteinAnnotator:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.annotator = None

    def initialize(self) -> bool:
        try:
            from functional_annotation import FunctionalAnnotator
            self.annotator = FunctionalAnnotator(self.config)
            return True
        except Exception as e:
            print(f"Failed to initialize annotator: {e}")
            return False

    def annotate(self, sequence: str, pdb_content: str,
                 plddt: Optional[np.ndarray] = None) -> Any:
        if not self.annotator:
            self.initialize()
        return self.annotator.annotate(sequence, pdb_content, plddt)

    def get_report(self, annotation: Any) -> str:
        if not self.annotator:
            self.initialize()
        return self.annotator.format_report(annotation)


class FoldSearcher:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.aligner = None

    def initialize(self) -> bool:
        try:
            from structure_alignment import StructureAligner
            self.aligner = StructureAligner(self.config)
            return True
        except Exception as e:
            print(f"Failed to initialize fold searcher: {e}")
            return False

    def search(self, sequence: str, pdb_content: str, top_k: int = 5) -> Any:
        if not self.aligner:
            self.initialize()
        return self.aligner.search_fold(sequence, pdb_content, top_k)

    def get_report(self, search_result: Any) -> str:
        if not self.aligner:
            self.initialize()
        return self.aligner.format_search_report(search_result)


class IntegratedProteinAnalyzer:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.structure_predictor = ProteinStructurePredictor(self.config)
        self.complex_predictor = ProteinComplexPredictor(self.config)
        self.annotator = ProteinAnnotator(self.config)
        self.fold_searcher = FoldSearcher(self.config)
        self._initialized = False

    def initialize(self) -> bool:
        self.structure_predictor.initialize()
        self.complex_predictor.initialize()
        self.annotator.initialize()
        self.fold_searcher.initialize()
        self._initialized = True
        return True

    def full_analysis(self, sequence: str, job_id: Optional[str] = None,
                     do_annotation: bool = True,
                     do_fold_search: bool = True) -> Dict[str, Any]:
        if not self._initialized:
            self.initialize()
        job_id = job_id or str(uuid.uuid4())[:8]
        print(f"\n[Step 1/3] Predicting structure for sequence (length={len(sequence)})...")
        structure_result = self.structure_predictor.predict(sequence, job_id)
        result = {
            "job_id": job_id,
            "structure": structure_result,
            "annotation": None,
            "fold_search": None,
        }
        if do_annotation:
            print(f"\n[Step 2/3] Annotating function and active sites...")
            try:
                annotation = self.annotator.annotate(
                    sequence,
                    structure_result.pdb_content,
                    structure_result.confidence_report.plddt_by_residue
                )
                result["annotation"] = annotation
            except Exception as e:
                print(f"Annotation skipped: {e}")
        if do_fold_search:
            print(f"\n[Step 3/3] Searching for similar folds...")
            try:
                fold_result = self.fold_searcher.search(
                    sequence,
                    structure_result.pdb_content,
                    top_k=5
                )
                result["fold_search"] = fold_result
            except Exception as e:
                print(f"Fold search skipped: {e}")
        print(f"\n✓ Full analysis completed!")
        return result

    def analyze_complex(self, sequences: Dict[str, str],
                       job_id: Optional[str] = None) -> Dict[str, Any]:
        if not self._initialized:
            self.initialize()
        job_id = job_id or f"complex_{str(uuid.uuid4())[:4]}"
        print(f"\n[Step 1/2] Predicting complex structure ({len(sequences)} chains)...")
        complex_result = self.complex_predictor.predict_heteromer(sequences)
        result = {
            "job_id": job_id,
            "complex": complex_result,
            "chain_annotations": {},
        }
        print(f"\n[Step 2/2] Annotating individual chains...")
        for chain_id, seq in sequences.items():
            try:
                chain_pdb = self.structure_predictor.predict(seq, f"{job_id}_{chain_id}")
                annotation = self.annotator.annotate(seq, chain_pdb.pdb_content,
                                                    chain_pdb.confidence_report.plddt_by_residue)
                result["chain_annotations"][chain_id] = annotation
            except Exception as e:
                print(f"  Chain {chain_id} annotation skipped: {e}")
        print(f"\n✓ Complex analysis completed!")
        return result


def create_predictor(config: Optional[Config] = None) -> ProteinStructurePredictor:
    predictor = ProteinStructurePredictor(config)
    predictor.initialize()
    return predictor


def predict_protein_structure(sequence: str, config: Optional[Config] = None) -> PredictionResult:
    predictor = create_predictor(config)
    return predictor.predict(sequence)


def analyze_protein(sequence: str, config: Optional[Config] = None,
                   do_annotation: bool = True,
                   do_fold_search: bool = True) -> Dict[str, Any]:
    analyzer = IntegratedProteinAnalyzer(config)
    analyzer.initialize()
    return analyzer.full_analysis(sequence, do_annotation=do_annotation,
                                do_fold_search=do_fold_search)
