import type { CardData, CardTemplate } from '@/types';
import { renderLoop, renderTextBlock, isLoopLayout } from '@/utils/templateEngine';

const RARITY_COLORS: Record<string, string> = {
  common: '#888888',
  rare: '#4488ff',
  epic: '#aa44ff',
  legendary: '#ff8800',
};

const TYPE_LABELS: Record<string, string> = {
  attack: '⚔ 攻击',
  defense: '🛡 防御',
  magic: '✦ 魔法',
  support: '♥ 辅助',
};

const ELEMENT_SYMBOLS: Record<string, string> = {
  fire: '🔥',
  water: '💧',
  earth: '⛰',
  wind: '🌪',
  light: '☀',
  dark: '🌙',
};

export function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
): number {
  const lines: string[] = [];
  let currentLine = '';

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '\n') {
      lines.push(currentLine);
      currentLine = '';
      continue;
    }
    const testLine = currentLine + char;
    const metrics = ctx.measureText(testLine);
    if (metrics.width > maxWidth && currentLine.length > 0) {
      lines.push(currentLine);
      currentLine = char;
    } else {
      currentLine = testLine;
    }
  }
  if (currentLine) lines.push(currentLine);

  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], x, y + i * lineHeight);
  }

  return lines.length * lineHeight;
}

export function drawOrnateBorder(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  color: string,
  style: 'solid' | 'double' | 'ornate',
): void {
  ctx.strokeStyle = color;

  if (style === 'solid') {
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
  } else if (style === 'double') {
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 4, y + 4, w - 8, h - 8);
  } else if (style === 'ornate') {
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 4, y + 4, w - 8, h - 8);

    const cornerSize = 12;
    ctx.fillStyle = color;
    const corners = [
      [x, y],
      [x + w, y],
      [x, y + h],
      [x + w, y + h],
    ];
    for (const [cx, cy] of corners) {
      ctx.beginPath();
      ctx.arc(cx, cy, cornerSize / 2, 0, Math.PI * 2);
      ctx.fill();
    }

    const midX = x + w / 2;
    const midY = y + h / 2;
    ctx.beginPath();
    ctx.moveTo(midX - 8, y);
    ctx.lineTo(midX, y - 6);
    ctx.lineTo(midX + 8, y);
    ctx.closePath();
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(midX - 8, y + h);
    ctx.lineTo(midX, y + h + 6);
    ctx.lineTo(midX + 8, y + h);
    ctx.closePath();
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(x, midY - 8);
    ctx.lineTo(x - 6, midY);
    ctx.lineTo(x, midY + 8);
    ctx.closePath();
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(x + w, midY - 8);
    ctx.lineTo(x + w + 6, midY);
    ctx.lineTo(x + w, midY + 8);
    ctx.closePath();
    ctx.fill();
  }
}

export function renderCardToCanvas(
  canvas: HTMLCanvasElement,
  cardData: CardData,
  template: CardTemplate,
): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const W = canvas.width;
  const H = canvas.height;
  const scale = W / (template.width || 400);
  const { colors, borders, layout } = template;

  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.scale(scale, scale);

  const tW = template.width || 400;
  const tH = template.height || 560;

  const bgGrad = ctx.createLinearGradient(0, 0, 0, tH);
  bgGrad.addColorStop(0, colors.background || '#1a1a2e');
  bgGrad.addColorStop(0.5, colors.secondary || '#16213e');
  bgGrad.addColorStop(1, colors.background || '#1a1a2e');
  ctx.fillStyle = bgGrad;

  if (borders.radius > 0) {
    roundRect(ctx, 0, 0, tW, tH, borders.radius);
    ctx.fill();
  } else {
    ctx.fillRect(0, 0, tW, tH);
  }

  const innerPad = borders.width + 6;
  const innerGrad = ctx.createLinearGradient(0, 0, 0, tH * 0.3);
  innerGrad.addColorStop(0, colors.primary || '#1a1a2e');
  innerGrad.addColorStop(1, colors.secondary || '#16213e');
  ctx.fillStyle = innerGrad;
  if (borders.radius > 0) {
    roundRect(ctx, innerPad, innerPad, tW - innerPad * 2, tH * 0.35, Math.max(0, borders.radius - 4));
    ctx.fill();
  } else {
    ctx.fillRect(innerPad, innerPad, tW - innerPad * 2, tH * 0.35);
  }

  drawOrnateBorder(ctx, borders.width / 2, borders.width / 2, tW - borders.width, tH - borders.width, borders.color, borders.style);

  const nameLayout = layout.name;
  ctx.font = `${nameLayout.fontWeight || 'bold'} ${nameLayout.fontSize}px ${nameLayout.fontFamily || 'Cinzel, serif'}`;
  ctx.fillStyle = nameLayout.color || colors.text || '#e0d6c2';
  ctx.textAlign = (nameLayout.textAnchor as CanvasTextAlign) || 'center';
  ctx.fillText(cardData.name || '未命名', nameLayout.textAnchor === 'middle' ? tW / 2 : nameLayout.x, nameLayout.y);

  const typeLayout = layout.type;
  ctx.font = `${typeLayout.fontSize}px Crimson Text, serif`;
  ctx.fillStyle = typeLayout.color || colors.accent || '#d4a853';
  ctx.textAlign = (typeLayout.textAnchor as CanvasTextAlign) || 'center';
  ctx.fillText(TYPE_LABELS[cardData.type] || cardData.type, typeLayout.textAnchor === 'middle' ? tW / 2 : typeLayout.x, typeLayout.y);

  const rarityColor = RARITY_COLORS[cardData.rarity] || '#888888';
  const rarityLabels: Record<string, string> = { common: '★ 普通', rare: '★ 稀有', epic: '★ 史诗', legendary: '★ 传说' };

  ctx.font = `${(layout.rarity.iconSize || 14) - 2}px Rajdhani, sans-serif`;
  ctx.fillStyle = rarityColor;
  ctx.textAlign = 'right';
  ctx.fillText(rarityLabels[cardData.rarity] || cardData.rarity, tW - innerPad - 8, layout.rarity.y);
  ctx.beginPath();
  ctx.arc(tW - innerPad - ctx.measureText(rarityLabels[cardData.rarity] || cardData.rarity).width - 16, layout.rarity.y - 4, 5, 0, Math.PI * 2);
  ctx.fillStyle = rarityColor;
  ctx.fill();
  ctx.strokeStyle = colors.text || '#e0d6c2';
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.textAlign = 'left';

  const attrs = cardData.attributes;
  const attrLayout = layout.attributes;

  const attrItems = [
    { layout: attrLayout.attack, icon: '⚔', value: attrs.attack },
    { layout: attrLayout.defense, icon: '🛡', value: attrs.defense },
    { layout: attrLayout.health, icon: '♥', value: attrs.health },
    { layout: attrLayout.cost, icon: '◈', value: attrs.cost },
  ];

  for (const attr of attrItems) {
    const al = attr.layout;
    const circleR = 16;
    const useCircle = al.circle ?? true;
    if (useCircle) {
      ctx.beginPath();
      ctx.arc(al.x + 12, al.y - 4, circleR, 0, Math.PI * 2);
      ctx.fillStyle = al.color + '26';
      ctx.fill();
      ctx.strokeStyle = al.color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    ctx.font = `${al.fontSize - 2}px sans-serif`;
    ctx.fillStyle = colors.text || '#e0d6c2';
    ctx.fillText(al.icon || attr.icon, al.x, al.y);
    ctx.font = `bold ${al.fontSize}px Rajdhani, sans-serif`;
    ctx.fillStyle = al.color || colors.text || '#e0d6c2';
    ctx.fillText(String(attr.value), al.x + 18, al.y);
  }

  if (isLoopLayout(layout.skills)) {
    renderLoop(ctx, cardData, layout.skills, colors.textSecondary || '#a89b8c', colors.primary || '#d4a853');
  } else {
    ctx.font = `600 ${layout.skills.fontSize}px Cinzel, serif`;
    ctx.fillStyle = colors.accent || '#d4a853';
    let skillY = layout.skills.y;

    for (const skill of cardData.skills) {
      ctx.fillText(`◆ ${skill.name}`, layout.skills.x, skillY);
      skillY += layout.skills.fontSize + 4;
      if (skill.description) {
        ctx.font = `${layout.skills.fontSize - 2}px Crimson Text, serif`;
        ctx.fillStyle = colors.text || '#e0d6c2';
        const linesUsed = wrapText(ctx, skill.description, layout.skills.x + 12, skillY, layout.skills.maxWidth, layout.skills.lineHeight || layout.skills.fontSize + 2);
        skillY += linesUsed + 4;
      }
      ctx.fillStyle = colors.accent || '#d4a853';
      ctx.font = `600 ${layout.skills.fontSize}px Cinzel, serif`;
    }
  }

  if (cardData.description) {
    const descLayout = layout.description;
    ctx.font = `${descLayout.fontSize}px Crimson Text, serif`;
    ctx.fillStyle = colors.text || '#e0d6c2';
    ctx.textAlign = 'left';
    renderTextBlock(ctx, cardData.description, descLayout, 0, colors.text);
  }

  if (cardData.flavorText) {
    const flavorLayout = layout.flavorText;
    ctx.font = `italic ${flavorLayout.fontSize}px Crimson Text, serif`;
    ctx.fillStyle = colors.accent || '#d4a853';
    ctx.textAlign = 'left';
    renderTextBlock(ctx, `"${cardData.flavorText}"`, flavorLayout, 0, colors.textSecondary);
  }

  if (cardData.element) {
    ctx.font = '20px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(ELEMENT_SYMBOLS[cardData.element] || '', tW - innerPad - 8, layout.type.y);
    ctx.textAlign = 'left';
  }

  ctx.restore();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
