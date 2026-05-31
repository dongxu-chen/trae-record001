from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..database import get_db, get_history_db
from ..schemas.alert import (
    PriceAlertCreate,
    PriceAlertResponse,
    FavoriteCreate,
    Favorite as FavoriteSchema
)
from ..services import AlertService
from ..models.alert import Favorite, User
from ..models.product import Product

router = APIRouter(tags=["alerts"])

MOCK_USER_ID = "user-001"


@router.get("/alerts", response_model=List[PriceAlertResponse])
def get_alerts(
    active_only: bool = True,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    service = AlertService(db, history_db)
    alerts = service.get_user_alerts(x_user_id, active_only)

    result = []
    for alert in alerts:
        alert_response = PriceAlertResponse.model_validate(alert)
        current_price = service._get_current_price(alert.product_id, alert.platform)
        alert_response.current_price = current_price
        result.append(alert_response)

    return result


@router.post("/alerts", response_model=PriceAlertResponse)
def create_alert(
    alert_data: PriceAlertCreate,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    service = AlertService(db, history_db)
    alert = service.create_alert(x_user_id, alert_data)
    alert_response = PriceAlertResponse.model_validate(alert)
    alert_response.current_price = service._get_current_price(alert.product_id, alert.platform)
    return alert_response


@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    service = AlertService(db, history_db)
    success = service.delete_alert(alert_id, x_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True}


@router.put("/alerts/{alert_id}/deactivate")
def deactivate_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    service = AlertService(db, history_db)
    success = service.deactivate_alert(alert_id, x_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True}


@router.get("/alerts/stats")
def get_alert_stats(
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    service = AlertService(db, history_db)
    return service.get_alert_stats(x_user_id)


@router.post("/alerts/check")
def check_alerts(
    db: Session = Depends(get_db),
    history_db: Session = Depends(get_history_db)
):
    service = AlertService(db, history_db)
    triggered = service.check_alerts()
    return {
        "triggered": triggered,
        "count": len(triggered)
    }


@router.get("/user/favorites", response_model=List[dict])
def get_favorites(
    db: Session = Depends(get_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    favorites = db.query(Favorite).filter(Favorite.user_id == x_user_id).all()
    result = []
    for fav in favorites:
        product = db.query(Product).filter(Product.id == fav.product_id).first()
        if product:
            result.append({
                "id": fav.id,
                "product": product,
                "created_at": fav.created_at
            })
    return result


@router.post("/user/favorites")
def add_favorite(
    favorite_data: FavoriteCreate,
    db: Session = Depends(get_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    existing = db.query(Favorite).filter(
        Favorite.user_id == x_user_id,
        Favorite.product_id == favorite_data.product_id
    ).first()
    if existing:
        return {"success": True, "message": "Already in favorites"}

    favorite = Favorite(
        user_id=x_user_id,
        product_id=favorite_data.product_id
    )
    db.add(favorite)
    db.commit()
    return {"success": True}


@router.delete("/user/favorites/{favorite_id}")
def remove_favorite(
    favorite_id: str,
    db: Session = Depends(get_db),
    x_user_id: str = Header(MOCK_USER_ID)
):
    favorite = db.query(Favorite).filter(
        Favorite.id == favorite_id,
        Favorite.user_id == x_user_id
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(favorite)
    db.commit()
    return {"success": True}
