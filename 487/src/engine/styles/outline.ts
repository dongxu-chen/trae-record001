import { RenderContext } from '../types';
import { darkenColor, lightenColor } from '../../utils/color';

export function renderOutline(context: RenderContext): void {
  const { ctx, config, width, height } = context;
  if (!ctx) return;

  const { text, primaryColor, secondaryColor, padding, borderRadius, showBackground, backgroundColor } = config;

  ctx.clearRect(0, 0, width, height);

  if (showBackground) {
    ctx.fillStyle = backgroundColor;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.fill();
  }

  const centerX = width / 2;
  const centerY = height / 2;
  const iconSize = Math.min(width, height) - padding * 2;

  const fontSize = iconSize * 0.5;
  ctx.font = `bold ${fontSize}px 'Space Grotesk', 'Inter', sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const strokeWidth = Math.max(3, iconSize * 0.03);

  const gradient = ctx.createLinearGradient(padding, padding, width - padding, height - padding);
  gradient.addColorStop(0, primaryColor);
  gradient.addColorStop(1, secondaryColor);

  ctx.strokeStyle = gradient;
  ctx.lineWidth = strokeWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';

  const displayText = text.substring(0, 2).toUpperCase();
  ctx.strokeText(displayText, centerX, centerY);

  ctx.strokeStyle = lightenColor(primaryColor, 0.3);
  ctx.lineWidth = strokeWidth / 3;
  ctx.globalAlpha = 0.5;

  ctx.beginPath();
  ctx.roundRect(padding + strokeWidth, padding + strokeWidth, width - padding * 2 - strokeWidth * 2, height - padding * 2 - strokeWidth * 2, borderRadius - strokeWidth);
  ctx.stroke();

  ctx.globalAlpha = 1;

  const decorSize = iconSize * 0.08;
  ctx.fillStyle = darkenColor(primaryColor, 0.1);

  const corners = [
    { x: padding + decorSize, y: padding + decorSize },
    { x: width - padding - decorSize, y: padding + decorSize },
    { x: padding + decorSize, y: height - padding - decorSize },
    { x: width - padding - decorSize, y: height - padding - decorSize },
  ];

  corners.forEach((corner) => {
    ctx.beginPath();
    ctx.arc(corner.x, corner.y, decorSize / 2, 0, Math.PI * 2);
    ctx.fill();
  });
}
