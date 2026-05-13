import { useRef, useEffect, useCallback } from 'react';

function Waveform({ isRecording, audioLevel, width = 600, height = 100 }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const barsRef = useRef([]);
  const gradientRef = useRef(null);
  const pathRef = useRef(null);
  const startTimeRef = useRef(null);

  const initBars = useCallback(() => {
    const barCount = Math.floor(width / 4);
    const bars = new Float32Array(barCount);
    for (let i = 0; i < barCount; i++) {
      bars[i] = Math.random() * 20 + 10;
    }
    barsRef.current = bars;
  }, [width]);

  const initGradient = useCallback((ctx) => {
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, '#667eea');
    gradient.addColorStop(0.5, '#764ba2');
    gradient.addColorStop(1, '#f093fb');
    gradientRef.current = gradient;
  }, [width]);

  useEffect(() => {
    initBars();
  }, [initBars]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    const barWidth = 2;
    const gap = 2;
    const centerY = height / 2;
    const bars = barsRef.current;
    const barCount = bars.length;

    if (!gradientRef.current) {
      initGradient(ctx);
    }

    startTimeRef.current = performance.now();

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      const now = performance.now() - startTimeRef.current;
      const baseHeight = isRecording ? 20 + audioLevel * 60 : 10;

      const path = new Path2D();

      for (let i = 0; i < barCount; i++) {
        let targetHeight;

        if (isRecording) {
          const offset = Math.sin(now / 200 + i * 0.5);
          targetHeight = baseHeight + offset * 10;
          bars[i] += (targetHeight - bars[i]) * 0.15;
        } else {
          targetHeight = 10 + (Math.sin(now / 500 + i * 0.3) + 1) * 7.5;
          bars[i] += (targetHeight - bars[i]) * 0.05;
        }

        const barHeight = isRecording ? bars[i] : bars[i] * 0.3;
        const x = i * (barWidth + gap);
        const y = centerY - barHeight / 2;

        path.rect(x, y, barWidth, barHeight);
      }

      ctx.fillStyle = gradientRef.current;
      ctx.fill(path);

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isRecording, audioLevel, width, height, initGradient]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        display: 'block',
        margin: '0 auto',
        borderRadius: '8px',
        imageRendering: 'optimizeSpeed',
      }}
    />
  );
}

export default Waveform;