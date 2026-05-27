import { useEffect, useRef, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { GraphNode, GraphLink, GraphData, PathResult } from '@/types';
import { useGraphStore } from '@/store/graphStore';

const COLORS = ['#06b6d4', '#8b5cf6', '#f472b6', '#10b981', '#f59e0b', '#ef4444', '#3b82f6'];
const NODE_RADIUS = 16;
const HIGHLIGHT_RADIUS = 22;
const PATH_RADIUS = 26;
const AGG_RADIUS = 30;

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
}

interface SimLink extends GraphLink {
  source: SimNode | string;
  target: SimNode | string;
}

interface Transform {
  x: number;
  y: number;
  k: number;
}

function screenToWorld(sx: number, sy: number, t: Transform) {
  return { x: (sx - t.x) / t.k, y: (sy - t.y) / t.k };
}

interface Props {
  pathResult: PathResult | null;
  hoveredNodeId: string | null;
}

export default function GraphCanvas({ pathResult, hoveredNodeId }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const simRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);
  const transformRef = useRef<Transform>({ x: 0, y: 0, k: 1 });
  const rafRef = useRef<number>(0);
  const dimRef = useRef({ w: 960, h: 640 });
  const selectionStartRef = useRef<{ x: number; y: number } | null>(null);
  const selectionCurrentRef = useRef<{ x: number; y: number } | null>(null);

  const selectNode = useGraphStore((s) => s.selectNode);
  const setHoveredNode = useGraphStore((s) => s.setHoveredNode);
  const searchResults = useGraphStore((s) => s.searchResults);
  const searchQuery = useGraphStore((s) => s.searchQuery);
  const currentTime = useGraphStore((s) => s.currentTime);
  const aggregationEnabled = useGraphStore((s) => s.aggregationEnabled);
  const selectionMode = useGraphStore((s) => s.selectionMode);
  const selectionBox = useGraphStore((s) => s.selectionBox);
  const setSelectionBox = useGraphStore((s) => s.setSelectionBox);
  const getFilteredGraph = useGraphStore((s) => s.getFilteredGraph);

  const filteredGraph = useMemo(() => getFilteredGraph(), [currentTime, aggregationEnabled, getFilteredGraph]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { w, h } = dimRef.current;
    const dpr = window.devicePixelRatio || 1;
    const t = transformRef.current;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w * dpr, h * dpr);

    ctx.save();
    ctx.scale(dpr, dpr);

    ctx.fillStyle = '#070b14';
    ctx.fillRect(0, 0, w, h);

    const grd1 = ctx.createRadialGradient(w * 0.2, h * 0.3, 0, w * 0.2, h * 0.3, w * 0.5);
    grd1.addColorStop(0, 'rgba(6,182,212,0.08)');
    grd1.addColorStop(1, 'transparent');
    ctx.fillStyle = grd1;
    ctx.fillRect(0, 0, w, h);

    const grd2 = ctx.createRadialGradient(w * 0.8, h * 0.7, 0, w * 0.8, h * 0.7, w * 0.5);
    grd2.addColorStop(0, 'rgba(139,92,246,0.08)');
    grd2.addColorStop(1, 'transparent');
    ctx.fillStyle = grd2;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(t.x, t.y);
    ctx.scale(t.k, t.k);

    const nodes = nodesRef.current;
    const links = linksRef.current;

    const highlightedIds = new Set<string>();
    if (searchQuery && searchResults.length) {
      searchResults.forEach((n) => highlightedIds.add(n.id));
    }
    if (hoveredNodeId) highlightedIds.add(hoveredNodeId);
    if (pathResult) pathResult.nodes.forEach((id) => highlightedIds.add(id));

    const pathLinkKeys = new Set<string>();
    if (pathResult) {
      pathResult.links.forEach((l) => pathLinkKeys.add(`${l.source}__${l.target}`));
    }

    for (const link of links) {
      const src = link.source as SimNode;
      const tgt = link.target as SimNode;
      if (!src || !tgt || src.x == null || tgt.x == null) continue;

      const sId = src.id;
      const tId = tgt.id;

      let opacity = 0.5;
      let color = '#475569';

      if (pathLinkKeys.has(`${sId}__${tId}`) || pathLinkKeys.has(`${tId}__${sId}`)) {
        opacity = 1;
        color = '#fde047';
      } else if (hoveredNodeId && (sId === hoveredNodeId || tId === hoveredNodeId)) {
        opacity = 1;
        color = '#94a3b8';
      } else if (highlightedIds.size > 0) {
        opacity = 0.1;
      }

      ctx.strokeStyle = color;
      ctx.globalAlpha = opacity;
      ctx.lineWidth = 1.5 / t.k;

      const dx = tgt.x - src.x;
      const dy = tgt.y - src.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ux = dx / dist;
      const uy = dy / dist;
      const r = NODE_RADIUS + 2;

      const sx = src.x + ux * r;
      const sy = src.y + uy * r;
      const ex = tgt.x - ux * r;
      const ey = tgt.y - uy * r;

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(ex, ey);
      ctx.stroke();

      const ah = 8 / t.k;
      const angle = Math.atan2(ey - sy, ex - sx);
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(ex - ah * Math.cos(angle - Math.PI / 10), ey - ah * Math.sin(angle - Math.PI / 10));
      ctx.lineTo(ex - ah * Math.cos(angle + Math.PI / 10), ey - ah * Math.sin(angle + Math.PI / 10));
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();

      if (t.k > 1.2 && opacity >= 0.5) {
        const mx = (sx + ex) / 2;
        const my = (sy + ey) / 2;
        ctx.font = `${11 / t.k}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#94a3b8';
        ctx.globalAlpha = opacity * 0.9;
        ctx.fillText(link.predicate, mx, my - 6 / t.k);
      }
    }
    ctx.globalAlpha = 1;

    for (const node of nodes) {
      if (node.x == null) continue;

      const isPath = pathResult?.nodes.includes(node.id);
      const isHighlight = highlightedIds.has(node.id);
      const dimmed = highlightedIds.size > 0 && !isHighlight;
      const isAgg = node.aggregated;
      const baseRadius = isAgg ? AGG_RADIUS : NODE_RADIUS;
      const radius = isPath ? PATH_RADIUS : isHighlight ? HIGHLIGHT_RADIUS : baseRadius;

      if (isPath || isHighlight) {
        const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius * 2);
        glow.addColorStop(0, isPath ? 'rgba(253,224,71,0.35)' : 'rgba(255,255,255,0.2)');
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius * 2, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = dimmed ? 0.25 : 1;
      ctx.fillStyle = COLORS[node.group % COLORS.length];
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = isPath ? '#fde047' : isHighlight ? '#fff' : '#0f172a';
      ctx.lineWidth = (isPath ? 3.5 : isHighlight ? 2.5 : 2) / t.k;
      ctx.stroke();

      if (isAgg) {
        ctx.fillStyle = '#fff';
        ctx.font = `bold ${14 / t.k}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.aggregatedCount ? `${node.aggregatedCount}` : '', node.x, node.y);
      }

      if (t.k > 0.6) {
        ctx.font = `bold ${13 / t.k}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#e2e8f0';
        ctx.shadowColor = 'rgba(0,0,0,0.9)';
        ctx.shadowBlur = 4;
        ctx.fillText(node.label, node.x, node.y - radius - 10 / t.k);
        ctx.shadowBlur = 0;
      }
    }
    ctx.globalAlpha = 1;

    ctx.restore();

    if (selectionMode && selectionStartRef.current && selectionCurrentRef.current) {
      const x1 = selectionStartRef.current.x;
      const y1 = selectionStartRef.current.y;
      const x2 = selectionCurrentRef.current.x;
      const y2 = selectionCurrentRef.current.y;
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
      ctx.fillStyle = 'rgba(6, 182, 212, 0.1)';
      ctx.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
      ctx.setLineDash([]);
    }

    ctx.restore();

    rafRef.current = requestAnimationFrame(draw);
  }, [searchQuery, searchResults, hoveredNodeId, pathResult, selectionMode]);

  useEffect(() => {
    const update = () => {
      if (containerRef.current && canvasRef.current) {
        const w = containerRef.current.clientWidth || 960;
        const h = containerRef.current.clientHeight || 640;
        dimRef.current = { w, h };
        const dpr = window.devicePixelRatio || 1;
        canvasRef.current.width = w * dpr;
        canvasRef.current.height = h * dpr;
        canvasRef.current.style.width = w + 'px';
        canvasRef.current.style.height = h + 'px';
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  useEffect(() => {
    if (!filteredGraph.nodes.length) {
      nodesRef.current = [];
      linksRef.current = [];
      return;
    }
    if (simRef.current) {
      simRef.current.stop();
    }

    const { w, h } = dimRef.current;
    const existingPositions = new Map(nodesRef.current.map((n) => [n.id, { x: n.x, y: n.y }]));

    const nodes: SimNode[] = filteredGraph.nodes.map((n) => {
      const existing = existingPositions.get(n.id);
      return {
        ...n,
        x: existing?.x ?? w / 2 + (Math.random() - 0.5) * 200,
        y: existing?.y ?? h / 2 + (Math.random() - 0.5) * 200,
        vx: 0,
        vy: 0,
        fx: n.fx ?? null,
        fy: n.fy ?? null,
      };
    });

    const links: SimLink[] = filteredGraph.links.map((l) => ({
      ...l,
      source: l.source as string | SimNode,
      target: l.target as string | SimNode,
    }));

    nodesRef.current = nodes;
    linksRef.current = links;

    const sim = d3
      .forceSimulation<SimNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance(120)
          .strength(0.6)
      )
      .force('charge', d3.forceManyBody().strength(-450))
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('collision', d3.forceCollide().radius(35));

    simRef.current = sim;
    sim.on('tick', () => {});

    return () => {
      sim.stop();
    };
  }, [filteredGraph]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [draw]);

  const getNodeAt = useCallback((sx: number, sy: number): SimNode | null => {
    const t = transformRef.current;
    const { x, y } = screenToWorld(sx, sy, t);
    const r = (AGG_RADIUS + 4) / t.k;
    let found: SimNode | null = null;
    let minDist = Infinity;
    for (const n of nodesRef.current) {
      if (n.x == null) continue;
      const dx = n.x - x;
      const dy = n.y - y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d <= r && d < minDist) {
        minDist = d;
        found = n;
      }
    }
    return found;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let dragging: SimNode | null = null;
    let panStart: { x: number; y: number; tx: number; ty: number } | null = null;
    let isPanning = false;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const t = transformRef.current;
      const scaleBy = e.deltaY < 0 ? 1.1 : 0.9;
      const newK = Math.max(0.2, Math.min(4, t.k * scaleBy));
      t.x = mx - ((mx - t.x) * newK) / t.k;
      t.y = my - ((my - t.y) * newK) / t.k;
      t.k = newK;
    };

    const onMouseDown = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const world = screenToWorld(sx, sy, transformRef.current);

      if (selectionMode) {
        selectionStartRef.current = { x: sx, y: sy };
        selectionCurrentRef.current = { x: sx, y: sy };
        setSelectionBox({ x1: world.x, y1: world.y, x2: world.x, y2: world.y });
        return;
      }

      const node = getNodeAt(sx, sy);
      if (node) {
        dragging = node;
        if (simRef.current) simRef.current.alphaTarget(0.3).restart();
        node.fx = node.x;
        node.fy = node.y;
      } else {
        isPanning = true;
        panStart = { x: sx, y: sy, tx: transformRef.current.x, ty: transformRef.current.y };
      }
    };

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const world = screenToWorld(sx, sy, transformRef.current);

      if (selectionMode && selectionStartRef.current) {
        selectionCurrentRef.current = { x: sx, y: sy };
        const startWorld = screenToWorld(selectionStartRef.current.x, selectionStartRef.current.y, transformRef.current);
        setSelectionBox({ x1: startWorld.x, y1: startWorld.y, x2: world.x, y2: world.y });
        return;
      }

      if (dragging) {
        const t = transformRef.current;
        const w = screenToWorld(sx, sy, t);
        dragging.fx = w.x;
        dragging.fy = w.y;
      } else if (isPanning && panStart) {
        transformRef.current.x = panStart.tx + (sx - panStart.x);
        transformRef.current.y = panStart.ty + (sy - panStart.y);
      } else {
        const node = getNodeAt(sx, sy);
        setHoveredNode(node ? node.id : null);
        canvas.style.cursor = selectionMode ? 'crosshair' : node ? 'pointer' : 'default';
      }
    };

    const onMouseUp = () => {
      if (selectionStartRef.current) {
        selectionStartRef.current = null;
        selectionCurrentRef.current = null;
      }
      if (dragging) {
        dragging.fx = null;
        dragging.fy = null;
        dragging = null;
        if (simRef.current) simRef.current.alphaTarget(0);
      }
      isPanning = false;
      panStart = null;
    };

    const onClick = (e: MouseEvent) => {
      if (e.detail !== 1) return;
      if (selectionMode) return;
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const node = getNodeAt(sx, sy);
      if (node) {
        selectNode({
          id: node.id,
          label: node.label,
          type: node.type,
          group: node.group,
          x: node.x,
          y: node.y,
          attributes: node.attributes,
          aggregated: node.aggregated,
          aggregatedCount: node.aggregatedCount,
          aggregatedIds: node.aggregatedIds,
        });
      }
    };

    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('click', onClick);

    return () => {
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      canvas.removeEventListener('click', onClick);
    };
  }, [getNodeAt, selectNode, setHoveredNode, selectionMode, setSelectionBox]);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-[#070b14]">
      <canvas ref={canvasRef} className="block" />
    </div>
  );
}
