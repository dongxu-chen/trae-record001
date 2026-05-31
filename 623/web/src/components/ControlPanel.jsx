import { useState } from 'react';
import { Settings, Zap, Database, Trash2, Save, AlertTriangle } from 'lucide-react';

function ControlPanel({ stats }) {
  const [maxConnections, setMaxConnections] = useState(stats?.limiter?.max_connections || 500);
  const [releaseCount, setReleaseCount] = useState(10);
  const [message, setMessage] = useState(null);

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleUpdateLimiter = async () => {
    try {
      const res = await fetch('/api/limiter/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_connections: maxConnections })
      });
      const data = await res.json();
      showMessage('success', data.message);
    } catch (err) {
      showMessage('error', '操作失败');
    }
  };

  const handleReleaseConnections = async () => {
    try {
      const res = await fetch('/api/connections/release', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: releaseCount })
      });
      const data = await res.json();
      showMessage('success', `已释放 ${data.released} 个空闲连接`);
    } catch (err) {
      showMessage('error', '操作失败');
    }
  };

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-900/30 border border-green-700 text-green-300' 
            : 'bg-red-900/30 border border-red-700 text-red-300'
        }`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-glass rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Settings className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">限流配置</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">最大连接数</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={maxConnections}
                  onChange={(e) => setMaxConnections(parseInt(e.target.value) || 0)}
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  min="1"
                  max="10000"
                />
                <button
                  onClick={handleUpdateLimiter}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Save className="w-4 h-4" />
                  保存
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
              <div>
                <p className="text-sm text-slate-500">当前连接数</p>
                <p className="text-2xl font-bold text-white">
                  {stats?.limiter?.total_connections || 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-500">连接使用率</p>
                <p className="text-2xl font-bold text-white">
                  {stats?.limiter?.max_connections 
                    ? ((stats.limiter.total_connections / stats.limiter.max_connections) * 100).toFixed(1) 
                    : 0}%
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card-glass rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 bg-orange-500/20 rounded-lg">
              <Zap className="w-5 h-5 text-orange-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">紧急操作</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">释放空闲连接数</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={releaseCount}
                  onChange={(e) => setReleaseCount(parseInt(e.target.value) || 0)}
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  min="1"
                  max="1000"
                />
                <button
                  onClick={handleReleaseConnections}
                  className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  释放
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-2">释放超过30秒未活动的连接</p>
            </div>

            <div className="pt-4 border-t border-slate-700">
              <div className="flex items-start gap-3 p-3 bg-amber-500/10 rounded-lg border border-amber-500/30">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-400">注意</p>
                  <p className="text-xs text-amber-300/70 mt-1">
                    紧急操作可能影响正在进行的业务，请谨慎使用。建议在业务低峰期执行。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card-glass rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-cyan-500/20 rounded-lg">
            <Database className="w-5 h-5 text-cyan-400" />
          </div>
          <h3 className="text-lg font-semibold text-white">系统状态</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-slate-800/50 rounded-lg">
            <p className="text-sm text-slate-500 mb-1">风暴检测</p>
            <p className={`text-lg font-bold ${
              stats?.limiter?.storm_detected ? 'text-red-400' : 'text-green-400'
            }`}>
              {stats?.limiter?.storm_detected ? '告警中' : '正常'}
            </p>
          </div>
          <div className="p-4 bg-slate-800/50 rounded-lg">
            <p className="text-sm text-slate-500 mb-1">慢建连统计</p>
            <p className="text-lg font-bold text-amber-400">
              {stats?.analyzer?.slow_connection_count || 0}
            </p>
          </div>
          <div className="p-4 bg-slate-800/50 rounded-lg">
            <p className="text-sm text-slate-500 mb-1">泄漏风险</p>
            <p className={`text-lg font-bold ${
              (stats?.analyzer?.leak_candidate_count || 0) > 0 ? 'text-red-400' : 'text-green-400'
            }`}>
              {stats?.analyzer?.leak_candidate_count || 0} 个
            </p>
          </div>
          <div className="p-4 bg-slate-800/50 rounded-lg">
            <p className="text-sm text-slate-500 mb-1">连接速率</p>
            <p className="text-lg font-bold text-blue-400">
              {stats?.proxy?.connection_rate?.toFixed(2) || 0} conn/s
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ControlPanel;
