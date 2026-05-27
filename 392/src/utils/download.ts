import { Icon } from '../types';
import { generateSvgCode } from './svgUtils';

export const downloadSingleIcon = (icon: Icon, color: string, size: number): void => {
  const svgContent = generateSvgCode(icon, color, size);
  const blob = new Blob([svgContent], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${icon.name}.svg`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

interface DownloadProgress {
  current: number;
  total: number;
  percent: number;
}

export const downloadMultipleIcons = async (
  icons: Icon[],
  color: string,
  size: number,
  onProgress?: (progress: DownloadProgress) => void
): Promise<void> => {
  try {
    const JSZip = (await import('jszip')).default;
    const zip = new JSZip();
    
    const total = icons.length;
    const chunkSize = Math.ceil(total / 10);
    
    for (let i = 0; i < icons.length; i += chunkSize) {
      const chunk = icons.slice(i, i + chunkSize);
      
      for (const icon of chunk) {
        const svgContent = generateSvgCode(icon, color, size);
        zip.file(`${icon.name}.svg`, svgContent);
      }
      
      const current = Math.min(i + chunkSize, total);
      const percent = (current / total) * 100;
      
      if (onProgress) {
        onProgress({ current, total, percent });
      }
      
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    if (onProgress) {
      onProgress({ current: total, total, percent: 100 });
    }
    
    const content = await zip.generateAsync({ 
      type: 'blob',
      compression: 'DEFLATE',
      compressionOptions: { level: 6 }
    }, (meta) => {
      if (onProgress) {
        onProgress({ 
          current: Math.round(meta.percent), 
          total: 100, 
          percent: 100 
        });
      }
    });
    
    const url = URL.createObjectURL(content);
    const link = document.createElement('a');
    link.href = url;
    link.download = `icons-${Date.now()}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
  } catch (error) {
    console.error('Failed to create zip:', error);
    for (const icon of icons) {
      downloadSingleIcon(icon, color, size);
    }
  }
};
