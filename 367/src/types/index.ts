export interface Triple {
  subject: string;
  predicate: string;
  object: string;
  subjectType?: string;
  objectType?: string;
  attributes?: Record<string, string>;
  startDate?: string;
  endDate?: string;
  timestamp?: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  group: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  attributes?: Record<string, string>;
  startDate?: string;
  endDate?: string;
  timestamp?: number;
  aggregated?: boolean;
  aggregatedIds?: string[];
  aggregatedCount?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  predicate: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface PathResult {
  nodes: string[];
  links: { source: string; target: string; predicate: string }[];
  distance: number;
}

export type WorkerMessage =
  | { type: 'init'; payload: GraphData }
  | { type: 'tick'; payload: GraphData }
  | { type: 'shortestPath'; payload: { source: string; target: string; nodes: GraphNode[]; links: GraphLink[] } }
  | { type: 'result'; payload: PathResult | null };

export interface ESResult {
  hits: {
    total: number;
    hits: Array<{
      _id: string;
      _score: number;
      _source: GraphNode;
    }>;
  };
}
