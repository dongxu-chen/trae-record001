import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Summary from './components/Summary';
import BranchNaming from './components/BranchNaming';
import MergeDirection from './components/MergeDirection';
import PRSize from './components/PRSize';
import CommitFrequency from './components/CommitFrequency';
import ConflictDetection from './components/ConflictDetection';
import BranchAge from './components/BranchAge';
import CommitQuality from './components/CommitQuality';
import TeamReport from './components/TeamReport';

function App() {
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [targetBranch, setTargetBranch] = useState('develop');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    fetchBranches();
  }, []);

  const fetchBranches = async () => {
    try {
      const response = await axios.get('/api/branches');
      setBranches(response.data.branches);
      setCurrentBranch(response.data.current);
      setSelectedBranch(response.data.current);
    } catch (error) {
      console.error('Error fetching branches:', error);
    }
  };

  const runCheck = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/check/all', {
        params: {
          source: selectedBranch,
          target: targetBranch
        }
      });
      setReport(response.data);
    } catch (error) {
      console.error('Error running check:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCheckResultByCategory = (category) => {
    if (!report || !report.check_results) return null;
    return report.check_results.find(cr => cr.category === category);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>🔍 Git Branch Policy Checker</h1>
        <p>检查分支命名、合并方向、PR大小和提交频率是否符合团队规范</p>
      </header>

      <div className="controls">
        <label>源分支:</label>
        <select 
          value={selectedBranch} 
          onChange={(e) => setSelectedBranch(e.target.value)}
        >
          {branches.map(branch => (
            <option key={branch} value={branch}>
              {branch} {branch === currentBranch && '(当前)'}
            </option>
          ))}
        </select>

        <label>目标分支:</label>
        <select 
          value={targetBranch} 
          onChange={(e) => setTargetBranch(e.target.value)}
        >
          {branches.map(branch => (
            <option key={branch} value={branch}>{branch}</option>
          ))}
        </select>

        <button onClick={runCheck} disabled={loading}>
          {loading ? '检查中...' : '运行检查'}
        </button>

        {report && (
          <span className={`status-badge ${report.summary.status}`}>
            {report.summary.status.toUpperCase()}
          </span>
        )}

        {report && (
          <button 
            className="fix-btn" 
            style={{ marginLeft: 'auto' }}
            onClick={() => window.open(`/api/check/all?source=${selectedBranch}&target=${targetBranch}&format=checklist`, '_blank')}
          >
            📋 查看Checklist
          </button>
        )}
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          正在检查...
        </div>
      )}

      {report && !loading && (
        <>
          <Summary summary={report.summary} report={report} />

          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              全部检查 ({report.check_results.length})
            </button>
            {report.check_results.map(cr => (
              <button 
                key={cr.category}
                className={`tab ${activeTab === cr.category ? 'active' : ''}`}
                onClick={() => setActiveTab(cr.category)}
              >
                {cr.display_name}
                {cr.summary && (
                  <span style={{ marginLeft: '8px', fontSize: '0.85em' }}>
                    {cr.summary.failed > 0 ? `(${cr.summary.failed})` : ''}
                  </span>
                )}
              </button>
            ))}
            <button 
              className={`tab ${activeTab === 'team_report' ? 'active' : ''}`}
              onClick={() => setActiveTab('team_report')}
            >
              👥 团队简报
            </button>
          </div>

          {(activeTab === 'all' || activeTab === 'branch_naming') && (
            <BranchNaming data={getCheckResultByCategory('branch_naming')} />
          )}

          {(activeTab === 'all' || activeTab === 'merge_direction') && (
            <MergeDirection data={getCheckResultByCategory('merge_direction')} />
          )}

          {(activeTab === 'all' || activeTab === 'pr_size') && (
            <PRSize data={getCheckResultByCategory('pr_size')} />
          )}

          {(activeTab === 'all' || activeTab === 'commit_frequency') && (
            <CommitFrequency data={getCheckResultByCategory('commit_frequency')} />
          )}

          {(activeTab === 'all' || activeTab === 'branch_age') && (
            <BranchAge 
              data={getCheckResultByCategory('branch_age')} 
              sourceBranch={selectedBranch}
              targetBranch={targetBranch}
            />
          )}

          {(activeTab === 'all' || activeTab === 'commit_quality') && (
            <CommitQuality data={getCheckResultByCategory('commit_quality')} />
          )}

          {(activeTab === 'all' || activeTab === 'conflict_detection') && (
            <ConflictDetection data={getCheckResultByCategory('conflict_detection')} />
          )}

          {activeTab === 'team_report' && (
            <TeamReport days={30} />
          )}
        </>
      )}

      {!report && !loading && activeTab === 'team_report' && (
        <TeamReport days={30} />
      )}
    </div>
  );
}

export default App;
