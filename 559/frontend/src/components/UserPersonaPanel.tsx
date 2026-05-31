import React from 'react';
import { Card, Tag, Progress } from 'antd';
import {
  TeamOutlined,
  WomanOutlined,
  ManOutlined,
  FireOutlined,
  DollarOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { UserPersona } from '../types';

interface UserPersonaPanelProps {
  persona: UserPersona;
}

const genderLabels: Record<string, string> = { female: '女性', male: '男性' };
const genderIcons: Record<string, React.ReactNode> = {
  female: <WomanOutlined style={{ color: '#ff9ff3' }} />,
  male: <ManOutlined style={{ color: '#48dbfb' }} />
};
const consumeLabels: Record<string, { label: string; color: string }> = {
  high: { label: '高消费', color: '#feca57' },
  medium: { label: '中消费', color: '#48dbfb' },
  low: { label: '低消费', color: '#ff9ff3' }
};
const priceSensLabels: Record<string, string> = {
  '150': '价格敏感', '250': '价格适中', '400': '价格不敏感'
};

export const UserPersonaPanel: React.FC<UserPersonaPanelProps> = ({ persona }) => {
  const totalUsers = persona.total_users;

  return (
    <Card
      title={<span><TeamOutlined /> 用户画像 <Tag color="blue" style={{ marginLeft: '6px', fontSize: '10px' }}>{totalUsers.toLocaleString()}人</Tag></span>}
      className="card-dark"
    >
      <div className="persona-section">
        <div className="section-label">性别分布</div>
        <div className="persona-bar-row">
          {Object.entries(persona.gender_distribution).map(([key, value]) => (
            <div key={key} className="persona-bar-item">
              <span className="persona-bar-icon">{genderIcons[key]}</span>
              <span className="persona-bar-label">{genderLabels[key]}</span>
              <div className="persona-bar-track">
                <div
                  className="persona-bar-fill"
                  style={{
                    width: `${value}%`,
                    background: key === 'female' ? 'linear-gradient(90deg, #ff9ff3, #f368e0)' : 'linear-gradient(90deg, #48dbfb, #0abde3)'
                  }}
                />
              </div>
              <span className="persona-bar-value">{value}%</span>
            </div>
          ))}
        </div>
      </div>

      <div className="persona-section">
        <div className="section-label">年龄段分布</div>
        <div className="persona-age-grid">
          {Object.entries(persona.age_distribution).map(([age, value]) => (
            <div key={age} className="persona-age-item">
              <div className="persona-age-label">{age}</div>
              <Progress
                percent={Math.round(value)}
                size="small"
                strokeColor="#48dbfb"
                trailColor="rgba(255,255,255,0.08)"
                showInfo={false}
              />
              <div className="persona-age-value">{value}%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="persona-section">
        <div className="section-label"><FireOutlined /> 兴趣偏好 TOP5</div>
        <div className="persona-interests">
          {Object.entries(persona.interest_distribution)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([interest, value], i) => (
              <div key={interest} className="persona-interest-item">
                <span className={`interest-rank rank-${i + 1}`}>{i + 1}</span>
                <span className="interest-name">{interest}</span>
                <div className="interest-bar-track">
                  <div
                    className="interest-bar-fill"
                    style={{
                      width: `${value}%`,
                      background: i < 3
                        ? 'linear-gradient(90deg, #feca57, #ff9f43)'
                        : 'linear-gradient(90deg, rgba(255,255,255,0.3), rgba(255,255,255,0.15))'
                    }}
                  />
                </div>
                <span className="interest-value">{value}%</span>
                {persona.top_interests.includes(interest) && (
                  <Tag color="gold" style={{ marginLeft: '4px', fontSize: '9px', padding: '0 3px', lineHeight: '16px' }}>
                    TOP
                  </Tag>
                )}
              </div>
            ))}
        </div>
      </div>

      <div className="persona-section">
        <div className="section-label"><DollarOutlined /> 消费能力</div>
        <div className="persona-consume-row">
          {Object.entries(persona.consume_level_distribution).map(([level, value]) => (
            <div key={level} className="persona-consume-item">
              <div
                className="consume-circle"
                style={{
                  borderColor: consumeLabels[level]?.color || '#fff',
                  boxShadow: `0 0 8px ${consumeLabels[level]?.color || '#fff'}33`
                }}
              >
                <span style={{ fontSize: '14px', fontWeight: 700, color: consumeLabels[level]?.color }}>
                  {value}%
                </span>
              </div>
              <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
                {consumeLabels[level]?.label}
              </div>
            </div>
          ))}
        </div>
        <div className="persona-price-sensitivity">
          <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>
            价格敏感度: ¥{persona.price_sensitivity}以下 · {priceSensLabels[String(persona.price_sensitivity)] || '适中'}
          </span>
        </div>
      </div>

      <div className="persona-section">
        <div className="section-label"><EnvironmentOutlined /> 地区分布</div>
        <div className="persona-region-row">
          {Object.entries(persona.region_distribution).map(([region, value]) => (
            <div key={region} className="persona-region-item">
              <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.6)' }}>{region}</span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#48dbfb' }}>{value}%</span>
            </div>
          ))}
        </div>
      </div>

      <div className="persona-impact">
        <div className="section-label">画像对推荐的影响</div>
        <div className="impact-tags">
          {persona.top_interests.map(interest => (
            <Tag key={interest} color="gold" style={{ fontSize: '10px' }}>
              {interest} +{Math.round(persona.interest_multiplier * 100)}%
            </Tag>
          ))}
          <Tag color="blue" style={{ fontSize: '10px' }}>
            ¥≤{persona.price_sensitivity} +{Math.round(persona.price_multiplier * 100)}%
          </Tag>
        </div>
      </div>
    </Card>
  );
};
