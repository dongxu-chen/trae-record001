import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { taskApi, exportApi } from '../services/api';

const PageTitle = styled.h1`
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 24px;
  color: var(--text-primary);
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
`;

const StatCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  
  h3 {
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 8px;
    font-weight: 500;
  }
  
  .value {
    font-size: 32px;
    font-weight: 700;
    color: var(--accent-primary);
  }
`;

const TaskListSection = styled.section`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
`;

const SectionHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    font-size: 20px;
    font-weight: 600;
  }
`;

const TaskTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  th {
    text-align: left;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-color);
  }
  
  td {
    padding: 16px;
    border-bottom: 1px solid var(--border-color);
    font-size: 14px;
  }
  
  tr:last-child td {
    border-bottom: none;
  }
`;

const ActionButton = styled(Link)`
  padding: 8px 16px;
  background-color: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  display: inline-block;
  
  &:hover {
    opacity: 0.9;
  }
`;

const StatusBadge = styled.span`
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  background-color: ${props => {
    switch(props.status) {
      case 'pending': return 'var(--warning)20';
      case 'annotated': return 'var(--success)20';
      case 'reviewed': return 'var(--accent-primary)20';
      default: return 'var(--bg-tertiary)';
    }
  }};
  color: ${props => {
    switch(props.status) {
      case 'pending': return 'var(--warning)';
      case 'annotated': return 'var(--success)';
      case 'reviewed': return 'var(--accent-primary)';
      default: return 'var(--text-secondary)';
    }
  }};
`;

const Dashboard = () => {
  const [tasks, setTasks] = useState([]);
  const [totalStats, setTotalStats] = useState({
    totalTasks: 0,
    totalDocuments: 0,
    annotatedDocuments: 0,
    entityCount: 0
  });

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const response = await taskApi.getAll();
      setTasks(response.data.slice(0, 5));
      
      let totalDocs = 0;
      let annotatedDocs = 0;
      let entities = 0;
      
      for (const task of response.data) {
        try {
          const statsRes = await exportApi.getStats(task._id);
          totalDocs += statsRes.data.total || 0;
          annotatedDocs += statsRes.data.annotated || 0;
          entities += Object.values(statsRes.data.entityCounts || {}).reduce((a, b) => a + b, 0);
        } catch (e) {
          console.log('No stats for task:', task._id);
        }
      }
      
      setTotalStats({
        totalTasks: response.data.length,
        totalDocuments: totalDocs,
        annotatedDocuments: annotatedDocs,
        entityCount: entities
      });
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
  };

  return (
    <div>
      <PageTitle>仪表盘</PageTitle>
      
      <StatsGrid>
        <StatCard>
          <h3>任务总数</h3>
          <div className="value">{totalStats.totalTasks}</div>
        </StatCard>
        <StatCard>
          <h3>文档总数</h3>
          <div className="value">{totalStats.totalDocuments}</div>
        </StatCard>
        <StatCard>
          <h3>已标注</h3>
          <div className="value" style={{ color: 'var(--success)' }}>
            {totalStats.annotatedDocuments}
          </div>
        </StatCard>
        <StatCard>
          <h3>实体数量</h3>
          <div className="value" style={{ color: 'var(--accent-secondary)' }}>
            {totalStats.entityCount}
          </div>
        </StatCard>
      </StatsGrid>
      
      <TaskListSection>
        <SectionHeader>
          <h2>最近任务</h2>
          <ActionButton to="/tasks">查看全部</ActionButton>
        </SectionHeader>
        
        <TaskTable>
          <thead>
            <tr>
              <th>任务名称</th>
              <th>创建时间</th>
              <th>实体类型</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(task => (
              <tr key={task._id}>
                <td style={{ fontWeight: 500 }}>{task.name}</td>
                <td>{new Date(task.createdAt).toLocaleDateString()}</td>
                <td>
                  <StatusBadge status="annotated">
                    {task.entityTypes?.length || 0} 种类型
                  </StatusBadge>
                </td>
                <td>
                  <ActionButton to={`/annotate/${task._id}`}>
                    开始标注
                  </ActionButton>
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                  暂无任务，请先创建任务
                </td>
              </tr>
            )}
          </tbody>
        </TaskTable>
      </TaskListSection>
    </div>
  );
};

export default Dashboard;
