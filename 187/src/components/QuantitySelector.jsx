import { observer } from 'mobx-react-lite'

const QuantitySelector = observer(({ store }) => {
  const { quantity, currentStock, setQuantity, increaseQuantity, decreaseQuantity } = store

  return (
    <div className="quantity-selector">
      <span className="label">购买数量</span>
      <div className="quantity-control">
        <button
          className="qty-btn"
          onClick={decreaseQuantity}
          disabled={quantity <= 1}
        >
          −
        </button>
        <input
          type="number"
          className="qty-input"
          value={quantity}
          onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
          min={1}
          max={currentStock || 99}
        />
        <button
          className="qty-btn"
          onClick={increaseQuantity}
          disabled={currentStock !== null && quantity >= currentStock}
        >
          +
        </button>
        {currentStock !== null && (
          <span className="stock-limit">库存 {currentStock} 件</span>
        )}
      </div>

      <style jsx>{`
        .quantity-selector {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: #fff;
          border-top: 1px solid #f0f0f0;
        }
        .label {
          font-size: 14px;
          color: #666;
          white-space: nowrap;
        }
        .quantity-control {
          display: flex;
          align-items: center;
          gap: 0;
        }
        .qty-btn {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid #e0e0e0;
          background: #fff;
          font-size: 18px;
          color: #666;
          transition: all 0.2s;
        }
        .qty-btn:hover:not(:disabled) {
          background: #f5f5f5;
          border-color: #ff4d4f;
          color: #ff4d4f;
        }
        .qty-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .qty-btn:first-child {
          border-radius: 4px 0 0 4px;
        }
        .qty-btn:last-child {
          border-radius: 0 4px 4px 0;
        }
        .qty-input {
          width: 60px;
          height: 36px;
          text-align: center;
          border: 1px solid #e0e0e0;
          border-left: none;
          border-right: none;
          font-size: 14px;
          color: #333;
          outline: none;
          -moz-appearance: textfield;
        }
        .qty-input::-webkit-outer-spin-button,
        .qty-input::-webkit-inner-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        .qty-input:focus {
          border-color: #ff4d4f;
        }
        .stock-limit {
          margin-left: 12px;
          font-size: 12px;
          color: #999;
        }
        @media (max-width: 768px) {
          .quantity-selector {
            padding: 12px;
          }
          .qty-btn {
            width: 32px;
            height: 32px;
            font-size: 16px;
          }
          .qty-input {
            width: 50px;
            height: 32px;
          }
        }
      `}</style>
    </div>
  )
})

export default QuantitySelector
