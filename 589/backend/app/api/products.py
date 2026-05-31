from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, get_history_db
from ..models.product import Product
from ..schemas.product import ProductCreate, ProductResponse, Product as ProductSchema
from ..schemas.price import ComparisonResult, PriceHistory
from ..services import SmartComparator, PriceAnalyzer

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search", response_model=dict)
def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.name.ilike(f"%{q}%"))
    if category:
        query = query.filter(Product.category == category)

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        "items": [ProductResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size
    }


@router.get("/hot", response_model=List[dict])
def get_hot_products(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db)
):
    products = db.query(Product).limit(limit).all()
    results = []

    for product in products:
        comparator = SmartComparator(db, history_db)
        comparison = comparator.compare_prices(product)
        if comparison.prices:
            results.append({
                "product": ProductSchema.model_validate(product),
                "best_price": min(p.price for p in comparison.prices),
                "lowest_ever": comparison.lowest_ever,
                "potential_savings": comparison.potential_savings
            })

    return sorted(results, key=lambda x: x["potential_savings"], reverse=True)[:limit]


@router.get("/{product_id}", response_model=ProductSchema)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductSchema.model_validate(product)


@router.get("/{product_id}/prices", response_model=ComparisonResult)
def get_product_prices(
    product_id: str,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    comparator = SmartComparator(db, history_db)
    from ..services import CouponMatcher
    coupon_matcher = CouponMatcher(db)
    coupons = coupon_matcher.get_active_coupons()

    return comparator.compare_prices(product, coupons)


@router.get("/{product_id}/history", response_model=List[PriceHistory])
def get_price_history(
    product_id: str,
    days: int = Query(30, ge=7, le=365),
    history_db: Session = Depends(get_history_db)
):
    analyzer = PriceAnalyzer(None, history_db)
    history = analyzer.get_price_history(product_id, days)
    return [
        PriceHistory(date=h.record_date, price=float(h.price), platform=h.platform)
        for h in history
    ]


@router.get("/{product_id}/stats")
def get_price_stats(
    product_id: str,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db)
):
    analyzer = PriceAnalyzer(db, history_db)
    return analyzer.calculate_price_stats(product_id, days)


@router.get("/{product_id}/recommendation")
def get_purchase_recommendation(
    product_id: str,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db)
):
    analyzer = PriceAnalyzer(db, history_db)
    return analyzer.get_optimal_purchase_time(product_id)


@router.post("/", response_model=ProductSchema)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductSchema.model_validate(product)


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Product.category).distinct().all()
    return [c[0] for c in categories]
