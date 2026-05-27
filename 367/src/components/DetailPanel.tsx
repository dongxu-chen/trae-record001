import { X, Link2, User } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import { esClient, ES_INDEX } from '@/services/elasticsearch';

export default function DetailPanel() {
  const selectedNode = useGraphStore((s) => s.selectedNode);
  const selectNode = useGraphStore((s) => s.selectNode);
  const graph = useGraphStore((s) => s.graph);

  if (!selectedNode) {
    return (
      <div className="w-80 border-l border-slate-700/50 glass-panel p-6 flex flex-col items-center justify-center text-slate-500">
        <User size={32} className="mb-3 opacity-50" />
        <div className="text-sm">点击节点查看详情</div>
      </div>
    );
  }

  const neighbors = graph.links
    .filter((l) => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      return s === selectedNode.id || t === selectedNode.id;
    })
    .map((l) => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      const isSource = s === selectedNode.id;
      const neighborId = isSource ? t : s;
      const neighborNode = esClient.get(ES_INDEX, neighborId);
      return {
        direction: isSource ? '→' : '←',
        predicate: l.predicate,
        neighbor: neighborNode,
      };
    });

  return (
    <div className="w-80 border-l border-slate-700/50 glass-panel overflow-y-auto animate-slide-in-right">
      <div className="p-4 border-b border-slate-700/50 flex items-start justify-between">
        <div>
          <div className="text-xs text-cyan-400 font-medium mb-1">{selectedNode.type}</div>
          <div className="text-lg font-bold text-slate-100">{selectedNode.label}</div>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      <div className="p-4">
        <div className="text-xs text-slate-400 mb-2 flex items-center gap-1.5">
          <Link2 size={12} />
          关联关系 ({neighbors.length})
        </div>
        <div className="space-y-1.5">
          {neighbors.map((n, i) => (
            <div
              key={i}
              className="group flex items-center gap-2 rounded-md bg-slate-800/40 px-3 py-2 text-sm hover:bg-slate-700/50 cursor-pointer transition-colors"
              onClick={() => {
                if (n.neighbor) {
                  selectNode({
                    id: n.neighbor.id,
                    label: n.neighbor.label,
                    type: n.neighbor.type,
                    group: n.neighbor.group,
                  });
                }
              }}
            >
              <span className="text-cyan-400 font-mono text-xs w-5">{n.direction}</span>
              <span className="text-slate-400 text-xs flex-1 truncate">{n.predicate}</span>
              <span className="text-slate-200 text-sm truncate group-hover:text-cyan-300 transition-colors">
                {n.neighbor?.label}
              </span>
            </div>
          ))}
        </div>

        {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
          <div className="mt-6">
            <div className="text-xs text-slate-400 mb-2">属性</div>
            <div className="space-y-1.5">
              {Object.entries(selectedNode.attributes).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 text-sm">
                  <span className="text-slate-400 text-xs w-20 truncate">{k}</span>
                  <span className="text-slate-200 text-xs bg-slate-800/40 rounded px-2 py-0.5">
                    {v}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
