import { useEffect, useRef } from 'react';

interface ScannerFrameProps {
  isScanning: boolean;
  detected: boolean;
}

export function ScannerFrame({ isScanning, detected }: ScannerFrameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let scanLineY = 0;
    let direction = 1;

    const draw = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      const frameSize = Math.min(width, height) * 0.6;
      const frameX = (width - frameSize) / 2;
      const frameY = (height - frameSize) / 2;
      const cornerLen = frameSize * 0.15;
      const lineWidth = 4;

      ctx.strokeStyle = detected ? '#10b981' : isScanning ? '#58a6ff' : '#6b7280';
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';

      const corners = [
        { x: frameX, y: frameY, x2: frameX, y2: frameY },
        { x: frameX + frameSize, y: frameY, x2: frameX + frameSize, y2: frameY },
        { x: frameX, y: frameY + frameSize, x2: frameX, y2: frameY + frameSize },
        { x: frameX + frameSize, y: frameY + frameSize, x2: frameX + frameSize, y2: frameY + frameSize },
      ];

      corners.forEach((corner, i) => {
        ctx.beginPath();
        const isLeft = i % 2 === 0;
        const isTop = i < 2;

        if (isLeft && isTop) {
          ctx.moveTo(corner.x, corner.y + cornerLen);
          ctx.lineTo(corner.x, corner.y);
          ctx.lineTo(corner.x + cornerLen, corner.y);
        } else if (!isLeft && isTop) {
          ctx.moveTo(corner.x - cornerLen, corner.y);
          ctx.lineTo(corner.x, corner.y);
          ctx.lineTo(corner.x, corner.y + cornerLen);
        } else if (isLeft && !isTop) {
          ctx.moveTo(corner.x, corner.y - cornerLen);
          ctx.lineTo(corner.x, corner.y);
          ctx.lineTo(corner.x + cornerLen, corner.y);
        } else {
          ctx.moveTo(corner.x - cornerLen, corner.y);
          ctx.lineTo(corner.x, corner.y);
          ctx.lineTo(corner.x, corner.y - cornerLen);
        }
        ctx.stroke();
      });

      if (isScanning && !detected) {
        const gradient = ctx.createLinearGradient(
          frameX,
          frameY + scanLineY,
          frameX,
          frameY + scanLineY + 50
        );
        gradient.addColorStop(0, 'rgba(88, 166, 255, 0)');
        gradient.addColorStop(0.5, 'rgba(88, 166, 255, 0.8)');
        gradient.addColorStop(1, 'rgba(88, 166, 255, 0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(frameX + 10, frameY + scanLineY, frameSize - 20, 50);

        scanLineY += direction * 3;
        if (scanLineY >= frameSize - 50) direction = -1;
        if (scanLineY <= 0) direction = 1;
      }

      if (detected) {
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.3)';
        ctx.lineWidth = 2;
        ctx.strokeRect(frameX, frameY, frameSize, frameSize);
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isScanning, detected]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={400}
      className="absolute inset-0 w-full h-full pointer-events-none"
    />
  );
}
