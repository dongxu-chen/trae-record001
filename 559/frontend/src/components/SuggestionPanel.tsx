import React from 'react';
import { Card, Tag, Progress } from 'antd';
import {
  BulbOutlined,
  SmileOutlined,
  FrownOutlined,
  MehOutlined,
  ShoppingCartOutlined,
  ThunderboltOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined
} from '@ant-design/icons';
import { SentimentSummary, HotWord, GuidedScript } from '../types';

interface SuggestionPanelProps {
  sentiment: SentimentSummary;
  hotWords: HotWord[];
  guidedScripts: GuidedScript[];
}

const trendIcons = {
  rising: <ArrowUpOutlined style={{ color: '#52c41a' }} />,
  declining: <ArrowDownOutlined style={{ color: '#ff4d4f' }} />,
  stable: <MinusOutlined style={{ color: '#faad14' }} />
};

const trendLabels = {
  rising: '上升',
  declining: '下降',
  stable: '平稳'
};

const priorityColors: Record<string, string> = {
  urgent: '#ff4d4f',
  high: '#faad14',
  medium: '#1890ff'
};

const categoryColors: Record<string, string> = {
  price: 'red',
  quality: 'blue',
  logistics: 'green',
  service: 'orange',
  feature: 'purple',
  other: 'default'
};

const categoryLabels: Record<string, string> = {
  price: '价格',
  quality: '品质',
  logistics: '物流',
  service: '服务',
  feature: '特色',
  other: '其他'
};

const scriptTypeLabels: Record<string, string> = {
  conversion_boost: '转化提升',
  damage_control: '危机公关',
  question_response: '问题回应',
  heat_boost: '热度提升',
  hot_product_push: '爆款推广',
  price_advantage: '价格优势'
};

export const SuggestionPanel: React.FC<SuggestionPanelProps> = ({
  sentiment,
  hotWords,
  guidedScripts
}) => {
  const sentimentColor = (ratio: number, inverse = false) => {
    const val = inverse ? 100 - ratio : ratio;
    if (val > 60) return '#52c41a';
    if (val > 30) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <Card
      title={<span><BulbOutlined /> 情感分析 & 引导话术</span>}
      className="card-dark"
    >
      <div className="sentiment-section">
        <div className="section-label">实时情感分析</div>
        <div className="sentiment-bar-container">
          <div className="sentiment-bar">
            <div
              className="sentiment-segment segment-positive"
              style={{ width: `${sentiment.positive_ratio}%` }}
            />
            <div
              className="sentiment-segment segment-intent"
              style={{ width: `${sentiment.intent_buy_ratio}%` }}
            />
            <div
              className="sentiment-segment segment-neutral"
              style={{ width: `${sentiment.neutral_ratio}%` }}
            />
            <div
              className="sentiment-segment segment-negative"
              style={{ width: `${sentiment.negative_ratio}%` }}
            />
          </div>
          <div className="sentiment-legend">
            <span className="legend-item">
              <SmileOutlined style={{ color: '#52c41a' }} /> 好评 {sentiment.positive_ratio}%
            </span>
            <span className="legend-item">
              <ShoppingCartOutlined style={{ color: '#48dbfb' }} /> 购买意向 {sentiment.intent_buy_ratio}%
            </span>
            <span className="legend-item">
              <MehOutlined style={{ color: '#faad14' }} /> 中性 {sentiment.neutral_ratio}%
            </span>
            <span className="legend-item">
              <FrownOutlined style={{ color: '#ff4d4f' }} /> 负面 {sentiment.negative_ratio}%
            </span>
          </div>
        </div>
        <div className="sentiment-score-row">
          <div className="sentiment-score">
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px' }}>情感评分</span>
            <span style={{
              fontSize: '24px',
              fontWeight: 700,
              color: sentimentColor(sentiment.overall_score)
            }}>
              {sentiment.overall_score}
            </span>
          </div>
          <div className="sentiment-trend">
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px' }}>趋势</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {trendIcons[sentiment.trend]}
              <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)' }}>
                {trendLabels[sentiment.trend]}
              </span>
            </span>
          </div>
        </div>
      </div>

      <div className="hot-words-section">
        <div className="section-label">热点词提取</div>
        <div className="hot-words-cloud">
          {hotWords.slice(0, 8).map((hw, i) => (
            <Tag
              key={i}
              color={categoryColors[hw.category] || 'default'}
              style={{
                fontSize: Math.max(12, 18 - i * 1.2),
                fontWeight: i < 3 ? 700 : 400,
                margin: '2px 4px',
                cursor: 'default'
              }}
            >
              {hw.word}
              <span style={{ fontSize: '10px', opacity: 0.7, marginLeft: '2px' }}>
                {hw.count}
              </span>
            </Tag>
          ))}
        </div>
      </div>

      <div className="guided-scripts-section">
        <div className="section-label">
          <ThunderboltOutlined /> AI引导话术
        </div>
        {guidedScripts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '12px', color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
            暂无话术建议
          </div>
        ) : (
          guidedScripts.map((gs, i) => (
            <div key={i} className="guided-script-item">
              <div className="script-header">
                <Tag
                  color={priorityColors[gs.priority]}
                  style={{ margin: 0, fontSize: '10px' }}
                >
                  {gs.priority === 'urgent' ? '紧急' : gs.priority === 'high' ? '重要' : '建议'}
                </Tag>
                <Tag
                  style={{ margin: 0, fontSize: '10px', background: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.7)', border: 'none' }}
                >
                  {scriptTypeLabels[gs.type] || gs.type}
                </Tag>
              </div>
              <div className="script-content">{gs.script}</div>
              <div className="script-reason">{gs.reason}</div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
