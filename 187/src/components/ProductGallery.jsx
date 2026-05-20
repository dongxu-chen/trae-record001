import { useRef, useState, useEffect } from 'react'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Navigation, Pagination, Lazy } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/navigation'
import 'swiper/css/pagination'
import 'swiper/css/lazy'
import { observer } from 'mobx-react-lite'

const ProductGallery = observer(({ images }) => {
  const mainSwiperRef = useRef(null)
  const thumbsSwiperRef = useRef(null)
  const [loadedImages, setLoadedImages] = useState(new Set())
  const [isTransitioning, setIsTransitioning] = useState(false)

  useEffect(() => {
    if (mainSwiperRef.current) {
      setIsTransitioning(true)
      mainSwiperRef.current.slideTo(0, 0)
      if (thumbsSwiperRef.current) {
        thumbsSwiperRef.current.slideTo(0, 0)
      }
      setTimeout(() => setIsTransitioning(false), 300)
    }
  }, [images])

  const imagesKey = images.join('|')

  const ImageWithSkeleton = ({ src, alt }) => {
    const [loaded, setLoaded] = useState(false)
    const [error, setError] = useState(false)

    useEffect(() => {
      if (loadedImages.has(src)) {
        setLoaded(true)
        return
      }
      const img = new Image()
      img.src = src
      img.onload = () => {
        setLoaded(true)
        setLoadedImages(prev => new Set([...prev, src]))
      }
      img.onerror = () => setError(true)
      return () => {
        img.onload = null
        img.onerror = null
      }
    }, [src, loadedImages])

    if (error) {
      return (
        <div className="image-error">
          <span>图片加载失败</span>
        </div>
      )
    }

    return (
      <div className="image-wrapper">
        {!loaded && (
          <div className="image-skeleton">
            <div className="skeleton-shimmer" />
          </div>
        )}
        <img
          src={src}
          alt={alt}
          loading="lazy"
          style={{ opacity: loaded ? 1 : 0 }}
          onLoad={() => setLoaded(true)}
        />
      </div>
    )
  }

  return (
    <div className="product-gallery">
      <div className={`main-gallery ${isTransitioning ? 'transitioning' : ''}`}>
        <Swiper
          key={imagesKey}
          modules={[Navigation, Pagination, Lazy]}
          navigation
          pagination={{ clickable: true }}
          lazy={{ loadPrevNext: true }}
          loop
          onSwiper={(swiper) => (mainSwiperRef.current = swiper)}
          onSlideChange={(swiper) => {
            if (thumbsSwiperRef.current) {
              thumbsSwiperRef.current.slideTo(swiper.activeIndex)
            }
          }}
          breakpoints={{
            320: {
              slidesPerView: 1,
              spaceBetween: 10
            },
            768: {
              slidesPerView: 1,
              spaceBetween: 20
            }
          }}
        >
          {images.map((img, index) => (
            <SwiperSlide key={`${imagesKey}-${index}`}>
              <div className="main-slide">
              <ImageWithSkeleton src={img} alt={`商品图片 ${index + 1}`} />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>

      <div className="thumbs-gallery">
        <Swiper
          key={`thumbs-${imagesKey}`}
          modules={[Navigation]}
          navigation
          spaceBetween={10}
          slidesPerView={4}
          loop
          onSwiper={(swiper) => (thumbsSwiperRef.current = swiper)}
          breakpoints={{
            320: {
              slidesPerView: 3,
              spaceBetween: 8
            },
            768: {
              slidesPerView: 4,
              spaceBetween: 12
            }
          }}
        >
          {images.map((img, index) => (
            <SwiperSlide key={`thumb-${imagesKey}-${index}`}>
              <div
                className={`thumb-item ${
                  mainSwiperRef.current?.activeIndex === index ? 'active' : ''
                }`}
                onClick={() => mainSwiperRef.current?.slideTo(index)}
              >
                <img src={img} alt={`缩略图 ${index + 1}`} loading="lazy" />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>

      <style jsx>{`
        .product-gallery {
          width: 100%;
          background: #fff;
          padding: 16px;
        }
        .main-gallery {
          position: relative;
          width: 100%;
          aspect-ratio: 1;
          border-radius: 12px;
          overflow: hidden;
          background: #fafafa;
          transition: opacity 0.3s ease;
        }
        .main-gallery.transitioning {
          opacity: 0.6;
        }
        .main-slide {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .image-wrapper {
          position: relative;
          width: 100%;
          height: 100%;
        }
        .image-wrapper img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: opacity 0.3s ease;
        }
        .image-skeleton {
          position: absolute;
          inset: 0;
          background: #f0f0f0;
        }
        .skeleton-shimmer {
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        .image-error {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f5f5f5;
          color: #999;
          font-size: 14px;
        }
        .thumbs-gallery {
          margin-top: 16px;
          padding: 0 8px;
        }
        .thumb-item {
          width: 100%;
          aspect-ratio: 1;
          border-radius: 8px;
          overflow: hidden;
          cursor: pointer;
          border: 2px solid transparent;
          transition: all 0.3s ease;
        }
        .thumb-item.active {
          border-color: #ff4d4f;
          transform: scale(1.05);
        }
        .thumb-item img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .thumb-item:hover {
          border-color: #ff7875;
        }
        @media (max-width: 768px) {
          .product-gallery {
            padding: 12px;
          }
          .main-gallery {
            border-radius: 8px;
          }
          .thumbs-gallery {
            margin-top: 12px;
          }
        }
      `}</style>
    </div>
  )
})

export default ProductGallery
