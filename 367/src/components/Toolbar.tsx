import { useState } from 'react';
import { Search, Upload, Filter, Route, Database, Layers, Square, Download, Image, FileJson } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import type { GraphData } from '@/types';

export default function Toolbar() {
  const searchQuery = useGraphStore((s) => s.searchQuery);
  const setSearchQuery = useGraphStore((s) => s.setSearchQuery);
  const availableTypes = useGraphStore((s) => s.availableTypes);
  const typeFilter = useGraphStore((s) => s.typeFilter);
  const setTypeFilter = useGraphStore((s) => s.setTypeFilter);
  const setImportDialogOpen = useGraphStore((s) => s.setImportDialogOpen);
  const graph = useGraphStore((s) => s.graph);
  const aggregationEnabled = useGraphStore((s) => s.aggregationEnabled);
  const setAggregationEnabled = useGraphStore((s) => s.setAggregationEnabled);
  const selectionMode = useGraphStore((s) => s.selectionMode);
  const setSelectionMode = useGraphStore((s) => s.setSelectionMode);
  const selectionBox = useGraphStore((s) => s.selectionBox);
  const getFilteredGraph = useGraphStore((s) => s.getFilteredGraph);
  const getSelectedSubgraph = useGraphStore((s) => s.getSelectedSubgraph);
  const setSelectionBox = useGraphStore((s) => s.setSelectionBox);

  const [showTypes, setShowTypes] = useState(false);
  const [showExport, setShowExport] = useState(false);

  const exportPNG = () => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `knowledge-graph-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    setShowExport(false);
  };

  const exportJSON = (subgraph: GraphData) => {
    const data = JSON.stringify(subgraph, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const link = document.createElement('a');
    link.download = `knowledge-graph-${Date.now()}.json`;
    link.href = URL.createObjectURL(blob);
    link.click();
    setShowExport(false);
  };

  const filteredGraph = getFilteredGraph();
  const selectedSubgraph = getSelectedSubgraph();

  return (
    <div className="flex items-center gap-3 px-4 py-3 glass-panel border-b border-slate-700/50">
      <div className="flex items-center gap-2 text-cyan-400 font-bold text-lg tracking-wider">
        <Database size={22} />
        <span>KG-Viz</span>
      </div>

      <div className="relative flex-1 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索实体、拼音首字母..."
          className="w-full rounded-lg bg-slate-800/60 border border-slate-600/50 pl-9 pr-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 focus:border-cyan-400/50 transition-all"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
          >
            ×
          </button>
        )}
      </div>

      <div className="relative">
        <button
          onClick={() => setShowTypes(!showTypes)}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-all ${
            typeFilter
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/30'
              : 'bg-slate-800/60 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60'
          }`}
        >
          <Filter size={14} />
          {typeFilter || '筛选类型'}
        </button>
        {showTypes && (
          <div className="absolute top-full mt-1 right-0 z-50 min-w-[140px] glass-panel rounded-lg overflow-hidden animate-fade-in">
            <button
              onClick={() => {
                setTypeFilter(null);
                setShowTypes(false);
              }}
              className="block w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-700/50"
            >
              全部类型
            </button>
            {availableTypes.map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTypeFilter(t === typeFilter ? null : t);
                  setShowTypes(false);
                }}
                className={`block w-full px-3 py-2 text-left text-sm hover:bg-slate-700/50 ${
                  t === typeFilter ? 'text-cyan-300 bg-cyan-500/10' : 'text-slate-300'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => setAggregationEnabled(!aggregationEnabled)}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-all ${
          aggregationEnabled
            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
            : 'bg-slate-800/60 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60'
        }`}
        title="节点聚合"
      >
        <Layers size={14} />
        聚合
      </button>

      <button
        onClick={() => {
          setSelectionMode(!selectionMode);
          setSelectionBox(null);
        }}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-all ${
          selectionMode
            ? 'bg-orange-500/20 text-orange-300 border border-orange-400/30'
            : 'bg-slate-800/60 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60'
        }`}
        title="框选模式"
      >
        <Square size={14} />
        框选
      </button>

      <PathQueryButton />

      <div className="relative">
        <button
          onClick={() => setShowExport(!showExport)}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm bg-slate-800/60 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60 transition-all"
        >
          <Download size={14} />
          导出
        </button>
        {showExport && (
          <div className="absolute top-full mt-1 right-0 z-50 w-52 glass-panel rounded-lg overflow-hidden animate-fade-in">
            <button
              onClick={exportPNG}
              className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-700/50"
            >
              <Image size={14} />
              导出图片 (PNG)
            </button>
            <button
              onClick={() => exportJSON(filteredGraph)}
              className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-700/50"
            >
              <FileJson size={14} />
              导出当前视图 JSON
            </button>
            {selectionBox && (
              <button
                onClick={() => exportJSON(selectedSubgraph)}
                className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm text-orange-300 hover:bg-slate-700/50"
              >
                <FileJson size={14} />
                导出选区 JSON ({selectedSubgraph.nodes.length}节点)
              </button>
            )}
          </div>
        )}
      </div>

      <button
        onClick={() => setImportDialogOpen(true)}
        className="flex items-center gap-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 px-3 py-2 text-sm hover:bg-cyan-500/30 transition-all"
      >
        <Upload size={14} />
        导入数据
      </button>

      <div className="ml-auto text-xs text-slate-500">
        {filteredGraph.nodes.length} 节点 · {filteredGraph.links.length} 关系
      </div>
    </div>
  );
}

function PathQueryButton() {
  const [open, setOpen] = useState(false);
  const pathSource = useGraphStore((s) => s.pathSource);
  const pathTarget = useGraphStore((s) => s.pathTarget);
  const setPathSource = useGraphStore((s) => s.setPathSource);
  const setPathTarget = useGraphStore((s) => s.setPathTarget);
  const setPathResult = useGraphStore((s) => s.setPathResult);
  const graph = useGraphStore((s) => s.graph);

  const runQuery = () => {
    if (!pathSource || !pathTarget) return;
    setPathResult(null);

    const worker = new Worker(new URL('@/workers/graphWorker.ts', import.meta.url), {
      type: 'module',
    });
    worker.postMessage({
      type: 'shortestPath',
      payload: {
        nodes: graph.nodes,
        links: graph.links,
        source: pathSource,
        target: pathTarget,
      },
    });
    worker.onmessage = (e) => {
      if (e.data.type === 'result') {
        setPathResult(e.data.payload);
      }
      worker.terminate();
    };
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-all ${
          open || pathSource || pathTarget
            ? 'bg-purple-500/20 text-purple-300 border border-purple-400/30'
            : 'bg-slate-800/60 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60'
        }`}
      >
        <Route size={14} />
        路径查询
      </button>
      {open && (
        <div className="absolute top-full mt-1 right-0 z-50 w-64 glass-panel rounded-lg p-3 animate-fade-in">
          <div className="text-xs text-slate-400 mb-2">输入起终点实体名</div>
          <input
            type="text"
            value={pathSource}
            onChange={(e) => setPathSource(e.target.value)}
            placeholder="起点"
            className="w-full rounded-md bg-slate-800/60 border border-slate-600/50 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-400/50 mb-2"
          />
          <input
            type="text"
            value={pathTarget}
            onChange={(e) => setPathTarget(e.target.value)}
            placeholder="终点"
            className="w-full rounded-md bg-slate-800/60 border border-slate-600/50 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-400/50 mb-2"
          />
          <div className="flex gap-2">
            <button
              onClick={runQuery}
              className="flex-1 rounded-md bg-purple-500/20 text-purple-300 border border-purple-400/30 px-3 py-1.5 text-sm hover:bg-purple-500/30 transition-all"
            >
              查询
            </button>
            <button
              onClick={() => {
                setPathSource('');
                setPathTarget('');
                setPathResult(null);
              }}
              className="rounded-md bg-slate-700/60 text-slate-300 px-3 py-1.5 text-sm hover:bg-slate-600/60"
            >
              清除
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
