import { makeAutoObservable, runInAction } from 'mobx'
import { productInfo, specGroups, skuList, productImages, reviews } from '../data/productData'

const SKU_STATES = {
  UNSELECTED: 'UNSELECTED',
  PARTIAL_SELECTED: 'PARTIAL_SELECTED',
  SELECTED: 'SELECTED',
  OUT_OF_STOCK: 'OUT_OF_STOCK'
}

class ProductStore {
  constructor() {
    makeAutoObservable(this)
  }

  selectedSpecs = {}
  quantity = 1
  currentSku = null
  cartCount = 0
  cartAnimationStartPos = null
  reviewPage = 1
  reviewsPerPage = 5
  loadedReviewPages = new Set()
  isLoadingReviews = false
  skuState = SKU_STATES.UNSELECTED

  get product() {
    return productInfo
  }

  get specs() {
    return specGroups
  }

  get allImages() {
    return productImages
  }

  get allReviews() {
    return reviews
  }

  get currentImages() {
    if (this.currentSku) {
      return this.currentSku.images.map(id => productImages[id])
    }
    const partialMatchedSku = this.findPartialMatchedSku()
    if (partialMatchedSku) {
      return partialMatchedSku.images.map(id => productImages[id])
    }
    return skuList[0].images.map(id => productImages[id])
  }

  get currentPrice() {
    if (this.currentSku) {
      return this.currentSku.price
    }
    return null
  }

  get currentOriginalPrice() {
    if (this.currentSku) {
      return this.currentSku.originalPrice
    }
    return null
  }

  get currentStock() {
    if (this.currentSku) {
      return this.currentSku.stock
    }
    return null
  }

  get isSkuSelected() {
    return this.skuState === SKU_STATES.SELECTED
  }

  get selectedSpecsText() {
    return specGroups
      .map(group => {
        const optionId = this.selectedSpecs[group.id]
        const option = group.options.find(opt => opt.id === optionId)
        return option ? option.name : ''
      })
      .filter(Boolean)
      .join(' / ')
  }

  get availableSpecOptions() {
    const result = {}
    specGroups.forEach(group => {
      result[group.id] = group.options.map(option => {
        const testSpecs = { ...this.selectedSpecs, [group.id]: option.id }
        const matchingSku = skuList.find(sku => {
          return Object.keys(testSpecs).every(key => sku.specs[key] === testSpecs[key])
        })
        return {
          ...option,
          available: matchingSku ? matchingSku.stock > 0 : true
        }
      })
    })
    return result
  }

  get paginatedReviews() {
    const start = (this.reviewPage - 1) * this.reviewsPerPage
    const end = start + this.reviewsPerPage
    return reviews.slice(start, end)
  }

  get totalReviewPages() {
    return Math.ceil(reviews.length / this.reviewsPerPage)
  }

  findPartialMatchedSku() {
    const selectedKeys = Object.keys(this.selectedSpecs)
    if (selectedKeys.length === 0) return null

    for (const sku of skuList) {
      const isMatch = selectedKeys.every(key => sku.specs[key] === this.selectedSpecs[key])
      if (isMatch && sku.stock > 0) {
        return sku
      }
    }
    return null
  }

  transitionSkuState() {
    const selectedCount = Object.keys(this.selectedSpecs).length
    const totalGroups = specGroups.length

    if (selectedCount === 0) {
      this.skuState = SKU_STATES.UNSELECTED
    } else if (selectedCount < totalGroups) {
      this.skuState = SKU_STATES.PARTIAL_SELECTED
    } else {
      if (this.currentSku && this.currentSku.stock > 0) {
        this.skuState = SKU_STATES.SELECTED
      } else {
        this.skuState = SKU_STATES.OUT_OF_STOCK
      }
    }
  }

  selectSpec(groupId, optionId) {
    runInAction(() => {
      if (this.selectedSpecs[groupId] === optionId) {
        delete this.selectedSpecs[groupId]
      } else {
        this.selectedSpecs[groupId] = optionId
      }
      this.updateCurrentSku()
      this.transitionSkuState()
    })
  }

  updateCurrentSku() {
    const selectedCount = Object.keys(this.selectedSpecs).length
    const totalGroups = specGroups.length

    if (selectedCount < totalGroups) {
      this.currentSku = null
      return
    }

    const matchingSku = skuList.find(sku => {
      return Object.keys(this.selectedSpecs).every(
        key => sku.specs[key] === this.selectedSpecs[key]
      )
    })
    this.currentSku = matchingSku || null
  }

  setQuantity(num) {
    const max = this.currentStock || 99
    this.quantity = Math.max(1, Math.min(num, max))
  }

  increaseQuantity() {
    this.setQuantity(this.quantity + 1)
  }

  decreaseQuantity() {
    this.setQuantity(this.quantity - 1)
  }

  addToCart(startPos) {
    if (this.skuState !== SKU_STATES.SELECTED) return false
    if (this.currentStock <= 0) return false

    this.cartAnimationStartPos = startPos
    return true
  }

  completeCartAnimation() {
    runInAction(() => {
      this.cartCount += this.quantity
      this.cartAnimationStartPos = null
    })
  }

  async setReviewPage(page) {
    if (page < 1 || page > this.totalReviewPages) return
    if (page === this.reviewPage) return
    if (this.isLoadingReviews) return
    if (this.loadedReviewPages.has(page)) {
      this.reviewPage = page
      return
    }

    runInAction(() => {
      this.isLoadingReviews = true
    })

    await new Promise(resolve => setTimeout(resolve, 300))

    runInAction(() => {
      this.reviewPage = page
      this.loadedReviewPages.add(page)
      this.isLoadingReviews = false
    })
  }
}

export const productStore = new ProductStore()
export { SKU_STATES }
