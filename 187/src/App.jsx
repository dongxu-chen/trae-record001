import { observer } from 'mobx-react-lite'
import { productStore } from './store/ProductStore'
import ProductGallery from './components/ProductGallery'
import ProductInfo from './components/ProductInfo'
import SkuSelector from './components/SkuSelector'
import QuantitySelector from './components/QuantitySelector'
import Model3DViewer from './components/Model3DViewer'
import VideoPlayer from './components/VideoPlayer'
import RelatedProducts from './components/RelatedProducts'
import ReviewList from './components/ReviewList'
import ProductDescription from './components/ProductDescription'
import ActionBar from './components/ActionBar'

const model3DImages = [
  'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1512054502232-10a0a035d672?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=600&h=600&fit=crop'
]

const App = observer(() => {
  return (
    <div className="app">
      <div className="container">
        <div className="product-layout">
          <div className="left-section">
            <ProductGallery images={productStore.currentImages} />
          </div>
          <div className="right-section">
            <ProductInfo store={productStore} />
            <SkuSelector store={productStore} />
            <QuantitySelector store={productStore} />
          </div>
        </div>
        <VideoPlayer />
        <Model3DViewer images={model3DImages} />
        <RelatedProducts />
        <ReviewList store={productStore} />
        <ProductDescription store={productStore} />
        <div style={{ height: '80px' }} />
      </div>
      <ActionBar store={productStore} />

      <style jsx>{`
        .app {
          min-height: 100vh;
          background: #f5f5f5;
        }
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 16px;
        }
        .product-layout {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          background: #fff;
          margin-top: 16px;
          border-radius: 12px;
          overflow: hidden;
        }
        .left-section {
          background: #fff;
        }
        .right-section {
          display: flex;
          flex-direction: column;
        }
        @media (max-width: 992px) {
          .product-layout {
            grid-template-columns: 1fr;
            gap: 0;
          }
        }
        @media (max-width: 768px) {
          .container {
            padding: 0;
          }
          .product-layout {
            margin-top: 0;
            border-radius: 0;
          }
        }
      `}</style>
    </div>
  )
})

export default App
