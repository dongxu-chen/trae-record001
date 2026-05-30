import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { preAnnotateApi, taskApi } from '../services/api';

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

const SummaryCards = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
`;

const SummaryCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  
  .value {
    font-size: 32px;
    font-weight: 700;
    color: ${props => props.color || 'var(--accent-primary)'};
    margin-bottom: 4px;
  }
  
  .label {
    font-size: 13px;
    color: var(--text-secondary);
  }
`;

const Card = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
`;

const CardTitle = styled.h3`
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
`;

const IssueItem = styled.div`
  padding: 16px;
  background-color: var(--bg-tertiary);
  border-radius: 8px;
  margin-bottom: 12px;
  border-left: 4px solid ${props => props.type === 'inconsistent_label' ? 'var(--warning)' : 'var(--error)'};
`;

const IssueHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
`;

const IssueType = styled.span`
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  background-color: ${props => props.type === 'inconsistent_label' ? 'var(--warning)20' : 'var(--error)20'};
  color: ${props => props.type === 'inconsistent_label' ? 'var(--warning)' : 'var(--error)'};
`;

const IssueText = styled.div`
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 8px;
`;

const IssueDetails = styled.div`
  font-size: 13px;
  color: var(--text-secondary);
`;

const LabelTags = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 8px;
`;

const LabelTag = styled.span`
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  background-color: ${props => props.color || '#ccc'}40;
  color: ${props => props.color || '#ccc'};
  border: 1px solid ${props => props.color || '#ccc'};
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
  
  .icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
  
  p {
    margin-bottom: 8px;
  }
`;

const CheckButton = styled.button`
  padding: 12px 24px;
  background-color: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    opacity: 0.9;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SamplingPanel = styled.div`
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 16px;
  background-color: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 24px;
  
  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    
    label {
      font-size: 12px;
      color: var(--text-secondary);
    }
    
    select, input {
      padding: 8px 12px;
      background-color: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 4px;
      color: var(--text-primary);
      font-size: 14px;
      min-width: 150px;
    }
  }
`;

const SamplingInfo = styled.div`
  padding: 12px 16px;
  background-color: var(--bg-tertiary);
  border-radius: 6px;
  margin-bottom: 24px;
  font-size: 13px;
  
  .info-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .label {
      color: var(--text-secondary);
    }
    
    .value {
      color: var(--accent-primary);
      font-weight: 600;
    }
  }
`;

const ConsistencyPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  
  const [task, setTask] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sampleSize, setSampleSize] = useState(50);
  const [sampleStrategy, setSampleStrategy] = useState('random');

  useEffect(() => {
    loadTask();
    runConsistencyCheck();
  }, [taskId]);

  const loadTask = async () => {
    try {
      const response = await taskApi.getById(taskId);
      setTask(response.data);
    } catch (error) {
      console.error('Error loading task:', error);
    }
  };

  const runConsistencyCheck = async () => {
    setLoading(true);
    try {
      const response = await preAnnotateApi.checkConsistency(taskId, {
        sampleSize,
        sampleStrategy
      });
      setResult(response.data);
    } catch (error) {
      console.error('Error checking consistency:', error);
    }
    setLoading(false);
  };

  const inconsistentIssues = result?.issues?.filter(i => i.type === 'inconsistent_label') || [];
  const overlappingIssue = result?.issues?.find(i => i.type === 'overlapping_entities');

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
          <PageTitle>一致性检查 - {task?.name}</PageTitle>
        </div>
      </PageHeader>

      <SamplingPanel>
        <div className="field">
          <label>抽样大小</label>
          <select
            value={sampleSize}
            onChange={(e) => setSampleSize(parseInt(e.target.value))}
          >
            <option value={20}>20 条</option>
            <option value={50}>50 条</option>
            <option value={100}>100 条</option>
            <option value={200}>200 条</option>
            <option value={500}>500 条</option>
          </select>
        </div>
        <div className="field">
          <label>抽样策略</label>
          <select
            value={sampleStrategy}
            onChange={(e) => setSampleStrategy(e.target.value)}
          >
            <option value="random">随机抽样</option>
            <option value="recent">最新优先</option>
            <option value="stratified">分层抽样</option>
          </select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
          <CheckButton onClick={runConsistencyCheck} disabled={loading}>
            {loading ? '检查中...' : '🔄 执行检查'}
          </CheckButton>
        </div>
      </SamplingPanel>

      {result && (
        <SamplingInfo>
          <div className="info-row">
            <span className="label">总标注文档数:</span>
            <span className="value">{result.totalAnnotations}</span>
          </div>
          <div className="info-row">
            <span className="label">实际抽样数量:</span>
            <span className="value">{result.sampledCount}</span>
          </div>
          <div className="info-row">
            <span className="label">抽样策略:</span>
            <span className="value">
              {sampleStrategy === 'random' ? '随机抽样' : 
               sampleStrategy === 'recent' ? '最新优先' : '分层抽样'}
            </span>
          </div>
          {result.isSampled && (
            <>
              <div className="info-row">
                <span className="label">估计标签不一致总数:</span>
                <span className="value" style={{ color: 'var(--warning)' }}>
                  {result.estimatedTotalIssues?.inconsistent} 处
                </span>
              </div>
              <div className="info-row">
                <span className="label">估计实体重叠总数:</span>
                <span className="value" style={{ color: 'var(--error)' }}>
                  {result.estimatedTotalIssues?.overlapping} 处
                </span>
              </div>
            </>
          )}
        </SamplingInfo>
      )}

      <SummaryCards>
        <SummaryCard>
          <div className="value">{result?.totalAnnotations || 0}</div>
          <div className="label">已标注文档</div>
        </SummaryCard>
        <SummaryCard color="var(--warning)">
          <div className="value">{result?.inconsistentCount || 0}</div>
          <div className="label">
            标签不一致
            {result?.inconsistencyRate && (
              <span style={{ display: 'block', fontSize: '10px' }}>
                ({result.inconsistencyRate})
              </span>
            )}
          </div>
        </SummaryCard>
        <SummaryCard color="var(--error)">
          <div className="value">{result?.overlappingCount || 0}</div>
          <div className="label">
            实体重叠
            {result?.overlapRate && (
              <span style={{ display: 'block', fontSize: '10px' }}>
                ({result.overlapRate})
              </span>
            )}
          </div>
        </SummaryCard>
        {result?.isSampled && (
          <SummaryCard color="var(--accent-secondary)">
            <div className="value">{result?.sampledCount || 0}</div>
            <div className="label">已抽样检查</div>
          </SummaryCard>
        )}
      </SummaryCards>

      <Card>
        <CardTitle>
          ⚠️ 标签不一致问题
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 'normal' }}>
            (同一文本被标注为不同类型)
          </span>
        </CardTitle>
        
        {inconsistentIssues.length > 0 ? (
          inconsistentIssues.map((issue, idx) => (
            <IssueItem key={idx} type={issue.type}>
              <IssueHeader>
                <div>
                  <IssueText>"{issue.text}"</IssueText>
                  <IssueDetails>
                    共 {issue.occurrences} 次出现，被标注为 {issue.labels.length} 种不同类型
                  </IssueDetails>
                  <LabelTags>
                    {issue.labels.map((label, i) => {
                      const entityType = task?.entityTypes?.find(et => et.label === label);
                      return (
                        <LabelTag key={i} color={entityType?.color}>
                          {label}
                        </LabelTag>
                      );
                    })}
                  </LabelTags>
                </div>
                <IssueType type={issue.type}>标签不一致</IssueType>
              </IssueHeader>
            </IssueItem>
          ))
        ) : (
          <EmptyState>
            <div className="icon">✅</div>
            <p>没有发现标签不一致问题</p>
            <p style={{ fontSize: '13px' }}>所有相同文本的标注类型保持一致</p>
          </EmptyState>
        )}
      </Card>

      <Card>
        <CardTitle>
          🔴 实体重叠问题
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 'normal' }}>
            (同一位置被多个实体标注)
          </span>
        </CardTitle>
        
        {overlappingIssue ? (
          <div>
            <IssueItem type="overlapping_entities">
              <IssueHeader>
                <div>
                  <IssueText>发现 {overlappingIssue.count} 处实体重叠</IssueText>
                </div>
                <IssueType type="overlapping_entities">实体重叠</IssueType>
              </IssueHeader>
              <IssueDetails>
                以下是部分重叠示例 (显示前 10 个):
                <div style={{ marginTop: '12px' }}>
                  {overlappingIssue.details?.map((item, idx) => (
                    <div key={idx} style={{ 
                      padding: '8px', 
                      backgroundColor: 'var(--bg-primary)', 
                      borderRadius: '4px',
                      marginBottom: '8px' 
                    }}>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        文本片段: "...{item.text?.slice(Math.max(0, item.entity1.start - 10), item.entity1.end + 10)}..."
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <LabelTag color={item.entity1.color}>{item.entity1.label}: "{item.entity1.text}"</LabelTag>
                        <LabelTag color={item.entity2.color}>{item.entity2.label}: "{item.entity2.text}"</LabelTag>
                      </div>
                    </div>
                  ))}
                </div>
              </IssueDetails>
            </IssueItem>
          </div>
        ) : (
          <EmptyState>
            <div className="icon">✅</div>
            <p>没有发现实体重叠问题</p>
            <p style={{ fontSize: '13px' }}>所有实体标注位置互不重叠</p>
          </EmptyState>
        )}
      </Card>

      <div style={{ 
        padding: '20px', 
        backgroundColor: 'var(--bg-secondary)', 
        borderRadius: '12px',
        border: '1px solid var(--border-color)'
      }}>
        <h4 style={{ marginBottom: '12px', fontSize: '16px' }}>💡 一致性建议</h4>
        <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px', lineHeight: '1.8' }}>
          <li>定期运行一致性检查，确保标注质量</li>
          <li>对于标签不一致问题，统一标注规范</li>
          <li>实体重叠通常表示标注错误，建议检查并修复</li>
          <li>可建立标注指南文档，明确各类实体的标注边界</li>
        </ul>
      </div>
    </div>
  );
};

export default ConsistencyPage;
