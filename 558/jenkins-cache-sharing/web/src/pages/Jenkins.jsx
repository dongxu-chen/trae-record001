import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { jenkinsApi } from '../services/api';

export default function Jenkins() {
  const [buildName, setBuildName] = useState('');
  const [buildNumber, setBuildNumber] = useState('');
  const [buildData, setBuildData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [triggering, setTriggering] = useState(false);

  const { data: jobs, loading: jobsLoading, refetch: refetchJobs } = useApi(jenkinsApi.listJobs);

  const testConnection = async () => {
    setConnectionStatus('testing');
    try {
      await jenkinsApi.testConnection();
      setConnectionStatus('connected');
    } catch (err) {
      setConnectionStatus('failed');
    }
  };

  const fetchBuild = async () => {
    if (!buildName || !buildNumber) return;
    try {
      const data = await jenkinsApi.getBuild(buildName, parseInt(buildNumber));
      setBuildData(data);
    } catch (err) {
      alert('Failed to fetch build: ' + err.message);
    }
  };

  const triggerBuild = async (jobName) => {
    setTriggering(true);
    try {
      await jenkinsApi.triggerBuild(jobName);
      alert('Build triggered successfully');
      refetchJobs();
    } catch (err) {
      alert('Trigger failed: ' + err.message);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Jenkins Integration</h2>
        <p>Connect to Jenkins and manage build caches from pipelines</p>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <div className="card">
          <div className="card-header">
            <h3>Connection Status</h3>
            <button className="btn btn-primary btn-sm" onClick={testConnection}>Test Connection</button>
          </div>
          <div className="card-body">
            {connectionStatus === 'testing' && <p>Testing connection...</p>}
            {connectionStatus === 'connected' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-active">Connected</span>
                <span className="text-sm text-muted">Jenkins server is reachable</span>
              </div>
            )}
            {connectionStatus === 'failed' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-failed">Failed</span>
                <span className="text-sm text-muted">Cannot reach Jenkins server</span>
              </div>
            )}
            {connectionStatus === null && (
              <p className="text-muted">Click "Test Connection" to verify Jenkins connectivity</p>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Build Lookup</h3>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="form-control" placeholder="Job name" value={buildName} onChange={(e) => setBuildName(e.target.value)} />
              <input className="form-control" placeholder="Build #" type="number" value={buildNumber} onChange={(e) => setBuildNumber(e.target.value)} style={{ maxWidth: 120 }} />
              <button className="btn btn-primary" onClick={fetchBuild}>Fetch</button>
            </div>
            {buildData && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div className="text-sm"><strong>Job:</strong> {buildData.job_name}</div>
                  <div className="text-sm"><strong>Build:</strong> #{buildData.build_number}</div>
                  <div className="text-sm"><strong>Result:</strong> <span className={`badge badge-${buildData.result === 'SUCCESS' ? 'active' : 'failed'}`}>{buildData.result}</span></div>
                  <div className="text-sm"><strong>Duration:</strong> {(buildData.duration / 1000).toFixed(1)}s</div>
                </div>
                {buildData.artifacts?.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <strong className="text-sm">Artifacts:</strong>
                    <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                      {buildData.artifacts.map((a, i) => (
                        <li key={i} className="text-sm">{a.file_name}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Jenkins Jobs</h3>
          <button className="btn btn-ghost btn-sm" onClick={refetchJobs}>Refresh</button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {jobsLoading ? (
            <div className="loading-spinner" />
          ) : jobs?.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Job Name</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job, i) => (
                  <tr key={i}>
                    <td><strong>{job}</strong></td>
                    <td>
                      <div className="actions-cell">
                        <button className="btn btn-primary btn-sm" disabled={triggering} onClick={() => triggerBuild(job)}>
                          Trigger Build
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">⚙️</div>
              <h4>No Jenkins jobs found</h4>
              <p>Make sure your Jenkins connection is properly configured</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
