import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { exportApi, taskApi } from '../services/api';

const PageHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
`;

const PageTitle = styled.h1`
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
`;

const BackButton = styled.button`
  padding: 8px 16px;
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    background-color: var(--accent-secondary);
  }
`;

const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
`;

const Card = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
`;

const CardTitle = styled.h3`
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
`;

const StatGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
`;

const StatItem = styled.div`
  padding: 16px;
  background-color: var(--bg-tertiary);
  border-radius: 8px;
  text-align: center;
  
  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--accent-primary);
    margin-bottom: 4px;
  }
  
  .stat-label {
    font-size: 12px;
    color: var(--text-secondary);
  }
`;

const StatList = styled.div`
  margin-top: 16px;
`;

const StatRow = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  
  &:last-child {
    border-bottom: none;
  }
  
  .label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
  }
  
  .count {
    font-weight: 600;
    font-size: 14px;
  }
`;

const ColorDot = styled.span`
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: ${props => props.color};
`;

const ExportSection = styled.div`
  margin-bottom: 32px;
`;

const ExportButton = styled.button`
  width: 100%;
  padding: 16px;
  background-color: ${props => props.primary ? 'var(--accent-primary)' : 'var(--bg-tertiary)'};
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
  
  &:hover {
    opacity: 0.9;
  }
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const ExportDescription = styled.p`
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
`;

const FormatSelector = styled.div`
  margin-bottom: 16px;
  padding: 12px;
  background-color: var(--bg-tertiary);
  border-radius: 6px;
  
  label {
    font-size: 13px;
    color: var(--text-secondary);
    display: block;
    margin-bottom: 8px;
  }
  
  .options {
    display: flex;
    gap: 12px;
  }
`;

const FormatOption = styled.label`
  flex: 1;
  padding: 12px;
  background-color: ${props => props.selected ? 'var(--accent-primary)20' : 'var(--bg-primary)'};
  border: 2px solid ${props => props.selected ? 'var(--accent-primary)' : 'var(--border-color)'};
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: var(--accent-primary);
  }
  
  input {
    margin-right: 8px;
  }
  
  .format-name {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
  }
  
  .format-desc {
    font-size: 11px;
    color: var(--text-secondary);
  }
`;

const ExportPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  
  const [task, setTask] = useState(null);
  const [stats, setStats] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [jsonFormat, setJsonFormat] = useState('flat');

  useEffect(() => {
    loadTask();
    loadStats();
  }, [taskId]);

  const loadTask = async () => {
    try {
      const response = await taskApi.getById(taskId);
      setTask(response.data);
    } catch (error) {
      console.error('Error loading task:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await exportApi.getStats(taskId);
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const handleExportJSON = async () => {
    setExporting(true);
    try {
      const response = await exportApi.exportJSON(taskId, jsonFormat);
      const filename = jsonFormat === 'flat' 
        ? `annotations_${taskId}_flat.json` 
        : `annotations_${taskId}_nested.json`;
      downloadBlob(response.data, filename);
    } catch (error) {
      console.error('Error exporting JSON:', error);
      alert('导出失败');
    }
    setExporting(false);
  };

  const handleExportCoNLL = async () => {
    setExporting(true);
    try {
      const response = await exportApi.exportCoNLL(taskId);
      downloadBlob(response.data, `annotations_${taskId}.conll`);
    } catch (error) {
      console.error('Error exporting CoNLL:', error);
      alert('导出失败');
    }
    setExporting(false);
  };

  return (
    <div>
      <PageHeader>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16px }}>
          <BackButton onClick={() => navigate('/tasks')}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
            </svg>
            返回
          </BackButton>
          <PageTitle>数据导出 - {task?.name}</PageTitle>
        </div>
      </PageHeader>

      <ContentGrid>
        <div>
          <Card>
            <CardTitle>📊 统计信息</CardTitle>
            
            <StatGrid>
              <StatItem>
                <div className="stat-value">{stats?.total || 0}</div>
                <div className="stat-label">总文档数</div>
              </StatItem>
              <StatItem>
                <div className="stat-value" style={{ color: 'var(--success)' }}>
                  {stats?.annotated || 0}
                </div>
                <div className="stat-label">已标注</div>
              </StatItem>
              <StatItem>
                <div className="stat-value" style={{ color: 'var(--warning)' }}>
                  {stats?.pending || 0}
                </div>
                <div className="stat-label">待标注</div>
              </StatItem>
              <StatItem>
                <div className="stat-value" style={{ color: 'var(--accent-secondary)' }}>
                  {Object.values(stats?.entityCounts || {}).reduce((a, b) => a + b, 0)}
                </div>
                <div className="stat-label">实体总数</div>
              </StatItem>
            </StatGrid>

            <h4 style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>实体分布</h4>
            <StatList>
              {Object.entries(stats?.entityCounts || {}).map(([label, count]) => {
                const entityType = task?.entityTypes?.find(et => et.label === label);
                return (
                  <StatRow key={label}>
                    <span className="label">
                      <ColorDot color={entityType?.color || '#ccc'} />
                      {label}
                    </span>
                    <span className="count">{count}</span>
                  </StatRow>
                );
              })}
              {Object.keys(stats?.entityCounts || {}).length === 0 && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                  暂无实体数据
                </p>
              )}
            </StatList>
          </Card>
        </div>

        <div>
          <Card>
            <CardTitle>📥 数据导出</CardTitle>
            
            <ExportSection>
              <FormatSelector>
                <label>JSON 导出格式</label>
                <div className="options">
                  <FormatOption selected={jsonFormat === 'flat'}>
                    <input
                      type="radio"
                      name="jsonFormat"
                      value="flat"
                      checked={jsonFormat === 'flat'}
                      onChange={(e) => setJsonFormat(e.target.value)}
                    />
                    <div>
                      <div className="format-name">扁平化格式</div>
                      <div className="format-desc">文档、实体、关系分离为独立数组，便于分析</div>
                    </div>
                  </FormatOption>
                  <FormatOption selected={jsonFormat === 'nested'}>
                    <input
                      type="radio"
                      name="jsonFormat"
                      value="nested"
                      checked={jsonFormat === 'nested'}
                      onChange={(e) => setJsonFormat(e.target.value)}
                    />
                    <div>
                      <div className="format-name">嵌套格式</div>
                      <div className="format-desc">按文档组织，实体嵌套在文档内部</div>
                    </div>
                  </FormatOption>
                </div>
              </FormatSelector>
              
              <ExportButton primary onClick={handleExportJSON} disabled={exporting}>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15.01l1.41 1.41L11 14.84V19h2v-4.16l1.59 1.59L16 15.01 12.01 11 8 15.01z"/>
                </svg>
                导出 {jsonFormat === 'flat' ? '扁平化' : '嵌套'} JSON
              </ExportButton>
              <ExportDescription>
                {jsonFormat === 'flat' 
                  ? '导出扁平化JSON格式，文档、实体、关系、事件分离为独立数组，降低嵌套复杂度，便于数据分析和处理。'
                  : '导出嵌套JSON格式，按文档组织所有标注信息，包含完整的层级结构。'}
              </ExportDescription>
            </ExportSection>

            <ExportSection>
              <ExportButton onClick={handleExportCoNLL} disabled={exporting}>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM9.03 13.78c-.21-.52-.77-.91-1.36-.79-.42.09-.74.37-.91.74-.34.72.15 1.56.87 1.76.42.12.82-.04 1.11-.34l.71 1.22c-.5.58-1.21.91-1.97.81-1.09-.15-1.96-1.07-2.06-2.16-.13-1.39.83-2.66 2.15-2.87.82-.13 1.57.18 2.12.77l-.67 1.14c-.02-.09-.08-.16-.09-.28zm5.98-1.06c.42-.12.69-.49.69-.92 0-.54-.44-.98-.98-.98h-.98v2.45h.77l.91 1.57c.3.52.92.68 1.44.38.38-.22.6-.65.55-1.08l-.8-.98zm.12-2.22c.55 0 1-.45 1-1s-.45-1-1-1-1 .45-1 1 .45 1 1 1zm-2.22 4.2h.98v3h-.98z"/>
                </svg>
                导出 CoNLL 格式
              </ExportButton>
              <ExportDescription>
                导出 CoNLL 格式的命名实体识别数据，适用于训练序列标注模型，
                采用 BIO 标注体系。
              </ExportDescription>
            </ExportSection>

            <div style={{ 
              padding: '16px', 
              backgroundColor: 'var(--bg-tertiary)', 
              borderRadius: '8px',
              marginTop: '24px'
            }}>
              <h4 style={{ marginBottom: '8px', fontSize: '14px' }}>💡 提示</h4>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                导出的数据可用于训练 NLP 模型或进行数据分析。
                JSON 格式包含最完整的信息，CoNLL 格式适合常见的 NER 训练框架。
              </p>
            </div>
          </Card>
        </div>
      </ContentGrid>
    </div>
  );
};

export default ExportPage;
