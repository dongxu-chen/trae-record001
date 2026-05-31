import type { CardData, LoopItemLayout, BlockLayout, TextLayout } from '@/types';

export interface RenderTextItem {
  text: string;
  x: number;
  y: number;
  fontSize: number;
  color: string;
  fontFamily: string;
  fontWeight: string | number;
  fontStyle: string;
  textAnchor: 'start' | 'middle' | 'end';
  prefix?: string;
}

export interface RenderLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  width: number;
  opacity?: number;
}

export interface RenderCircle {
  cx: number;
  cy: number;
  r: number;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  opacity?: number;
}

export interface RenderRect {
  x: number;
  y: number;
  width: number;
  height: number;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  rx?: number;
  opacity?: number;
}

export type RenderElement = 
  | { type: 'text'; data: RenderTextItem }
  | { type: 'line'; data: RenderLine }
  | { type: 'circle'; data: RenderCircle }
  | { type: 'rect'; data: RenderRect };

function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((acc, key) => acc?.[key], obj);
}

function applyTextLayoutDefaults(
  layout: Partial<TextLayout>,
  defaults: Partial<TextLayout> = {}
): TextLayout {
  return {
    x: 0,
    y: 0,
    fontSize: 12,
    color: '#000000',
    fontFamily: 'sans-serif',
    fontWeight: 'normal',
    fontStyle: 'normal',
    textAnchor: 'start' as const,
    ...defaults,
    ...layout,
  };
}

export function renderTextBlock(
  ctx: CanvasRenderingContext2D,
  text: string,
  layout: BlockLayout,
  yOffset: number = 0,
  colorOverride?: string
): number {
  const lines: string[] = [];
  let currentLine = '';
  const maxWidth = layout.maxWidth;
  const lineHeight = layout.lineHeight;

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

  let currentY = layout.y + yOffset;
  const color = colorOverride || layout.color || '#000000';
  const fontFamily = layout.fontFamily || 'sans-serif';
  const fontStyle = layout.fontStyle || 'normal';

  ctx.font = `${fontStyle} ${layout.fontSize}px ${fontFamily}`;
  ctx.fillStyle = color;

  for (const line of lines) {
    ctx.fillText((layout.prefix || '') + line, layout.x, currentY);
    currentY += lineHeight;
  }

  return (lines.length - 1) * lineHeight;
}

export function renderLoop(
  ctx: CanvasRenderingContext2D,
  cardData: CardData,
  layout: LoopItemLayout,
  textColor?: string,
  titleColor?: string
): number {
  const array = getNestedValue(cardData, layout.arrayPath) as any[];
  
  if (!Array.isArray(array) || array.length === 0) {
    return 0;
  }

  const maxItems = layout.maxItems ?? array.length;
  const items = array.slice(0, maxItems);
  let currentY = layout.startY;
  const indent = layout.itemLayout.indent || 0;

  if (layout.headerLine) {
    ctx.strokeStyle = (titleColor || '#d4a853') + '4d';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(layout.itemLayout.title.x, currentY - 10);
    ctx.lineTo(layout.itemLayout.title.x + 340, currentY - 10);
    ctx.stroke();
  }

  for (let i = 0; i < items.length; i++) {
    const item = items[i];

    const titleLayout = applyTextLayoutDefaults(layout.itemLayout.title, {
      x: layout.itemLayout.title.x,
      y: currentY,
    });

    ctx.font = `${titleLayout.fontStyle} ${titleLayout.fontWeight} ${titleLayout.fontSize}px ${titleLayout.fontFamily}`;
    ctx.fillStyle = titleColor || titleLayout.color;
    ctx.textAlign = titleLayout.textAnchor as CanvasTextAlign;
    ctx.fillText((titleLayout.prefix || '') + (item.name || item.title || ''), titleLayout.x, titleLayout.y);

    if (item.description && layout.itemLayout.description) {
      const descLayout = applyTextLayoutDefaults(layout.itemLayout.description, {
        x: layout.itemLayout.description.x + indent,
        y: currentY + layout.itemLayout.title.fontSize + 4,
      });

      ctx.font = `${descLayout.fontStyle} ${descLayout.fontWeight} ${descLayout.fontSize}px ${descLayout.fontFamily}`;
      ctx.fillStyle = textColor || descLayout.color;
      ctx.textAlign = descLayout.textAnchor as CanvasTextAlign;

      const lines: string[] = [];
      let currentLine = '';
      for (let j = 0; j < item.description.length; j++) {
        const char = item.description[j];
        const testLine = currentLine + char;
        const metrics = ctx.measureText(testLine);
        if (metrics.width > descLayout.fontSize * 32 && currentLine.length > 0) {
          lines.push(currentLine);
          currentLine = char;
        } else {
          currentLine = testLine;
        }
      }
      if (currentLine) lines.push(currentLine);

      let descY = descLayout.y;
      for (const line of lines) {
        ctx.fillText(line, descLayout.x, descY);
        descY += descLayout.fontSize + 4;
      }

      currentY = descY + layout.itemSpacing;
    } else {
      currentY += layout.itemLayout.title.fontSize + layout.itemSpacing;
    }

    if (layout.separator && i < items.length - 1) {
      ctx.strokeStyle = (textColor || '#888888') + '33';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(layout.itemLayout.title.x + indent, currentY - layout.itemSpacing / 2);
      ctx.lineTo(layout.itemLayout.title.x + 340, currentY - layout.itemSpacing / 2);
      ctx.stroke();
    }
  }

  return currentY - layout.startY;
}

export function isLoopLayout(layout: any): layout is LoopItemLayout {
  return layout?.type === 'loop';
}
