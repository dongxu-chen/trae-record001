import { useState } from 'react'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Navigation } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/navigation'
import { relatedProducts } from '../data/productData'

const RelatedProducts = () => {
  const [hoveredId, setHoveredId] = useState(null)

  const renderStars = (rating) => {
    return [...Array(5)].map((_, i) => (
      <span key={i} className={`star ${i < Math.round(rating) ? 'filled' : ''}`}>★</span>
    ))
  }

  return (
    <div className="related-products">
      <div className="section-header">
        <h3 className="section-title">搭配推荐</h3>
        <span className="section-subtitle">购买此商品的用户还买了</span>
      </div>

      <div className="products-carousel">
        <Swiper
          modules={[Navigation]}
          navigation
          spaceBetween={12}
          slidesPerView={4}
          breakpoints={{
            320: {
              slidesPerView: 2,
              spaceBetween: 8
            },
            640: {
              slidesPerView: 3,
              spaceBetween: 10
            },
            1024: {
              slidesPerView: 4,
              spaceBetween: 12
            }
          }}
        >
          {relatedProducts.map((product) => (
            <SwiperSlide key={product.id}>
              <div
                className={`product-card ${hoveredId === product.id ? 'hovered' : ''}`}
                onMouseEnter={() => setHoveredId(product.id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                <div className="product-image">
                  <img src={product.image} alt={product.title} loading="lazy" />
                  <div className="match-rate">
                    <span>契合度 {product.matchRate}%</span>
                  </div>
                </div>
                <div className="product-info">
                  <h4 className="product-title">{product.title}</h4>
                  <div className="product-rating">
                    <div className="stars">{renderStars(product.rating)}</div>
                    <span className="rating-value">{product.rating}</span>
                  </div>
                  <div className="product-price">
                    <span className="current-price">¥{product.price}</span>
                    <span className="original-price">¥{product.originalPrice}</span>
                  </div>
                  <div className="product-sales">
                    已售 {product.sales.toLocaleString()}
                  </div>
                  <button className="add-btn">
                    <span>+</span> 加入购物车
                  </button>
                </div>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>

      <style jsx>{`
        .related-products {
          background: #fff;
          margin-top: 12px;
          padding: 16px;
          border-radius: 12px;
        }
        .section-header {
          display: flex;
          align-items: baseline;
          gap: 12px;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #333;
          margin: 0;
        }
        .section-subtitle {
          font-size: 12px;
          color: #999;
        }
        .products-carousel {
          padding: 0 8px;
        }
        .product-card {
          background: #fff;
          border-radius: 12px;
          overflow: hidden;
          border: 1px solid #f0f0f0;
          transition: all 0.3s ease;
          cursor: pointer;
        }
        .product-card.hovered {
          transform: translateY(-4px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
          border-color: #ff4d4f;
        }
        .product-image {
          position: relative;
          width: 100%;
          aspect-ratio: 1;
          background: #fafafa;
          overflow: hidden;
        }
        .product-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.3s ease;
        }
        .product-card.hovered .product-image img {
          transform: scale(1.05);
        }
        .match-rate {
          position: absolute;
          top: 8px;
          left: 8px;
          background: linear-gradient(135deg, #ff7875, #ff4d4f);
          color: #fff;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 500;
        }
        .product-info {
          padding: 12px;
        }
        .product-title {
          font-size: 13px;
          font-weight: 500;
          color: #333;
          margin: 0 0 8px 0;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          height: 36px;
        }
        .product-rating {
          display: flex;
          align-items: center;
          gap: 4px;
          margin-bottom: 6px;
        }
        .stars {
          display: flex;
          gap: 1px;
        }
        .star {
          font-size: 11px;
          color: #e0e0e0;
        }
        .star.filled {
          color: #faad14;
        }
        .rating-value {
          font-size: 11px;
          color: #fa8c16;
        }
        .product-price {
          display: flex;
          align-items: baseline;
          gap: 6px;
          margin-bottom: 4px;
        }
        .current-price {
          font-size: 16px;
          font-weight: 600;
          color: #ff4d4f;
        }
        .original-price {
          font-size: 11px;
          color: #999;
          text-decoration: line-through;
        }
        .product-sales {
          font-size: 11px;
          color: #999;
          margin-bottom: 10px;
        }
        .add-btn {
          width: 100%;
          padding: 6px 0;
          border: 1px solid #ff4d4f;
          background: #fff;
          color: #ff4d4f;
          border-radius: 16px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 4px;
        }
        .add-btn:hover {
          background: #ff4d4f;
          color: #fff;
        }
        .add-btn span {
          font-size: 14px;
          font-weight: bold;
        }
        @media (max-width: 768px) {
          .related-products {
            padding: 12px;
            border-radius: 0;
            margin-top: 0;
          }
          .product-title {
            font-size: 12px;
            height: 32px;
          }
          .current-price {
            font-size: 14px;
          }
        }
      `}</style>
    </div>
  )
}

export default RelatedProducts
