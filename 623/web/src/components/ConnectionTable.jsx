import { Clock, Globe, Activity } from 'lucide-react';

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function ConnectionTable({ connections, compact = false }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-slate-400 border-b border-slate-700">
            <th className="pb-3 font-medium">ID</th>
            <th className="pb-3 font-medium">客户端IP</th>
            <th className="pb-3 font-medium">连接时长</th>
            {!compact && <th className="pb-3 font-medium">空闲时间</th>}
            {!compact && <th className="pb-3 font-medium">查询次数</th>}
            {!compact && <th className="pb-3 font-medium">状态</th>}
          </tr>
        </thead>
        <tbody className="text-sm">
          {connections.length === 0 ? (
            <tr>
              <td colSpan={compact ? 3 : 6} className="py-8 text-center text-slate-500">
                暂无连接数据
              </td>
            </tr>
          ) : (
            connections.map((conn) => {
              const isIdle = conn.idle_time > 60;
              const isLongRunning = conn.duration > 3600;
              
              return (
                <tr key={conn.id} className="border-b border-slate-700/50 hover:bg-slate-800/50">
                  <td className="py-3 text-slate-300 font-mono">#{conn.id}</td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-slate-500" />
                      <span className="text-slate-300 font-mono">{conn.client_ip}</span>
                    </div>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <Clock className={`w-4 h-4 ${isLongRunning ? 'text-amber-400' : 'text-slate-500'}`} />
                      <span className={isLongRunning ? 'text-amber-400' : 'text-slate-300'}>
                        {formatDuration(conn.duration)}
                      </span>
                    </div>
                  </td>
                  {!compact && (
                    <td className="py-3">
                      <span className={isIdle ? 'text-amber-400' : 'text-slate-300'}>
                        {formatDuration(conn.idle_time)}
                      </span>
                    </td>
                  )}
                  {!compact && (
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-300">{conn.query_count}</span>
                      </div>
                    </td>
                  )}
                  {!compact && (
                    <td className="py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
                        isIdle 
                          ? 'bg-amber-500/20 text-amber-400' 
                          : 'bg-green-500/20 text-green-400'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${isIdle ? 'bg-amber-400' : 'bg-green-400'}`}></span>
                        {isIdle ? '空闲' : '活跃'}
                      </span>
                    </td>
                  )}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ConnectionTable;
