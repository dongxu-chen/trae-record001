import sharp from 'sharp';
import PDFDocument from 'pdfkit';
import archiver from 'archiver';
import { Writable } from 'stream';
import * as cardService from './cardService.js';
import * as templateService from './templateService.js';
import { renderCard } from './renderService.js';
import { promisePoolWithProgress, DEFAULT_CONCURRENCY } from '../utils/promisePool.js';
import type { CardData, PrintLayoutOptions } from '../types/index.js';

const PAPER_SIZES: Record<string, Record<string, [number, number]>> = {
  A4: { portrait: [595.28, 841.89], landscape: [841.89, 595.28] },
  A3: { portrait: [841.89, 1190.55], landscape: [1190.55, 841.89] },
  Letter: { portrait: [612, 792], landscape: [792, 612] },
};

const PRINT_DPI = 300;
const POINTS_PER_INCH = 72;
const DPI_SCALE = PRINT_DPI / POINTS_PER_INCH;

export async function exportCardAsImage(cardId: string, format: string = 'png', resolution: number = 1): Promise<Buffer> {
  const card = await cardService.getCard(cardId);
  if (!card) throw new Error(`Card not found: ${cardId}`);

  const template = await templateService.getTemplate(card.templateId);
  if (!template) throw new Error(`Template not found: ${card.templateId}`);

  const pngBuffer = await renderCard(card, template, resolution);

  if (format === 'jpg' || format === 'jpeg') {
    return sharp(pngBuffer).jpeg({ quality: 95 }).toBuffer();
  }
  if (format === 'webp') {
    return sharp(pngBuffer).webp({ quality: 95 }).toBuffer();
  }

  return pngBuffer;
}

export async function exportBatchAsZip(
  cardIds: string[],
  format: string = 'png',
  resolution: number = 1,
  onProgress?: (completed: number, total: number) => void
): Promise<Buffer> {
  const chunks: Buffer[] = [];

  const writable = new Writable({
    write(chunk, _encoding, callback) {
      chunks.push(chunk);
      callback();
    },
  });

  const archive = archiver('zip', { zlib: { level: 9 } });
  archive.pipe(writable);

  await promisePoolWithProgress(
    cardIds,
    async (cardId) => {
      try {
        const card = await cardService.getCard(cardId);
        if (!card) return;
        const imageBuffer = await exportCardAsImage(cardId, format, resolution);
        const ext = format === 'jpeg' ? 'jpg' : format;
        const safeName = card.name.replace(/[^a-zA-Z0-9\u4e00-\u9fa5-_]/g, '_') || card.id;
        archive.append(imageBuffer, { name: `${safeName}_${card.id.substring(0, 8)}.${ext}` });
      } catch {
        // Skip failed cards
      }
    },
    DEFAULT_CONCURRENCY,
    onProgress
  );

  await archive.finalize();

  return Buffer.concat(chunks);
}

export async function batchGenerateCards(
  cards: Array<Partial<CardData> & { name: string; templateId: string }>,
  onProgress?: (completed: number, total: number) => void
): Promise<CardData[]> {
  const results: CardData[] = [];

  await promisePoolWithProgress(
    cards,
    async (cardData, index) => {
      const card = await cardService.createCard({
        ...cardData,
        id: cardData.id || crypto.randomUUID(),
        type: cardData.type || 'attack',
        rarity: cardData.rarity || 'common',
        element: cardData.element || 'fire',
        attributes: cardData.attributes || { attack: 5, defense: 5, health: 10, cost: 3 },
        skills: cardData.skills || [],
        description: cardData.description || '',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      } as CardData);
      results[index] = card;
      return card;
    },
    DEFAULT_CONCURRENCY,
    onProgress
  );

  return results.filter(Boolean);
}

export async function exportAsPdf(
  printOptions: PrintLayoutOptions,
  onProgress?: (completed: number, total: number) => void
): Promise<Buffer> {
  const cardIds = printOptions.cardIds || [];
  const cards: CardData[] = [];

  for (const cardId of cardIds) {
    const card = await cardService.getCard(cardId);
    if (card) cards.push(card);
  }

  if (cards.length === 0) throw new Error('No valid cards to export');

  const [pageWidth, pageHeight] = PAPER_SIZES[printOptions.paperSize]?.[printOptions.orientation] || PAPER_SIZES.A4.portrait;
  const margin = printOptions.margin;
  const bleed = printOptions.bleed;
  const cols = printOptions.columns;
  const rows = printOptions.rows;

  const availWidth = pageWidth - margin * 2;
  const availHeight = pageHeight - margin * 2;
  const cellWidth = availWidth / cols;
  const cellHeight = availHeight / rows;

  const doc = new PDFDocument({
    size: [pageWidth, pageHeight],
    margin: 0,
    autoFirstPage: false,
    info: {
      Title: 'Card Forge - Print Sheet',
      Producer: 'Card Forge Generator',
      Creator: 'Card Forge',
    },
  });

  const chunks: Buffer[] = [];
  const writable = new Writable({
    write(chunk, _encoding, callback) {
      chunks.push(chunk);
      callback();
    },
  });

  doc.pipe(writable);

  let cardIndex = 0;
  const cardsPerPage = cols * rows;
  const totalPages = Math.ceil(cards.length / cardsPerPage);

  const cardImages: Buffer[] = await promisePoolWithProgress(
    cards,
    async (card) => {
      const template = await templateService.getTemplate(card.templateId);
      if (!template) return Buffer.alloc(0);
      return renderCard(card, template, DPI_SCALE);
    },
    DEFAULT_CONCURRENCY,
    onProgress
  );

  while (cardIndex < cards.length) {
    doc.addPage({ size: [pageWidth, pageHeight], margin: 0 });

    if (printOptions.cropMarks) {
      doc.strokeColor('#999999').lineWidth(0.5);
      for (let r = 0; r <= rows; r++) {
        const y = margin + r * cellHeight;
        doc.moveTo(margin - 10, y).lineTo(margin - 3, y).stroke();
        doc.moveTo(margin + availWidth + 3, y).lineTo(margin + availWidth + 10, y).stroke();
      }
      for (let c = 0; c <= cols; c++) {
        const x = margin + c * cellWidth;
        doc.moveTo(x, margin - 10).lineTo(x, margin - 3).stroke();
        doc.moveTo(x, margin + availHeight + 3).lineTo(x, margin + availHeight + 10).stroke();
      }

      for (let r = 0; r <= rows; r++) {
        for (let c = 0; c <= cols; c++) {
          const x = margin + c * cellWidth;
          const y = margin + r * cellHeight;
          if (bleed > 0) {
            doc.strokeColor('#cccccc').lineWidth(0.3).opacity(0.5);
            doc.rect(x - bleed, y - bleed, cellWidth + bleed * 2, cellHeight + bleed * 2).stroke();
            doc.opacity(1);
          }
        }
      }
    }

    for (let r = 0; r < rows && cardIndex < cards.length; r++) {
      for (let c = 0; c < cols && cardIndex < cards.length; c++) {
        const imageBuffer = cardImages[cardIndex];
        if (imageBuffer.length === 0) {
          cardIndex++;
          continue;
        }

        const x = margin + c * cellWidth + bleed;
        const y = margin + r * cellHeight + bleed;
        const imgW = cellWidth - bleed * 2;
        const imgH = cellHeight - bleed * 2;

        try {
          doc.image(imageBuffer, x, y, { width: imgW, height: imgH });
        } catch {
          doc.fillColor('#eeeeee').rect(x, y, imgW, imgH).fill();
          doc.fillColor('#999999').fontSize(8).text('渲染失败', x + imgW / 2 - 20, y + imgH / 2, { width: 40, align: 'center' });
        }
        cardIndex++;
      }
    }

    if (totalPages > 1) {
      const currentPage = Math.floor((cardIndex - 1) / cardsPerPage) + 1;
      doc.fillColor('#999999').fontSize(8).text(
        `第 ${currentPage} / ${totalPages} 页 · Card Forge`,
        margin,
        pageHeight - margin + 12,
        { width: pageWidth - margin * 2, align: 'center' }
      );
    }
  }

  doc.end();

  return new Promise((resolve, reject) => {
    writable.on('finish', () => resolve(Buffer.concat(chunks)));
    writable.on('error', reject);
  });
}

export async function exportAsJson(cardIds: string[]): Promise<string> {
  const cards: CardData[] = [];
  for (const cardId of cardIds) {
    const card = await cardService.getCard(cardId);
    if (card) cards.push(card);
  }
  return JSON.stringify(cards, null, 2);
}
