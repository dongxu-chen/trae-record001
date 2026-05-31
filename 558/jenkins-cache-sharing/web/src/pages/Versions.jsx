import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { versionApi } from '../services/api';

export default function Versions() {
  const [selectedType, setSelectedType] = useState('');
  const { data: versions, loading, refetch } = useApi(
    () => versionApi.list(selectedType),
    [selectedType]
  );

  const handlePromote = async (type, version) => {
    if (!confirm(`Promote version "${version}" for ${type}?`)) return;
    try {
      await versionApi.promote(type, version);
      refetch();
    } catch (err) {
      alert('Promote failed: ' + err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Version Control</h2>
        <p>Manage cache versions and promote latest builds</p>
      </div>

      <div className="search-bar">
        <select className="form-control" value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
          <option value="">All Types</option>
          <option value="maven">Maven</option>
          <option value="npm">NPM</option>
          <option value="gradle">Gradle</option>
        </select>
        <button className="btn btn-ghost" onClick={refetch}>Refresh</button>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="loading-spinner" />
          ) : versions?.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Cache Type</th>
                  <th>Entries</th>
                  <th>Is Latest</th>
                  <th>Description</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.id}>
                    <td><strong style={{ fontFamily: 'monospace' }}>{v.version}</strong></td>
                    <td><span className={`badge badge-${v.cache_type}`}>{v.cache_type}</span></td>
                    <td>{v.entries?.length || 0} entries</td>
                    <td>
                      {v.is_latest ? (
                        <span className="badge badge-active">Latest</span>
                      ) : (
                        <span className="badge badge-pending">Not Latest</span>
                      )}
                    </td>
                    <td className="text-sm text-muted">{v.description}</td>
                    <td>{new Date(v.created_at).toLocaleDateString()}</td>
                    <td>
                      {!v.is_latest && (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => handlePromote(v.cache_type, v.version)}
                        >
                          Promote
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🏷️</div>
              <h4>No versions yet</h4>
              <p>Versions are created automatically when caches are uploaded</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
