import { OutlineNode } from '../types';
import { generateId } from './coordinateUtils';

interface PdfOutlineItem {
  title: string;
  dest?: any;
  items?: PdfOutlineItem[];
}

export const parseOutline = async (
  outline: PdfOutlineItem[] | null,
  pdfDoc: any
): Promise<OutlineNode[]> => {
  if (!outline || outline.length === 0) {
    return [];
  }

  const parseNode = async (item: PdfOutlineItem): Promise<OutlineNode> => {
    let pageIndex = 0;

    if (item.dest) {
      try {
        const dest = typeof item.dest === 'string'
          ? await pdfDoc.getDestination(item.dest)
          : item.dest;

        if (dest && dest[0]) {
          const pageIndexResult = await pdfDoc.getPageIndex(dest[0]);
          pageIndex = pageIndexResult;
        }
      } catch (e) {
        console.warn('Failed to parse outline destination:', e);
      }
    }

    const children = item.items
      ? await Promise.all(item.items.map(parseNode))
      : [];

    return {
      id: generateId(),
      title: item.title || 'Untitled',
      pageIndex,
      children,
    };
  };

  return Promise.all(outline.map(parseNode));
};

export const flattenOutline = (nodes: OutlineNode[]): OutlineNode[] => {
  const result: OutlineNode[] = [];

  const traverse = (node: OutlineNode) => {
    result.push(node);
    node.children.forEach(traverse);
  };

  nodes.forEach(traverse);
  return result;
};
