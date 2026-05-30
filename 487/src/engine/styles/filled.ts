import { RenderContext } from '../types';
import { darkenColor, lightenColor } from '../../utils/color';

export function renderFilled(context: RenderContext): void {
  const { ctx, config, width, height } = context;
  if (!ctx) return;

  const { text, primaryColor, padding, borderRadius, showBackground, backgroundColor } = config;

  ctx.clearRect(0, 0, width, height);

  const bgGradient = ctx.createLinearGradient(padding, padding, width - padding, height - padding);
  bgGradient.addColorStop(0, lightenColor(primaryColor, 0.2));
  bgGradient.addColorStop(1, darkenColor(primaryColor, 0.1));

  ctx.fillStyle = showBackground ? bgGradient : 'transparent';
  ctx.beginPath();
  ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
  ctx.fill();

  if (showBackground) {
    ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
    ctx.shadowBlur = 20;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 8;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.fill();
    ctx.shadowColor = 'transparent';
  }

  const centerX = width / 2;
  const centerY = height / 2;
  const iconSize = Math.min(width, height) - padding * 2;

  const fontSize = iconSize * 0.5;
  ctx.font = `bold ${fontSize}px 'Space Grotesk', 'Inter', sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const textColor = showBackground ? '#ffffff' : primaryColor;
  ctx.fillStyle = textColor;

  const displayText = text.substring(0, 2).toUpperCase();

  ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
  ctx.shadowBlur = 4;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = 2;
  ctx.fillText(displayText, centerX, centerY);
  ctx.shadowColor = 'transparent';

  const decorRadius = iconSize * 0.15;
  ctx.globalAlpha = 0.15;
  ctx.fillStyle = '#ffffff';

  ctx.beginPath();
  ctx.arc(width - padding - decorRadius * 0.5, padding + decorRadius * 0.5, decorRadius, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.arc(padding + decorRadius * 0.3, height - padding - decorRadius * 0.3, decorRadius * 0.6, 0, Math.PI * 2);
  ctx.fill();

  ctx.globalAlpha = 1;

  if (showBackground) {
    ctx.globalAlpha = 0.3;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(padding + 8, padding + 8, width - padding * 2 - 16, height - padding * 2 - 16, borderRadius - 8);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}
