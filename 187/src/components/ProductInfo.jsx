import { observer } from 'mobx-react-lite'
import { SKU_STATES } from '../store/ProductStore'

const ProductInfo = observer(({ store }) => {
  const { product, currentPrice, currentOriginalPrice, currentStock, skuState } = store

  const getStatusTip = () => {
    switch (skuState) {
      case SKU_STATES.UNSELECTED:
        return '请选择规格以查看价格和库存'
      case SKU_STATES.PARTIAL_SELECTED:
        return '请继续选择完整规格'
      case SKU_STATES.OUT_OF_STOCK:
        return '该规格暂时缺货，请选择其他规格'
      default:
        return ''
    }
  }

  return (
    <div className="product-info">
      <div className="price-section">
        <div className="price-row">
          <span className="current-price">
            ¥{skuState === SKU_STATES.SELECTED ? currentPrice?.toLocaleString() : '--'}
          </span>
          {skuState === SKU_STATES.SELECTED && currentOriginalPrice && (
            <span className="original-price">¥{currentOriginalPrice.toLocaleString()}</span>
          )}
          {skuState === SKU_STATES.SELECTED && currentOriginalPrice && (
            <span className="discount-tag">
              省 ¥{(currentOriginalPrice - currentPrice).toLocaleString()}
            </span>
          )}
        </div>
        <div className="stock-row">
          {skuState === SKU_STATES.SELECTED ? (
            <>
              <span className={`stock ${currentStock > 0 ? 'in-stock' : 'out-of-stock'}`}>
                {currentStock > 0 ? `库存 ${currentStock} 件` : '暂时缺货'}
              </span>
              <span className="sales">已售 {product.sales.toLocaleString()}</span>
            </>
          ) : (
            <span className={`select-tip ${skuState === SKU_STATES.OUT_OF_STOCK ? 'error' : ''}`}>
              {getStatusTip()}
            </span>
          )}
        </div>
      </div>

      <div className="title-section">
        <h1 className="product-title">{product.title}</h1>
        <p className="product-subtitle">{product.subtitle}</p>
      </div>

      <div className="meta-section">
        <div className="rating">
          <span className="rating-score">{product.rating}</span>
          <div className="stars">
            {[1, 2, 3, 4, 5].map(i => (
              <span key={i} className={`star ${i <= Math.round(product.rating) ? 'filled' : ''}`}>★</span>
            ))}
          </div>
          <span className="review-count">{product.reviewCount} 条评价</span>
        </div>
        <div className="brand">品牌：{product.brand}</div>
      </div>

      <div className="services-section">
        <div className="shipping">
          <span className="icon">🚚</span>
          {product.shipping}
        </div>
        <div className="service-tags">
          {product.services.map((service, index) => (
            <span key={index} className="service-tag">
              <span className="check">✓</span>
              {service}
            </span>
          ))}
        </div>
      </div>

      <style jsx>{`
        .product-info {
          background: #fff;
          padding: 16px;
        }
        .price-section {
          margin-bottom: 16px;
        }
        .price-row {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }
        .current-price {
          font-size: 32px;
          font-weight: 700;
          color: #ff4d4f;
          line-height: 1;
        }
        .original-price {
          font-size: 16px;
          color: #999;
          text-decoration: line-through;
        }
        .discount-tag {
          padding: 2px 8px;
          background: #fff2f0;
          color: #ff4d4f;
          font-size: 12px;
          border-radius: 4px;
        }
        .stock-row {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-top: 8px;
          font-size: 13px;
        }
        .stock.in-stock {
          color: #52c41a;
        }
        .stock.out-of-stock {
          color: #ff4d4f;
        }
        .sales {
          color: #999;
        }
        .select-tip {
          color: #fa8c16;
        }
        .select-tip.error {
          color: #ff4d4f;
        }
        .title-section {
          margin-bottom: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid #f0f0f0;
        }
        .product-title {
          font-size: 18px;
          font-weight: 600;
          color: #333;
          line-height: 1.4;
          margin-bottom: 8px;
        }
        .product-subtitle {
          font-size: 14px;
          color: #666;
          line-height: 1.5;
        }
        .meta-section {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid #f0f0f0;
        }
        .rating {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .rating-score {
          font-size: 20px;
          font-weight: 600;
          color: #fa8c16;
        }
        .stars {
          display: flex;
          gap: 2px;
        }
        .star {
          font-size: 14px;
          color: #e0e0e0;
        }
        .star.filled {
          color: #faad14;
        }
        .review-count {
          font-size: 13px;
          color: #999;
        }
        .brand {
          font-size: 13px;
          color: #666;
        }
        .services-section {
          font-size: 13px;
        }
        .shipping {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #666;
          margin-bottom: 12px;
        }
        .icon {
          font-size: 16px;
        }
        .service-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
        .service-tag {
          display: flex;
          align-items: center;
          gap: 4px;
          color: #666;
          font-size: 12px;
        }
        .check {
          color: #52c41a;
        }
        @media (max-width: 768px) {
          .product-info {
            padding: 12px;
          }
          .current-price {
            font-size: 28px;
          }
          .product-title {
            font-size: 16px;
          }
          .meta-section {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }
        }
      `}</style>
    </div>
  )
})

export default ProductInfo
