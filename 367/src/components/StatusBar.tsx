import { useGraphStore } from '@/store/graphStore';

export default function StatusBar() {
  const graph = useGraphStore((s) => s.graph);
  const pathResult = useGraphStore((s) => s.pathResult);
  const searchQuery = useGraphStore((s) => s.searchQuery);
  const searchResults = useGraphStore((s) => s.searchResults);

  return (
    <div className="px-4 py-2 border-t border-slate-700/50 glass-panel flex items-center gap-6 text-xs text-slate-500">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        就绪
      </div>
      <div>节点: <span className="text-slate-300">{graph.nodes.length}</span></div>
      <div>关系: <span className="text-slate-300">{graph.links.length}</span></div>
      {searchQuery && (
        <div className="text-cyan-400">搜索结果: {searchResults.length}</div>
      )}
      {pathResult && (
        <div className="text-yellow-400">
          最短路径: {pathResult.nodes.length} 节点 · {pathResult.distance} 跳
        </div>
      )}
    </div>
  );
}
