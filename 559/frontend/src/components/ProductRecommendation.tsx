import React from 'react';
import { Card, Button, Tag, Progress } from 'antd';
import { AimOutlined, ShoppingCartOutlined, DollarOutlined, StockOutlined } from '@ant-design/icons';
import { OptimizedProduct } from '../types';

interface ProductRecommendationProps {
  products: OptimizedProduct[];
  onSwitchProduct: (product: OptimizedProduct) => void;
}

const stockStatusMap: Record<string, { color: string; text: string }> = {
  danger: { color: '#ff4d4f', text: '库存告急' },
  warning: { color: '#faad14', text: '库存偏低' },
  normal: { color: '#52c41a', text: '库存充足' }
};

const objectiveColors: Record<string, string> = {
  click_rate: '#48dbfb',
  profit_rate: '#52c41a',
  stock_urgency: '#ff9ff3'
};

const objectiveLabels: Record<string, string> = {
  click_rate: '点击率',
  profit_rate: '利润率',
  stock_urgency: '库存紧迫'
};

export const ProductRecommendation: React.FC<ProductRecommendationProps> = ({
  products,
  onSwitchProduct
}) => {
  return (
    <Card title={<span><AimOutlined /> 多目标优化推荐</span>} className="card-dark">
      <div className="optimization-legend">
        <span className="legend-dot" style={{ background: '#48dbfb' }}></span> 点击率
        <span className="legend-dot" style={{ background: '#52c41a', marginLeft: '8px' }}></span> 利润率
        <span className="legend-dot" style={{ background: '#ff9ff3', marginLeft: '8px' }}></span> 库存紧迫
      </div>
      {products.map((product, index) => {
        const stockInfo = stockStatusMap[product.stock_status];
        const stockPercent = product.initial_stock > 0
          ? Math.round((product.stock / product.initial_stock) * 100)
          : 0;

        return (
          <div key={product.id} className="product-card optimization-card">
            <div className="product-header-row">
              <div className={`product-rank rank-${index + 1}`}>
                {index + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: '#fff' }}>
                  {product.name}
                </div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '4px', alignItems: 'center' }}>
                  <Tag color="blue" style={{ margin: 0, fontSize: '10px' }}>
                    {product.category}
                  </Tag>
                  <span style={{ color: '#ff4d4f', fontWeight: 600, fontSize: '13px' }}>
                    ¥{product.price}
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>
                    成本¥{product.cost}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                  综合评分
                </div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#feca57' }}>
                  {product.composite_score}
                </div>
              </div>
            </div>

            <div className="objectives-row">
              {(Object.entries(product.objectives) as [string, number][]).map(([key, value]) => (
                <div key={key} className="objective-item">
                  <div className="objective-label">{objectiveLabels[key]}</div>
                  <Progress
                    percent={Math.round(value)}
                    size="small"
                    strokeColor={objectiveColors[key]}
                    trailColor="rgba(255,255,255,0.08)"
                    showInfo={false}
                    style={{ margin: 0 }}
                  />
                  <div className="objective-value" style={{ color: objectiveColors[key] }}>
                    {key === 'click_rate' && `${product.click_rate}%`}
                    {key === 'profit_rate' && `${product.profit_rate}%`}
                    {key === 'stock_urgency' && `${product.stock_urgency}`}
                  </div>
                </div>
              ))}
            </div>

            <div className="stock-row">
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>
                <StockOutlined /> 库存: {product.stock}/{product.initial_stock}
              </span>
              <div style={{ flex: 1, margin: '0 8px' }}>
                <Progress
                  percent={stockPercent}
                  size="small"
                  strokeColor={stockInfo.color}
                  trailColor="rgba(255,255,255,0.08)"
                  showInfo={false}
                  style={{ margin: 0 }}
                />
              </div>
              <Tag
                color={stockInfo.color}
                style={{ margin: 0, fontSize: '10px', padding: '0 4px' }}
              >
                {stockInfo.text}
              </Tag>
            </div>

            <Button
              type="primary"
              size="small"
              icon={<ShoppingCartOutlined />}
              onClick={() => onSwitchProduct(product)}
              style={{
                width: '100%',
                marginTop: '8px',
                background: product.stock_status === 'danger'
                  ? 'linear-gradient(135deg, #ff4d4f, #cf1322)'
                  : 'linear-gradient(135deg, #48dbfb, #0abde3)',
                border: 'none'
              }}
            >
              {product.stock_status === 'danger' ? '清仓推荐' : '切换讲解此商品'}
            </Button>
          </div>
        );
      })}
    </Card>
  );
};
