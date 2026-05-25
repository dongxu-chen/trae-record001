import JSZip from 'jszip';
import { generateQRCodeDataURL } from './qrGenerator';
import type { QRStyle, BatchCSVRow } from '@/types';
import { generateContent } from './contentGenerator';

export async function downloadAsPNG(canvasId: string, filename: string = 'qrcode'): Promise<void> {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  if (!canvas) return;

  const link = document.createElement('a');
  link.download = `${filename}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

export async function downloadAsSVG(content: string, style: QRStyle, filename: string = 'qrcode'): Promise<void> {
  const QRCode = await import('qrcode');
  const svgString = await QRCode.toString(content, {
    type: 'svg',
    width: style.size,
    margin: 2,
    color: {
      dark: style.foregroundColor,
      light: style.backgroundColor,
    },
    errorCorrectionLevel: style.errorCorrectionLevel,
  });

  const blob = new Blob([svgString], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `${filename}.svg`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

export async function downloadAsJPEG(canvasId: string, filename: string = 'qrcode', quality: number = 0.95): Promise<void> {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  if (!canvas) return;

  const link = document.createElement('a');
  link.download = `${filename}.jpg`;
  link.href = canvas.toDataURL('image/jpeg', quality);
  link.click();
}

interface WorkerResult {
  name: string;
  dataUrl: string;
}

export async function batchGenerateAndDownload(
  rows: Array<{ content: string; name?: string }>,
  style: QRStyle,
  preGeneratedResults?: WorkerResult[]
): Promise<void> {
  const zip = new JSZip();
  const folder = zip.folder('qrcodes');
  if (!folder) return;

  if (preGeneratedResults && preGeneratedResults.length > 0) {
    for (let i = 0; i < preGeneratedResults.length; i++) {
      const result = preGeneratedResults[i];
      const base64Data = result.dataUrl.split(',')[1];
      folder.file(`${result.name}.png`, base64Data, { base64: true });
    }
  } else {
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const content = row.content || '';
      const filename = row.name || `qrcode_${i + 1}`;

      try {
        const dataUrl = await generateQRCodeDataURL(content, style);
        const base64Data = dataUrl.split(',')[1];
        folder.file(`${filename}.png`, base64Data, { base64: true });
      } catch (error) {
        console.error(`Failed to generate QR code for row ${i}:`, error);
      }
    }
  }

  const content = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(content);
  const link = document.createElement('a');
  link.download = 'qrcodes_bundle.zip';
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export async function copyImageToClipboard(canvasId: string): Promise<void> {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  if (!canvas) return;

  return new Promise((resolve, reject) => {
    canvas.toBlob(async (blob) => {
      if (!blob) {
        reject(new Error('Failed to create blob'));
        return;
      }
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ 'image/png': blob }),
        ]);
        resolve();
      } catch (error) {
        reject(error);
      }
    }, 'image/png');
  });
}

export function generateFileName(type: string, prefix: string = 'qrcode'): string {
  const timestamp = new Date().toISOString().slice(0, 10);
  return `${prefix}_${type}_${timestamp}`;
}
