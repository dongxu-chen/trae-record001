import json
import os
import uuid
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
import copy


@dataclass
class AnnotationVersion:
    version_id: str
    image_id: str
    annotations: list
    created_at: int
    description: str
    author: str = "system"
    metadata: dict = field(default_factory=dict)


@dataclass
class VersionDiff:
    added: list
    removed: list
    modified: list
    unchanged: int


class VersionService:
    _instance = None

    def __init__(self, versions_dir: str = "versions"):
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(exist_ok=True)
        
        self._versions: Dict[str, List[AnnotationVersion]] = {}
        self._current_version: Dict[str, str] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def save_version(
        self,
        image_id: str,
        annotations: list,
        description: str = "",
        author: str = "system"
    ) -> AnnotationVersion:
        version_id = str(uuid.uuid4())
        created_at = int(datetime.now().timestamp() * 1000)
        
        annotations_copy = copy.deepcopy(annotations)
        
        version = AnnotationVersion(
            version_id=version_id,
            image_id=image_id,
            annotations=annotations_copy,
            created_at=created_at,
            description=description,
            author=author,
            metadata={
                'annotation_count': len(annotations_copy),
                'labels': list(set(
                    ann.get('label', 'unlabeled') 
                    for ann in annotations_copy
                ))
            }
        )
        
        if image_id not in self._versions:
            self._versions[image_id] = []
        
        self._versions[image_id].append(version)
        self._current_version[image_id] = version_id
        
        self._save_version_to_disk(version)
        
        return version

    def get_versions(self, image_id: str) -> List[AnnotationVersion]:
        if image_id not in self._versions:
            self._load_versions_from_disk(image_id)
        
        return sorted(
            self._versions.get(image_id, []),
            key=lambda v: v.created_at,
            reverse=True
        )

    def get_version(self, image_id: str, version_id: str) -> Optional[AnnotationVersion]:
        versions = self.get_versions(image_id)
        for version in versions:
            if version.version_id == version_id:
                return version
        return None

    def get_current_version(self, image_id: str) -> Optional[AnnotationVersion]:
        if image_id not in self._current_version:
            versions = self.get_versions(image_id)
            if versions:
                self._current_version[image_id] = versions[0].version_id
        
        current_id = self._current_version.get(image_id)
        if current_id:
            return self.get_version(image_id, current_id)
        return None

    def rollback_to_version(
        self,
        image_id: str,
        version_id: str
    ) -> Optional[list]:
        version = self.get_version(image_id, version_id)
        if version:
            self._current_version[image_id] = version_id
            return copy.deepcopy(version.annotations)
        return None

    def compare_versions(
        self,
        image_id: str,
        version_id_1: str,
        version_id_2: str
    ) -> Optional[VersionDiff]:
        v1 = self.get_version(image_id, version_id_1)
        v2 = self.get_version(image_id, version_id_2)
        
        if not v1 or not v2:
            return None
        
        return self._calculate_diff(v1.annotations, v2.annotations)

    def compare_with_current(
        self,
        image_id: str,
        current_annotations: list
    ) -> Optional[VersionDiff]:
        current_version = self.get_current_version(image_id)
        if not current_version:
            return VersionDiff(
                added=current_annotations,
                removed=[],
                modified=[],
                unchanged=0
            )
        
        return self._calculate_diff(
            current_version.annotations,
            current_annotations
        )

    def delete_version(self, image_id: str, version_id: str) -> bool:
        versions = self._versions.get(image_id, [])
        for i, version in enumerate(versions):
            if version.version_id == version_id:
                versions.pop(i)
                
                version_file = self.versions_dir / image_id / f"{version_id}.json"
                if version_file.exists():
                    os.remove(version_file)
                
                if self._current_version.get(image_id) == version_id:
                    if versions:
                        self._current_version[image_id] = versions[-1].version_id
                    else:
                        del self._current_version[image_id]
                
                return True
        return False

    def _calculate_diff(
        self,
        annotations_1: list,
        annotations_2: list
    ) -> VersionDiff:
        ann_by_id_1 = {ann.get('id', str(i)): ann for i, ann in enumerate(annotations_1)}
        ann_by_id_2 = {ann.get('id', str(i)): ann for i, ann in enumerate(annotations_2)}
        
        ids_1 = set(ann_by_id_1.keys())
        ids_2 = set(ann_by_id_2.keys())
        
        added_ids = ids_2 - ids_1
        removed_ids = ids_1 - ids_2
        common_ids = ids_1 & ids_2
        
        added = [ann_by_id_2[id] for id in added_ids]
        removed = [ann_by_id_1[id] for id in removed_ids]
        
        modified = []
        unchanged = 0
        for id in common_ids:
            ann1 = ann_by_id_1[id]
            ann2 = ann_by_id_2[id]
            if ann1 != ann2:
                modified.append({
                    'id': id,
                    'old': ann1,
                    'new': ann2
                })
            else:
                unchanged += 1
        
        return VersionDiff(
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged
        )

    def _save_version_to_disk(self, version: AnnotationVersion):
        image_dir = self.versions_dir / version.image_id
        image_dir.mkdir(exist_ok=True)
        
        version_data = {
            'version_id': version.version_id,
            'image_id': version.image_id,
            'annotations': version.annotations,
            'created_at': version.created_at,
            'description': version.description,
            'author': version.author,
            'metadata': version.metadata
        }
        
        version_file = image_dir / f"{version.version_id}.json"
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)

    def _load_versions_from_disk(self, image_id: str):
        image_dir = self.versions_dir / image_id
        if not image_dir.exists():
            return
        
        self._versions[image_id] = []
        
        for version_file in image_dir.glob("*.json"):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                version = AnnotationVersion(
                    version_id=data['version_id'],
                    image_id=data['image_id'],
                    annotations=data['annotations'],
                    created_at=data['created_at'],
                    description=data.get('description', ''),
                    author=data.get('author', 'system'),
                    metadata=data.get('metadata', {})
                )
                
                self._versions[image_id].append(version)
            except Exception as e:
                print(f"Error loading version {version_file}: {e}")


version_service = VersionService.get_instance()
