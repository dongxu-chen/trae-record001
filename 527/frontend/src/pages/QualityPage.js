import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import styled from 'styled-components';
import { qualityApi, achievementApi } from '../services/api';

const ANNOTATOR = 'default_user';

const PageContainer = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 24px;
`;

const Title = styled.h1`
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
`;

const Subtitle = styled.p`
  color: var(--text-secondary);
  margin-top: 4px;
  font-size: 14px;
`;

const FilterBar = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  align-items: center;
  flex-wrap: wrap;
`;

const Label = styled.label`
  font-size: 13px;
  color: var(--text-secondary);
`;

const Select = styled.select`
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  
  &:focus {
    border-color: var(--accent-primary);
  }
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
`;

const StatCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  
  ${props => props.highlight && `
    border-color: var(--accent-primary);
    background: linear-gradient(135deg, var(--bg-secondary), var(--accent-primary)10);
  `}
`;

const StatLabel = styled.div`
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
`;

const StatValue = styled.div`
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  
  ${props => props.color && `color: ${props.color};`}
`;

const StatSubtext = styled.div`
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
`;

const ProgressRing = styled.div`
  position: relative;
  width: 120px;
  height: 120px;
  
  svg {
    transform: rotate(-90deg);
  }
  
  .bg {
    fill: none;
    stroke: var(--border-color);
    stroke-width: 10;
  }
  
  .progress {
    fill: none;
    stroke: var(--accent-primary);
    stroke-width: 10;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.5s ease;
  }
`;

const ProgressText = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
`;

const ProgressPercent = styled.div`
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
`;

const ProgressLabel = styled.div`
  font-size: 11px;
  color: var(--text-secondary);
`;

const TwoColumns = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  
  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
`;

const Card = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 24px;
  margin-bottom: 24px;
`;

const CardTitle = styled.h3`
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
`;

const ScoreBreakdown = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const ScoreItem = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const ScoreLabel = styled.div`
  width: 100px;
  font-size: 13px;
  color: var(--text-secondary);
`;

const ScoreBar = styled.div`
  flex: 1;
  height: 12px;
  background-color: var(--bg-tertiary);
  border-radius: 6px;
  overflow: hidden;
`;

const ScoreFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), #667eea);
  border-radius: 6px;
  transition: width 0.5s ease;
`;

const ScoreValue = styled.div`
  width: 50px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
`;

const RankingsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHeader = styled.th`
  text-align: left;
  padding: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-color);
`;

const TableRow = styled.tr`
  ${props => props.isCurrentUser && `
    background-color: var(--accent-primary)10;
  `}
  
  &:hover {
    background-color: var(--bg-tertiary);
  }
`;

const TableCell = styled.td`
  padding: 12px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
`;

const RankBadge = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 12px;
  
  ${props => {
    if (props.rank === 1) return 'background: linear-gradient(135deg, #f1c40f, #f39c12); color: #fff;';
    if (props.rank === 2) return 'background: linear-gradient(135deg, #bdc3c7, #95a5a6); color: #fff;';
    if (props.rank === 3) return 'background: linear-gradient(135deg, #e67e22, #d35400); color: #fff;';
    return 'background: var(--bg-tertiary); color: var(--text-secondary);';
  }}
`;

const RankChange = styled.span`
  font-size: 11px;
  margin-left: 6px;
  
  ${props => props.change > 0 ? 'color: #27ae60;' : props.change < 0 ? 'color: #e74c3c;' : 'color: var(--text-secondary);'}
`;

const ChartContainer = styled.div`
  margin-top: 20px;
`;

const ChartBars = styled.div`
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 150px;
  padding: 16px 0;
`;

const ChartBar = styled.div`
  flex: 1;
  background: linear-gradient(to top, var(--accent-primary), var(--accent-primary)60);
  border-radius: 4px 4px 0 0;
  position: relative;
  min-height: 4px;
  transition: height 0.3s ease;
  
  &:hover {
    opacity: 0.8;
  }
  
  &::after {
    content: attr(data-value);
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--text-secondary);
    opacity: 0;
    transition: opacity 0.2s;
  }
  
  &:hover::after {
    opacity: 1;
  }
`;

const ChartLabels = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 8px;
`;

const ChartLabel = styled.div`
  flex: 1;
  text-align: center;
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const InfoText = styled.div`
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
  font-size: 14px;
`;

const QualityPage = () => {
  const { taskId } = useParams();
  const [sortBy, setSortBy] = useState('overallScore');
  const [personalScore, setPersonalScore] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [trends, setTrends] = useState({ labels: [], annotations: [], scores: [] });
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all_time');

  useEffect(() => {
    if (taskId) {
      loadData();
    }
  }, [taskId, sortBy, period]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [personalRes, rankingsRes, trendsRes] = await Promise.all([
        qualityApi.getPersonal(ANNOTATOR, taskId).catch(() => ({ data: null })),
        qualityApi.getRankings(taskId, { sortBy, limit: 50 }),
        qualityApi.getTrends(ANNOTATOR, taskId, 'daily')
      ]);
      
      setPersonalScore(personalRes.data);
      setRankings(rankingsRes.data.rankings || []);
      setTrends(trendsRes.data);
    } catch (error) {
      console.error('Failed to load quality data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#27ae60';
    if (score >= 80) return '#2ecc71';
    if (score >= 70) return '#f39c12';
    if (score >= 60) return '#e67e22';
    return '#e74c3c';
  };

  const getRingDashOffset = (value) => {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    return circumference - (value / 100) * circumference;
  };

  if (!taskId) {
    return (
      <PageContainer>
        <InfoText>请从任务管理页面选择一个任务查看质量评分</InfoText>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader>
        <Title>标注质量评分</Title>
        <Subtitle>查看标注准确率和个人排名，持续提升标注质量</Subtitle>
      </PageHeader>

      <FilterBar>
        <Label>排序方式:</Label>
        <Select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="overallScore">综合得分</option>
          <option value="accuracyScore">准确率</option>
          <option value="consistencyScore">一致性</option>
          <option value="speedScore">速度</option>
          <option value="totalAnnotations">标注数量</option>
        </Select>
      </FilterBar>

      {loading ? (
        <InfoText>加载中...</InfoText>
      ) : (
        <>
          {personalScore && (
            <Card highlight>
              <CardTitle>📊 我的评分详情</CardTitle>
              <TwoColumns>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                  <ProgressRing>
                    <svg width="120" height="120" viewBox="0 0 120 120">
                      <circle className="bg" cx="60" cy="60" r="50" />
                      <circle 
                        className="progress" 
                        cx="60" 
                        cy="60" 
                        r="50"
                        strokeDasharray="314.16"
                        strokeDashoffset={getRingDashOffset(personalScore.overallScore)}
                        stroke={getScoreColor(personalScore.overallScore)}
                      />
                    </svg>
                    <ProgressText>
                      <ProgressPercent style={{ color: getScoreColor(personalScore.overallScore) }}>
                        {personalScore.overallScore}
                      </ProgressPercent>
                      <ProgressLabel>综合得分</ProgressLabel>
                    </ProgressText>
                  </ProgressRing>
                  
                  <StatsGrid style={{ gridTemplateColumns: '1fr 1fr', gap: '8px', width: '100%' }}>
                    <StatCard style={{ padding: '12px', textAlign: 'center' }}>
                      <StatLabel>排名</StatLabel>
                      <StatValue color="#f39c12">#{personalScore.rank}</StatValue>
                      <StatSubtext>共 {personalScore.totalAnnotators} 人</StatSubtext>
                    </StatCard>
                    <StatCard style={{ padding: '12px', textAlign: 'center' }}>
                      <StatLabel>百分位</StatLabel>
                      <StatValue color="#27ae60">Top {personalScore.percentile}%</StatValue>
                      <StatSubtext>优于 {personalScore.percentile}% 用户</StatSubtext>
                    </StatCard>
                  </StatsGrid>
                </div>
                
                <div>
                  <ScoreBreakdown>
                    <ScoreItem>
                      <ScoreLabel>准确率</ScoreLabel>
                      <ScoreBar>
                        <ScoreFill style={{ width: `${personalScore.accuracyScore}%`, background: 'linear-gradient(90deg, #27ae60, #2ecc71)' }} />
                      </ScoreBar>
                      <ScoreValue style={{ color: getScoreColor(personalScore.accuracyScore) }}>
                        {personalScore.accuracyScore}
                      </ScoreValue>
                    </ScoreItem>
                    
                    <ScoreItem>
                      <ScoreLabel>一致性</ScoreLabel>
                      <ScoreBar>
                        <ScoreFill style={{ width: `${personalScore.consistencyScore}%`, background: 'linear-gradient(90deg, #3498db, #2980b9)' }} />
                      </ScoreBar>
                      <ScoreValue style={{ color: getScoreColor(personalScore.consistencyScore) }}>
                        {personalScore.consistencyScore}
                      </ScoreValue>
                    </ScoreItem>
                    
                    <ScoreItem>
                      <ScoreLabel>速度</ScoreLabel>
                      <ScoreBar>
                        <ScoreFill style={{ width: `${personalScore.speedScore}%`, background: 'linear-gradient(90deg, #9b59b6, #8e44ad)' }} />
                      </ScoreBar>
                      <ScoreValue style={{ color: getScoreColor(personalScore.speedScore) }}>
                        {personalScore.speedScore}
                      </ScoreValue>
                    </ScoreItem>
                    
                    <ScoreItem>
                      <ScoreLabel>预标注接受率</ScoreLabel>
                      <ScoreBar>
                        <ScoreFill style={{ width: `${personalScore.preAnnotateAcceptRate}%`, background: 'linear-gradient(90deg, #f39c12, #e67e22)' }} />
                      </ScoreBar>
                      <ScoreValue style={{ color: getScoreColor(personalScore.preAnnotateAcceptRate) }}>
                        {personalScore.preAnnotateAcceptRate}%
                      </ScoreValue>
                    </ScoreItem>
                  </ScoreBreakdown>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginTop: '20px' }}>
                    <div style={{ textAlign: 'center', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {personalScore.entitiesAnnotated}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>实体标注</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {personalScore.relationsAnnotated}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>关系标注</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {personalScore.eventsAnnotated}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>事件标注</div>
                    </div>
                  </div>
                </div>
              </TwoColumns>
            </Card>
          )}

          {trends.labels?.length > 0 && (
            <Card>
              <CardTitle>📈 近期趋势</CardTitle>
              <ChartContainer>
                <ChartBars>
                  {trends.annotations?.slice(-14).map((value, i) => (
                    <ChartBar 
                      key={i} 
                      style={{ height: `${Math.max(5, (value / (Math.max(...trends.annotations.slice(-14)) || 1)) * 100)}%` }}
                      data-value={value}
                    />
                  ))}
                </ChartBars>
                <ChartLabels>
                  {trends.labels?.slice(-14).map((label, i) => (
                    <ChartLabel key={i}>{label.slice(5)}</ChartLabel>
                  ))}
                </ChartLabels>
                <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  标注数量趋势（近14天）
                </div>
              </ChartContainer>
            </Card>
          )}

          <Card>
            <CardTitle>🏆 标注排行榜</CardTitle>
            {rankings.length === 0 ? (
              <InfoText>暂无排名数据，开始标注后将显示排名</InfoText>
            ) : (
              <RankingsTable>
                <thead>
                  <tr>
                    <TableHeader>排名</TableHeader>
                    <TableHeader>标注者</TableHeader>
                    <TableHeader>综合得分</TableHeader>
                    <TableHeader>准确率</TableHeader>
                    <TableHeader>一致性</TableHeader>
                    <TableHeader>标注总数</TableHeader>
                  </tr>
                </thead>
                <tbody>
                  {rankings.map((r, index) => (
                    <TableRow key={index} isCurrentUser={r.annotator === ANNOTATOR}>
                      <TableCell>
                        <RankBadge rank={r.rank}>
                          {r.rank <= 3 ? ['🥇', '🥈', '🥉'][r.rank - 1] : r.rank}
                        </RankBadge>
                        <RankChange change={r.rankChange}>
                          {r.rankChange > 0 ? `↑${r.rankChange}` : r.rankChange < 0 ? `↓${Math.abs(r.rankChange)}` : '—'}
                        </RankChange>
                      </TableCell>
                      <TableCell>
                        {r.annotator}
                        {r.annotator === ANNOTATOR && <span style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--accent-primary)' }}>（我）</span>}
                      </TableCell>
                      <TableCell>
                        <strong style={{ color: getScoreColor(r.score) }}>{r.score}</strong>
                      </TableCell>
                      <TableCell style={{ color: getScoreColor(r.accuracy) }}>{r.accuracy}</TableCell>
                      <TableCell style={{ color: getScoreColor(r.consistency) }}>{r.consistency}</TableCell>
                      <TableCell>{r.annotations}</TableCell>
                    </TableRow>
                  ))}
                </tbody>
              </RankingsTable>
            )}
          </Card>
        </>
      )}
    </PageContainer>
  );
};

export default QualityPage;
