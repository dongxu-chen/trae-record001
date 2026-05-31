import React, { useState, useEffect } from 'react';
import {
  fetchAllHeatTiers,
  fetchHeatTierStats,
  HeatTierStats,
} from '../api/apiClient';

interface Props {}

const HeatTierPanel: React.FC<Props> = () => {
  const [heatTiers, setHeatTiers] = useState<Record<string, string>>({});
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [serviceStats, setServiceStats] = useState<HeatTierStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHeatTiers = async () => {
      try {
        const res = await fetchAllHeatTiers();
        setHeatTiers(res.data);
      } catch (e) {
        console.error('Failed to load heat tiers', e);
      } finally {
        setLoading(false);
      }
    };
    loadHeatTiers();
    const interval = setInterval(loadHeatTiers, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedService) {
      const loadStats = async () => {
        try {
          const res = await fetchHeatTierStats(selectedService);
          setServiceStats(res.data);
        } catch (e) {
          console.error('Failed to load heat stats', e);
        }
      };
      loadStats();
      const interval = setInterval(loadStats, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedService]);

  const getTierStyle = (tier: string) => {
    return {
      HOT: { bg: '#7f1d1d', color: '#fca5a5', icon: '🔥', label: '热' },
      WARM: { bg: '#422006', color: '#fbbf24', icon: '☀️', label: '温' },
      COLD: { bg: '#1e3a8a', color: '#93c5fd', icon: '❄️', label: '冷' },
    }[tier] || { bg: '#1e293b', color: '#94a3b8', icon: '⚪', label: '未知' };
  };

  const tierDistribution = React.useMemo(() => {
    const dist: Record<string, number> = { HOT: 0, WARM: 0, COLD: 0 };
    Object.values(heatTiers).forEach(tier => {
      if (dist[tier] !== undefined) {
        dist[tier]++;
      }
    });
    return dist;
  }, [heatTiers]);

  const totalServices = Object.keys(heatTiers).length || 1;

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
        🔥 冷热数据存储策略
      </h3>

      {loading ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: '20px' }}>
          加载中...
        </div>
      ) : (
        <>
          {}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            {(['HOT', 'WARM', 'COLD'] as const).map(tier => {
              const style = getTierStyle(tier);
              const count = tierDistribution[tier] || 0;
              const percent = (count / totalServices) * 100;
              return (
                <div
                  key={tier}
                  style={{
                    flex: 1,
                    background: '#0f172a',
                    borderRadius: '8px',
                    padding: '10px',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>{style.icon}</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>{style.label}数据</div>
                  <div style={{ fontSize: '16px', fontWeight: 700, color: style.color }}>
                    {count} ({percent.toFixed(0)}%)
                  </div>
                </div>
              );
            })}
          </div>

          {}
          <div style={{ marginBottom: '12px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' }}>服务列表</h4>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {Object.entries(heatTiers).map(([service, tier]) => {
                const style = getTierStyle(tier);
                return (
                  <div
                    key={service}
                    onClick={() => setSelectedService(service)}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      marginBottom: '4px',
                      cursor: 'pointer',
                      background: selectedService === service ? style.bg + '40' : '#0f172a',
                      border: selectedService === service ? `1px solid ${style.color}` : '1px solid transparent',
                      transition: 'all 0.2s',
                    }}
                  >
                    <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                      {service.replace('-service', '')}
                    </span>
                    <span style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: style.bg,
                      color: style.color,
                      fontWeight: 600,
                    }}>
                      {style.icon} {style.label}
                    </span>
                  </div>
                );
              })}
              {Object.keys(heatTiers).length === 0 && (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '20px' }}>
                  暂无数据
                </div>
              )}
            </div>
          </div>

          {}
          {selectedService && serviceStats && (
            <div style={{
              background: '#0f172a',
              borderRadius: '8px',
              padding: '12px',
              border: '1px solid #334155',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>
                  {selectedService.replace('-service', '')} 详情
                </span>
                <span style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: getTierStyle(serviceStats.heatTier).bg,
                  color: getTierStyle(serviceStats.heatTier).color,
                  fontWeight: 600,
                }}>
                  {getTierStyle(serviceStats.heatTier).icon} {getTierStyle(serviceStats.heatTier).label}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
                <div style={{ background: '#1e293b', padding: '6px 8px', borderRadius: '4px' }}>
                  <div style={{ color: '#64748b' }}>最后访问</div>
                  <div style={{ color: '#f1f5f9', fontWeight: 600 }}>
                    {serviceStats.timeSinceLastAccessMs > 0
                      ? `${(serviceStats.timeSinceLastAccessMs / 1000).toFixed(0)}s 前`
                      : '活跃中'}
                  </div>
                </div>
                <div style={{ background: '#1e293b', padding: '6px 8px', borderRadius: '4px' }}>
                  <div style={{ color: '#64748b' }}>最近5分钟访问</div>
                  <div style={{ color: '#f1f5f9', fontWeight: 600 }}>
                    {serviceStats.recentAccessCount?.toLocaleString() || 0} 次
                  </div>
                </div>
                <div style={{ background: '#1e293b', padding: '6px 8px', borderRadius: '4px' }}>
                  <div style={{ color: '#64748b' }}>总访问量</div>
                  <div style={{ color: '#f1f5f9', fontWeight: 600 }}>
                    {serviceStats.totalAccessCount?.toLocaleString() || 0}
                  </div>
                </div>
                <div style={{ background: '#1e293b', padding: '6px 8px', borderRadius: '4px' }}>
                  <div style={{ color: '#64748b' }}>调整后采样率</div>
                  <div style={{ color: '#3b82f6', fontWeight: 600 }}>
                    {(serviceStats.adjustedSamplingRate * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '10px', fontSize: '10px', color: '#64748b' }}>
                <div>策略说明：</div>
                <div>• 🔥 热数据（5分钟内访问）: 高采样 90%</div>
                <div>• ☀️ 温数据（1小时内访问）: 中采样 50%</div>
                <div>• ❄️ 冷数据（超过1小时）: 低采样 5%</div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default HeatTierPanel;
