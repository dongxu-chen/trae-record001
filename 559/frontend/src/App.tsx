import React, { useState } from 'react';
import { Row, Col, Card, Statistic, message } from 'antd';
import {
  UserOutlined,
  ClickOutlined,
  ShoppingCartOutlined,
  RiseOutlined,
  FireOutlined
} from '@ant-design/icons';
import { useWebSocket } from './hooks/useWebSocket';
import { TrendChart } from './components/TrendChart';
import { ProductBarChart } from './components/ProductBarChart';
import { ChatPieChart } from './components/ChatPieChart';
import { SuggestionPanel } from './components/SuggestionPanel';
import { ProductRecommendation } from './components/ProductRecommendation';
import { CompetitorMonitor } from './components/CompetitorMonitor';
import { UserPersonaPanel } from './components/UserPersonaPanel';
import { VirtualStreamerPanel } from './components/VirtualStreamerPanel';
import { HotProductPrediction } from './components/HotProductPrediction';
import { OptimizedProduct } from './types';

const App: React.FC = () => {
  const { data, connected } = useWebSocket();
  const [currentProduct, setCurrentProduct] = useState<OptimizedProduct | null>(null);

  const handleSwitchProduct = (product: OptimizedProduct) => {
    setCurrentProduct(product);
    message.success(`已切换讲解: ${product.name}`);
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>直播带货数据实时分析面板</h1>
        <div className={`connection-status ${connected ? 'status-connected' : 'status-disconnected'}`}>
          <span className="status-dot" style={{ background: connected ? '#52c41a' : '#ff4d4f' }}></span>
          {connected ? '实时连接中' : '连接断开'}
        </div>
        {currentProduct && (
          <div style={{ marginTop: '8px', color: '#feca57' }}>
            当前讲解: {currentProduct.name}
            {currentProduct.persona_boosted && (
              <span style={{ color: '#48dbfb', marginLeft: '8px', fontSize: '12px' }}>✦ 画像加权</span>
            )}
            {currentProduct.stock_status === 'danger' && (
              <span style={{ color: '#ff4d4f', marginLeft: '8px' }}>库存告急!</span>
            )}
          </div>
        )}
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card className="card-dark stat-card">
            <Statistic
              title={<span className="stat-label"><UserOutlined /> 观看人数</span>}
              value={data?.current_viewers || 0}
              valueStyle={{ color: '#48dbfb' }}
              formatter={(value) => <span className="stat-value">{value.toLocaleString()}</span>}
            />
            <div className="stat-change" style={{ color: data && data.current_viewers > 1500 ? '#52c41a' : '#ff4d4f' }}>
              <RiseOutlined /> 实时更新
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="card-dark stat-card">
            <Statistic
              title={<span className="stat-label"><ClickOutlined /> 商品点击</span>}
              value={data?.total_clicks || 0}
              valueStyle={{ color: '#ff9ff3' }}
              formatter={(value) => <span className="stat-value">{value.toLocaleString()}</span>}
            />
            <div className="stat-change" style={{ color: '#ff9ff3' }}>
              <RiseOutlined /> 累计点击
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="card-dark stat-card">
            <Statistic
              title={<span className="stat-label"><ShoppingCartOutlined /> 订单量</span>}
              value={data?.total_orders || 0}
              valueStyle={{ color: '#52c41a' }}
              formatter={(value) => <span className="stat-value">{value.toLocaleString()}</span>}
            />
            <div className="stat-change" style={{ color: '#52c41a' }}>
              <RiseOutlined /> 累计订单
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card className="card-dark stat-card">
            <Statistic
              title={<span className="stat-label"><RiseOutlined /> 转化率</span>}
              value={data?.conversion_rate || 0}
              suffix="%"
              valueStyle={{ color: '#feca57' }}
              formatter={(value) => <span className="stat-value">{value}</span>}
            />
            <div className="stat-change" style={{ color: (data?.conversion_rate || 0) > 3 ? '#52c41a' : '#ff4d4f' }}>
              <FireOutlined /> {(data?.conversion_rate || 0) > 3 ? '优秀' : '待提升'}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col xs={24} lg={16}>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card className="card-dark">
                {data?.viewer_trend && (
                  <TrendChart data={data.viewer_trend} title="观看人数趋势" color="#48dbfb" dataKey="count" />
                )}
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card className="card-dark">
                {data?.heat_trend && (
                  <TrendChart data={data.heat_trend} title="直播间热度趋势" color="#ff6b6b" dataKey="score" />
                )}
              </Card>
            </Col>

            <Col xs={24}>
              <Card className="card-dark">
                {data && (
                  <ProductBarChart clickData={data.product_clicks} orderData={data.product_orders} />
                )}
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card className="card-dark">
                {data?.chat_analysis && <ChatPieChart data={data.chat_analysis} />}
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card className="card-dark" title="当前热度评分">
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <div style={{
                    fontSize: '64px', fontWeight: 700,
                    background: 'linear-gradient(135deg, #ff6b6b, #feca57)',
                    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
                  }}>
                    {data?.heat_score || 0}
                  </div>
                  <div style={{ color: 'rgba(255,255,255,0.6)', marginTop: '8px' }}>热度指数 (满分100)</div>
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${data?.heat_score || 0}%`, height: '100%', background: 'linear-gradient(90deg, #ff6b6b, #feca57)', borderRadius: '4px', transition: 'width 0.5s' }}></div>
                    </div>
                  </div>
                  {data?.sentiment_analysis && (
                    <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'center', gap: '16px' }}>
                      <div>
                        <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>情感评分</span>
                        <div style={{ fontSize: '18px', fontWeight: 600, color: data.sentiment_analysis.overall_score > 60 ? '#52c41a' : data.sentiment_analysis.overall_score > 30 ? '#faad14' : '#ff4d4f' }}>
                          {data.sentiment_analysis.overall_score}
                        </div>
                      </div>
                      <div>
                        <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>情感趋势</span>
                        <div style={{ fontSize: '14px', fontWeight: 600, color: data.sentiment_analysis.trend === 'rising' ? '#52c41a' : data.sentiment_analysis.trend === 'declining' ? '#ff4d4f' : '#faad14' }}>
                          {data.sentiment_analysis.trend === 'rising' ? '↑ 上升' : data.sentiment_analysis.trend === 'declining' ? '↓ 下降' : '→ 平稳'}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </Col>

            <Col xs={24}>
              {data?.user_persona && <UserPersonaPanel persona={data.user_persona} />}
            </Col>

            <Col xs={24}>
              {data?.hot_predictions && <HotProductPrediction predictions={data.hot_predictions} />}
            </Col>
          </Row>
        </Col>

        <Col xs={24} lg={8}>
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              {data?.virtual_streamer && data?.streamer_action && (
                <VirtualStreamerPanel streamer={data.virtual_streamer} action={data.streamer_action} />
              )}
            </Col>

            <Col xs={24}>
              {data?.sentiment_analysis && data?.hot_words && data?.guided_scripts && (
                <SuggestionPanel sentiment={data.sentiment_analysis} hotWords={data.hot_words} guidedScripts={data.guided_scripts} />
              )}
            </Col>

            <Col xs={24}>
              {data?.recommended_products && (
                <ProductRecommendation products={data.recommended_products} onSwitchProduct={handleSwitchProduct} />
              )}
            </Col>

            <Col xs={24}>
              {data?.competitor_data && (
                <CompetitorMonitor competitors={data.competitor_data} />
              )}
            </Col>
          </Row>
        </Col>
      </Row>
    </div>
  );
};

export default App;
