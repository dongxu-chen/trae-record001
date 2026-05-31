import React, { useState, useEffect } from 'react';
import { Card, Tag } from 'antd';
import {
  EyeOutlined,
  RiseOutlined,
  UserOutlined,
  ThunderboltOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  CheckCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { CompetitorRealtimeData } from '../types';

interface CompetitorMonitorProps {
  competitors: Record<string, CompetitorRealtimeData>;
}

const trendIcons = {
  up: <ArrowUpOutlined style={{ color: '#ff4d4f', fontSize: '12px' }} />,
  down: <ArrowDownOutlined style={{ color: '#52c41a', fontSize: '12px' }} />,
  stable: <MinusOutlined style={{ color: '#faad14', fontSize: '12px' }} />
};

const trendLabels = { up: '涨价', down: '降价', stable: '持平' };

export const CompetitorMonitor: React.FC<CompetitorMonitorProps> = ({ competitors }) => {
  const competitorList = Object.values(competitors);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [latencyMs, setLatencyMs] = useState<number>(0);

  useEffect(() => {
    if (competitorList.length > 0) {
      setLastUpdate(competitorList[0].timestamp);
      const maxLatency = Math.max(...competitorList.map(c => c.update_latency_ms));
      setLatencyMs(maxLatency);
    }
  }, [competitorList]);

  const getMiniChartOption = (priceHistory: { timestamp: string; price: number }[]) => {
    if (!priceHistory || priceHistory.length < 2) return {};
    return {
      grid: { left: 0, right: 0, top: 2, bottom: 2 },
      xAxis: { type: 'category', show: false, data: priceHistory.map((_, i) => i) },
      yAxis: { type: 'value', show: false, min: (value: { min: number }) => value.min - 2 },
      series: [{
        type: 'line',
        data: priceHistory.map(p => p.price),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: priceHistory[priceHistory.length - 1].price >= priceHistory[0].price ? '#ff6b6b' : '#52c41a', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 107, 107, 0.15)' },
              { offset: 1, color: 'rgba(255, 107, 107, 0)' }
            ]
          }
        }
      }],
      tooltip: { show: false }
    };
  };

  return (
    <Card
      title={
        <span>
          <EyeOutlined /> 竞品秒级监控
          <Tag
            color={latencyMs > 0 && latencyMs < 1000 ? '#52c41a' : '#faad14'}
            style={{ marginLeft: '8px', fontSize: '10px' }}
          >
            <ThunderboltOutlined /> {latencyMs > 0 ? `${latencyMs}ms` : '实时'}
          </Tag>
        </span>
      }
      className="card-dark"
    >
      <div className="realtime-indicator">
        <span className="realtime-dot"></span>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
          每秒刷新 · {lastUpdate ? new Date(lastUpdate).toLocaleTimeString('zh-CN') : '--:--:--'}
        </span>
      </div>

      {competitorList.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px', color: 'rgba(255,255,255,0.5)' }}>
          暂无竞品数据
        </div>
      ) : (
        competitorList.map((competitor) => (
          <div key={competitor.competitor_id} className="competitor-card realtime-competitor">
            <div className="competitor-main-row">
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>
                    {competitor.competitor_name}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                    {trendIcons[competitor.price_trend]}
                    <span style={{
                      fontSize: '10px',
                      color: competitor.price_trend === 'up' ? '#ff4d4f' : competitor.price_trend === 'down' ? '#52c41a' : '#faad14'
                    }}>
                      {trendLabels[competitor.price_trend]}
                    </span>
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '2px' }}>
                  商品: {competitor.product}
                </div>
              </div>

              <div style={{ width: '80px', height: '30px' }}>
                {competitor.price_history && competitor.price_history.length >= 2 && (
                  <ReactECharts
                    option={getMiniChartOption(competitor.price_history)}
                    style={{ height: '30px', width: '80px' }}
                  />
                )}
              </div>

              <div style={{ textAlign: 'right', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#ff6b6b' }}>
                  ¥{competitor.current_price}
                </div>
              </div>
            </div>

            <div className="competitor-price-compare">
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                我方: ¥{competitor.our_price}
              </span>
              {competitor.price_advantage ? (
                <Tag
                  icon={<CheckCircleOutlined />}
                  color="success"
                  style={{ margin: 0, fontSize: '10px', padding: '0 4px' }}
                >
                  价格优势 ¥{Math.abs(competitor.price_diff)}
                </Tag>
              ) : (
                <Tag
                  icon={<WarningOutlined />}
                  color="error"
                  style={{ margin: 0, fontSize: '10px', padding: '0 4px' }}
                >
                  价格劣势 ¥{Math.abs(competitor.price_diff)}
                </Tag>
              )}
            </div>

            <div className="competitor-stats-row">
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>
                <UserOutlined /> {competitor.viewer_count.toLocaleString()}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>
                <RiseOutlined /> {competitor.sales_volume}
              </span>
              <span style={{
                color: competitor.update_latency_ms < 500 ? '#52c41a' : '#faad14',
                fontSize: '10px'
              }}>
                <ThunderboltOutlined /> {competitor.update_latency_ms}ms
              </span>
            </div>
          </div>
        ))
      )}
    </Card>
  );
};
