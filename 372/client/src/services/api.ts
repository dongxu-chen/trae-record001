import type { ImageInfo, Annotation, VideoInfo, VideoFrameInfo, QualityReport, AnnotationVersion, VersionDiff } from '@/types/annotation';

const API_BASE = '/api';

export type ExportFormat = 'json' | 'mask' | 'yolo' | 'labelme' | 'voc' | 'coco';

export interface ExportFormatInfo {
  id: ExportFormat;
  name: string;
  description: string;
  extension: string;
}

export async function uploadImage(file: File): Promise<ImageInfo> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/images`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload image');
  }

  return response.json();
}

export async function getImages(): Promise<ImageInfo[]> {
  const response = await fetch(`${API_BASE}/images`);
  if (!response.ok) {
    throw new Error('Failed to fetch images');
  }
  return response.json();
}

export async function getImageData(id: string): Promise<string> {
  const response = await fetch(`${API_BASE}/images/${id}/data`);
  if (!response.ok) {
    throw new Error('Failed to fetch image data');
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function deleteImage(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/images/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete image');
  }
}

export async function uploadVideo(file: File): Promise<VideoInfo> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/videos`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload video');
  }

  return response.json();
}

export async function getVideos(): Promise<VideoInfo[]> {
  const response = await fetch(`${API_BASE}/videos`);
  if (!response.ok) {
    throw new Error('Failed to fetch videos');
  }
  return response.json();
}

export async function getVideoInfo(videoId: string): Promise<VideoInfo> {
  const response = await fetch(`${API_BASE}/videos/${videoId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch video info');
  }
  return response.json();
}

export async function extractKeyframes(
  videoId: string,
  interval: number = 30,
  maxKeyframes: number = 100
): Promise<VideoFrameInfo[]> {
  const response = await fetch(
    `${API_BASE}/videos/${videoId}/keyframes?interval=${interval}&max_keyframes=${maxKeyframes}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error('Failed to extract keyframes');
  }
  const data = await response.json();
  return data.keyframes;
}

export async function getVideoFrame(videoId: string, frameIdx: number): Promise<string> {
  const response = await fetch(`${API_BASE}/videos/${videoId}/frames/${frameIdx}`);
  if (!response.ok) {
    throw new Error('Failed to fetch video frame');
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function interpolateAnnotations(
  videoId: string,
  startFrame: number,
  endFrame: number,
  startAnnotations: Annotation[],
  endAnnotations: Annotation[]
): Promise<Record<number, Annotation[]>> {
  const response = await fetch(`${API_BASE}/videos/${videoId}/interpolate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_frame: startFrame,
      end_frame: endFrame,
      start_annotations: startAnnotations,
      end_annotations: endAnnotations
    })
  });
  if (!response.ok) {
    throw new Error('Failed to interpolate annotations');
  }
  const data = await response.json();
  return data.interpolated;
}

export async function saveVideoAnnotations(
  videoId: string,
  frameIdx: number,
  annotations: Annotation[]
): Promise<void> {
  const response = await fetch(`${API_BASE}/videos/${videoId}/annotations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_idx: frameIdx, annotations })
  });
  if (!response.ok) {
    throw new Error('Failed to save video annotations');
  }
}

export async function getVideoAnnotations(videoId: string): Promise<Record<number, Annotation[]>> {
  const response = await fetch(`${API_BASE}/videos/${videoId}/annotations`);
  if (!response.ok) {
    throw new Error('Failed to get video annotations');
  }
  return response.json();
}

export async function deleteVideo(videoId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/videos/${videoId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete video');
  }
}

export async function checkAnnotationQuality(
  imageId: string,
  annotations: Annotation[]
): Promise<QualityReport> {
  const response = await fetch(`${API_BASE}/quality/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId, annotations })
  });
  if (!response.ok) {
    throw new Error('Failed to check annotation quality');
  }
  return response.json();
}

export async function checkVideoQuality(
  videoId: string,
  frameAnnotations: Record<number, Annotation[]>
): Promise<QualityReport> {
  const response = await fetch(`${API_BASE}/quality/check-video`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, frame_annotations: frameAnnotations })
  });
  if (!response.ok) {
    throw new Error('Failed to check video quality');
  }
  return response.json();
}

export async function getVersions(imageId: string): Promise<AnnotationVersion[]> {
  const response = await fetch(`${API_BASE}/versions/${imageId}`);
  if (!response.ok) {
    throw new Error('Failed to get versions');
  }
  const data = await response.json();
  return data.versions;
}

export async function saveVersion(
  imageId: string,
  annotations: Annotation[],
  description: string = '',
  author: string = 'user'
): Promise<AnnotationVersion> {
  const response = await fetch(`${API_BASE}/versions/${imageId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ annotations, description, author })
  });
  if (!response.ok) {
    throw new Error('Failed to save version');
  }
  const data = await response.json();
  return data.version;
}

export async function getVersion(imageId: string, versionId: string): Promise<AnnotationVersion> {
  const response = await fetch(`${API_BASE}/versions/${imageId}/${versionId}`);
  if (!response.ok) {
    throw new Error('Failed to get version');
  }
  const data = await response.json();
  return data.version;
}

export async function rollbackToVersion(imageId: string, versionId: string): Promise<Annotation[]> {
  const response = await fetch(`${API_BASE}/versions/${imageId}/${versionId}/rollback`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error('Failed to rollback to version');
  }
  const data = await response.json();
  return data.annotations;
}

export async function compareVersions(
  imageId: string,
  versionId1: string,
  versionId2: string
): Promise<VersionDiff> {
  const response = await fetch(`${API_BASE}/versions/${imageId}/compare/${versionId1}/${versionId2}`);
  if (!response.ok) {
    throw new Error('Failed to compare versions');
  }
  return response.json();
}

export async function deleteVersion(imageId: string, versionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/versions/${imageId}/${versionId}`, {
    method: 'DELETE'
  });
  if (!response.ok) {
    throw new Error('Failed to delete version');
  }
}

async function downloadExport(
  endpoint: string,
  imageId: string,
  annotations: Annotation[],
  filename: string
): Promise<void> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      imageId,
      annotations,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to export: ${response.statusText}`);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function exportAnnotationsJSON(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  await downloadExport('/export/json', imageId, annotations, `annotations_${imageId}.json`);
}

export async function exportMaskImage(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  await downloadExport('/export/mask', imageId, annotations, `mask_${imageId}.png`);
}

export async function exportYOLO(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  const response = await fetch(`${API_BASE}/export/yolo`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      imageId,
      annotations,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to export YOLO: ${response.statusText}`);
  }

  const data = await response.json();
  
  if (data.annotations) {
    const blob = new Blob([data.annotations], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `yolo_${imageId}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  }
  
  if (data.label_map) {
    const labelMapContent = Object.entries(data.label_map)
      .map(([name, id]) => `${id}: ${name}`)
      .join('\n');
    const blob = new Blob([labelMapContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `labels_${imageId}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  }
}

export async function exportLabelMe(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  await downloadExport('/export/labelme', imageId, annotations, `labelme_${imageId}.json`);
}

export async function exportVOC(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  await downloadExport('/export/voc', imageId, annotations, `voc_${imageId}.xml`);
}

export async function exportCOCO(
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  await downloadExport('/export/coco', imageId, annotations, `coco_${imageId}.json`);
}

export async function exportByFormat(
  format: ExportFormat,
  imageId: string,
  annotations: Annotation[]
): Promise<void> {
  switch (format) {
    case 'json':
      await exportAnnotationsJSON(imageId, annotations);
      break;
    case 'mask':
      await exportMaskImage(imageId, annotations);
      break;
    case 'yolo':
      await exportYOLO(imageId, annotations);
      break;
    case 'labelme':
      await exportLabelMe(imageId, annotations);
      break;
    case 'voc':
      await exportVOC(imageId, annotations);
      break;
    case 'coco':
      await exportCOCO(imageId, annotations);
      break;
  }
}

export async function getExportFormats(): Promise<ExportFormatInfo[]> {
  const response = await fetch(`${API_BASE}/export/formats`);
  if (!response.ok) {
    return [
      { id: 'json', name: 'JSON', description: 'Custom JSON format', extension: '.json' },
      { id: 'mask', name: 'Mask PNG', description: 'Segmentation mask image', extension: '.png' },
      { id: 'yolo', name: 'YOLO', description: 'YOLO object detection format', extension: '.txt' },
      { id: 'labelme', name: 'LabelMe', description: 'LabelMe annotation format', extension: '.json' },
      { id: 'voc', name: 'Pascal VOC', description: 'Pascal VOC XML format', extension: '.xml' },
      { id: 'coco', name: 'COCO', description: 'COCO JSON format', extension: '.json' },
    ];
  }
  const data = await response.json();
  return data.formats;
}

export async function getSAMStatus(): Promise<{ loaded: boolean; modelType: string }> {
  const response = await fetch(`${API_BASE}/sam/status`);
  if (!response.ok) {
    return { loaded: false, modelType: 'unknown' };
  }
  return response.json();
}

export async function getSAMStats(): Promise<any> {
  const response = await fetch(`${API_BASE}/sam/stats`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export async function clearSAMCache(imageId?: string): Promise<void> {
  const url = imageId 
    ? `${API_BASE}/sam/cache/clear?image_id=${imageId}`
    : `${API_BASE}/sam/cache/clear`;
  await fetch(url);
}
