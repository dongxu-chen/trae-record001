import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { cacheApi } from '../services/api';

function formatSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(1)} ${units[i]}`;
}

export default function Caches() {
  const [type, setType] = useState('');
  const [job, setJob] = useState('');
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);

  const { data, loading, refetch } = useApi(
    () => cacheApi.list({ type: type || undefined, job: job || undefined, page, page_size: 20 }),
    [type, job, page]
  );

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this cache?')) return;
    try {
      await cacheApi.delete(id);
      refetch();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Cache Manager</h2>
        <p>Manage build caches across Jenkins pipelines</p>
      </div>

      <div className="search-bar">
        <select className="form-control" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}>
          <option value="">All Types</option>
          <option value="maven">Maven</option>
          <option value="npm">NPM</option>
          <option value="gradle">Gradle</option>
        </select>
        <input
          className="form-control"
          placeholder="Filter by job name..."
          value={job}
          onChange={(e) => { setJob(e.target.value); setPage(1); }}
        />
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>+ Upload Cache</button>
        <button className="btn btn-ghost" onClick={refetch}>Refresh</button>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onDone={() => { setShowUpload(false); refetch(); }} />}

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="loading-spinner" />
          ) : data?.items?.length > 0 ? (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Version</th>
                    <th>Job</th>
                    <th>Build #</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Access</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.id}>
                      <td><strong>{c.name}</strong></td>
                      <td><span className={`badge badge-${c.type}`}>{c.type}</span></td>
                      <td style={{ fontFamily: 'monospace' }}>{c.version}</td>
                      <td>{c.job_name}</td>
                      <td>#{c.build_number}</td>
                      <td>{formatSize(c.size)}</td>
                      <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                      <td>{c.access_count}</td>
                      <td>{new Date(c.created_at).toLocaleDateString()}</td>
                      <td>
                        <div className="actions-cell">
                          <a href={cacheApi.download(c.id)} className="btn btn-ghost btn-sm">Download</a>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c.id)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 8, padding: 16 }}>
                <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
                <span className="text-sm text-muted" style={{ padding: '6px 12px' }}>Page {page} of {data?.total_pages || 1}</span>
                <button className="btn btn-ghost btn-sm" disabled={page >= (data?.total_pages || 1)} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <h4>No caches found</h4>
              <p>Upload a cache or adjust your filters</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function UploadModal({ onClose, onDone }) {
  const [form, setForm] = useState({ cache_type: 'maven', job_name: '', version: '', build_number: '' });
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert('Please select a file');
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('cache_type', form.cache_type);
      fd.append('job_name', form.job_name);
      fd.append('version', form.version);
      fd.append('build_number', form.build_number);
      await cacheApi.upload(fd);
      onDone();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Upload Cache</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Cache Type</label>
              <select className="form-control" value={form.cache_type} onChange={(e) => setForm({ ...form, cache_type: e.target.value })}>
                <option value="maven">Maven</option>
                <option value="npm">NPM</option>
                <option value="gradle">Gradle</option>
              </select>
            </div>
            <div className="form-group">
              <label>Job Name</label>
              <input className="form-control" required value={form.job_name} onChange={(e) => setForm({ ...form, job_name: e.target.value })} placeholder="my-project-build" />
            </div>
            <div className="form-group">
              <label>Version</label>
              <input className="form-control" required value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} placeholder="v1.0.0" />
            </div>
            <div className="form-group">
              <label>Build Number</label>
              <input className="form-control" type="number" value={form.build_number} onChange={(e) => setForm({ ...form, build_number: e.target.value })} placeholder="42" />
            </div>
            <div className="form-group">
              <label>Cache File (.tar.gz)</label>
              <input className="form-control" type="file" accept=".tar.gz,.tgz" required onChange={(e) => setFile(e.target.files[0])} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
