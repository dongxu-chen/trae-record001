import socketio
from datetime import datetime
from typing import Dict, Set
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..database import SessionLocal, HistorySessionLocal
from ..services import AlertService


sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    ping_interval=25000,
    ping_timeout=60000
)

app = socketio.ASGIApp(sio)

connected_users: Dict[str, Set[str]] = {}
scheduler = None


@sio.event(namespace="/alerts")
async def connect(sid, environ):
    user_id = environ.get('HTTP_X_USER_ID', 'anonymous')
    if user_id not in connected_users:
        connected_users[user_id] = set()
    connected_users[user_id].add(sid)
    print(f"User {user_id} connected with sid {sid}")
    await sio.emit("connected", {"status": "ok", "user_id": user_id}, room=sid, namespace="/alerts")


@sio.event(namespace="/alerts")
async def disconnect(sid):
    for user_id, sids in connected_users.items():
        if sid in sids:
            sids.remove(sid)
            if not sids:
                del connected_users[user_id]
            print(f"User {user_id} disconnected with sid {sid}")
            break


@sio.event(namespace="/alerts")
async def subscribe_product(sid, data):
    product_id = data.get('product_id')
    if product_id:
        await sio.enter_room(sid, f"product_{product_id}", namespace="/alerts")
        await sio.emit("subscribed", {"product_id": product_id}, room=sid, namespace="/alerts")


@sio.event(namespace="/alerts")
async def unsubscribe_product(sid, data):
    product_id = data.get('product_id')
    if product_id:
        await sio.leave_room(sid, f"product_{product_id}", namespace="/alerts")
        await sio.emit("unsubscribed", {"product_id": product_id}, room=sid, namespace="/alerts")


async def check_price_alerts():
    db = SessionLocal()
    history_db = HistorySessionLocal()
    try:
        service = AlertService(db, history_db, sio)
        triggered = service.check_alerts()

        for alert in triggered:
            user_id = alert.get('user_id')
            if user_id and user_id in connected_users:
                for sid in connected_users[user_id]:
                    await sio.emit(
                        "price_drop",
                        alert,
                        room=sid,
                        namespace="/alerts"
                    )
            print(f"Alert triggered for product {alert.get('product_id')}: "
                  f"¥{alert.get('current_price')} (target: ¥{alert.get('target_price')})")
    except Exception as e:
        print(f"Error checking price alerts: {e}")
    finally:
        db.close()
        history_db.close()


async def broadcast_price_update(product_id: str, price_data: Dict):
    await sio.emit(
        "price_update",
        {
            "product_id": product_id,
            "price": price_data.get("price"),
            "platform": price_data.get("platform"),
            "timestamp": datetime.now().isoformat()
        },
        room=f"product_{product_id}",
        namespace="/alerts"
    )


def start_scheduler():
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')
        scheduler.add_job(check_price_alerts, 'interval', minutes=5)
        scheduler.start()
        print("WebSocket scheduler started - checking alerts every 5 minutes")


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None


def get_sio_app():
    return app
