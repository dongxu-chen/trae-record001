import type { CardData, LoopItemLayout, BlockLayout, TextLayout } from '../types/index.js';

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

function wrapTextToLines(text: string, maxWidth: number, fontSize: number): string[] {
  const charWidth = fontSize * 0.6;
  const maxChars = Math.floor(maxWidth / charWidth);
  const lines: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      lines.push(remaining);
      break;
    }
    let breakIndex = remaining.lastIndexOf(' ', maxChars);
    if (breakIndex <= 0) breakIndex = maxChars;
    lines.push(remaining.substring(0, breakIndex));
    remaining = remaining.substring(breakIndex).trimStart();
  }

  return lines;
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
  text: string,
  layout: BlockLayout,
  yOffset: number = 0,
  colorOverride?: string
): { elements: RenderElement[]; height: number } {
  const elements: RenderElement[] = [];
  const lines = wrapTextToLines(text, layout.maxWidth, layout.fontSize);
  let currentY = layout.y + yOffset;
  const color = colorOverride || layout.color || '#000000';

  for (const line of lines) {
    elements.push({
      type: 'text',
      data: {
        text: (layout.prefix || '') + line,
        x: layout.x,
        y: currentY,
        fontSize: layout.fontSize,
        color,
        fontFamily: layout.fontFamily || 'sans-serif',
        fontWeight: 'normal',
        fontStyle: layout.fontStyle || 'normal',
        textAnchor: 'start',
      },
    });
    currentY += layout.lineHeight;
  }

  return { elements, height: (lines.length - 1) * layout.lineHeight };
}

export function renderLoop(
  cardData: CardData,
  layout: LoopItemLayout,
  textColor?: string,
  titleColor?: string
): { elements: RenderElement[]; height: number } {
  const elements: RenderElement[] = [];
  const array = getNestedValue(cardData, layout.arrayPath) as any[];
  
  if (!Array.isArray(array) || array.length === 0) {
    return { elements, height: 0 };
  }

  const maxItems = layout.maxItems ?? array.length;
  const items = array.slice(0, maxItems);
  let currentY = layout.startY;

  if (layout.headerLine) {
    elements.push({
      type: 'line',
      data: {
        x1: layout.itemLayout.title.x,
        y1: currentY - 10,
        x2: layout.itemLayout.title.x + 340,
        y2: currentY - 10,
        color: titleColor || '#d4a853',
        width: 0.5,
        opacity: 0.3,
      },
    });
  }

  const indent = layout.itemLayout.indent || 0;

  for (let i = 0; i < items.length; i++) {
    const item = items[i];

    const titleLayout = applyTextLayoutDefaults(layout.itemLayout.title, {
      x: layout.itemLayout.title.x,
      y: currentY,
    });

    elements.push({
      type: 'text',
      data: {
        text: (titleLayout.prefix || '') + (item.name || item.title || ''),
        x: titleLayout.x,
        y: titleLayout.y,
        fontSize: titleLayout.fontSize,
        color: titleColor || titleLayout.color,
        fontFamily: titleLayout.fontFamily,
        fontWeight: titleLayout.fontWeight,
        fontStyle: titleLayout.fontStyle,
        textAnchor: titleLayout.textAnchor,
      },
    });

    if (item.description && layout.itemLayout.description) {
      const descLayout = applyTextLayoutDefaults(layout.itemLayout.description, {
        x: layout.itemLayout.description.x + indent,
        y: currentY + layout.itemLayout.title.fontSize + 4,
      });

      const descText = item.description || '';
      const descLines = wrapTextToLines(descText, descLayout.fontSize, layout.itemLayout.description.fontSize);

      let descY = descLayout.y;
      for (const line of descLines) {
        elements.push({
          type: 'text',
          data: {
            text: line,
            x: descLayout.x,
            y: descY,
            fontSize: descLayout.fontSize,
            color: textColor || descLayout.color,
            fontFamily: descLayout.fontFamily,
            fontWeight: descLayout.fontWeight,
            fontStyle: descLayout.fontStyle,
            textAnchor: descLayout.textAnchor,
          },
        });
        descY += descLayout.fontSize + 4;
      }

      currentY = descY + layout.itemSpacing;
    } else {
      currentY += layout.itemLayout.title.fontSize + layout.itemSpacing;
    }

    if (layout.separator && i < items.length - 1) {
      elements.push({
        type: 'line',
        data: {
          x1: layout.itemLayout.title.x + indent,
          y1: currentY - layout.itemSpacing / 2,
          x2: layout.itemLayout.title.x + 340,
          y2: currentY - layout.itemSpacing / 2,
          color: textColor || '#888888',
          width: 0.5,
          opacity: 0.2,
        },
      });
    }
  }

  const totalHeight = currentY - layout.startY;
  return { elements, height: totalHeight };
}

export function isLoopLayout(layout: any): layout is LoopItemLayout {
  return layout?.type === 'loop';
}
