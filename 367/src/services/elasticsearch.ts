import { pinyin } from 'pinyin-pro';
import { GraphNode, ESResult } from '@/types';

function toPinyinInitials(text: string): string {
  return pinyin(text, { pattern: 'first', toneType: 'none', type: 'array' }).join('');
}

function toPinyinFull(text: string): string {
  return pinyin(text, { pattern: 'pinyin', toneType: 'none', type: 'array' }).join('');
}

interface IndexEntry {
  doc: GraphNode;
  fieldTokens: string[];
}

class MockElasticsearch {
  private indices: Record<string, Map<string, IndexEntry>> = {};
  private inverted: Record<string, Map<string, Set<string>>> = {};

  createIndex(index: string) {
    if (!this.indices[index]) {
      this.indices[index] = new Map();
      this.inverted[index] = new Map();
    }
  }

  index(index: string, doc: GraphNode) {
    this.createIndex(index);
    const tokens = this.tokenize(doc.label + ' ' + doc.type);
    const pinyinInitials = toPinyinInitials(doc.label);
    const pinyinFull = toPinyinFull(doc.label);
    const allTokens = [...tokens, pinyinInitials, pinyinFull];
    this.indices[index].set(doc.id, { doc, fieldTokens: allTokens });
    for (const token of allTokens) {
      if (!this.inverted[index].has(token)) {
        this.inverted[index].set(token, new Set());
      }
      this.inverted[index].get(token)!.add(doc.id);
    }
  }

  bulk(index: string, docs: GraphNode[]) {
    docs.forEach((d) => this.index(index, d));
  }

  search(index: string, query: string, typeFilter?: string): ESResult {
    if (!this.indices[index]) return { hits: { total: 0, hits: [] } };
    const queryLower = query.toLowerCase().trim();
    if (!queryLower) return { hits: { total: 0, hits: [] } };

    const tokens = this.tokenize(queryLower);
    const pyInitials = toPinyinInitials(queryLower);
    const pyFull = toPinyinFull(queryLower);
    const allQueryTerms = [...tokens, pyInitials, pyFull];

    const scores = new Map<string, number>();
    for (const term of allQueryTerms) {
      const ids = this.inverted[index].get(term);
      if (ids) ids.forEach((id) => scores.set(id, (scores.get(id) || 0) + 1));
    }

    for (const [id, entry] of this.indices[index]) {
      if (entry.doc.label.toLowerCase().includes(queryLower)) {
        scores.set(id, (scores.get(id) || 0) + 3);
      }
      if (toPinyinInitials(entry.doc.label).startsWith(pyInitials) && pyInitials.length >= 1) {
        scores.set(id, (scores.get(id) || 0) + 2);
      }
      if (toPinyinFull(entry.doc.label).startsWith(pyFull) && pyFull.length >= 2) {
        scores.set(id, (scores.get(id) || 0) + 2);
      }
    }

    const sorted = Array.from(scores.entries()).sort((a, b) => b[1] - a[1]).slice(0, 50);
    const hits = sorted
      .map(([id, score]) => {
        const src = this.indices[index].get(id)!.doc;
        return { _id: id, _score: score, _source: src };
      })
      .filter((h) => !typeFilter || h._source.type === typeFilter);
    return { hits: { total: hits.length, hits } };
  }

  get(index: string, id: string): GraphNode | undefined {
    return this.indices[index]?.get(id)?.doc;
  }

  list(index: string): GraphNode[] {
    return Array.from(this.indices[index]?.values() || []).map((e) => e.doc);
  }

  clear(index: string) {
    this.indices[index] = new Map();
    this.inverted[index] = new Map();
  }

  private tokenize(text: string): string[] {
    return text.toLowerCase().split(/[\s\-_./]+/).filter(Boolean);
  }
}

export const esClient = new MockElasticsearch();
export const ES_INDEX = 'entities';
