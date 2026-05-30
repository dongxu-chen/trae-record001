import type { Annotation, AnnotationVersion, VersionDiff } from '../types';

const VERSIONS_STORAGE_KEY = 'annotation_versions';

function getStoredVersions(): Map<string, AnnotationVersion[]> {
  try {
    const stored = localStorage.getItem(VERSIONS_STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored) as Record<string, AnnotationVersion[]>;
      return new Map(Object.entries(data));
    }
  } catch (e) {
    console.error('Failed to load versions:', e);
  }
  return new Map();
}

function saveVersions(versions: Map<string, AnnotationVersion[]>) {
  try {
    const data = Object.fromEntries(versions);
    localStorage.setItem(VERSIONS_STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.error('Failed to save versions:', e);
  }
}

export function createVersion(
  projectId: string,
  annotations: Annotation[],
  name: string,
  description: string,
  createdBy: string
): AnnotationVersion {
  const versions = getStoredVersions();
  const projectVersions = versions.get(projectId) || [];

  const version: AnnotationVersion = {
    id: `v_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
    projectId,
    version: projectVersions.length + 1,
    name,
    description,
    annotations: JSON.parse(JSON.stringify(annotations)),
    createdBy,
    createdAt: new Date().toISOString(),
  };

  projectVersions.push(version);
  versions.set(projectId, projectVersions);
  saveVersions(versions);

  return version;
}

export function getProjectVersions(projectId: string): AnnotationVersion[] {
  const versions = getStoredVersions();
  return versions.get(projectId) || [];
}

export function getVersion(projectId: string, versionId: string): AnnotationVersion | null {
  const versions = getProjectVersions(projectId);
  return versions.find((v) => v.id === versionId) || null;
}

export function deleteVersion(projectId: string, versionId: string): boolean {
  const versions = getStoredVersions();
  const projectVersions = versions.get(projectId) || [];
  const filtered = projectVersions.filter((v) => v.id !== versionId);

  if (filtered.length === projectVersions.length) {
    return false;
  }

  versions.set(projectId, filtered);
  saveVersions(versions);
  return true;
}

export function compareVersions(
  versionA: AnnotationVersion,
  versionB: AnnotationVersion
): VersionDiff {
  const mapA = new Map(versionA.annotations.map((a) => [a.dataPointIndex, a]));
  const mapB = new Map(versionB.annotations.map((a) => [a.dataPointIndex, a]));

  const added: Annotation[] = [];
  const removed: Annotation[] = [];
  const modified: { old: Annotation; new: Annotation }[] = [];

  mapB.forEach((annotation, index) => {
    if (!mapA.has(index)) {
      added.push(annotation);
    } else {
      const oldAnnotation = mapA.get(index)!;
      if (
        oldAnnotation.type !== annotation.type ||
        oldAnnotation.label !== annotation.label ||
        oldAnnotation.description !== annotation.description
      ) {
        modified.push({ old: oldAnnotation, new: annotation });
      }
    }
  });

  mapA.forEach((annotation, index) => {
    if (!mapB.has(index)) {
      removed.push(annotation);
    }
  });

  return { added, removed, modified };
}

export function restoreVersion(
  projectId: string,
  versionId: string,
  currentAnnotations: Annotation[]
): Annotation[] {
  const version = getVersion(projectId, versionId);
  if (!version) return currentAnnotations;

  return JSON.parse(JSON.stringify(version.annotations));
}

export function getVersionStats(version: AnnotationVersion): {
  total: number;
  byType: Record<string, number>;
  uniqueLabels: string[];
  coverage: number;
} {
  const byType: Record<string, number> = {};
  const labels = new Set<string>();

  version.annotations.forEach((a) => {
    byType[a.type] = (byType[a.type] || 0) + 1;
    labels.add(a.label);
  });

  return {
    total: version.annotations.length,
    byType,
    uniqueLabels: Array.from(labels),
    coverage: 0,
  };
}

export function mergeVersions(
  baseVersion: AnnotationVersion,
  targetVersion: AnnotationVersion,
  strategy: 'keep-base' | 'keep-target' | 'merge' = 'merge'
): Annotation[] {
  const baseMap = new Map(baseVersion.annotations.map((a) => [a.dataPointIndex, a]));
  const targetMap = new Map(targetVersion.annotations.map((a) => [a.dataPointIndex, a]));
  const merged = new Map<number, Annotation>();

  const allIndices = new Set([...baseMap.keys(), ...targetMap.keys()]);

  allIndices.forEach((index) => {
    const baseAnn = baseMap.get(index);
    const targetAnn = targetMap.get(index);

    if (!baseAnn) {
      merged.set(index, targetAnn!);
    } else if (!targetAnn) {
      merged.set(index, baseAnn);
    } else {
      if (strategy === 'keep-base') {
        merged.set(index, baseAnn);
      } else if (strategy === 'keep-target') {
        merged.set(index, targetAnn);
      } else {
        const mergedAnnotation: Annotation = {
          ...baseAnn,
          label: mergeLabels(baseAnn.label, targetAnn.label),
          description: mergeDescriptions(baseAnn.description, targetAnn.description),
        };
        merged.set(index, mergedAnnotation);
      }
    }
  });

  return Array.from(merged.values());
}

function mergeLabels(label1: string, label2: string): string {
  const labels1 = label1.split(/[,，]/).map((l) => l.trim());
  const labels2 = label2.split(/[,，]/).map((l) => l.trim());
  const merged = [...new Set([...labels1, ...labels2])];
  return merged.join(', ');
}

function mergeDescriptions(desc1?: string, desc2?: string): string {
  const parts: string[] = [];
  if (desc1) parts.push(desc1);
  if (desc2 && desc2 !== desc1) parts.push(desc2);
  return parts.join(' | ');
}

export function formatVersionName(version: number): string {
  return `v${version}.0`;
}

export function getChangeSummary(diff: VersionDiff): {
  totalChanges: number;
  addedCount: number;
  removedCount: number;
  modifiedCount: number;
  summary: string;
} {
  const addedCount = diff.added.length;
  const removedCount = diff.removed.length;
  const modifiedCount = diff.modified.length;
  const totalChanges = addedCount + removedCount + modifiedCount;

  const parts: string[] = [];
  if (addedCount > 0) parts.push(`${addedCount} 新增`);
  if (removedCount > 0) parts.push(`${removedCount} 删除`);
  if (modifiedCount > 0) parts.push(`${modifiedCount} 修改`);

  return {
    totalChanges,
    addedCount,
    removedCount,
    modifiedCount,
    summary: parts.length > 0 ? parts.join('，') : '无变化',
  };
}
