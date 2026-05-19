import { observer } from 'mobx-react-lite'
import { useRef, useState, useCallback } from 'react'
import { SKU_STATES } from '../store/ProductStore'

const ActionBar = observer(({ store }) => {
  const { cartCount, cartAnimationStartPos, skuState, currentStock, currentImages, addToCart, completeCartAnimation } = store
  const cartBtnRef = useRef(null)
  const animatingRef = useRef(false)
  const [cartBounce, setCartBounce] = useState(false)

  const playCartAnimation = useCallback((startX, startY, imageSrc) => {
    if (animatingRef.current) return
    animatingRef.current = true

    const animEl = document.createElement('div')
    animEl.style.cssText = `
      position: fixed;
      left: ${startX}px;
      top: ${startY}px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      overflow: hidden;
      pointer-events: none;
      z-index: 1000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      transform: translate(-50%, -50%);
    `
    animEl.innerHTML = `<img src="${imageSrc}" style="width:100%;height:100%;object-fit:cover;" />`
    document.body.appendChild(animEl)

    const cartIcon = cartBtnRef.current
    const cartRect = cartIcon.getBoundingClientRect()
    const endX = cartRect.left + cartRect.width / 2
    const endY = cartRect.top + cartRect.height / 2

    const deltaX = endX - startX
    const deltaY = endY - startY
    const controlY = startY - 150

    const animation = animEl.animate([
      {
        transform: 'translate(-50%, -50%) scale(1)',
        opacity: 1,
        offset: 0
      },
      {
        transform: `translate(calc(-50% + ${deltaX * 0.5}px), calc(-150% + ${(controlY - startY) * 0.5}px)) scale(0.7)`,
        opacity: 0.9,
        offset: 0.5
      },
      {
        transform: `translate(calc(-50% + ${deltaX}px), calc(-50% + ${deltaY}px)) scale(0.2)`,
        opacity: 0,
        offset: 1
      }
    ], {
      duration: 800,
      easing: 'cubic-bezier(0.5, -0.5, 1, 1)',
      fill: 'forwards'
    })

    animation.onfinish = () => {
      animEl.remove()
      animatingRef.current = false
      setCartBounce(true)
      completeCartAnimation()
      setTimeout(() => setCartBounce(false), 500)
    }
  }, [completeCartAnimation])

  const handleAddToCart = () => {
    if (skuState !== SKU_STATES.SELECTED) {
      alert('请先选择商品规格')
      return
    }
    if (currentStock <= 0) {
      alert('该商品暂时缺货')
      return
    }
    if (animatingRef.current) return

    const addBtn = event.currentTarget
    const rect = addBtn.getBoundingClientRect()
    const startPos = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
    
    const success = addToCart(startPos)
    if (success && currentImages[0]) {
      playCartAnimation(startPos.x, startPos.y, currentImages[0])
    }
  }

  const handleBuyNow = () => {
    if (skuState !== SKU_STATES.SELECTED) {
      alert('请先选择商品规格')
      return
    }
    if (currentStock <= 0) {
      alert('该商品暂时缺货')
      return
    }
    alert('立即购买功能开发中...')
  }

  return (
    <>
      <div className="action-bar">
        <div className="action-left">
          <div className="action-icon" title="首页">
            <span className="icon">🏠</span>
            <span className="text">首页</span>
          </div>
          <div 
            className={`action-icon cart-icon ${cartBounce ? 'bounce' : ''}`} 
            ref={cartBtnRef} 
            title="购物车"
          >
            <span className="icon">🛒</span>
            <span className="text">购物车</span>
            {cartCount > 0 && (
              <span className={`cart-badge ${cartBounce ? 'bounce' : ''}`}>
                {cartCount > 99 ? '99+' : cartCount}
              </span>
            )}
          </div>
          <div className="action-icon" title="客服">
            <span className="icon">💬</span>
            <span className="text">客服</span>
          </div>
        </div>
        <div className="action-right">
          <button className="btn btn-add" onClick={handleAddToCart}>
            加入购物车
          </button>
          <button className="btn btn-buy" onClick={handleBuyNow}>
            立即购买
          </button>
        </div>
      </div>

      <style jsx>{`
        .action-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 16px;
          background: #fff;
          box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
          z-index: 100;
        }
        .action-left {
          display: flex;
          gap: 16px;
        }
        .action-icon {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          cursor: pointer;
          position: relative;
          padding: 4px;
          transition: transform 0.2s;
        }
        .action-icon.bounce {
          animation: iconBounce 0.5s ease;
        }
        .action-icon .icon {
          font-size: 20px;
        }
        .action-icon .text {
          font-size: 10px;
          color: #666;
        }
        .cart-badge {
          position: absolute;
          top: 0;
          right: -4px;
          min-width: 16px;
          height: 16px;
          padding: 0 4px;
          background: #ff4d4f;
          color: #fff;
          font-size: 10px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s;
        }
        .cart-badge.bounce {
          animation: badgeBounce 0.5s ease;
        }
        .action-right {
          display: flex;
          gap: 8px;
        }
        .btn {
          padding: 10px 20px;
          border-radius: 20px;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        }
        .btn-add {
          background: linear-gradient(135deg, #ffd666, #faad14);
          color: #fff;
        }
        .btn-add:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }
        .btn-add:active {
          transform: scale(0.98);
        }
        .btn-buy {
          background: linear-gradient(135deg, #ff7875, #ff4d4f);
          color: #fff;
        }
        .btn-buy:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }
        .btn-buy:active {
          transform: scale(0.98);
        }
        @keyframes iconBounce {
          0%, 100% {
            transform: scale(1);
          }
          30% {
            transform: scale(1.2);
          }
          50% {
            transform: scale(0.95);
          }
          70% {
            transform: scale(1.1);
          }
        }
        @keyframes badgeBounce {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.4);
          }
        }
        @media (min-width: 769px) {
          .action-bar {
            max-width: 1200px;
            left: 50%;
            transform: translateX(-50%);
            border-radius: 12px 12px 0 0;
          }
        }
        @media (max-width: 768px) {
          .btn {
            padding: 10px 16px;
            font-size: 13px;
          }
          .action-left {
            gap: 12px;
          }
        }
      `}</style>
    </>
  )
})

export default ActionBar
