from .products import router as products_router
from .coupon import router as coupon_router
from .alert import router as alert_router

__all__ = [
    "products_router",
    "coupon_router",
    "alert_router"
]
