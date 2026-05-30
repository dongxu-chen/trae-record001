import { RenderContext } from '../types';
import { darkenColor, lightenColor, hexToRgb } from '../../utils/color';

const LIGHT_ANGLE = Math.PI * 1.25;
const LIGHT_DIR_X = Math.cos(LIGHT_ANGLE);
const LIGHT_DIR_Y = Math.sin(LIGHT_ANGLE);

function computeLighting(
  nx: number,
  ny: number,
  ambientStrength: number,
  diffuseStrength: number,
  specularStrength: number,
  shininess: number
): { diffuse: number; specular: number } {
  const dotNL = -(nx * LIGHT_DIR_X + ny * LIGHT_DIR_Y);
  const diffuse = Math.max(0, dotNL) * diffuseStrength;

  const halfX = LIGHT_DIR_X;
  const halfY = LIGHT_DIR_Y + 1;
  const halfLen = Math.sqrt(halfX * halfX + halfY * halfY);
  const dotNH = -(nx * halfX / halfLen + ny * halfY / halfLen);
  const specular = Math.pow(Math.max(0, dotNH), shininess) * specularStrength;

  return { diffuse, specular };
}

function shadeColor(baseColor: string, diffuse: number, specular: number, ambient: number): string {
  const rgb = hexToRgb(baseColor);
  if (!rgb) return baseColor;

  const intensity = ambient + diffuse;
  const r = Math.min(255, Math.round(rgb.r * intensity + 255 * specular));
  const g = Math.min(255, Math.round(rgb.g * intensity + 255 * specular));
  const b = Math.min(255, Math.round(rgb.b * intensity + 255 * specular));

  return `rgb(${r},${g},${b})`;
}

export function render3D(context: RenderContext): void {
  const { ctx, config, width, height } = context;
  if (!ctx) return;

  const { text, primaryColor, secondaryColor, padding, borderRadius, showBackground } = config;

  ctx.clearRect(0, 0, width, height);

  const centerX = width / 2;
  const centerY = height / 2;
  const iconSize = Math.min(width, height) - padding * 2;
  const depth = iconSize * 0.1;

  const shadowOffsetX = -LIGHT_DIR_X * depth;
  const shadowOffsetY = -LIGHT_DIR_Y * depth;
  const highlightOffsetX = LIGHT_DIR_X * depth * 0.3;
  const highlightOffsetY = LIGHT_DIR_Y * depth * 0.3;

  if (showBackground) {
    ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
    ctx.shadowBlur = depth * 1.5;
    ctx.shadowOffsetX = shadowOffsetX;
    ctx.shadowOffsetY = shadowOffsetY;

    const bgNx = 0;
    const bgNy = -1;
    const bgLight = computeLighting(bgNx, bgNy, 0.6, 0.4, 0.15, 32);
    const bgTop = shadeColor(primaryColor, bgLight.diffuse, bgLight.specular, bgLight.diffuse > 0 ? 0.5 : 0.65);
    const bgBottom = shadeColor(darkenColor(primaryColor, 0.15), bgLight.diffuse * 0.5, 0, 0.7);

    const bgGradient = ctx.createLinearGradient(
      centerX + highlightOffsetX * 2,
      padding,
      centerX - highlightOffsetX * 2,
      height - padding
    );
    bgGradient.addColorStop(0, bgTop);
    bgGradient.addColorStop(1, bgBottom);

    ctx.fillStyle = bgGradient;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.fill();
    ctx.shadowColor = 'transparent';

    const edgeNx = -LIGHT_DIR_X;
    const edgeNy = 0;
    const edgeLight = computeLighting(edgeNx, edgeNy, 0, 0.3, 0.1, 16);
    const edgeAlpha = Math.max(0.05, edgeLight.diffuse * 0.4);

    const edgeGradient = ctx.createLinearGradient(
      padding + highlightOffsetX * 3,
      padding,
      width - padding - highlightOffsetX * 3,
      height - padding
    );
    edgeGradient.addColorStop(0, `rgba(255,255,255,${edgeAlpha + 0.2})`);
    edgeGradient.addColorStop(0.5, `rgba(255,255,255,0)`);
    edgeGradient.addColorStop(1, `rgba(0,0,0,0.08)`);

    ctx.strokeStyle = edgeGradient;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(padding / 2, padding / 2, width - padding, height - padding, borderRadius);
    ctx.stroke();
  }

  const fontSize = iconSize * 0.45;
  ctx.font = `bold ${fontSize}px 'Space Grotesk', 'Inter', sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const displayText = text.substring(0, 2).toUpperCase();

  const extrusionSteps = Math.max(1, Math.round(depth));
  for (let i = extrusionSteps; i >= 1; i--) {
    const t = i / extrusionSteps;
    const layerNx = 0;
    const layerNy = 1;
    const layerLight = computeLighting(layerNx, layerNy, 0.3, 0.15, 0, 1);
    const shade = shadeColor(primaryColor, layerLight.diffuse, 0, 0.25 + t * 0.15);

    ctx.globalAlpha = 0.9 - t * 0.2;
    ctx.fillStyle = shade;
    ctx.fillText(
      displayText,
      centerX + shadowOffsetX * t,
      centerY + shadowOffsetY * t
    );
  }
  ctx.globalAlpha = 1;

  const faceNx = 0;
  const faceNy = -1;
  const faceLight = computeLighting(faceNx, faceNy, 0.5, 0.45, 0.2, 64);

  const faceCenterColor = shadeColor(primaryColor, faceLight.diffuse, faceLight.specular, 0.5);
  const faceEdgeColor = shadeColor(primaryColor, faceLight.diffuse * 0.6, 0, 0.6);

  const faceGradient = ctx.createLinearGradient(
    centerX + highlightOffsetX * 3,
    centerY + highlightOffsetY * 3,
    centerX - highlightOffsetX * 3,
    centerY - highlightOffsetY * 3
  );
  faceGradient.addColorStop(0, lightenColor(faceCenterColor, 0.15));
  faceGradient.addColorStop(0.6, faceCenterColor);
  faceGradient.addColorStop(1, faceEdgeColor);

  ctx.fillStyle = showBackground ? faceGradient : faceGradient;
  ctx.fillText(displayText, centerX, centerY);

  if (faceLight.specular > 0.05) {
    ctx.globalAlpha = Math.min(0.5, faceLight.specular * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(displayText, centerX + highlightOffsetX * 0.3, centerY + highlightOffsetY * 0.3);
    ctx.globalAlpha = 1;
  }

  ctx.shadowColor = 'rgba(0, 0, 0, 0.25)';
  ctx.shadowBlur = depth * 0.8;
  ctx.shadowOffsetX = shadowOffsetX * 0.4;
  ctx.shadowOffsetY = shadowOffsetY * 0.4;

  const metrics = ctx.measureText(displayText);
  const textW = metrics.width;
  const textH = fontSize;

  ctx.fillStyle = 'rgba(0,0,0,0)';
  ctx.fillRect(
    centerX - textW / 2,
    centerY - textH / 2,
    textW,
    textH
  );
  ctx.shadowColor = 'transparent';

  if (showBackground) {
    const reflGradient = ctx.createLinearGradient(
      padding,
      padding,
      padding + Math.abs(highlightOffsetX) * 4,
      padding + (height - padding) * 0.35
    );
    reflGradient.addColorStop(0, `rgba(255,255,255,${Math.min(0.25, faceLight.specular + 0.1)})`);
    reflGradient.addColorStop(1, 'rgba(255,255,255,0)');

    ctx.fillStyle = reflGradient;
    ctx.beginPath();
    ctx.roundRect(
      padding / 2,
      padding / 2,
      width - padding,
      (height - padding) * 0.4,
      [borderRadius, borderRadius, 0, 0]
    );
    ctx.fill();
  }
}
