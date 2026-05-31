import { useApi } from '../hooks/useApi';
import { statsApi, cacheApi } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function formatSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(1)} ${units[i]}`;
}

const PIE_COLORS = ['#f97316', '#22c55e', '#3b82f6'];

export default function Dashboard() {
  const { data: stats, loading: statsLoading, refetch: refetchStats } = useApi(statsApi.get);
  const { data: caches, loading: cachesLoading } = useApi(() => cacheApi.list({ page: 1, page_size: 5 }));

  if (statsLoading) return <div className="loading-spinner" />;

  const pieData = stats?.by_type
    ? Object.entries(stats.by_type).map(([type, count]) => ({
        name: type.charAt(0).toUpperCase() + type.slice(1),
        value: count,
      }))
    : [];

  const barData = stats?.by_type_size
    ? Object.entries(stats.by_type_size).map(([type, size]) => ({
        name: type.charAt(0).toUpperCase() + type.slice(1),
        size: Math.round(size / (1024 * 1024)),
      }))
    : [];

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of Jenkins build cache sharing system</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">📦</div>
          <div className="stat-value">{stats?.total_caches || 0}</div>
          <div className="stat-label">Total Caches</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">💾</div>
          <div className="stat-value">{formatSize(stats?.total_size)}</div>
          <div className="stat-label">Total Storage</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon orange">✅</div>
          <div className="stat-value">{stats?.active_count || 0}</div>
          <div className="stat-label">Active Caches</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">⏰</div>
          <div className="stat-value">{stats?.expired_count || 0}</div>
          <div className="stat-label">Expired Caches</div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="card">
          <div className="card-header">
            <h3>Cache Distribution</h3>
          </div>
          <div className="card-body">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">
                <p>No cache data available</p>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Storage by Type (MB)</h3>
          </div>
          <div className="card-body">
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="size" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">
                <p>No storage data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Recent Caches</h3>
          <button className="btn btn-ghost btn-sm" onClick={refetchStats}>Refresh</button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {cachesLoading ? (
            <div className="loading-spinner" />
          ) : caches?.items?.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Version</th>
                  <th>Size</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {caches.items.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td><span className={`badge badge-${c.type}`}>{c.type}</span></td>
                    <td>{c.version}</td>
                    <td>{formatSize(c.size)}</td>
                    <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                    <td>{new Date(c.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <h4>No caches yet</h4>
              <p>Upload your first build cache to get started</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
