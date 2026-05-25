import QRCode from 'qrcode';

interface QRStyle {
  foregroundColor: string;
  backgroundColor: string;
  size: number;
  errorCorrectionLevel: 'L' | 'M' | 'Q' | 'H';
  dotStyle: 'square' | 'round' | 'dots';
  cornerRadius: number;
}

interface BatchRow {
  content: string;
  name?: string;
}

interface WorkerMessage {
  type: 'start' | 'cancel';
  rows?: BatchRow[];
  style?: QRStyle;
}

interface WorkerResponse {
  type: 'progress' | 'complete' | 'error';
  progress?: number;
  total?: number;
  current?: number;
  results?: Array<{ name: string; dataUrl: string }>;
  error?: string;
}

let isCancelled = false;

async function generateQRCodeDataURL(
  content: string,
  style: QRStyle
): Promise<string> {
  const canvas = new OffscreenCanvas(style.size, style.size);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('无法获取Canvas上下文');

  ctx.fillStyle = style.backgroundColor;
  ctx.fillRect(0, 0, style.size, style.size);

  const qrSize = style.size * 0.9;
  const offset = (style.size - qrSize) / 2;

  const qrCanvas = new OffscreenCanvas(qrSize, qrSize);
  const effectiveErrorLevel: 'L' | 'M' | 'Q' | 'H' = 'H';

  await QRCode.toCanvas(qrCanvas as unknown as HTMLCanvasElement, content, {
    width: qrSize,
    margin: 0,
    errorCorrectionLevel: effectiveErrorLevel,
    color: {
      dark: style.foregroundColor,
      light: '#ffffff00',
    },
  });

  const qrCtx = qrCanvas.getContext('2d');
  if (!qrCtx) throw new Error('无法获取QR Canvas上下文');

  if (style.dotStyle === 'square' && style.cornerRadius === 0) {
    ctx.drawImage(qrCanvas, offset, offset);
  } else {
    const imageData = qrCtx.getImageData(0, 0, qrSize, qrSize);
    const moduleSize = qrSize / Math.ceil(Math.sqrt(content.length / 2) + 2);

    ctx.fillStyle = style.foregroundColor;

    for (let row = 0; row < qrSize / moduleSize; row++) {
      for (let col = 0; col < qrSize / moduleSize; col++) {
        const pixelX = Math.floor(col * moduleSize + moduleSize / 2);
        const pixelY = Math.floor(row * moduleSize + moduleSize / 2);
        const index = (pixelY * qrSize + pixelX) * 4;
        const alpha = imageData.data[index + 3];

        if (alpha > 128) {
          const drawX = offset + col * moduleSize;
          const drawY = offset + row * moduleSize;
          const radius = style.cornerRadius * (moduleSize / 10);

          if (style.dotStyle === 'round' || style.dotStyle === 'dots') {
            const r = style.dotStyle === 'dots' ? moduleSize / 3 : moduleSize / 2 - 0.5;
            ctx.beginPath();
            ctx.arc(drawX + moduleSize / 2, drawY + moduleSize / 2, r, 0, Math.PI * 2);
            ctx.fill();
          } else {
            const r = Math.min(radius, moduleSize / 2);
            ctx.beginPath();
            ctx.moveTo(drawX + r, drawY);
            ctx.lineTo(drawX + moduleSize - r, drawY);
            ctx.quadraticCurveTo(drawX + moduleSize, drawY, drawX + moduleSize, drawY + r);
            ctx.lineTo(drawX + moduleSize, drawY + moduleSize - r);
            ctx.quadraticCurveTo(drawX + moduleSize, drawY + moduleSize, drawX + moduleSize - r, drawY + moduleSize);
            ctx.lineTo(drawX + r, drawY + moduleSize);
            ctx.quadraticCurveTo(drawX, drawY + moduleSize, drawX, drawY + moduleSize - r);
            ctx.lineTo(drawX, drawY + r);
            ctx.quadraticCurveTo(drawX, drawY, drawX + r, drawY);
            ctx.closePath();
            ctx.fill();
          }
        }
      }
    }
  }

  const blob = await canvas.convertToBlob({ type: 'image/png' });
  const arrayBuffer = await blob.arrayBuffer();
  const base64 = arrayBufferToBase64(arrayBuffer);
  return `data:image/png;base64,${base64}`;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.slice(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, Array.from(chunk));
  }
  
  return btoa(binary);
}

async function processBatch(rows: BatchRow[], style: QRStyle) {
  const results: Array<{ name: string; dataUrl: string }> = [];
  const total = rows.length;

  for (let i = 0; i < total; i++) {
    if (isCancelled) {
      self.postMessage({ type: 'error', error: '已取消' } as WorkerResponse);
      return;
    }

    try {
      const row = rows[i];
      const dataUrl = await generateQRCodeDataURL(row.content, style);
      results.push({
        name: row.name || `qrcode_${i + 1}`,
        dataUrl,
      });

      self.postMessage({
        type: 'progress',
        progress: ((i + 1) / total) * 100,
        current: i + 1,
        total,
      } as WorkerResponse);
    } catch (error) {
      console.error(`生成第 ${i + 1} 个二维码失败:`, error);
    }
  }

  self.postMessage({
    type: 'complete',
    results,
  } as WorkerResponse);
}

self.addEventListener('message', async (event: MessageEvent<WorkerMessage>) => {
  const { type, rows, style } = event.data;

  if (type === 'cancel') {
    isCancelled = true;
    return;
  }

  if (type === 'start' && rows && style) {
    isCancelled = false;
    try {
      await processBatch(rows, style);
    } catch (error) {
      self.postMessage({
        type: 'error',
        error: error instanceof Error ? error.message : '未知错误',
      } as WorkerResponse);
    }
  }
});

export {};
