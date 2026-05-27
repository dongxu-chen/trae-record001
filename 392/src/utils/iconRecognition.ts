import { Icon } from '../types';
import { fontawesomeIcons } from '../data/fontawesome';
import { materialIcons } from '../data/material';

export const analyzeImage = async (
  imageFile: File
): Promise<ImageData> => {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx?.drawImage(img, 0, 0);
      const imageData = ctx?.getImageData(0, 0, canvas.width, canvas.height);
      if (imageData) {
        resolve(imageData);
      } else {
        reject(new Error('Failed to get image data'));
      }
    };

    img.onerror = reject;
    img.src = URL.createObjectURL(imageFile);
  });
};

export const extractFeatures = (imageData: ImageData): number[] => {
  const { data, width, height } = imageData;
  const features: number[] = [];
  
  const gridSize = 8;
  const cellWidth = Math.floor(width / gridSize);
  const cellHeight = Math.floor(height / gridSize);

  for (let gy = 0; gy < gridSize; gy++) {
    for (let gx = 0; gx < gridSize; gx++) {
      let r = 0, g = 0, b = 0, count = 0;
      
      for (let y = gy * cellHeight; y < (gy + 1) * cellHeight; y++) {
        for (let x = gx * cellWidth; x < (gx + 1) * cellWidth; x++) {
          const i = (y * width + x) * 4;
          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          count++;
        }
      }
      
      features.push(r / count / 255);
      features.push(g / count / 255);
      features.push(b / count / 255);
    }
  }

  let edgeCount = 0;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const i = (y * width + x) * 4;
      const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
      const rightBrightness = (data[i + 4] + data[i + 5] + data[i + 6]) / 3;
      const bottomBrightness = (data[(y + 1) * width * 4 + x * 4] + data[(y + 1) * width * 4 + x * 4 + 1] + data[(y + 1) * width * 4 + x * 4 + 2]) / 3;
      
      if (Math.abs(brightness - rightBrightness) > 30 || Math.abs(brightness - bottomBrightness) > 30) {
        edgeCount++;
      }
    }
  }
  
  features.push(edgeCount / (width * height));
  
  return features;
};

export const cosineSimilarity = (a: number[], b: number[]): number => {
  if (a.length !== b.length) return 0;
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  
  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
};

export const matchIconToLibrary = async (
  imageFile: File
): Promise<{ icon: Icon; confidence: number }[]> => {
  const imageData = await analyzeImage(imageFile);
  const imageFeatures = extractFeatures(imageData);
  
  const allIcons = [...fontawesomeIcons, ...materialIcons];
  const matches: { icon: Icon; confidence: number }[] = [];
  
  for (const icon of allIcons) {
    const iconFeatures = extractFeaturesFromPath(icon.svgPath);
    const similarity = cosineSimilarity(imageFeatures, iconFeatures);
    
    if (similarity > 0.3) {
      matches.push({ icon, confidence: similarity });
    }
  }
  
  return matches.sort((a, b) => b.confidence - a.confidence).slice(0, 10);
};

export const extractFeaturesFromPath = (svgPath: string): number[] => {
  const features: number[] = [];
  const gridSize = 8;
  
  const pathPoints = parsePathToPoints(svgPath);
  const bounds = getBounds(pathPoints);
  
  for (let gy = 0; gy < gridSize; gy++) {
    for (let gx = 0; gx < gridSize; gx++) {
      const cellX1 = bounds.minX + (bounds.maxX - bounds.minX) * (gx / gridSize);
      const cellY1 = bounds.minY + (bounds.maxY - bounds.minY) * (gy / gridSize);
      const cellX2 = bounds.minX + (bounds.maxX - bounds.minX) * ((gx + 1) / gridSize);
      const cellY2 = bounds.minY + (bounds.maxY - bounds.minY) * ((gy + 1) / gridSize);
      
      const pointsInCell = pathPoints.filter(p => 
        p.x >= cellX1 && p.x < cellX2 && p.y >= cellY1 && p.y < cellY2
      );
      
      features.push(pointsInCell.length / pathPoints.length);
      features.push(0.5);
      features.push(0.5);
    }
  }
  
  features.push(0.3);
  
  return features;
};

export const parsePathToPoints = (d: string): { x: number; y: number }[] => {
  const points: { x: number; y: number }[] = [];
  const commands = d.match(/[MLQCZ][^MLQCZ]*/gi) || [];
  
  let currentX = 0;
  let currentY = 0;
  
  for (const cmd of commands) {
    const type = cmd[0].toUpperCase();
    const coords = cmd.slice(1).trim().split(/[\s,]+/).map(Number);
    
    switch (type) {
      case 'M':
        for (let i = 0; i < coords.length; i += 2) {
          currentX = coords[i];
          currentY = coords[i + 1];
          points.push({ x: currentX, y: currentY });
        }
        break;
      case 'L':
        for (let i = 0; i < coords.length; i += 2) {
          currentX = coords[i];
          currentY = coords[i + 1];
          points.push({ x: currentX, y: currentY });
        }
        break;
      case 'Q':
        for (let i = 0; i < coords.length; i += 4) {
          const cx = coords[i];
          const cy = coords[i + 1];
          const x = coords[i + 2];
          const y = coords[i + 3];
          for (let t = 0; t <= 1; t += 0.2) {
            const px = (1 - t) * (1 - t) * currentX + 2 * (1 - t) * t * cx + t * t * x;
            const py = (1 - t) * (1 - t) * currentY + 2 * (1 - t) * t * cy + t * t * y;
            points.push({ x: px, y: py });
          }
          currentX = x;
          currentY = y;
        }
        break;
      case 'C':
        for (let i = 0; i < coords.length; i += 6) {
          const cx1 = coords[i];
          const cy1 = coords[i + 1];
          const cx2 = coords[i + 2];
          const cy2 = coords[i + 3];
          const x = coords[i + 4];
          const y = coords[i + 5];
          for (let t = 0; t <= 1; t += 0.2) {
            const px = Math.pow(1 - t, 3) * currentX + 3 * Math.pow(1 - t, 2) * t * cx1 + 3 * (1 - t) * t * t * cx2 + Math.pow(t, 3) * x;
            const py = Math.pow(1 - t, 3) * currentY + 3 * Math.pow(1 - t, 2) * t * cy1 + 3 * (1 - t) * t * t * cy2 + Math.pow(t, 3) * y;
            points.push({ x: px, y: py });
          }
          currentX = x;
          currentY = y;
        }
        break;
    }
  }
  
  return points;
};

export const getBounds = (points: { x: number; y: number }[]): { minX: number; maxX: number; minY: number; maxY: number } => {
  if (points.length === 0) return { minX: 0, maxX: 24, minY: 0, maxY: 24 };
  
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  
  for (const p of points) {
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }
  
  return { minX, maxX, minY, maxY };
};

export const extractDominantColors = async (imageFile: File): Promise<string[]> => {
  const imageData = await analyzeImage(imageFile);
  const { data } = imageData;
  
  const colorCounts: Record<string, number> = {};
  
  for (let i = 0; i < data.length; i += 4) {
    const r = Math.round(data[i] / 32) * 32;
    const g = Math.round(data[i + 1] / 32) * 32;
    const b = Math.round(data[i + 2] / 32) * 32;
    const a = data[i + 3];
    
    if (a > 128) {
      const key = `${r},${g},${b}`;
      colorCounts[key] = (colorCounts[key] || 0) + 1;
    }
  }
  
  const sortedColors = Object.entries(colorCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([key]) => {
      const [r, g, b] = key.split(',').map(Number);
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    });
  
  return sortedColors;
};
