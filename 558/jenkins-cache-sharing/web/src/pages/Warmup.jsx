import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { warmupApi } from '../services/api';

export default function Warmup() {
  const [showCreate, setShowCreate] = useState(false);
  const { data: tasks, loading, refetch } = useApi(warmupApi.list);

  const handleCreateFromJenkins = async (e) => {
    e.preventDefault();
    const form = Object.fromEntries(new FormData(e.target));
    try {
      await warmupApi.fromJenkins({
        cache_type: form.cache_type,
        job_name: form.job_name,
        build_number: parseInt(form.build_number) || 0,
      });
      setShowCreate(false);
      refetch();
    } catch (err) {
      alert('Warmup failed: ' + err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Cache Warmup</h2>
        <p>Pre-populate caches across Jenkins pipelines for faster builds</p>
      </div>

      <div className="search-bar">
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Warmup Task</button>
        <button className="btn btn-ghost" onClick={refetch}>Refresh</button>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Warmup Task</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateFromJenkins}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Cache Type</label>
                  <select className="form-control" name="cache_type" required defaultValue="maven">
                    <option value="maven">Maven</option>
                    <option value="npm">NPM</option>
                    <option value="gradle">Gradle</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Source Job Name</label>
                  <input className="form-control" name="job_name" required placeholder="my-project-build" />
                </div>
                <div className="form-group">
                  <label>Source Build Number (0 = latest)</label>
                  <input className="form-control" name="build_number" type="number" placeholder="0" />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Warmup</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="loading-spinner" />
          ) : tasks?.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Source Job</th>
                  <th>Build #</th>
                  <th>Target Jobs</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td style={{ fontFamily: 'monospace' }}>{t.id}</td>
                    <td><span className={`badge badge-${t.cache_type}`}>{t.cache_type}</span></td>
                    <td>{t.source_job}</td>
                    <td>#{t.source_build}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {t.target_jobs?.map((j, i) => (
                          <span key={i} className="badge badge-pending">{j}</span>
                        ))}
                      </div>
                    </td>
                    <td><span className={`badge badge-${t.status}`}>{t.status}</span></td>
                    <td style={{ minWidth: 150 }}>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${t.progress}%` }} />
                      </div>
                      <span className="text-sm text-muted">{t.progress?.toFixed(1)}%</span>
                    </td>
                    <td>{new Date(t.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔥</div>
              <h4>No warmup tasks</h4>
              <p>Create a warmup task to pre-populate caches across pipelines</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
