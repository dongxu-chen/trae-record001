
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from db import init_db, get_db
from shortener import create_short_url, get_original_url, increment_click_count, delete_short_url
from auth import get_api_key

app = FastAPI()


class URLCreate(BaseModel):
    url: str
    custom_code: Optional[str] = None
    expires_at: Optional[datetime] = None


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/shorten")
def create_shorten(
    url_create: URLCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    try:
        db_url = create_short_url(
            db,
            url_create.url,
            custom_code=url_create.custom_code,
            expires_at=url_create.expires_at
        )
        return {
            "original_url": db_url.original_url,
            "short_code": db_url.short_code,
            "click_count": db_url.click_count,
            "expires_at": db_url.expires_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/{short_code}")
def delete_shorten(
    short_code: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    success = delete_short_url(db, short_code)
    if success:
        return {"detail": "Short URL deleted successfully"}
    raise HTTPException(status_code=404, detail="Short URL not found")


@app.get("/{short_code}")
def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    db_url = get_original_url(db, short_code)
    if db_url:
        if db_url.expires_at and db_url.expires_at < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Short URL has expired")
        increment_click_count(db, db_url)
        return RedirectResponse(url=db_url.original_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")


@app.get("/stats/{short_code}")
def get_stats(short_code: str, db: Session = Depends(get_db)):
    db_url = get_original_url(db, short_code)
    if db_url:
        return {
            "original_url": db_url.original_url,
            "short_code": db_url.short_code,
            "click_count": db_url.click_count,
            "created_at": db_url.created_at,
            "expires_at": db_url.expires_at
        }
    raise HTTPException(status_code=404, detail="Short URL not found")
