import { observer } from 'mobx-react-lite'
import { useState, useCallback } from 'react'

const ReviewList = observer(({ store }) => {
  const { paginatedReviews, totalReviewPages, reviewPage, setReviewPage, product, isLoadingReviews, loadedReviewPages } = store
  const [previewImage, setPreviewImage] = useState(null)

  const handlePageChange = useCallback(async (page) => {
    if (page === reviewPage) return
    if (isLoadingReviews) return
    await setReviewPage(page)
  }, [reviewPage, isLoadingReviews, setReviewPage])

  const renderStars = (rating) => {
    return [...Array(5)].map((_, i) => (
      <span key={i} className={`star ${i < rating ? 'filled' : ''}`}>★</span>
    ))
  }

  return (
    <div className="review-list">
      <div className="section-header">
        <h3 className="section-title">商品评价</h3>
        <span className="review-count">共 {product.reviewCount} 条评价</span>
      </div>

      <div className={`reviews ${isLoadingReviews ? 'loading' : ''}`}>
        {isLoadingReviews ? (
          <div className="loading-skeleton">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton-item">
                <div className="skeleton-header">
                  <div className="skeleton-avatar" />
                  <div className="skeleton-lines">
                    <div className="skeleton-line short" />
                    <div className="skeleton-line medium" />
                  </div>
                </div>
                <div className="skeleton-line long" />
                <div className="skeleton-line full" />
              </div>
            ))}
          </div>
        ) : (
          paginatedReviews.map((review, index) => (
            <div
              key={review.id}
              className="review-item"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="review-header">
                <img src={review.avatar} alt={review.userName} className="avatar" />
                <div className="user-info">
                  <div className="user-name">{review.userName}</div>
                  <div className="review-meta">
                    <div className="stars">{renderStars(review.rating)}</div>
                    <span className="date">{review.date}</span>
                  </div>
                </div>
              </div>
              <div className="review-specs">购买规格：{review.specs}</div>
              <div className="review-content">{review.content}</div>
              {review.images.length > 0 && (
                <div className="review-images">
                  {review.images.map((img, idx) => (
                    <img
                      key={idx}
                      src={img}
                      alt={`评价图片 ${idx + 1}`}
                      className="review-image"
                      loading="lazy"
                      onClick={() => setPreviewImage(img)}
                    />
                  ))}
                </div>
              )}
              <div className="review-footer">
                <span className="helpful">👍 有用 ({review.helpful})</span>
              </div>
            </div>
          ))
        )}
      </div>

      {totalReviewPages > 1 && (
        <div className="pagination">
          <button
            className="page-btn"
            onClick={() => handlePageChange(reviewPage - 1)}
            disabled={reviewPage === 1 || isLoadingReviews}
          >
            上一页
          </button>
          <div className="page-numbers">
            {[...Array(totalReviewPages)].map((_, i) => (
              <button
                key={i + 1}
                className={`page-num ${reviewPage === i + 1 ? 'active' : ''} ${loadedReviewPages.has(i + 1) ? 'cached' : ''}`}
                onClick={() => handlePageChange(i + 1)}
                disabled={isLoadingReviews}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <button
            className="page-btn"
            onClick={() => handlePageChange(reviewPage + 1)}
            disabled={reviewPage === totalReviewPages || isLoadingReviews}
          >
            下一页
          </button>
        </div>
      )}

      {previewImage && (
        <div className="image-preview" onClick={() => setPreviewImage(null)}>
          <img src={previewImage} alt="预览" />
          <span className="close-btn">✕</span>
        </div>
      )}

      <style jsx>{`
        .review-list {
          background: #fff;
          margin-top: 12px;
          padding: 16px;
        }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        .review-count {
          font-size: 13px;
          color: #999;
        }
        .reviews {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .reviews.loading {
          opacity: 0.7;
        }
        .loading-skeleton {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .skeleton-item {
          padding-bottom: 20px;
          border-bottom: 1px solid #f5f5f5;
        }
        .skeleton-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }
        .skeleton-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        .skeleton-lines {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .skeleton-line {
          height: 12px;
          border-radius: 4px;
          background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        .skeleton-line.short {
          width: 80px;
        }
        .skeleton-line.medium {
          width: 120px;
        }
        .skeleton-line.long {
          width: 60%;
          margin-bottom: 8px;
        }
        .skeleton-line.full {
          width: 100%;
          height: 40px;
        }
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
        .review-item {
          padding-bottom: 20px;
          border-bottom: 1px solid #f5f5f5;
          animation: fadeIn 0.5s ease forwards;
          opacity: 0;
        }
        .review-item:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }
        .review-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 10px;
        }
        .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          object-fit: cover;
        }
        .user-info {
          flex: 1;
        }
        .user-name {
          font-size: 14px;
          font-weight: 500;
          color: #333;
          margin-bottom: 4px;
        }
        .review-meta {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .stars {
          display: flex;
          gap: 2px;
        }
        .star {
          font-size: 12px;
          color: #e0e0e0;
        }
        .star.filled {
          color: #faad14;
        }
        .date {
          font-size: 12px;
          color: #999;
        }
        .review-specs {
          font-size: 12px;
          color: #999;
          margin-bottom: 8px;
          background: #f5f5f5;
          padding: 4px 8px;
          border-radius: 4px;
          display: inline-block;
        }
        .review-content {
          font-size: 14px;
          color: #333;
          line-height: 1.6;
          margin-bottom: 12px;
        }
        .review-images {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 12px;
        }
        .review-image {
          width: 80px;
          height: 80px;
          object-fit: cover;
          border-radius: 8px;
          cursor: pointer;
          transition: transform 0.2s;
        }
        .review-image:hover {
          transform: scale(1.05);
        }
        .review-footer {
          display: flex;
          justify-content: flex-end;
        }
        .helpful {
          font-size: 12px;
          color: #999;
          padding: 4px 12px;
          border-radius: 12px;
          background: #f5f5f5;
        }
        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 8px;
          margin-top: 20px;
          padding-top: 16px;
          border-top: 1px solid #f0f0f0;
        }
        .page-btn {
          padding: 6px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          background: #fff;
          font-size: 13px;
          color: #666;
          transition: all 0.2s;
        }
        .page-btn:hover:not(:disabled) {
          border-color: #ff4d4f;
          color: #ff4d4f;
        }
        .page-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .page-numbers {
          display: flex;
          gap: 6px;
        }
        .page-num {
          width: 32px;
          height: 32px;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          background: #fff;
          font-size: 13px;
          color: #666;
          transition: all 0.2s;
        }
        .page-num:hover {
          border-color: #ff4d4f;
          color: #ff4d4f;
        }
        .page-num.active {
          background: #ff4d4f;
          border-color: #ff4d4f;
          color: #fff;
        }
        .page-num.cached:not(.active) {
          background: #f0f5ff;
          border-color: #91caff;
          color: #1677ff;
        }
        .image-preview {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .image-preview img {
          max-width: 90%;
          max-height: 90%;
          object-fit: contain;
        }
        .close-btn {
          position: absolute;
          top: 20px;
          right: 20px;
          color: #fff;
          font-size: 24px;
          cursor: pointer;
        }
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @media (max-width: 768px) {
          .review-list {
            padding: 12px;
          }
          .review-image {
            width: 60px;
            height: 60px;
          }
          .pagination {
            flex-wrap: wrap;
          }
          .page-numbers {
            order: -1;
            width: 100%;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  )
})

export default ReviewList
