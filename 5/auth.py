
from fastapi import HTTPException, Header
import os

DEFAULT_API_KEY = "secret-key-12345"
API_KEY = os.getenv("SHORTENER_API_KEY", DEFAULT_API_KEY)


async def get_api_key(x_api_key: str = Header(..., description="API Key for authentication")):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
