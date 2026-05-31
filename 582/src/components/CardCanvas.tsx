import { useRef, useEffect, useState } from 'react';
import type { CardData, CardTemplate } from '@/types';
import { renderCardToCanvas } from '@/utils/cardRenderer';

interface CardCanvasProps {
  cardData: CardData;
  template: CardTemplate;
  width?: number;
  height?: number;
}

const DEFAULT_WIDTH = 300;
const DEFAULT_HEIGHT = 420;
const CARD_RATIO = 5 / 7;

export default function CardCanvas({ cardData, template, width, height }: CardCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState(false);

  const displayWidth = width || DEFAULT_WIDTH;
  const displayHeight = height || Math.round(displayWidth / CARD_RATIO);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cardData || !template) return;

    const scale = 2;
    canvas.width = displayWidth * scale;
    canvas.height = displayHeight * scale;

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.scale(scale, scale);
    }

    renderCardToCanvas(canvas, cardData, template);

    if (ctx) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    }
  }, [cardData, template, displayWidth, displayHeight]);

  return (
    <div
      ref={containerRef}
      className={`relative inline-block transition-all duration-300 ${
        hovered ? 'scale-[1.02]' : ''
      }`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <canvas
        ref={canvasRef}
        style={{ width: displayWidth, height: displayHeight }}
        className={`rounded-lg transition-shadow duration-300 ${
          hovered
            ? 'shadow-[0_0_25px_rgba(212,168,83,0.5)]'
            : 'shadow-[0_0_10px_rgba(0,0,0,0.5)]'
        }`}
      />
    </div>
  );
}
