import os
import numpy as np
import torch
import torch.nn.functional as F
import json
from typing import List, Tuple, Dict, Optional
from tqdm import tqdm
import SimpleITK as sitk

from config import Config
from data_loader import get_file_paths, DICOMDataset
from augmentation import get_inference_transforms


def calculate_entropy(probabilities: np.ndarray, axis: int = 0) -> np.ndarray:
    probabilities = np.clip(probabilities, 1e-7, 1 - 1e-7)
    entropy = -np.sum(probabilities * np.log(probabilities), axis=axis)
    return entropy


def calculate_uncertainty(
    probabilities: torch.Tensor,
    uncertainty_type: str = "entropy",
) -> float:
    probs = probabilities.detach().cpu().numpy()
    probs = np.clip(probs, 1e-7, 1 - 1e-7)

    if uncertainty_type == "entropy":
        uncertainty = -np.sum(probs * np.log(probs), axis=1)
        return float(np.mean(uncertainty))

    elif uncertainty_type == "confidence":
        top_probs = np.sort(probs, axis=1)[:, ::-1][:, :2]
        confidence = top_probs[:, 0] - top_probs[:, 1]
        uncertainty = 1.0 - confidence
        return float(np.mean(uncertainty))

    elif uncertainty_type == "variance":
        mean_prob = np.mean(probs, axis=1, keepdims=True)
        variance = np.mean((probs - mean_prob) ** 2, axis=1)
        return float(np.mean(variance))

    elif uncertainty_type == "mutual_info":
        expected_entropy = np.mean(-np.sum(probs * np.log(probs), axis=1))
        mean_probs = np.mean(probs, axis=0, keepdims=True)
        mean_probs = np.clip(mean_probs, 1e-7, 1 - 1e-7)
        total_entropy = -np.sum(mean_probs * np.log(mean_probs))
        mutual_info = total_entropy - expected_entropy
        return float(mutual_info)

    else:
        raise ValueError(f"Unknown uncertainty type: {uncertainty_type}")


class QueryStrategy:
    def __init__(self, strategy: str = "uncertainty", uncertainty_type: str = "entropy"):
        self.strategy = strategy
        self.uncertainty_type = uncertainty_type

    def score_samples(
        self,
        model: torch.nn.Module,
        unlabeled_data: List[str],
        config: Config,
        device: torch.device,
    ) -> List[Tuple[str, float]]:
        if self.strategy == "uncertainty":
            return self._uncertainty_sampling(model, unlabeled_data, config, device)
        elif self.strategy == "random":
            return self._random_sampling(unlabeled_data)
        elif self.strategy == "diversity":
            return self._diversity_sampling(model, unlabeled_data, config, device)
        else:
            raise ValueError(f"Unknown query strategy: {self.strategy}")

    def _random_sampling(
        self,
        unlabeled_data: List[str],
    ) -> List[Tuple[str, float]]:
        indices = np.random.permutation(len(unlabeled_data))
        scores = [(unlabeled_data[i], float(np.random.rand())) for i in indices]
        return sorted(scores, key=lambda x: x[1], reverse=True)

    def _uncertainty_sampling(
        self,
        model: torch.nn.Module,
        unlabeled_data: List[str],
        config: Config,
        device: torch.device,
    ) -> List[Tuple[str, float]]:
        model.eval()
        transform = get_inference_transforms(config)
        scores = []

        with torch.no_grad():
            for image_path in tqdm(unlabeled_data, desc="Calculating uncertainty"):
                try:
                    data = transform({"image": image_path})
                    image_tensor = data["image"].unsqueeze(0).to(device)

                    outputs = model(image_tensor)
                    probabilities = F.softmax(outputs, dim=1)

                    uncertainty = calculate_uncertainty(
                        probabilities,
                        self.uncertainty_type,
                    )

                    scores.append((image_path, uncertainty))
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    scores.append((image_path, 0.0))

        return sorted(scores, key=lambda x: x[1], reverse=True)

    def _diversity_sampling(
        self,
        model: torch.nn.Module,
        unlabeled_data: List[str],
        config: Config,
        device: torch.device,
    ) -> List[Tuple[str, float]]:
        model.eval()
        transform = get_inference_transforms(config)

        features = []
        valid_paths = []

        with torch.no_grad():
            for image_path in tqdm(unlabeled_data, desc="Extracting features"):
                try:
                    data = transform({"image": image_path})
                    image_tensor = data["image"].unsqueeze(0).to(device)

                    outputs = model(image_tensor)
                    feat = outputs.view(outputs.shape[0], -1).mean(dim=0).cpu().numpy()
                    features.append(feat)
                    valid_paths.append(image_path)
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")

        if len(features) == 0:
            return [(path, 0.0) for path in unlabeled_data]

        features = np.array(features)
        features = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-7)

        similarity_matrix = features @ features.T
        np.fill_diagonal(similarity_matrix, -np.inf)

        diversity_scores = -np.max(similarity_matrix, axis=1)

        scores = list(zip(valid_paths, diversity_scores))
        return sorted(scores, key=lambda x: x[1], reverse=True)


class ActiveLearningLoop:
    def __init__(
        self,
        config: Config,
        all_image_paths: List[str],
        all_label_paths: Optional[List[str]] = None,
    ):
        self.config = config
        self.all_image_paths = all_image_paths
        self.all_label_paths = all_label_paths or []

        self.iteration = 0
        self.labeled_indices: List[int] = []
        self.unlabeled_indices: List[int] = list(range(len(all_image_paths)))

        self.history = []

    def initialize_labeled_set(self, num_initial: Optional[int] = None) -> Tuple[List[str], List[str]]:
        if num_initial is None:
            num_initial = int(len(self.all_image_paths) * self.config.al_initial_labeled_ratio)

        num_initial = max(1, min(num_initial, len(self.unlabeled_indices)))

        np.random.seed(self.config.random_seed)
        selected = np.random.choice(
            self.unlabeled_indices,
            size=num_initial,
            replace=False,
        )

        for idx in selected:
            self.labeled_indices.append(idx)
            self.unlabeled_indices.remove(idx)

        labeled_images = [self.all_image_paths[i] for i in self.labeled_indices]
        labeled_labels = [self.all_label_paths[i] for i in self.labeled_indices] if self.all_label_paths else []

        print(f"Initial labeled set: {len(labeled_images)} samples")
        return labeled_images, labeled_labels

    def select_samples_for_labeling(
        self,
        model: torch.nn.Module,
        device: torch.device,
        num_samples: Optional[int] = None,
    ) -> List[str]:
        if num_samples is None:
            num_samples = self.config.al_num_queries_per_iter

        if len(self.unlabeled_indices) == 0:
            return []

        num_samples = min(num_samples, len(self.unlabeled_indices))

        unlabeled_images = [self.all_image_paths[i] for i in self.unlabeled_indices]

        query_strategy = QueryStrategy(
            strategy=self.config.al_query_strategy,
            uncertainty_type=self.config.al_uncertainty_type,
        )

        scored_samples = query_strategy.score_samples(
            model, unlabeled_images, self.config, device
        )

        selected_paths = [path for path, score in scored_samples[:num_samples]]
        selected_indices = [
            self.unlabeled_indices[unlabeled_images.index(path)]
            for path in selected_paths
        ]

        return selected_paths

    def add_labeled_samples(self, image_paths: List[str]) -> List[int]:
        newly_labeled_indices = []

        for path in image_paths:
            if path in self.all_image_paths:
                idx = self.all_image_paths.index(path)
                if idx in self.unlabeled_indices:
                    self.unlabeled_indices.remove(idx)
                    self.labeled_indices.append(idx)
                    newly_labeled_indices.append(idx)

        return newly_labeled_indices

    def get_labeled_data(self) -> Tuple[List[str], List[str]]:
        labeled_images = [self.all_image_paths[i] for i in self.labeled_indices]
        labeled_labels = [self.all_label_paths[i] for i in self.labeled_indices] if self.all_label_paths else []
        return labeled_images, labeled_labels

    def get_unlabeled_data(self) -> List[str]:
        return [self.all_image_paths[i] for i in self.unlabeled_indices]

    def save_state(self, save_dir: str) -> None:
        os.makedirs(save_dir, exist_ok=True)
        state = {
            "iteration": self.iteration,
            "labeled_indices": self.labeled_indices,
            "unlabeled_indices": self.unlabeled_indices,
            "history": self.history,
        }
        with open(os.path.join(save_dir, f"al_state_iter_{self.iteration}.json"), "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self, load_path: str) -> None:
        with open(load_path, "r") as f:
            state = json.load(f)
        self.iteration = state["iteration"]
        self.labeled_indices = state["labeled_indices"]
        self.unlabeled_indices = state["unlabeled_indices"]
        self.history = state["history"]

    def record_iteration(
        self,
        metrics: Dict[str, float],
        num_newly_labeled: int,
    ) -> None:
        record = {
            "iteration": self.iteration,
            "num_labeled": len(self.labeled_indices),
            "num_newly_labeled": num_newly_labeled,
            "num_unlabeled": len(self.unlabeled_indices),
            "metrics": metrics,
        }
        self.history.append(record)
        self.iteration += 1

    def get_statistics(self) -> Dict[str, int]:
        return {
            "total_samples": len(self.all_image_paths),
            "labeled_samples": len(self.labeled_indices),
            "unlabeled_samples": len(self.unlabeled_indices),
            "current_iteration": self.iteration,
        }
