import QRCode from 'qrcode';
import type { QRStyle, ArtPattern, EyeStyle } from '@/types';

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 0, g: 0, b: 0 };
}

function getRainbowColor(index: number, total: number): string {
  const hue = (index / total) * 360;
  return `hsl(${hue}, 80%, 50%)`;
}

function getGradientColor(
  x: number,
  y: number,
  size: number,
  startColor: string,
  endColor: string,
  type: 'linear' | 'radial' | 'diagonal'
): string {
  const start = hexToRgb(startColor);
  const end = hexToRgb(endColor);
  
  let ratio: number;
  if (type === 'radial') {
    const centerX = size / 2;
    const centerY = size / 2;
    const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
    ratio = distance / (size / 2);
  } else if (type === 'diagonal') {
    ratio = (x + y) / (size * 2);
  } else {
    ratio = x / size;
  }
  
  const r = Math.round(start.r + (end.r - start.r) * ratio);
  const g = Math.round(start.g + (end.g - start.g) * ratio);
  const b = Math.round(start.b + (end.b - start.b) * ratio);
  
  return `rgb(${r}, ${g}, ${b})`;
}

function drawEyeShape(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  style: EyeStyle,
  color: string
) {
  ctx.fillStyle = color;
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(2, size * 0.08);

  if (style === 'square') {
    ctx.fillRect(x, y, size, size);
    ctx.clearRect(x + size * 0.25, y + size * 0.25, size * 0.5, size * 0.5);
    ctx.fillRect(x + size * 0.35, y + size * 0.35, size * 0.3, size * 0.3);
  } else if (style === 'rounded') {
    const radius = size * 0.2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + size - radius, y);
    ctx.quadraticCurveTo(x + size, y, x + size, y + radius);
    ctx.lineTo(x + size, y + size - radius);
    ctx.quadraticCurveTo(x + size, y + size, x + size - radius, y + size);
    ctx.lineTo(x + radius, y + size);
    ctx.quadraticCurveTo(x, y + size, x, y + size - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();
    
    ctx.globalCompositeOperation = 'destination-out';
    const innerSize = size * 0.5;
    const innerX = x + size * 0.25;
    const innerY = y + size * 0.25;
    const innerRadius = innerSize * 0.2;
    ctx.beginPath();
    ctx.moveTo(innerX + innerRadius, innerY);
    ctx.lineTo(innerX + innerSize - innerRadius, innerY);
    ctx.quadraticCurveTo(innerX + innerSize, innerY, innerX + innerSize, innerY + innerRadius);
    ctx.lineTo(innerX + innerSize, innerY + innerSize - innerRadius);
    ctx.quadraticCurveTo(innerX + innerSize, innerY + innerSize, innerX + innerSize - innerRadius, innerY + innerSize);
    ctx.lineTo(innerX + innerRadius, innerY + innerSize);
    ctx.quadraticCurveTo(innerX, innerY + innerSize, innerX, innerY + innerSize - innerRadius);
    ctx.lineTo(innerX, innerY + innerRadius);
    ctx.quadraticCurveTo(innerX, innerY, innerX + innerRadius, innerY);
    ctx.closePath();
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    
    ctx.fillRect(x + size * 0.35, y + size * 0.35, size * 0.3, size * 0.3);
  } else if (style === 'circle') {
    ctx.beginPath();
    ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(x + size / 2, y + size / 2, size * 0.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    ctx.beginPath();
    ctx.arc(x + size / 2, y + size / 2, size * 0.15, 0, Math.PI * 2);
    ctx.fill();
  } else if (style === 'heart') {
    const centerX = x + size / 2;
    const centerY = y + size / 2;
    
    ctx.beginPath();
    const heartSize = size * 0.4;
    ctx.moveTo(centerX, centerY + heartSize * 0.3);
    ctx.bezierCurveTo(centerX, centerY, centerX - heartSize, centerY, centerX - heartSize, centerY - heartSize * 0.5);
    ctx.bezierCurveTo(centerX - heartSize, centerY - heartSize, centerX, centerY - heartSize, centerX, centerY - heartSize * 0.5);
    ctx.bezierCurveTo(centerX, centerY - heartSize, centerX + heartSize, centerY - heartSize, centerX + heartSize, centerY - heartSize * 0.5);
    ctx.bezierCurveTo(centerX + heartSize, centerY, centerX, centerY, centerX, centerY + heartSize * 0.3);
    ctx.closePath();
    ctx.fill();
  } else if (style === 'star') {
    const centerX = x + size / 2;
    const centerY = y + size / 2;
    const outerRadius = size * 0.45;
    const innerRadius = size * 0.2;
    const points = 5;
    
    ctx.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const radius = i % 2 === 0 ? outerRadius : innerRadius;
      const angle = (i * Math.PI) / points - Math.PI / 2;
      const px = centerX + Math.cos(angle) * radius;
      const py = centerY + Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
  }
}

function drawArtBackground(
  ctx: CanvasRenderingContext2D,
  size: number,
  artPattern: ArtPattern,
  gradientStart: string,
  gradientEnd: string,
  gradientType: 'linear' | 'radial' | 'diagonal'
) {
  if (artPattern === 'gradient' || artPattern === 'rainbow') {
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    if (gradientType === 'radial') {
      const radialGradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
      radialGradient.addColorStop(0, gradientStart);
      radialGradient.addColorStop(1, gradientEnd);
      ctx.fillStyle = radialGradient;
    } else if (gradientType === 'diagonal') {
      const diagGradient = ctx.createLinearGradient(0, 0, size, size);
      diagGradient.addColorStop(0, gradientStart);
      diagGradient.addColorStop(0.5, gradientEnd);
      diagGradient.addColorStop(1, gradientStart);
      ctx.fillStyle = diagGradient;
    } else {
      gradient.addColorStop(0, gradientStart);
      gradient.addColorStop(1, gradientEnd);
      ctx.fillStyle = gradient;
    }
    ctx.fillRect(0, 0, size, size);
  } else if (artPattern === 'cyber') {
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = 'rgba(0, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i < size; i += 20) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, size);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(size, i);
      ctx.stroke();
    }
  } else if (artPattern === 'nature') {
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, '#f0fdf4');
    gradient.addColorStop(1, '#dcfce7');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  } else if (artPattern === 'vintage') {
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    gradient.addColorStop(0, '#fef3c7');
    gradient.addColorStop(1, '#fde68a');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    ctx.globalAlpha = 0.05;
    for (let i = 0; i < 100; i++) {
      ctx.fillStyle = '#92400e';
      ctx.beginPath();
      ctx.arc(Math.random() * size, Math.random() * size, Math.random() * 3 + 1, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  } else if (artPattern === 'abstract') {
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    gradient.addColorStop(0, '#f0f9ff');
    gradient.addColorStop(0.5, '#e0f2fe');
    gradient.addColorStop(1, '#f0f9ff');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
  } else if (artPattern === 'geometric') {
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.1)';
    ctx.lineWidth = 2;
    for (let i = 0; i < size; i += 40) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(0, i);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(size - i, size);
      ctx.lineTo(size, size - i);
      ctx.stroke();
    }
  }
}

export async function generateQRCodeCanvas(
  content: string,
  style: QRStyle,
  canvasId: string
): Promise<HTMLCanvasElement | null> {
  if (!content) return null;
  
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  if (!canvas) return null;

  const {
    foregroundColor,
    backgroundColor,
    size,
    dotStyle,
    cornerRadius,
    logo,
    logoSize,
    logoBackgroundColor,
    artPattern = 'none',
    eyeStyle = 'square',
    gradientStart = '#1e3a8a',
    gradientEnd = '#06b6d4',
    gradientType = 'linear',
  } = style;

  const effectiveErrorLevel: 'L' | 'M' | 'Q' | 'H' = logo ? 'H' : style.errorCorrectionLevel;

  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  if (artPattern !== 'none' && artPattern !== 'rainbow') {
    drawArtBackground(ctx, size, artPattern, gradientStart, gradientEnd, gradientType);
  } else {
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, size, size);
  }

  const qrCanvas = document.createElement('canvas');
  const qrSize = size * 0.9;
  const offset = (size - qrSize) / 2;

  await QRCode.toCanvas(qrCanvas, content, {
    width: qrSize,
    margin: 0,
    errorCorrectionLevel: effectiveErrorLevel,
    color: {
      dark: foregroundColor,
      light: '#ffffff00',
    },
  });

  const qrCtx = qrCanvas.getContext('2d');
  if (!qrCtx) return null;

  const imageData = qrCtx.getImageData(0, 0, qrSize, qrSize);
  const moduleCount = Math.ceil(Math.sqrt(content.length / 2) + 2);
  const moduleSize = qrSize / moduleCount;
  const eyeModuleSize = 7 * moduleSize;

  const isInEye = (row: number, col: number): boolean => {
    const isTopLeft = row < 7 && col < 7;
    const isTopRight = row < 7 && col >= moduleCount - 7;
    const isBottomLeft = row >= moduleCount - 7 && col < 7;
    return isTopLeft || isTopRight || isBottomLeft;
  };

  for (let row = 0; row < moduleCount; row++) {
    for (let col = 0; col < moduleCount; col++) {
      const pixelX = Math.floor(col * moduleSize + moduleSize / 2);
      const pixelY = Math.floor(row * moduleSize + moduleSize / 2);
      const index = (pixelY * qrSize + pixelX) * 4;
      const alpha = imageData.data[index + 3];

      if (alpha > 128 && !isInEye(row, col)) {
        const drawX = offset + col * moduleSize;
        const drawY = offset + row * moduleSize;
        const radius = cornerRadius * (moduleSize / 10);

        let dotColor = foregroundColor;
        if (artPattern === 'rainbow') {
          const position = (row + col) / (moduleCount * 2);
          dotColor = getRainbowColor(position * moduleCount, moduleCount);
        } else if (artPattern === 'gradient') {
          dotColor = getGradientColor(
            drawX + moduleSize / 2,
            drawY + moduleSize / 2,
            size,
            gradientStart,
            gradientEnd,
            gradientType
          );
        } else if (artPattern === 'cyber') {
          const position = (row * col) % 10;
          dotColor = position < 5 ? '#00ffff' : '#ff00ff';
        } else if (artPattern === 'nature') {
          const position = (row + col) % 3;
          const colors = ['#166534', '#15803d', '#16a34a'];
          dotColor = colors[position];
        } else if (artPattern === 'vintage') {
          const position = (row + col) % 3;
          const colors = ['#92400e', '#b45309', '#d97706'];
          dotColor = colors[position];
        } else if (artPattern === 'abstract') {
          const position = (row * col) % 4;
          const colors = ['#1e40af', '#0369a1', '#0891b2', '#0e7490'];
          dotColor = colors[position];
        } else if (artPattern === 'geometric') {
          const position = (row + col) % 2;
          dotColor = position === 0 ? '#1d4ed8' : '#0284c7';
        }

        ctx.fillStyle = dotColor;

        if (dotStyle === 'round') {
          ctx.beginPath();
          ctx.arc(
            drawX + moduleSize / 2,
            drawY + moduleSize / 2,
            moduleSize / 2 - 0.5,
            0,
            Math.PI * 2
          );
          ctx.fill();
        } else if (dotStyle === 'dots') {
          ctx.beginPath();
          ctx.arc(
            drawX + moduleSize / 2,
            drawY + moduleSize / 2,
            moduleSize / 3,
            0,
            Math.PI * 2
          );
          ctx.fill();
        } else if (dotStyle === 'square' && cornerRadius === 0) {
          ctx.fillRect(drawX, drawY, moduleSize - 0.5, moduleSize - 0.5);
        } else {
          drawRoundedRect(ctx, drawX, drawY, moduleSize - 0.5, moduleSize - 0.5, radius);
          ctx.fill();
        }
      }
    }
  }

  const eyePositions = [
    { x: offset, y: offset },
    { x: offset + qrSize - eyeModuleSize, y: offset },
    { x: offset, y: offset + qrSize - eyeModuleSize },
  ];

  const eyeColor = artPattern === 'gradient' || artPattern === 'rainbow'
    ? gradientStart
    : foregroundColor;

  eyePositions.forEach(pos => {
    drawEyeShape(ctx, pos.x, pos.y, eyeModuleSize, eyeStyle, eyeColor);
  });

  if (logo) {
    await drawLogo(ctx, logo, size, logoSize || 0.2, logoBackgroundColor || '#ffffff');
  }

  return canvas;
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
): void {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

async function drawLogo(
  ctx: CanvasRenderingContext2D,
  logoSrc: string,
  canvasSize: number,
  logoSizeRatio: number,
  logoBgColor: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const logoSize = canvasSize * logoSizeRatio;
      const logoX = (canvasSize - logoSize) / 2;
      const logoY = (canvasSize - logoSize) / 2;
      const padding = logoSize * 0.1;
      const bgSize = logoSize + padding * 2;
      const bgX = logoX - padding;
      const bgY = logoY - padding;

      ctx.fillStyle = logoBgColor;
      ctx.beginPath();
      ctx.roundRect(bgX, bgY, bgSize, bgSize, 8);
      ctx.fill();

      ctx.drawImage(img, logoX, logoY, logoSize, logoSize);
      resolve();
    };
    img.onerror = reject;
    img.src = logoSrc;
  });
}

export async function generateQRCodeDataURL(
  content: string,
  style: QRStyle
): Promise<string> {
  const tempCanvas = document.createElement('canvas');
  tempCanvas.id = 'temp-qr-canvas';
  document.body.appendChild(tempCanvas);

  try {
    await generateQRCodeCanvas(content, style, 'temp-qr-canvas');
    const dataUrl = tempCanvas.toDataURL('image/png');
    return dataUrl;
  } finally {
    document.body.removeChild(tempCanvas);
  }
}
