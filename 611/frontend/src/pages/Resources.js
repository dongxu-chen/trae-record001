import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { mockData } from '../services/api';

const Resources = () => {
  const [resources, setResources] = useState([]);
  const [filteredResources, setFilteredResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    accountId: '',
    type: '',
    status: '',
    search: '',
  });

  useEffect(() => {
    setTimeout(() => {
      setResources(mockData.resources);
      setFilteredResources(mockData.resources);
      setLoading(false);
    }, 500);
  }, []);

  useEffect(() => {
    let result = resources;

    if (filters.accountId) {
      result = result.filter((r) => r.accountId === filters.accountId);
    }
    if (filters.type) {
      result = result.filter((r) => r.type === filters.type);
    }
    if (filters.status) {
      result = result.filter((r) => r.status === filters.status);
    }
    if (filters.search) {
      result = result.filter(
        (r) =>
          r.name.toLowerCase().includes(filters.search.toLowerCase()) ||
          r.id.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    setFilteredResources(result);
  }, [filters, resources]);

  const renderTags = (tags) => {
    const tagEntries = Object.entries(tags);
    if (tagEntries.length === 0) {
      return <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>无标签</span>;
    }
    return tagEntries.slice(0, 3).map(([key, value]) => (
      <span key={key} className="tag">
        <span className="tag-key">{key}:</span>
        <span className="tag-value">{value}</span>
      </span>
    ));
  };

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>加载中...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', fontSize: '1.75rem', fontWeight: '700' }}>资源列表</h1>

      <div className="card">
        <div className="filter-bar">
          <div className="filter-group">
            <label>账号</label>
            <select
              value={filters.accountId}
              onChange={(e) => setFilters({ ...filters, accountId: e.target.value })}
            >
              <option value="">全部账号</option>
              {mockData.accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>资源类型</label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
            >
              <option value="">全部类型</option>
              <option value="ECS">ECS</option>
              <option value="RDS">RDS</option>
              <option value="OSS">OSS</option>
            </select>
          </div>
          <div className="filter-group">
            <label>状态</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">全部状态</option>
              <option value="Running">Running</option>
              <option value="Stopped">Stopped</option>
              <option value="Active">Active</option>
            </select>
          </div>
          <div className="filter-group">
            <label>搜索</label>
            <input
              type="text"
              placeholder="搜索资源名称或ID"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span>资源 ({filteredResources.length})</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>资源ID</th>
                <th>名称</th>
                <th>类型</th>
                <th>账号</th>
                <th>区域</th>
                <th>状态</th>
                <th>标签</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredResources.map((resource) => (
                <tr key={resource.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{resource.id}</td>
                  <td style={{ fontWeight: '500' }}>{resource.name}</td>
                  <td>
                    <span className={`badge badge-${resource.type.toLowerCase()}`}>{resource.type}</span>
                  </td>
                  <td style={{ fontSize: '0.875rem' }}>{resource.accountName}</td>
                  <td style={{ fontSize: '0.875rem' }}>{resource.region}</td>
                  <td>
                    <span
                      style={{
                        color: resource.status === 'Running' || resource.status === 'Active' ? '#10b981' : '#6b7280',
                        fontWeight: '500',
                      }}
                    >
                      {resource.status}
                    </span>
                  </td>
                  <td>{renderTags(resource.tags)}</td>
                  <td>
                    <Link
                      to={`/resources/${resource.id}`}
                      style={{ color: '#3b82f6', textDecoration: 'none', fontSize: '0.875rem' }}
                    >
                      详情
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Resources;
