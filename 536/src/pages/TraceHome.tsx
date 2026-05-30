import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Network } from 'lucide-react';

export default function TraceHome() {
  const navigate = useNavigate();
  const [traceId, setTraceId] = useState('');

  const handleSearch = () => {
    if (traceId.trim()) {
      navigate(`/trace/${encodeURIComponent(traceId.trim())}`);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-sans font-bold text-monitor-text">链路追踪</h2>
        <p className="text-monitor-text-muted text-sm mt-1 font-sans">通过Trace ID查询分布式事务执行链路</p>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-8">
        <div className="max-w-lg mx-auto text-center">
          <Network className="w-16 h-16 text-monitor-accent/30 mx-auto mb-4" />
          <h3 className="text-lg font-sans font-semibold text-monitor-text mb-2">查询事务链路</h3>
          <p className="text-sm font-sans text-monitor-text-muted mb-6">输入Trace ID以可视化查看事务执行链路、DAG图和Span瀑布图</p>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="w-4 h-4 text-monitor-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="输入 Trace ID..."
                value={traceId}
                onChange={(e) => setTraceId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full bg-monitor-surface border border-monitor-border rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={!traceId.trim()}
              className="px-6 py-3 rounded-lg bg-monitor-accent text-monitor-bg text-sm font-sans font-semibold hover:bg-monitor-accent/90 disabled:opacity-50 transition-colors"
            >
              查询
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
