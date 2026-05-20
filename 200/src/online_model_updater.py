import os
import json
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np
from pathlib import Path
import yaml
import cv2
from ultralytics import YOLO


@dataclass
class LabeledSample:
    id: str
    image_path: str
    label_path: str
    class_id: int
    class_name: str
    bbox: Dict[str, float]
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: float = 1.0
    is_verified: bool = False
    used_in_training: bool = False
    model_version: Optional[str] = None


@dataclass
class ModelVersion:
    version: str
    model_path: str
    timestamp: datetime
    num_samples_trained: int
    base_model_version: Optional[str]
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = 'active'
    description: str = ''


@dataclass
class TrainingConfig:
    img_sz: int = 640
    batch_size: int = 16
    epochs: int = 20
    lr0: float = 0.0001
    lrf: float = 0.01
    momentum: float = 0.937
    weight_decay: float = 0.0005
    warmup_epochs: int = 3
    warmup_momentum: float = 0.8
    warmup_bias_lr: float = 0.1
    freeze: int = 10
    optimizer: str = 'SGD'
    patience: int = 10
    cos_lr: bool = True
    overlap_mask: bool = True
    augment: bool = True
    mixup: float = 0.15
    copy_paste: float = 0.1
    fliplr: float = 0.5
    scale: float = 0.5


@dataclass
class UpdatePolicy:
    min_samples_for_update: int = 50
    max_samples_per_update: int = 500
    auto_update_enabled: bool = True
    scheduled_update_time: Optional[str] = None
    min_days_between_updates: int = 7
    min_improvement_threshold: float = 0.02
    max_model_versions: int = 10
    quality_threshold: float = 0.6
    class_balancing: bool = True
    hard_negative_mining: bool = True


class SampleBuffer:
    def __init__(self, buffer_dir: str = "data/sample_buffer",
                 max_samples: int = 5000):
        self.buffer_dir = buffer_dir
        self.max_samples = max_samples
        self.samples: List[LabeledSample] = []
        self.index_path = os.path.join(buffer_dir, 'sample_index.json')
        self._load()

    def _load(self):
        os.makedirs(self.buffer_dir, exist_ok=True)
        os.makedirs(os.path.join(self.buffer_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.buffer_dir, 'labels'), exist_ok=True)

        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for s in data:
                    s['timestamp'] = datetime.fromisoformat(s['timestamp'])
                    self.samples.append(LabeledSample(**s))
                print(f"Loaded {len(self.samples)} samples from buffer")
            except Exception as e:
                print(f"Warning: Failed to load sample buffer: {e}")
                self.samples = []

    def _save(self):
        data = []
        for s in self.samples:
            s_dict = asdict(s)
            s_dict['timestamp'] = s.timestamp.isoformat()
            data.append(s_dict)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_sample(self, image: np.ndarray, label_data: Dict[str, Any],
                   source: str = 'manual', quality_score: float = 1.0,
                   is_verified: bool = False) -> Optional[LabeledSample]:
        if len(self.samples) >= self.max_samples:
            self._remove_oldest_samples(100)

        sample_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        img_ext = '.jpg'
        img_path = os.path.join(self.buffer_dir, 'images', f'{sample_id}{img_ext}')
        lbl_path = os.path.join(self.buffer_dir, 'labels', f'{sample_id}.txt')

        cv2.imwrite(img_path, image)

        h, w = image.shape[:2]
        bbox = label_data['bbox']
        x_center = (bbox['x1'] + bbox['x2']) / (2 * w)
        y_center = (bbox['y1'] + bbox['y2']) / (2 * h)
        bw = (bbox['x2'] - bbox['x1']) / w
        bh = (bbox['y2'] - bbox['y1']) / h

        with open(lbl_path, 'w') as f:
            f.write(f"{label_data['class_id']} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n")

        sample = LabeledSample(
            id=sample_id,
            image_path=img_path,
            label_path=lbl_path,
            class_id=label_data['class_id'],
            class_name=label_data.get('class_name', str(label_data['class_id'])),
            bbox=bbox,
            source=source,
            quality_score=quality_score,
            is_verified=is_verified
        )

        self.samples.append(sample)
        self._save()

        print(f"Added sample {sample_id} to buffer (total: {len(self.samples)})")
        return sample

    def add_sample_from_detection(self, image: np.ndarray,
                                   detection: Dict[str, Any],
                                   is_correct: bool = True,
                                   corrected_class: Optional[int] = None) -> Optional[LabeledSample]:
        label_data = detection.copy()
        if not is_correct and corrected_class is not None:
            label_data['class_id'] = corrected_class

        quality = detection['confidence'] if is_correct else 0.5

        return self.add_sample(
            image=image,
            label_data=label_data,
            source='correction' if not is_correct else 'detection',
            quality_score=quality,
            is_verified=not is_correct
        )

    def _remove_oldest_samples(self, count: int):
        if len(self.samples) > count:
            samples_to_remove = self.samples[:count]
            for s in samples_to_remove:
                if os.path.exists(s.image_path):
                    os.remove(s.image_path)
                if os.path.exists(s.label_path):
                    os.remove(s.label_path)
            self.samples = self.samples[count:]
            self._save()
            print(f"Removed {count} oldest samples from buffer")

    def get_unused_samples(self, min_quality: float = 0.0,
                            max_samples: int = None) -> List[LabeledSample]:
        unused = [s for s in self.samples
                   if not s.used_in_training and s.quality_score >= min_quality]

        if max_samples and len(unused) > max_samples:
            unused = unused[-max_samples:]

        return sorted(unused, key=lambda s: s.timestamp)

    def get_samples_by_class(self, class_id: int) -> List[LabeledSample]:
        return [s for s in self.samples if s.class_id == class_id]

    def get_class_distribution(self) -> Dict[int, int]:
        counts = defaultdict(int)
        for s in self.samples:
            counts[s.class_id] += 1
        return dict(counts)

    def mark_samples_used(self, sample_ids: List[str]):
        for s in self.samples:
            if s.id in sample_ids:
                s.used_in_training = True
        self._save()

    def clear(self):
        for s in self.samples:
            if os.path.exists(s.image_path):
                os.remove(s.image_path)
            if os.path.exists(s.label_path):
                os.remove(s.label_path)
        self.samples = []
        self._save()

    def export_to_yolo_dataset(self, output_dir: str,
                                samples: List[LabeledSample] = None,
                                train_ratio: float = 0.8) -> str:
        if samples is None:
            samples = self.samples

        dataset_dir = output_dir
        os.makedirs(dataset_dir, exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, 'images', 'train'), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, 'images', 'val'), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, 'labels', 'train'), exist_ok=True)
        os.makedirs(os.path.join(dataset_dir, 'labels', 'val'), exist_ok=True)

        indices = np.random.permutation(len(samples))
        split_idx = int(len(samples) * train_ratio)
        train_indices = indices[:split_idx]
        val_indices = indices[split_idx:]

        class_names = {}
        for s in samples:
            class_names[s.class_id] = s.class_name

        yaml_content = {
            'path': os.path.abspath(dataset_dir),
            'train': 'images/train',
            'val': 'images/val',
            'names': dict(sorted(class_names.items()))
        }

        yaml_path = os.path.join(dataset_dir, 'data.yaml')
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)

        for idx_set, split in [(train_indices, 'train'), (val_indices, 'val')]:
            for idx in idx_set:
                s = samples[idx]
                img_dst = os.path.join(dataset_dir, 'images', split, f'{s.id}.jpg')
                lbl_dst = os.path.join(dataset_dir, 'labels', split, f'{s.id}.txt')
                shutil.copy2(s.image_path, img_dst)
                shutil.copy2(s.label_path, lbl_dst)

        print(f"Exported {len(samples)} samples to YOLO dataset: {dataset_dir}")
        print(f"  Train: {len(train_indices)}, Val: {len(val_indices)}")
        return yaml_path


class ModelVersionManager:
    def __init__(self, model_dir: str = "models/versions"):
        self.model_dir = model_dir
        self.versions: List[ModelVersion] = []
        self.index_path = os.path.join(model_dir, 'model_versions.json')
        self._load()

    def _load(self):
        os.makedirs(self.model_dir, exist_ok=True)

        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for v in data:
                    v['timestamp'] = datetime.fromisoformat(v['timestamp'])
                    self.versions.append(ModelVersion(**v))
                print(f"Loaded {len(self.versions)} model versions")
            except Exception as e:
                print(f"Warning: Failed to load model versions: {e}")
                self.versions = []

    def _save(self):
        data = []
        for v in self.versions:
            v_dict = asdict(v)
            v_dict['timestamp'] = v.timestamp.isoformat()
            data.append(v_dict)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_version_str(self) -> str:
        return f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def add_version(self, model_path: str, num_samples: int,
                     base_version: Optional[str] = None,
                     metrics: Dict[str, float] = None,
                     description: str = '') -> ModelVersion:
        version_str = self._generate_version_str()

        version_dir = os.path.join(self.model_dir, version_str)
        os.makedirs(version_dir, exist_ok=True)

        dst_model_path = os.path.join(version_dir, 'best.pt')
        if os.path.exists(model_path) and os.path.abspath(model_path) != os.path.abspath(dst_model_path):
            shutil.copy2(model_path, dst_model_path)

        version = ModelVersion(
            version=version_str,
            model_path=dst_model_path,
            timestamp=datetime.now(),
            num_samples_trained=num_samples,
            base_model_version=base_version,
            metrics=metrics or {},
            status='active',
            description=description
        )

        self.versions.append(version)
        self._enforce_version_limit()
        self._save()

        print(f"Added model version: {version_str}")
        return version

    def _enforce_version_limit(self, max_versions: int = 10):
        if len(self.versions) > max_versions:
            versions_to_archive = self.versions[:-max_versions]
            for v in versions_to_archive:
                v.status = 'archived'
            print(f"Archived {len(versions_to_archive)} old model versions")

    def get_latest_version(self) -> Optional[ModelVersion]:
        active = [v for v in self.versions if v.status == 'active']
        if active:
            return max(active, key=lambda v: v.timestamp)
        return None

    def get_version(self, version_str: str) -> Optional[ModelVersion]:
        for v in self.versions:
            if v.version == version_str:
                return v
        return None

    def rollback_to_version(self, version_str: str) -> Optional[ModelVersion]:
        target_version = self.get_version(version_str)
        if target_version:
            target_version.status = 'active'

            for v in self.versions:
                if v.timestamp > target_version.timestamp and v.status == 'active':
                    v.status = 'rolled_back'

            self._save()
            print(f"Rolled back to version: {version_str}")
            return target_version
        return None

    def get_version_history(self) -> List[Dict[str, Any]]:
        history = []
        for v in sorted(self.versions, key=lambda x: x.timestamp, reverse=True):
            history.append({
                'version': v.version,
                'timestamp': v.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'num_samples': v.num_samples_trained,
                'metrics': v.metrics,
                'status': v.status,
                'base_version': v.base_model_version,
                'description': v.description
            })
        return history

    def compare_versions(self, version1: str, version2: str) -> Dict[str, Any]:
        v1 = self.get_version(version1)
        v2 = self.get_version(version2)

        if not v1 or not v2:
            return {}

        comparison = {
            'version1': version1,
            'version2': version2,
            'metrics_v1': v1.metrics,
            'metrics_v2': v2.metrics,
            'improvement': {}
        }

        for metric in v1.metrics.keys() & v2.metrics.keys():
            diff = v2.metrics[metric] - v1.metrics[metric]
            pct = (diff / v1.metrics[metric] * 100) if v1.metrics[metric] != 0 else 0
            comparison['improvement'][metric] = {
                'absolute': diff,
                'percentage': pct
            }

        return comparison


class IncrementalTrainer:
    def __init__(self, base_model_path: str,
                 config: TrainingConfig = None,
                 device: str = '0'):
        self.base_model_path = base_model_path
        self.config = config or TrainingConfig()
        self.device = device
        self.training_callback: Optional[Callable[[str, float], None]] = None

    def set_training_callback(self, callback: Callable[[str, float], None]):
        self.training_callback = callback

    def train(self, dataset_yaml: str, output_dir: str,
              base_model_path: str = None,
              epochs: int = None) -> Tuple[str, Dict[str, float]]:
        if base_model_path is None:
            base_model_path = self.base_model_path

        if epochs is None:
            epochs = self.config.epochs

        print("\n" + "=" * 60)
        print("INCREMENTAL MODEL TRAINING")
        print("=" * 60)
        print(f"Base model: {base_model_path}")
        print(f"Dataset: {dataset_yaml}")
        print(f"Epochs: {epochs}")
        print(f"Image size: {self.config.img_sz}")
        print(f"Batch size: {self.config.batch_size}")
        print(f"Freeze layers: {self.config.freeze}")
        print("=" * 60 + "\n")

        model = YOLO(base_model_path)

        results = model.train(
            data=dataset_yaml,
            epochs=epochs,
            imgsz=self.config.img_sz,
            batch=self.config.batch_size,
            lr0=self.config.lr0,
            lrf=self.config.lrf,
            momentum=self.config.momentum,
            weight_decay=self.config.weight_decay,
            warmup_epochs=self.config.warmup_epochs,
            warmup_momentum=self.config.warmup_momentum,
            warmup_bias_lr=self.config.warmup_bias_lr,
            freeze=self.config.freeze,
            optimizer=self.config.optimizer,
            patience=self.config.patience,
            cos_lr=self.config.cos_lr,
            overlap_mask=self.config.overlap_mask,
            augment=self.config.augment,
            mixup=self.config.mixup,
            copy_paste=self.config.copy_paste,
            fliplr=self.config.fliplr,
            scale=self.config.scale,
            device=self.device,
            project=output_dir,
            name='incremental_training',
            exist_ok=True,
            verbose=True
        )

        metrics = {
            'map50': float(results.box.map50),
            'map50_95': float(results.box.map),
            'precision': float(results.box.mp),
            'recall': float(results.box.mr),
            'f1': float(2 * results.box.mp * results.box.mr / (results.box.mp + results.box.mr + 1e-10))
        }

        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)
        for k, v in metrics.items():
            print(f"  {k:15s}: {v:.4f}")
        print("=" * 60 + "\n")

        best_model_path = os.path.join(output_dir, 'incremental_training', 'weights', 'best.pt')
        return best_model_path, metrics

    def validate(self, model_path: str, dataset_yaml: str) -> Dict[str, float]:
        print(f"\nValidating model: {model_path}")

        model = YOLO(model_path)
        results = model.val(
            data=dataset_yaml,
            imgsz=self.config.img_sz,
            batch=self.config.batch_size,
            device=self.device,
            split='val',
            verbose=False
        )

        metrics = {
            'map50': float(results.box.map50),
            'map50_95': float(results.box.map),
            'precision': float(results.box.mp),
            'recall': float(results.box.mr),
            'f1': float(2 * results.box.mp * results.box.mr / (results.box.mp + results.box.mr + 1e-10))
        }

        print("Validation results:")
        for k, v in metrics.items():
            print(f"  {k:15s}: {v:.4f}")

        return metrics


class OnlineModelUpdater:
    def __init__(self,
                 base_model_path: str,
                 buffer_dir: str = "data/sample_buffer",
                 model_dir: str = "models/versions",
                 device: str = '0',
                 policy: UpdatePolicy = None):
        self.base_model_path = base_model_path
        self.device = device
        self.policy = policy or UpdatePolicy()

        self.sample_buffer = SampleBuffer(buffer_dir)
        self.version_manager = ModelVersionManager(model_dir)
        self.trainer = IncrementalTrainer(base_model_path, device=device)

        self.temp_dir = "data/temp_training"

    def add_manual_label(self, image: np.ndarray, bbox: Dict[str, float],
                         class_id: int, class_name: str = None) -> LabeledSample:
        label_data = {
            'class_id': class_id,
            'class_name': class_name or str(class_id),
            'bbox': bbox
        }
        return self.sample_buffer.add_sample(
            image=image,
            label_data=label_data,
            source='manual',
            quality_score=1.0,
            is_verified=True
        )

    def add_corrected_detection(self, image: np.ndarray, detection: Dict[str, Any],
                                 is_correct: bool = True,
                                 corrected_class: int = None) -> Optional[LabeledSample]:
        return self.sample_buffer.add_sample_from_detection(
            image=image,
            detection=detection,
            is_correct=is_correct,
            corrected_class=corrected_class
        )

    def _balance_classes(self, samples: List[LabeledSample]) -> List[LabeledSample]:
        if not self.policy.class_balancing:
            return samples

        class_samples = defaultdict(list)
        for s in samples:
            class_samples[s.class_id].append(s)

        if not class_samples:
            return samples

        max_count = max(len(v) for v in class_samples.values())
        target_count = min(max_count, self.policy.max_samples_per_update // len(class_samples))

        balanced = []
        for class_id, ss in class_samples.items():
            if len(ss) > target_count:
                indices = np.random.choice(len(ss), target_count, replace=False)
                balanced.extend([ss[i] for i in indices])
            else:
                balanced.extend(ss)

        print(f"Class balancing: {len(samples)} -> {len(balanced)} samples")
        return balanced

    def _select_hard_samples(self, samples: List[LabeledSample]) -> List[LabeledSample]:
        if not self.policy.hard_negative_mining:
            return samples

        sorted_samples = sorted(samples, key=lambda s: s.quality_score)
        hard_count = int(len(sorted_samples) * 0.3)

        hard = sorted_samples[:hard_count]
        normal = sorted_samples[hard_count:]

        selected = hard + normal[:len(normal) - hard_count // 2]

        print(f"Hard negative mining: {len(samples)} -> {len(selected)} samples")
        return selected

    def should_update(self) -> Tuple[bool, str]:
        if not self.policy.auto_update_enabled:
            return False, "Auto update disabled"

        unused = self.sample_buffer.get_unused_samples(
            min_quality=self.policy.quality_threshold
        )
        num_unused = len(unused)

        if num_unused < self.policy.min_samples_for_update:
            return False, f"Insufficient samples: {num_unused}/{self.policy.min_samples_for_update}"

        latest_version = self.version_manager.get_latest_version()
        if latest_version and self.policy.min_days_between_updates > 0:
            days_since_update = (datetime.now() - latest_version.timestamp).days
            if days_since_update < self.policy.min_days_between_updates:
                return False, f"Too soon since last update: {days_since_update}/{self.policy.min_days_between_updates} days"

        if self.policy.scheduled_update_time:
            current_time = datetime.now().strftime('%H:%M')
            if current_time < self.policy.scheduled_update_time:
                return False, f"Waiting for scheduled time: {self.policy.scheduled_update_time}"

        return True, f"Ready to update with {num_unused} samples"

    def check_and_update(self, force: bool = False) -> Optional[ModelVersion]:
        should_update, reason = self.should_update()

        if not should_update and not force:
            print(f"Update skipped: {reason}")
            return None

        if force:
            print("Forcing model update...")
        else:
            print(f"Starting model update: {reason}")

        return self.perform_update()

    def perform_update(self) -> Optional[ModelVersion]:
        print("\n" + "=" * 60)
        print("ONLINE MODEL UPDATE")
        print("=" * 60)

        unused = self.sample_buffer.get_unused_samples(
            min_quality=self.policy.quality_threshold
        )

        if len(unused) < self.policy.min_samples_for_update:
            print(f"Not enough samples for update: {len(unused)}")
            return None

        if len(unused) > self.policy.max_samples_per_update:
            unused = unused[-self.policy.max_samples_per_update:]

        print(f"Selected {len(unused)} samples for training")

        unused = self._balance_classes(unused)
        unused = self._select_hard_samples(unused)

        if len(unused) < 10:
            print("Not enough samples after filtering")
            return None

        latest_version = self.version_manager.get_latest_version()
        base_version = latest_version.version if latest_version else None
        base_model = latest_version.model_path if latest_version else self.base_model_path

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_dir = os.path.join(self.temp_dir, f'dataset_{timestamp}')

        try:
            yaml_path = self.sample_buffer.export_to_yolo_dataset(
                output_dir=dataset_dir,
                samples=unused,
                train_ratio=0.8
            )

            training_output_dir = os.path.join(self.temp_dir, f'training_{timestamp}')
            trained_model_path, metrics = self.trainer.train(
                dataset_yaml=yaml_path,
                output_dir=training_output_dir,
                base_model_path=base_model,
                epochs=self.config.epochs if hasattr(self, 'config') else 20
            )

            improvement = 0.0
            if latest_version and 'map50' in latest_version.metrics and 'map50' in metrics:
                improvement = metrics['map50'] - latest_version.metrics['map50']
                print(f"mAP@0.5 improvement: {improvement:+.4f}")

                if improvement < self.policy.min_improvement_threshold:
                    print(f"Improvement {improvement:.4f} below threshold {self.policy.min_improvement_threshold}")
                    print("New model rejected, keeping current version.")
                    self.sample_buffer.mark_samples_used([s.id for s in unused])
                    return None

            description = f"Incremental update with {len(unused)} samples. "
            if base_version:
                description += f"Based on {base_version}."

            new_version = self.version_manager.add_version(
                model_path=trained_model_path,
                num_samples=len(unused),
                base_version=base_version,
                metrics=metrics,
                description=description
            )

            self.sample_buffer.mark_samples_used([s.id for s in unused])

            print(f"\nModel update complete! New version: {new_version.version}")
            return new_version

        except Exception as e:
            print(f"Error during model update: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_update_status(self) -> Dict[str, Any]:
        should_update, reason = self.should_update()
        unused_samples = self.sample_buffer.get_unused_samples(
            min_quality=self.policy.quality_threshold
        )

        latest = self.version_manager.get_latest_version()
        days_since_update = None
        if latest:
            days_since_update = (datetime.now() - latest.timestamp).days

        return {
            'should_update': should_update,
            'update_reason': reason,
            'pending_samples': len(unused_samples),
            'min_samples_required': self.policy.min_samples_for_update,
            'latest_version': latest.version if latest else None,
            'latest_version_date': latest.timestamp.strftime('%Y-%m-%d %H:%M:%S') if latest else None,
            'days_since_last_update': days_since_update,
            'class_distribution': self.sample_buffer.get_class_distribution(),
            'auto_update_enabled': self.policy.auto_update_enabled,
            'total_samples': len(self.sample_buffer.samples)
        }

    def print_status(self):
        status = self.get_update_status()

        print("\n" + "=" * 60)
        print("ONLINE UPDATE STATUS")
        print("=" * 60)
        print(f"Should update: {'YES' if status['should_update'] else 'NO'}")
        print(f"Reason: {status['update_reason']}")
        print(f"Pending samples: {status['pending_samples']}/{status['min_samples_required']}")
        print(f"Total samples: {status['total_samples']}")
        print(f"Latest version: {status['latest_version']}")
        print(f"Last updated: {status['latest_version_date']}")
        print(f"Days since update: {status['days_since_last_update']}")
        print(f"Auto update: {'Enabled' if status['auto_update_enabled'] else 'Disabled'}")

        print("\nClass distribution:")
        for cls, count in sorted(status['class_distribution'].items()):
            print(f"  Class {cls}: {count} samples")
        print("=" * 60 + "\n")

    def rollback_model(self, version_str: str) -> Optional[ModelVersion]:
        return self.version_manager.rollback_to_version(version_str)

    def get_model_history(self) -> List[Dict[str, Any]]:
        return self.version_manager.get_version_history()
