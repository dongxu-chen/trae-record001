import sharp from 'sharp';
import type { CardData, CardTemplate } from '../types/index.js';
import { renderLoop, renderTextBlock, isLoopLayout, type RenderElement } from './templateEngine.js';

const RARITY_SYMBOLS: Record<string, string> = {
  common: '☆',
  rare: '★',
  epic: '◆',
  legendary: '✦',
};

const ELEMENT_COLORS: Record<string, string> = {
  fire: '#e74c3c',
  water: '#3498db',
  earth: '#8b6914',
  wind: '#1abc9c',
  light: '#f1c40f',
  dark: '#9b59b6',
};

const TYPE_LABELS: Record<string, string> = {
  attack: '攻击',
  defense: '防御',
  magic: '魔法',
  support: '辅助',
};

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function buildBorderSvg(template: CardTemplate, w: number, h: number): string {
  const { borders, colors } = template;
  const bw = borders.width;
  const r = borders.radius;
  let svg = '';

  if (borders.style === 'double') {
    const outerPad = bw;
    const innerPad = bw * 2.5;
    svg += `<rect x="${outerPad}" y="${outerPad}" width="${w - outerPad * 2}" height="${h - outerPad * 2}" rx="${r}" ry="${r}" fill="none" stroke="${borders.color}" stroke-width="${bw}"/>`;
    svg += `<rect x="${innerPad}" y="${innerPad}" width="${w - innerPad * 2}" height="${h - innerPad * 2}" rx="${Math.max(r - 4, 0)}" ry="${Math.max(r - 4, 0)}" fill="none" stroke="${borders.color}" stroke-width="${bw * 0.7}"/>`;
  } else if (borders.style === 'ornate') {
    svg += `<rect x="${bw}" y="${bw}" width="${w - bw * 2}" height="${h - bw * 2}" rx="${r}" ry="${r}" fill="none" stroke="${borders.color}" stroke-width="${bw}"/>`;
    const cornerSize = 20;
    const positions = [
      [bw + 4, bw + 4],
      [w - bw - 4 - cornerSize, bw + 4],
      [bw + 4, h - bw - 4 - cornerSize],
      [w - bw - 4 - cornerSize, h - bw - 4 - cornerSize],
    ];
    for (const [cx, cy] of positions) {
      svg += `<rect x="${cx}" y="${cy}" width="${cornerSize}" height="${cornerSize}" fill="none" stroke="${borders.color}" stroke-width="1.5" rx="2"/>`;
      svg += `<line x1="${cx + 4}" y1="${cy + cornerSize / 2}" x2="${cx + cornerSize - 4}" y2="${cy + cornerSize / 2}" stroke="${borders.color}" stroke-width="1"/>`;
      svg += `<line x1="${cx + cornerSize / 2}" y1="${cy + 4}" x2="${cx + cornerSize / 2}" y2="${cy + cornerSize - 4}" stroke="${borders.color}" stroke-width="1"/>`;
    }
    svg += `<rect x="${bw * 2 + 6}" y="${bw * 2 + 6}" width="${w - (bw * 2 + 6) * 2}" height="${h - (bw * 2 + 6) * 2}" rx="${Math.max(r - 2, 0)}" ry="${Math.max(r - 2, 0)}" fill="none" stroke="${borders.color}" stroke-width="0.5" stroke-dasharray="4,4" opacity="0.5"/>`;
  } else {
    svg += `<rect x="${bw / 2}" y="${bw / 2}" width="${w - bw}" height="${h - bw}" rx="${r}" ry="${r}" fill="none" stroke="${borders.color}" stroke-width="${bw}"/>`;
  }

  return svg;
}

function buildGradientOverlay(w: number, h: number, bgColor: string): string {
  return `
    <defs>
      <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${bgColor}" stop-opacity="1"/>
        <stop offset="60%" stop-color="${bgColor}" stop-opacity="1"/>
        <stop offset="100%" stop-color="${bgColor}" stop-opacity="0.85"/>
      </linearGradient>
      <linearGradient id="headerGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="white" stop-opacity="0.08"/>
        <stop offset="100%" stop-color="white" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="footerGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="black" stop-opacity="0"/>
        <stop offset="100%" stop-color="black" stop-opacity="0.15"/>
      </linearGradient>
    </defs>
    <rect x="0" y="0" width="${w}" height="${h}" fill="url(#bgGrad)"/>
    <rect x="0" y="0" width="${w}" height="80" fill="url(#headerGrad)"/>
    <rect x="0" y="${h - 60}" width="${w}" height="60" fill="url(#footerGrad)"/>
  `;
}

function buildAttributeSvg(card: CardData, template: CardTemplate): string {
  const { layout, colors } = template;
  const attrs = card.attributes;
  let svg = '';

  const attrEntries: Array<{ key: string; value: number; label: string; x: number; y: number; fontSize: number; color: string; circle?: boolean }> = [
    { key: 'attack', value: attrs.attack, label: 'ATK', ...layout.attributes.attack },
    { key: 'defense', value: attrs.defense, label: 'DEF', ...layout.attributes.defense },
    { key: 'health', value: attrs.health, label: 'HP', ...layout.attributes.health },
    { key: 'cost', value: attrs.cost, label: 'COST', ...layout.attributes.cost },
  ];

  for (const attr of attrEntries) {
    const circleR = 16;
    const useCircle = attr.circle ?? true;
    if (useCircle) {
      svg += `<circle cx="${attr.x + 12}" cy="${attr.y - 4}" r="${circleR}" fill="${attr.color}" opacity="0.15"/>`;
      svg += `<circle cx="${attr.x + 12}" cy="${attr.y - 4}" r="${circleR}" fill="none" stroke="${attr.color}" stroke-width="1.5"/>`;
    }
    svg += `<text x="${attr.x + 12}" y="${attr.y + 1}" text-anchor="middle" font-size="${attr.fontSize}" font-weight="bold" fill="${attr.color}" font-family="sans-serif">${attr.value}</text>`;
    svg += `<text x="${attr.x + 12}" y="${attr.y + 14}" text-anchor="middle" font-size="8" fill="${colors.textSecondary}" font-family="sans-serif">${attr.label}</text>`;
  }

  return svg;
}

function renderElementsToSvg(elements: RenderElement[]): string {
  let svg = '';
  for (const el of elements) {
    if (el.type === 'text') {
      const d = el.data;
      const fontWeight = d.fontWeight !== 'normal' ? `font-weight="${d.fontWeight}"` : '';
      const fontStyle = d.fontStyle !== 'normal' ? `font-style="${d.fontStyle}"` : '';
      const textAnchor = d.textAnchor !== 'start' ? `text-anchor="${d.textAnchor}"` : '';
      svg += `<text x="${d.x}" y="${d.y}" font-size="${d.fontSize}" fill="${d.color}" font-family="${d.fontFamily}" ${fontWeight} ${fontStyle} ${textAnchor}>${escapeXml(d.text)}</text>`;
    } else if (el.type === 'line') {
      const d = el.data;
      const opacity = d.opacity !== undefined ? `opacity="${d.opacity}"` : '';
      svg += `<line x1="${d.x1}" y1="${d.y1}" x2="${d.x2}" y2="${d.y2}" stroke="${d.color}" stroke-width="${d.width}" ${opacity}/>`;
    } else if (el.type === 'circle') {
      const d = el.data;
      const opacity = d.opacity !== undefined ? `opacity="${d.opacity}"` : '';
      const fill = d.fill ? `fill="${d.fill}"` : 'fill="none"';
      const stroke = d.stroke ? `stroke="${d.stroke}" stroke-width="${d.strokeWidth || 1}"` : '';
      svg += `<circle cx="${d.cx}" cy="${d.cy}" r="${d.r}" ${fill} ${stroke} ${opacity}/>`;
    } else if (el.type === 'rect') {
      const d = el.data;
      const opacity = d.opacity !== undefined ? `opacity="${d.opacity}"` : '';
      const fill = d.fill ? `fill="${d.fill}"` : 'fill="none"';
      const stroke = d.stroke ? `stroke="${d.stroke}" stroke-width="${d.strokeWidth || 1}"` : '';
      const rx = d.rx !== undefined ? `rx="${d.rx}"` : '';
      svg += `<rect x="${d.x}" y="${d.y}" width="${d.width}" height="${d.height}" ${fill} ${stroke} ${rx} ${opacity}/>`;
    }
  }
  return svg;
}

function buildDynamicSvg(card: CardData, template: CardTemplate): string {
  const { layout, colors } = template;
  let svg = '';

  svg += `<text x="${layout.name.x}" y="${layout.name.y}" font-size="${layout.name.fontSize}" font-weight="${layout.name.fontWeight || 'bold'}" fill="${layout.name.color}" font-family="${layout.name.fontFamily || 'serif'}" text-anchor="${layout.name.textAnchor || 'start'}">${escapeXml(card.name)}</text>`;

  const typeLabel = TYPE_LABELS[card.type] || card.type;
  const elementLabel = card.element ? ` · ${card.element.toUpperCase()}` : '';
  svg += `<text x="${layout.type.x}" y="${layout.type.y}" font-size="${layout.type.fontSize}" fill="${layout.type.color}" font-family="sans-serif">${escapeXml(typeLabel)}${elementLabel}</text>`;

  const raritySymbol = RARITY_SYMBOLS[card.rarity] || '☆';
  const rarityColor = card.rarity === 'legendary' ? '#f39c12' : card.rarity === 'epic' ? '#9b59b6' : card.rarity === 'rare' ? '#3498db' : '#95a5a6';
  const rarityCount = card.rarity === 'legendary' ? 3 : card.rarity === 'epic' ? 2 : 1;
  svg += `<text x="${layout.rarity.x}" y="${layout.rarity.y + layout.rarity.iconSize * 0.7}" text-anchor="end" font-size="${layout.rarity.iconSize}" fill="${rarityColor}" font-family="sans-serif">${raritySymbol.repeat(rarityCount)}</text>`;

  if (card.element) {
    const elemColor = ELEMENT_COLORS[card.element] || colors.textSecondary;
    svg += `<circle cx="${layout.rarity.x - layout.rarity.iconSize * 2 - 12}" cy="${layout.rarity.y + layout.rarity.iconSize * 0.4}" r="6" fill="${elemColor}" opacity="0.3"/>`;
    svg += `<circle cx="${layout.rarity.x - layout.rarity.iconSize * 2 - 12}" cy="${layout.rarity.y + layout.rarity.iconSize * 0.4}" r="6" fill="none" stroke="${elemColor}" stroke-width="1"/>`;
  }

  if (isLoopLayout(layout.skills)) {
    const { elements } = renderLoop(card, layout.skills, colors.textSecondary, colors.primary);
    svg += renderElementsToSvg(elements);
  }

  const descResult = renderTextBlock(card.description, layout.description, 0, colors.text);
  svg += renderElementsToSvg(descResult.elements);

  if (card.flavorText && layout.flavorText) {
    const fontStyle = layout.flavorText.fontStyle || 'italic';
    const flavorResult = renderTextBlock(card.flavorText, layout.flavorText, 0, colors.textSecondary);
    svg += `<line x1="${layout.flavorText.x}" y1="${layout.flavorText.y - 10}" x2="${layout.flavorText.x + layout.flavorText.maxWidth}" y2="${layout.flavorText.y - 10}" stroke="${colors.divider}" stroke-width="0.5"/>`;
    for (const el of flavorResult.elements) {
      if (el.type === 'text') {
        svg += `<text x="${el.data.x}" y="${el.data.y}" font-size="${el.data.fontSize}" fill="${el.data.color}" font-family="${el.data.fontFamily}" font-style="${fontStyle}">${escapeXml(el.data.text)}</text>`;
      }
    }
  }

  return svg;
}

function buildCharacterAreaSvg(template: CardTemplate): string {
  const { layout, colors } = template;
  const charArea = layout.characterImage;
  let svg = '';

  svg += `<rect x="${charArea.x}" y="${charArea.y}" width="${charArea.width}" height="${charArea.height}" rx="6" ry="6" fill="${colors.cardBackground}" opacity="0.5"/>`;
  svg += `<rect x="${charArea.x}" y="${charArea.y}" width="${charArea.width}" height="${charArea.height}" rx="6" ry="6" fill="none" stroke="${colors.divider}" stroke-width="0.5"/>`;

  svg += `<text x="${charArea.x + charArea.width / 2}" y="${charArea.y + charArea.height / 2}" text-anchor="middle" font-size="14" fill="${colors.textSecondary}" font-family="sans-serif" opacity="0.5">CHARACTER</text>`;

  return svg;
}

export async function renderCard(card: CardData, template: CardTemplate, resolution: number = 1): Promise<Buffer> {
  const w = Math.round(template.width * resolution);
  const h = Math.round(template.height * resolution);
  const bgColor = template.colors.background;

  const baseImage = sharp({
    create: {
      width: w,
      height: h,
      channels: 4,
      background: bgColor,
    },
  });

  let overlaySvg = `<svg width="${template.width}" height="${template.height}" xmlns="http://www.w3.org/2000/svg">`;
  overlaySvg += buildGradientOverlay(template.width, template.height, bgColor);
  overlaySvg += buildCharacterAreaSvg(template);
  overlaySvg += buildBorderSvg(template, template.width, template.height);
  overlaySvg += buildDynamicSvg(card, template);
  overlaySvg += buildAttributeSvg(card, template);
  overlaySvg += '</svg>';

  const svgBuffer = Buffer.from(overlaySvg);

  let pipeline = baseImage.composite([{
    input: svgBuffer,
    density: 72 * resolution,
  }]);

  if (resolution !== 1) {
    pipeline = pipeline.resize(w, h, { kernel: 'lanczos3' });
  }

  return pipeline.png().toBuffer();
}
