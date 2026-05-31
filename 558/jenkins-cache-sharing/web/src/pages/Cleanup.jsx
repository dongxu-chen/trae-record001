import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { cleanupApi } from '../services/api';

function formatDuration(ns) {
  if (!ns) return '-';
  const hours = Math.floor(ns / 3600000000000);
  const mins = Math.floor((ns % 3600000000000) / 60000000000);
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(1)} ${units[i]}`;
}

export default function Cleanup() {
  const [tab, setTab] = useState('policies');
  const { data: policies, loading: policiesLoading, refetch: refetchPolicies } = useApi(cleanupApi.listPolicies);
  const { data: results, loading: resultsLoading, refetch: refetchResults } = useApi(cleanupApi.listResults);

  const handleExecute = async (id) => {
    if (!confirm('Execute this cleanup policy now?')) return;
    try {
      await cleanupApi.executePolicy(id);
      refetchPolicies();
      refetchResults();
    } catch (err) {
      alert('Execution failed: ' + err.message);
    }
  };

  const handleToggle = async (id, enabled) => {
    try {
      await cleanupApi.updatePolicy(id, { enabled: !enabled });
      refetchPolicies();
    } catch (err) {
      alert('Update failed: ' + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this cleanup policy?')) return;
    try {
      await cleanupApi.deletePolicy(id);
      refetchPolicies();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Cleanup Policies</h2>
        <p>Configure automated cache cleanup and retention strategies</p>
      </div>

      <div className="tabs">
        <div className={`tab ${tab === 'policies' ? 'active' : ''}`} onClick={() => setTab('policies')}>Policies</div>
        <div className={`tab ${tab === 'results' ? 'active' : ''}`} onClick={() => setTab('results')}>Execution Results</div>
      </div>

      {tab === 'policies' && (
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            {policiesLoading ? (
              <div className="loading-spinner" />
            ) : policies?.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Cache Types</th>
                    <th>Max Age</th>
                    <th>Max Size</th>
                    <th>Max Versions</th>
                    <th>Keep Latest</th>
                    <th>Cron</th>
                    <th>Enabled</th>
                    <th>Last Run</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {policies.map((p) => (
                    <tr key={p.id}>
                      <td><strong>{p.name}</strong></td>
                      <td>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {p.cache_types?.map((t) => (
                            <span key={t} className={`badge badge-${t}`}>{t}</span>
                          ))}
                        </div>
                      </td>
                      <td>{formatDuration(p.max_age)}</td>
                      <td>{p.max_size ? formatSize(p.max_size) : 'Unlimited'}</td>
                      <td>{p.max_versions || 'Unlimited'}</td>
                      <td>{p.keep_latest}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{p.cron_expression}</td>
                      <td>
                        <span className={`badge ${p.enabled ? 'badge-enabled' : 'badge-disabled'}`}>
                          {p.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </td>
                      <td>{p.last_run_at ? new Date(p.last_run_at).toLocaleString() : 'Never'}</td>
                      <td>
                        <div className="actions-cell">
                          <button className="btn btn-primary btn-sm" onClick={() => handleExecute(p.id)}>Run</button>
                          <button className="btn btn-ghost btn-sm" onClick={() => handleToggle(p.id, p.enabled)}>
                            {p.enabled ? 'Disable' : 'Enable'}
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">🧹</div>
                <h4>No cleanup policies</h4>
                <p>Default policies are created automatically</p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'results' && (
        <div className="card">
          <div className="card-header">
            <h3>Execution History</h3>
            <button className="btn btn-ghost btn-sm" onClick={refetchResults}>Refresh</button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {resultsLoading ? (
              <div className="loading-spinner" />
            ) : results?.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Policy ID</th>
                    <th>Removed</th>
                    <th>Freed Space</th>
                    <th>Errors</th>
                    <th>Started</th>
                    <th>Finished</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'monospace' }}>{r.policy_id}</td>
                      <td>{r.removed_ids?.length || 0} caches</td>
                      <td>{formatSize(r.freed_bytes)}</td>
                      <td>{r.errors?.length > 0 ? <span className="badge badge-failed">{r.errors.length} errors</span> : <span className="badge badge-active">None</span>}</td>
                      <td>{new Date(r.started_at).toLocaleString()}</td>
                      <td>{new Date(r.finished_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <h4>No execution results</h4>
                <p>Run a cleanup policy to see results here</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
