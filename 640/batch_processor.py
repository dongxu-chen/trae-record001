import SimpleITK as sitk
import numpy as np
import os
import json
import glob
import logging
from typing import Dict, List, Optional, Tuple
from postprocessor import PostProcessor

logger = logging.getLogger(__name__)


class BatchProcessor:
    ORGAN_NAMES = {
        1: "Liver",
        2: "Right Kidney",
        3: "Left Kidney",
        4: "Spleen",
        5: "Pancreas",
        6: "Aorta",
        7: "Inferior Vena Cava",
        8: "Right Adrenal Gland",
        9: "Left Adrenal Gland",
        10: "Gallbladder",
        11: "Esophagus",
        12: "Stomach",
        13: "Duodenum",
        14: "Bladder",
        21: "Lung Left",
        22: "Lung Right",
        31: "Femur Left",
        32: "Femur Right",
        33: "Vertebra",
    }

    def __init__(self):
        self.processor = PostProcessor()
        self.organ_params: Dict[int, Dict] = {}
        self.default_params = self.processor.default_params.copy()

    def get_organ_name(self, label: int) -> str:
        return self.ORGAN_NAMES.get(label, f"Organ_{label}")

    def set_organ_params(self, label: int, params: Dict):
        self.organ_params[label] = params

    def set_global_params(self, params: Dict):
        self.default_params = params
        for label in self.organ_params:
            self.organ_params[label] = params.copy()

    def load_mask(self, filepath: str) -> Tuple[np.ndarray, Tuple[float, ...]]:
        sitk_img = sitk.ReadImage(filepath)
        arr = sitk.GetArrayFromImage(sitk_img)
        spacing = sitk_img.GetSpacing()[::-1]
        return arr, spacing

    def save_mask(
        self,
        arr: np.ndarray,
        reference_path: str,
        output_path: str,
        spacing: Optional[Tuple[float, ...]] = None,
    ):
        ref = sitk.ReadImage(reference_path)
        out_img = sitk.GetImageFromArray(arr)
        out_img.CopyInformation(ref)
        if spacing is not None:
            out_img.SetSpacing(spacing[::-1])
        sitk.WriteImage(out_img, output_path)
        logger.info(f"Saved: {output_path}")

    def process_single(
        self,
        input_path: str,
        output_path: str,
        params: Optional[Dict] = None,
    ) -> Dict:
        arr, spacing = self.load_mask(input_path)
        if params is None:
            params = self.default_params
        unique_labels = np.unique(arr)
        unique_labels = unique_labels[unique_labels != 0]
        if len(unique_labels) == 0:
            logger.warning(f"No labels found in {input_path}")
            self.save_mask(arr, input_path, output_path, spacing)
            return {"input": input_path, "output": output_path, "labels": []}
        if len(unique_labels) == 1 and unique_labels[0] == 1:
            result = self.processor.process_label(arr, params, spacing)
        else:
            per_label_params = {}
            for lbl in unique_labels:
                lbl_int = int(lbl)
                per_label_params[lbl_int] = self.organ_params.get(
                    lbl_int, params
                )
            result = self.processor.process_multi_label(arr, per_label_params, spacing)
        self.save_mask(result, input_path, output_path, spacing)
        stats = self._compute_stats(arr, result, unique_labels)
        return {"input": input_path, "output": output_path, "labels": stats}

    def process_batch(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.nii.gz",
        params: Optional[Dict] = None,
        callback=None,
    ) -> List[Dict]:
        os.makedirs(output_dir, exist_ok=True)
        files = sorted(glob.glob(os.path.join(input_dir, pattern)))
        if not files:
            alt_patterns = ["*.nii", "*.mha", "*.mhd", "*.nrrd"]
            for p in alt_patterns:
                files = sorted(glob.glob(os.path.join(input_dir, p)))
                if files:
                    break
        if not files:
            logger.error(f"No segmentation files found in {input_dir}")
            return []
        results = []
        for i, f in enumerate(files):
            basename = os.path.basename(f)
            out_path = os.path.join(output_dir, basename)
            try:
                result = self.process_single(f, out_path, params)
                results.append(result)
                if callback:
                    callback(i + 1, len(files), f, result)
            except Exception as e:
                logger.error(f"Error processing {f}: {e}")
                results.append({"input": f, "error": str(e)})
        return results

    def _compute_stats(
        self,
        original: np.ndarray,
        processed: np.ndarray,
        labels: np.ndarray,
    ) -> List[Dict]:
        stats = []
        voxel_vol = 1.0
        for lbl in labels:
            lbl_int = int(lbl)
            orig_vol = np.sum(original == lbl_int) * voxel_vol
            proc_vol = np.sum(processed == lbl_int) * voxel_vol
            diff = np.sum((original == lbl_int) != (processed == lbl_int))
            dice = self._compute_dice(original, processed, lbl_int)
            stats.append(
                {
                    "label": lbl_int,
                    "name": self.get_organ_name(lbl_int),
                    "original_volume": int(orig_vol),
                    "processed_volume": int(proc_vol),
                    "changed_voxels": int(diff),
                    "dice": round(dice, 4),
                }
            )
        return stats

    @staticmethod
    def _compute_dice(a: np.ndarray, b: np.ndarray, label: int) -> float:
        a_bin = (a == label).astype(np.float32)
        b_bin = (b == label).astype(np.float32)
        intersection = np.sum(a_bin * b_bin)
        total = np.sum(a_bin) + np.sum(b_bin)
        if total == 0:
            return 1.0
        return float(2.0 * intersection / total)

    def save_params(self, filepath: str):
        data = {
            "default_params": self.default_params,
            "organ_params": {str(k): v for k, v in self.organ_params.items()},
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_params(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.default_params = data.get("default_params", self.default_params)
        self.organ_params = {
            int(k): v for k, v in data.get("organ_params", {}).items()
        }
