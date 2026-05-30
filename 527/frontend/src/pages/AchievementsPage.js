import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import styled from 'styled-components';
import { achievementApi } from '../services/api';

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

const Tabs = styled.div`
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background-color: var(--bg-secondary);
  padding: 4px;
  border-radius: 8px;
  width: fit-content;
`;

const Tab = styled.button`
  padding: 10px 20px;
  border: none;
  background: ${props => props.active ? 'var(--accent-primary)' : 'transparent'};
  color: ${props => props.active ? 'white' : 'var(--text-secondary)'};
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    color: ${props => props.active ? 'white' : 'var(--text-primary)'};
  }
`;

const SummaryRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
`;

const SummaryCard = styled.div`
  background: linear-gradient(135deg, var(--bg-secondary), var(--accent-primary)10);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  
  ${props => props.highlight && `
    border-color: var(--accent-primary);
    background: linear-gradient(135deg, var(--accent-primary)20, var(--accent-primary)05);
  `}
`;

const SummaryValue = styled.div`
  font-size: 32px;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 4px;
  
  ${props => props.color && `color: ${props.color};`}
`;

const SummaryLabel = styled.div`
  font-size: 13px;
  color: var(--text-secondary);
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

const AchievementsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
`;

const AchievementCard = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  
  ${props => props.unlocked ? `
    border-color: var(--accent-primary);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
  ` : `
    opacity: 0.6;
  `}
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
`;

const AchievementIcon = styled.div`
  font-size: 48px;
  text-align: center;
  margin-bottom: 12px;
  
  ${props => !props.unlocked && `
    filter: grayscale(100%);
    opacity: 0.5;
  `}
`;

const RarityBadge = styled.span`
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  
  ${props => {
    const colors = {
      common: { bg: '#95a5a6', color: '#fff' },
      rare: { bg: '#3498db', color: '#fff' },
      epic: { bg: '#9b59b6', color: '#fff' },
      legendary: { bg: 'linear-gradient(135deg, #f1c40f, #e74c3c)', color: '#fff' }
    };
    const c = colors[props.rarity] || colors.common;
    return `
      background: ${c.bg};
      color: ${c.color};
    `;
  }}
`;

const PointsBadge = styled.span`
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  background: var(--accent-primary);
  color: white;
`;

const AchievementName = styled.h3`
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 8px;
`;

const AchievementDesc = styled.p`
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: 16px;
  line-height: 1.4;
`;

const ProgressBar = styled.div`
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), #667eea);
  border-radius: 4px;
  transition: width 0.5s ease;
  
  ${props => props.unlocked && `
    background: linear-gradient(90deg, #27ae60, #2ecc71);
  `}
`;

const ProgressText = styled.div`
  font-size: 11px;
  color: var(--text-secondary);
  text-align: center;
`;

const UnlockedAt = styled.div`
  font-size: 11px;
  color: #27ae60;
  text-align: center;
  margin-top: 8px;
`;

const CategoryFilter = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
`;

const CategoryChip = styled.button`
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid ${props => props.active ? 'var(--accent-primary)' : 'var(--border-color)'};
  background: ${props => props.active ? 'var(--accent-primary)' : 'transparent'};
  color: ${props => props.active ? 'white' : 'var(--text-secondary)'};
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: var(--accent-primary);
  }
`;

const LeaderboardTable = styled.table`
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
  padding: 16px 12px;
  font-size: 14px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
`;

const RankBadge = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 14px;
  
  ${props => {
    if (props.rank === 1) return 'background: linear-gradient(135deg, #f1c40f, #f39c12); color: #fff; box-shadow: 0 0 20px rgba(241, 196, 15, 0.4);';
    if (props.rank === 2) return 'background: linear-gradient(135deg, #bdc3c7, #95a5a6); color: #fff;';
    if (props.rank === 3) return 'background: linear-gradient(135deg, #e67e22, #d35400); color: #fff;';
    return 'background: var(--bg-tertiary); color: var(--text-secondary);';
  }}
`;

const RankChange = styled.span`
  font-size: 12px;
  margin-left: 8px;
  
  ${props => props.change > 0 ? 'color: #27ae60;' : props.change < 0 ? 'color: #e74c3c;' : 'color: var(--text-secondary);'}
`;

const PeriodTabs = styled.div`
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
`;

const PeriodTab = styled.button`
  padding: 8px 16px;
  border: 1px solid ${props => props.active ? 'var(--accent-primary)' : 'var(--border-color)'};
  background: ${props => props.active ? 'var(--accent-primary)' : 'var(--bg-secondary)'};
  color: ${props => props.active ? 'white' : 'var(--text-secondary)'};
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  
  &:hover {
    border-color: var(--accent-primary);
  }
`;

const ToastNotification = styled.div`
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0);
  background: linear-gradient(135deg, var(--accent-primary), #667eea);
  color: white;
  padding: 32px 48px;
  border-radius: 16px;
  text-align: center;
  z-index: 3000;
  animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
  box-shadow: 0 20px 60px rgba(99, 102, 241, 0.4);
  
  @keyframes popIn {
    0% { transform: translate(-50%, -50%) scale(0); }
    100% { transform: translate(-50%, -50%) scale(1); }
  }
`;

const ToastIcon = styled.div`
  font-size: 64px;
  margin-bottom: 16px;
`;

const ToastTitle = styled.div`
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
`;

const ToastName = styled.div`
  font-size: 18px;
  margin-bottom: 4px;
`;

const ToastPoints = styled.div`
  font-size: 14px;
  opacity: 0.9;
`;

const InfoText = styled.div`
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
`;

const Card = styled.div`
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 24px;
`;

const AchievementsPage = () => {
  const { taskId } = useParams();
  const [activeTab, setActiveTab] = useState('achievements');
  const [achievements, setAchievements] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [summary, setSummary] = useState(null);
  const [category, setCategory] = useState('');
  const [period, setPeriod] = useState('all_time');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (taskId) {
      loadData();
    }
  }, [taskId, activeTab, category, period]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      if (activeTab === 'achievements') {
        const [achRes, summaryRes] = await Promise.all([
          achievementApi.getUserAchievements(ANNOTATOR, taskId),
          achievementApi.getSummary(ANNOTATOR, taskId)
        ]);
        
        setAchievements(achRes.data.achievements || []);
        setSummary(summaryRes.data);
      } else {
        const lbRes = await achievementApi.getLeaderboard(taskId, { period, limit: 50 });
        setLeaderboard(lbRes.data.rankings || []);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredAchievements = category 
    ? achievements.filter(a => a.category === category)
    : achievements;

  const getCategoryLabel = (cat) => {
    const labels = {
      annotation: '标注数量',
      quality: '质量',
      speed: '速度',
      streak: '连续打卡',
      special: '特殊'
    };
    return labels[cat] || cat;
  };

  const getRarityLabel = (rarity) => {
    const labels = {
      common: '普通',
      rare: '稀有',
      epic: '史诗',
      legendary: '传说'
    };
    return labels[rarity] || rarity;
  };

  if (!taskId) {
    return (
      <PageContainer>
        <InfoText>请从任务管理页面选择一个任务查看成就系统</InfoText>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader>
        <Title>🏆 成就中心</Title>
        <Subtitle>完成任务解锁成就，和其他标注者一起比拼排名</Subtitle>
      </PageHeader>

      <Tabs>
        <Tab active={activeTab === 'achievements'} onClick={() => setActiveTab('achievements')}>
          🎖️ 我的成就
        </Tab>
        <Tab active={activeTab === 'leaderboard'} onClick={() => setActiveTab('leaderboard')}>
          🏆 排行榜
        </Tab>
      </Tabs>

      {loading ? (
        <InfoText>加载中...</InfoText>
      ) : activeTab === 'achievements' ? (
        <>
          {summary && (
            <SummaryRow>
              <SummaryCard highlight>
                <SummaryValue color="var(--accent-primary)">{summary.totalPoints || 0}</SummaryValue>
                <SummaryLabel>总积分</SummaryLabel>
              </SummaryCard>
              <SummaryCard>
                <SummaryValue>{summary.achievementsCount || 0}/{summary.totalAchievementsCount}</SummaryValue>
                <SummaryLabel>已解锁成就</SummaryLabel>
              </SummaryCard>
              <SummaryCard>
                <SummaryValue color="#f39c12">#{summary.rank || '-'}</SummaryValue>
                <SummaryLabel>当前排名 / {summary.totalAnnotators}人</SummaryLabel>
              </SummaryCard>
              <SummaryCard>
                <SummaryValue color="#27ae60">{summary.totalAnnotations || 0}</SummaryValue>
                <SummaryLabel>标注总数</SummaryLabel>
              </SummaryCard>
            </SummaryRow>
          )}

          <FilterBar>
            <Label>分类:</Label>
            <CategoryFilter>
              <CategoryChip active={!category} onClick={() => setCategory('')}>
                全部
              </CategoryChip>
              {['annotation', 'quality', 'speed', 'streak', 'special'].map(cat => (
                <CategoryChip 
                  key={cat} 
                  active={category === cat} 
                  onClick={() => setCategory(cat)}
                >
                  {getCategoryLabel(cat)}
                </CategoryChip>
              ))}
            </CategoryFilter>
            
            <span style={{ marginLeft: 'auto', color: 'var(--text-secondary)', fontSize: '13px' }}>
              已解锁 {achievements.filter(a => a.unlocked).length} / {achievements.length}
            </span>
          </FilterBar>

          {filteredAchievements.length === 0 ? (
            <InfoText>暂无该分类的成就</InfoText>
          ) : (
            <AchievementsGrid>
              {filteredAchievements.map(achievement => (
                <AchievementCard key={achievement._id || achievement.id} unlocked={achievement.unlocked}>
                  <PointsBadge>+{achievement.points}分</PointsBadge>
                  <RarityBadge rarity={achievement.rarity}>
                    {getRarityLabel(achievement.rarity)}
                  </RarityBadge>
                  
                  <AchievementIcon unlocked={achievement.unlocked}>
                    {achievement.icon}
                  </AchievementIcon>
                  
                  <AchievementName>{achievement.name}</AchievementName>
                  <AchievementDesc>{achievement.description}</AchievementDesc>
                  
                  <ProgressBar>
                    <ProgressFill 
                      unlocked={achievement.unlocked}
                      style={{ width: `${achievement.progressPercent}%` }} 
                    />
                  </ProgressBar>
                  
                  <ProgressText>
                    {achievement.progress} / {achievement.requirement.value}
                    {' '}
                    ({achievement.progressPercent}%)
                  </ProgressText>
                  
                  {achievement.unlocked && achievement.unlockedAt && (
                    <UnlockedAt>
                      ✅ 解锁于 {new Date(achievement.unlockedAt).toLocaleDateString()}
                    </UnlockedAt>
                  )}
                </AchievementCard>
              ))}
            </AchievementsGrid>
          )}
        </>
      ) : (
        <Card>
          <PeriodTabs>
            {[
              { key: 'daily', label: '今日' },
              { key: 'weekly', label: '本周' },
              { key: 'monthly', label: '本月' },
              { key: 'all_time', label: '总榜' }
            ].map(p => (
              <PeriodTab 
                key={p.key} 
                active={period === p.key}
                onClick={() => setPeriod(p.key)}
              >
                {p.label}
              </PeriodTab>
            ))}
          </PeriodTabs>

          {leaderboard.length === 0 ? (
            <InfoText>暂无排行数据，开始标注后将显示排名</InfoText>
          ) : (
            <LeaderboardTable>
              <thead>
                <tr>
                  <TableHeader style={{ width: '80px' }}>排名</TableHeader>
                  <TableHeader>标注者</TableHeader>
                  <TableHeader>积分</TableHeader>
                  <TableHeader>综合得分</TableHeader>
                  <TableHeader>标注数</TableHeader>
                  <TableHeader>准确率</TableHeader>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((r, index) => (
                  <TableRow key={index} isCurrentUser={r.annotator === ANNOTATOR}>
                    <TableCell>
                      <RankBadge rank={r.rank}>
                        {r.rank <= 3 ? ['🥇', '🥈', '🥉'][r.rank - 1] : r.rank}
                      </RankBadge>
                      {r.rankChange !== undefined && (
                        <RankChange change={r.rankChange}>
                          {r.rankChange > 0 ? `↑${r.rankChange}` : r.rankChange < 0 ? `↓${Math.abs(r.rankChange)}` : '—'}
                        </RankChange>
                      )}
                    </TableCell>
                    <TableCell>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ 
                          width: '32px', height: '32px', borderRadius: '50%',
                          background: `linear-gradient(135deg, var(--accent-primary), #667eea)`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: 'white', fontWeight: '600', fontSize: '14px'
                        }}>
                          {r.annotator.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: '500' }}>
                            {r.annotator}
                            {r.annotator === ANNOTATOR && (
                              <span style={{ marginLeft: '6px', fontSize: '11px', color: 'var(--accent-primary)' }}>
                                （我）
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <strong style={{ color: 'var(--accent-primary)' }}>
                        {r.totalPoints?.toLocaleString() || 0}
                      </strong>
                    </TableCell>
                    <TableCell>
                      <strong>{r.score}</strong>
                    </TableCell>
                    <TableCell>{r.annotations}</TableCell>
                    <TableCell>
                      <span style={{ 
                        color: r.accuracy >= 90 ? '#27ae60' : r.accuracy >= 70 ? '#f39c12' : '#e74c3c' 
                      }}>
                        {r.accuracy}%
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </tbody>
            </LeaderboardTable>
          )}
        </Card>
      )}

      {toast && (
        <ToastNotification>
          <ToastIcon>{toast.icon}</ToastIcon>
          <ToastTitle>🎉 成就解锁！</ToastTitle>
          <ToastName>{toast.name}</ToastName>
          <ToastPoints>+{toast.points} 积分</ToastPoints>
        </ToastNotification>
      )}
    </PageContainer>
  );
};

export default AchievementsPage;
