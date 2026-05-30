import { hyphenate } from 'hyphen/en';

const SOFT_HYPHEN = '\u00AD';

export async function hyphenateText(text: string): Promise<string> {
  try {
    return await hyphenate(text, { hyphenChar: SOFT_HYPHEN });
  } catch {
    return text;
  }
}

export interface WrapResult {
  lines: string[];
  lineWidths: number[];
}

export function wrapTextWithHyphenation(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): WrapResult {
  const words = text.split(/(\s+)/);
  const lines: string[] = [];
  const lineWidths: number[] = [];
  let currentLine = '';
  let currentWidth = 0;

  for (const word of words) {
    if (!word) continue;

    const wordWidth = ctx.measureText(word).width;
    const spaceWidth = currentLine ? ctx.measureText(' ').width : 0;
    const totalWidth = currentWidth + spaceWidth + wordWidth;

    if (totalWidth <= maxWidth || !currentLine) {
      if (currentLine && word !== ' ') {
        currentLine += ' ';
        currentWidth += spaceWidth;
      }
      if (word !== ' ') {
        currentLine += word;
        currentWidth += wordWidth;
      }
    } else {
      if (word.length > 10 && word.includes(SOFT_HYPHEN)) {
        const parts = word.split(SOFT_HYPHEN);
        let partialWord = '';
        let partialWidth = 0;

        for (let i = 0; i < parts.length; i++) {
          const part = parts[i] + (i < parts.length - 1 ? '-' : '');
          const partWidth = ctx.measureText(part).width;
          const testWidth = currentWidth + spaceWidth + partialWidth + partWidth;

          if (testWidth <= maxWidth || i === 0) {
            partialWord += part;
            partialWidth += partWidth;
          } else {
            if (partialWord) {
              lines.push(currentLine + (currentLine ? ' ' : '') + partialWord);
              lineWidths.push(currentWidth + spaceWidth + partialWidth);
              currentLine = parts.slice(i).join('');
              currentWidth = ctx.measureText(currentLine).width;
            } else {
              lines.push(currentLine);
              lineWidths.push(currentWidth);
              currentLine = word;
              currentWidth = wordWidth;
            }
            break;
          }

          if (i === parts.length - 1) {
            currentLine += (currentLine ? ' ' : '') + partialWord;
            currentWidth += spaceWidth + partialWidth;
          }
        }
      } else if (wordWidth > maxWidth && !word.includes(SOFT_HYPHEN)) {
        if (currentLine) {
          lines.push(currentLine);
          lineWidths.push(currentWidth);
        }

        let remaining = word;
        while (remaining.length > 0) {
          let low = 0;
          let high = remaining.length;
          let best = 0;

          while (low <= high) {
            const mid = Math.floor((low + high) / 2);
            const testStr = remaining.slice(0, mid) + (mid < remaining.length ? '-' : '');
            const testWidth = ctx.measureText(testStr).width;

            if (testWidth <= maxWidth) {
              best = mid;
              low = mid + 1;
            } else {
              high = mid - 1;
            }
          }

          if (best === 0) {
            best = 1;
          }

          const isLast = best >= remaining.length;
          const linePart = remaining.slice(0, best) + (isLast ? '' : '-');
          lines.push(linePart);
          lineWidths.push(ctx.measureText(linePart).width);
          remaining = remaining.slice(best);
        }

        currentLine = '';
        currentWidth = 0;
      } else {
        lines.push(currentLine);
        lineWidths.push(currentWidth);
        currentLine = word;
        currentWidth = wordWidth;
      }
    }
  }

  if (currentLine) {
    lines.push(currentLine);
    lineWidths.push(currentWidth);
  }

  return { lines, lineWidths };
}

export function wrapTextSimple(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): WrapResult {
  const words = text.split(' ');
  const lines: string[] = [];
  const lineWidths: number[] = [];
  let currentLine = '';
  let currentWidth = 0;

  for (const word of words) {
    const testLine = currentLine ? currentLine + ' ' + word : word;
    const testWidth = ctx.measureText(testLine).width;

    if (testWidth <= maxWidth || currentLine === '') {
      currentLine = testLine;
      currentWidth = testWidth;
    } else {
      lines.push(currentLine);
      lineWidths.push(currentWidth);
      currentLine = word;
      currentWidth = ctx.measureText(word).width;
    }
  }

  if (currentLine) {
    lines.push(currentLine);
    lineWidths.push(currentWidth);
  }

  return { lines, lineWidths };
}
