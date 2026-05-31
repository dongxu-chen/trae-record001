import React, { useState } from 'react';
import { Card, Tag, Button, Switch } from 'antd';
import {
  RobotOutlined,
  AudioOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  HistoryOutlined,
  ThunderboltOutlined,
  StockOutlined
} from '@ant-design/icons';
import { VirtualStreamerStatus, StreamerAction } from '../types';

interface VirtualStreamerPanelProps {
  streamer: VirtualStreamerStatus;
  action: StreamerAction;
}

const stateColors: Record<string, string> = {
  idle: '#8c8c8c',
  intro: '#48dbfb',
  urgency: '#ff6b6b',
  interaction: '#feca57',
  closing: '#52c41a',
  greeting: '#48dbfb'
};

export const VirtualStreamerPanel: React.FC<VirtualStreamerPanelProps> = ({ streamer, action }) => {
  const [enabled, setEnabled] = useState(true);

  return (
    <Card
      title={
        <span>
          <RobotOutlined /> {streamer.name}
          <Tag
            color={enabled ? 'success' : 'default'}
            style={{ marginLeft: '8px', fontSize: '10px' }}
          >
            {enabled ? '运行中' : '已暂停'}
          </Tag>
        </span>
      }
      className="card-dark"
      extra={
        <Switch
          size="small"
          checked={enabled}
          onChange={setEnabled}
          checkedChildren="ON"
          unCheckedChildren="OFF"
        />
      }
    >
      <div className="streamer-status-bar">
        <div className="streamer-avatar-container">
          <div
            className="streamer-avatar"
            style={{ borderColor: stateColors[streamer.state] || '#48dbfb' }}
          >
            <span style={{ fontSize: '24px' }}>{streamer.avatar}</span>
          </div>
          <div className="streamer-state-indicator" style={{ background: stateColors[streamer.state] || '#48dbfb' }}></div>
        </div>
        <div className="streamer-info">
          <div className="streamer-state-label">
            <span style={{ color: stateColors[streamer.state] || '#fff', fontWeight: 600, fontSize: '14px' }}>
              {streamer.state_label}
            </span>
          </div>
          {streamer.current_product && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
              正在讲解: <span style={{ color: '#feca57' }}>{streamer.current_product}</span>
            </div>
          )}
          <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>
            已执行 {streamer.total_speeches} 条话术
          </div>
        </div>
      </div>

      <div className="streamer-current-script">
        <div className="section-label"><AudioOutlined /> 当前话术</div>
        <div className="streamer-script-bubble">
          <div className="streamer-script-text">{streamer.current_script || '等待中...'}</div>
        </div>
        {action.auto_action && (
          <div className="streamer-auto-action">
            <Tag color="red" style={{ fontSize: '10px' }}>
              <StockOutlined /> 自动操作: {action.auto_action.type === 'restock_alert' ? '补货提醒' : action.auto_action.type}
              — {action.auto_action.product} 库存{action.auto_action.stock}
            </Tag>
          </div>
        )}
      </div>

      <div className="streamer-history">
        <div className="section-label"><HistoryOutlined /> 话术历史</div>
        <div className="streamer-history-list">
          {streamer.script_history.slice().reverse().slice(0, 5).map((item, i) => (
            <div key={i} className="streamer-history-item">
              <div className="history-state-dot" style={{ background: stateColors[item.state] || '#8c8c8c' }}></div>
              <div className="history-content">
                <div className="history-meta">
                  <Tag
                    style={{
                      fontSize: '9px',
                      padding: '0 3px',
                      lineHeight: '14px',
                      background: `${stateColors[item.state] || '#8c8c8c'}22`,
                      color: stateColors[item.state] || '#8c8c8c',
                      border: 'none',
                      margin: 0
                    }}
                  >
                    {item.state === 'intro' ? '介绍' :
                     item.state === 'urgency' ? '促单' :
                     item.state === 'interaction' ? '互动' :
                     item.state === 'closing' ? '过渡' :
                     item.state === 'greeting' ? '问候' : item.state}
                  </Tag>
                  {item.product && (
                    <span style={{ fontSize: '10px', color: '#feca57', marginLeft: '4px' }}>{item.product}</span>
                  )}
                  <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.3)', marginLeft: 'auto' }}>
                    {new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                <div className="history-script">{item.script}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};
