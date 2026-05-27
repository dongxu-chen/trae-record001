import { GraphData, GraphLink, GraphNode, Triple, WorkerMessage, PathResult } from '@/types';

type ShortestPathPayload = {
  nodes: GraphNode[];
  links: GraphLink[];
  source: string;
  target: string;
};

const ctx: Worker = self as unknown as Worker;

const MAX_DEPTH = 10;

function bidirectionalBFS(
  adj: Map<string, Set<string>>,
  source: string,
  target: string,
  maxDepth: number
): string[] | null {
  if (source === target) return null;
  if (!adj.has(source) || !adj.has(target)) return null;

  const prevForward = new Map<string, string | null>();
  const prevBackward = new Map<string, string | null>();
  const visitedForward = new Map<string, number>();
  const visitedBackward = new Map<string, number>();

  let queueForward: string[] = [source];
  let queueBackward: string[] = [target];
  prevForward.set(source, null);
  prevBackward.set(target, null);
  visitedForward.set(source, 0);
  visitedBackward.set(target, 0);

  let meetingNode: string | null = null;

  for (let depth = 1; depth <= maxDepth && meetingNode === null; depth++) {
    const nextForward: string[] = [];
    for (const cur of queueForward) {
      if (visitedBackward.has(cur)) {
        meetingNode = cur;
        break;
      }
      const neighbors = adj.get(cur);
      if (!neighbors) continue;
      for (const n of neighbors) {
        if (!visitedForward.has(n)) {
          visitedForward.set(n, depth);
          prevForward.set(n, cur);
          nextForward.push(n);
        }
      }
    }
    if (meetingNode) break;
    queueForward = nextForward;

    const nextBackward: string[] = [];
    for (const cur of queueBackward) {
      if (visitedForward.has(cur)) {
        meetingNode = cur;
        break;
      }
      const neighbors = adj.get(cur);
      if (!neighbors) continue;
      for (const n of neighbors) {
        if (!visitedBackward.has(n)) {
          visitedBackward.set(n, depth);
          prevBackward.set(n, cur);
          nextBackward.push(n);
        }
      }
    }
    if (meetingNode) break;
    queueBackward = nextBackward;

    if (queueForward.length === 0 && queueBackward.length === 0) break;
  }

  if (!meetingNode) return null;

  const pathForward: string[] = [];
  let cur: string | null = meetingNode;
  while (cur !== null) {
    pathForward.unshift(cur);
    cur = prevForward.get(cur) ?? null;
  }

  const pathBackward: string[] = [];
  cur = prevBackward.get(meetingNode) ?? null;
  while (cur !== null) {
    pathBackward.push(cur);
    cur = prevBackward.get(cur) ?? null;
  }

  return [...pathForward, ...pathBackward];
}

function computeShortestPath(payload: ShortestPathPayload): PathResult | null {
  const { nodes, links, source, target } = payload;
  if (source === target) return null;

  const adj = new Map<string, Set<string>>();
  nodes.forEach((n) => adj.set(n.id, new Set()));
  links.forEach((l) => {
    const s = typeof l.source === 'string' ? l.source : l.source.id;
    const t = typeof l.target === 'string' ? l.target : l.target.id;
    adj.get(s)?.add(t);
    adj.get(t)?.add(s);
  });

  const path = bidirectionalBFS(adj, source, target, MAX_DEPTH);
  if (!path) return null;

  const linkList: { source: string; target: string; predicate: string }[] = [];
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const found = links.find((l) => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      return (s === a && t === b) || (s === b && t === a);
    });
    if (found) {
      const s = typeof found.source === 'string' ? found.source : found.source.id;
      const t = typeof found.target === 'string' ? found.target : found.target.id;
      linkList.push({ source: s, target: t, predicate: found.predicate });
    }
  }
  return { nodes: path, links: linkList, distance: path.length - 1 };
}

ctx.onmessage = (e: MessageEvent<WorkerMessage>) => {
  const msg = e.data;
  if (msg.type === 'shortestPath') {
    const payload = msg.payload as unknown as ShortestPathPayload;
    const result = computeShortestPath(payload);
    ctx.postMessage({ type: 'result', payload: result });
  }
};

export {};
