import { RenderContext } from '../types';
import { lightenColor } from '../../utils/color';

export function renderGradient(context: RenderContext): void {
  const { ctx, config, width, height } = context;
  if (!ctx) return;

  const { text, primaryColor, secondaryColor, padding, borderRadius, showBackground, backgroundColor } = config;

  ctx.clearRect(0, 0, width, height);

  const bgGradient = ctx.createLinearGradient(padding, padding, width - padding, height - padding);
  bgGradient.addColorStop(0, primaryColor);
  bgGradient.addColorStop(0.5, secondaryColor);
  bgGradient.addColorStop(1, primaryColor);

  if (showBackground) {
    ctx.fillStyle = bgGradient;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.fill();

    ctx.shadowColor = primaryColor + '80';
    ctx.shadowBlur = 30;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 10;
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

  const textGradient = ctx.createLinearGradient(
    centerX - iconSize / 2,
    centerY - iconSize / 2,
    centerX + iconSize / 2,
    centerY + iconSize / 2
  );
  textGradient.addColorStop(0, '#ffffff');
  textGradient.addColorStop(1, lightenColor(secondaryColor, 0.3));

  ctx.fillStyle = showBackground ? textGradient : bgGradient;

  const displayText = text.substring(0, 2).toUpperCase();

  if (showBackground) {
    ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
    ctx.shadowBlur = 10;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 4;
  }
  ctx.fillText(displayText, centerX, centerY);
  ctx.shadowColor = 'transparent';

  const ringSize = iconSize * 0.35;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(centerX, centerY, ringSize, 0, Math.PI * 2);
  ctx.stroke();

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(centerX, centerY, ringSize * 1.3, 0, Math.PI * 2);
  ctx.stroke();

  const sparklePositions = [
    { x: centerX - ringSize * 0.7, y: centerY - ringSize * 0.7, size: 4 },
    { x: centerX + ringSize * 0.8, y: centerY - ringSize * 0.5, size: 3 },
    { x: centerX + ringSize * 0.5, y: centerY + ringSize * 0.8, size: 5 },
    { x: centerX - ringSize * 0.6, y: centerY + ringSize * 0.6, size: 3 },
  ];

  ctx.fillStyle = '#ffffff';
  sparklePositions.forEach((pos) => {
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, pos.size, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  if (showBackground) {
    const shineGradient = ctx.createLinearGradient(padding, padding, padding + 50, height - padding);
    shineGradient.addColorStop(0, 'rgba(255, 255, 255, 0)');
    shineGradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
    shineGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

    ctx.fillStyle = shineGradient;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.fill();
  }
}
