import { observer } from 'mobx-react-lite'

const ProductDescription = observer(({ store }) => {
  const { product } = store

  return (
    <div className="product-description">
      <div className="section-header">
        <h3 className="section-title">商品详情</h3>
      </div>
      <div className="description-content">
        {product.description.split('\n').map((line, index) => (
          <p key={index} className="desc-line">{line}</p>
        ))}
      </div>
      <div className="detail-images">
        {[17, 18, 19, 20].map(i => (
          <img
            key={i}
            src={`https://picsum.photos/seed/product${i}/800/600`}
            alt={`详情图 ${i - 16}`}
            loading="lazy"
          />
        ))}
      </div>

      <style jsx>{`
        .product-description {
          background: #fff;
          margin-top: 12px;
          padding: 16px;
        }
        .section-header {
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        .description-content {
          margin-bottom: 20px;
        }
        .desc-line {
          font-size: 14px;
          color: #666;
          line-height: 1.8;
          margin-bottom: 8px;
          padding-left: 12px;
          position: relative;
        }
        .desc-line::before {
          content: '•';
          position: absolute;
          left: 0;
          color: #ff4d4f;
        }
        .detail-images {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .detail-images img {
          width: 100%;
          border-radius: 8px;
          object-fit: cover;
        }
        @media (max-width: 768px) {
          .product-description {
            padding: 12px;
          }
          .desc-line {
            font-size: 13px;
          }
        }
      `}</style>
    </div>
  )
})

export default ProductDescription
