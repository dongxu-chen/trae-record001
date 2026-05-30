import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import type { ImageItem, ImageFormat } from '../types';

export type DownloadProgressCallback = (current: number, total: number) => void;

export async function downloadAsMultiPartZip(
  images: ImageItem[],
  format: ImageFormat,
  maxChunkSize: number,
  onProgress?: DownloadProgressCallback
): Promise<void> {
  const completedImages = images.filter(img => img.status === 'completed' && img.compressedUrl);
  if (completedImages.length === 0) return;

  const imageBlobs: { name: string; blob: Blob; size: number }[] = [];

  for (const image of completedImages) {
    const response = await fetch(image.compressedUrl!);
    const blob = await response.blob();
    const baseName = image.file.name.replace(/\.[^/.]+$/, '');
    imageBlobs.push({
      name: `${baseName}.${format}`,
      blob,
      size: blob.size
    });
  }

  const chunks: { name: string; blob: Blob; size: number }[][] = [[]];
  let currentChunkSize = 0;
  let currentChunkIndex = 0;

  for (const imageBlob of imageBlobs) {
    if (currentChunkSize + imageBlob.size > maxChunkSize && chunks[currentChunkIndex].length > 0) {
      currentChunkIndex++;
      chunks[currentChunkIndex] = [];
      currentChunkSize = 0;
    }
    chunks[currentChunkIndex].push(imageBlob);
    currentChunkSize += imageBlob.size;
  }

  const timestamp = Date.now();

  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const zip = new JSZip();

    for (const imageBlob of chunk) {
      zip.file(imageBlob.name, imageBlob.blob);
    }

    const content = await zip.generateAsync({ type: 'blob' });
    const fileName = chunks.length > 1
      ? `compressed_images_${timestamp}_part${i + 1}.zip`
      : `compressed_images_${timestamp}.zip`;

    saveAs(content, fileName);

    if (onProgress) {
      onProgress(i + 1, chunks.length);
    }

    if (i < chunks.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
}

export async function downloadAsZip(
  images: ImageItem[],
  format: ImageFormat
): Promise<void> {
  await downloadAsMultiPartZip(images, format, Infinity);
}

export function downloadSingleImage(image: ImageItem, format: ImageFormat): void {
  if (!image.compressedUrl) return;
  const link = document.createElement('a');
  link.href = image.compressedUrl;
  const baseName = image.file.name.replace(/\.[^/.]+$/, '');
  link.download = `${baseName}_compressed.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
