from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
from datetime import datetime, date
import uuid

from ..core.database import get_db
from ..core.websocket import manager
from ..core.security import analyze_crisis_level, desensitize_text
from ..models.models import Counselor, Appointment, Confession, Reply, SCL90Test
from ..schemas.schemas import (
    Counselor as CounselorSchema,
    Appointment as AppointmentSchema,
    AppointmentCreate,
    Confession as ConfessionSchema,
    ConfessionCreate,
    ApiResponse
)

router = APIRouter()
templates = Jinja2Templates(directory="fastapi_app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/counselors", response_class=HTMLResponse)
async def counselors_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counselor))
    counselors = result.scalars().all()
    return templates.TemplateResponse("counselors.html", {"request": request, "counselors": counselors})


@router.get("/api/counselors", response_model=List[CounselorSchema])
async def get_counselors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counselor))
    return result.scalars().all()


@router.get("/book/{counselor_id}", response_class=HTMLResponse)
async def book_page(request: Request, counselor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counselor).where(Counselor.id == counselor_id))
    counselor = result.scalar_one_or_none()
    if not counselor:
        raise HTTPException(status_code=404, detail="咨询师不存在")
    return templates.TemplateResponse("book.html", {"request": request, "counselor": counselor})


@router.post("/api/appointments", response_model=ApiResponse)
async def create_appointment(appointment: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.counselor_id == appointment.counselor_id,
                Appointment.appointment_date == appointment.appointment_date,
                Appointment.appointment_time == appointment.appointment_time,
                Appointment.status.in_(["待确认", "已确认"])
            )
        ).with_for_update()
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return ApiResponse(success=False, message="该时段已被预约，请选择其他时间")
    
    room_id = str(uuid.uuid4())[:8]
    reason_desensitized = desensitize_text(appointment.reason or "")
    
    db_appointment = Appointment(
        **appointment.model_dump(),
        video_room_id=room_id,
        reason_desensitized=reason_desensitized
    )
    
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    
    return ApiResponse(
        success=True,
        message="预约成功",
        data={"appointment_id": db_appointment.id, "video_room_id": room_id}
    )


@router.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).order_by(Appointment.created_at.desc())
    )
    appointments = result.scalars().all()
    return templates.TemplateResponse("appointments.html", {"request": request, "appointments": appointments})


@router.get("/api/appointments", response_model=List[AppointmentSchema])
async def get_appointments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).order_by(Appointment.created_at.desc())
    )
    return result.scalars().all()


@router.post("/api/appointments/{appointment_id}/status")
async def update_appointment_status(appointment_id: int, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id).with_for_update()
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="预约不存在")
    
    appointment.status = status
    appointment.version += 1
    await db.commit()
    
    return ApiResponse(success=True, message="状态已更新")


@router.get("/video/{room_id}", response_class=HTMLResponse)
async def video_room(request: Request, room_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Appointment).where(Appointment.video_room_id == room_id)
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        return RedirectResponse(url="/appointments")
    
    return templates.TemplateResponse("video.html", {
        "request": request,
        "room_id": room_id,
        "appointment": appointment
    })


@router.get("/confessions", response_class=HTMLResponse)
async def confessions_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Confession).order_by(Confession.created_at.desc())
    )
    confessions = result.scalars().all()
    return templates.TemplateResponse("confessions.html", {"request": request, "confessions": confessions})


@router.get("/api/confessions", response_model=List[ConfessionSchema])
async def get_confessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Confession).order_by(Confession.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.post("/api/confessions", response_model=ApiResponse)
async def create_confession(confession: ConfessionCreate, db: AsyncSession = Depends(get_db)):
    crisis_level, crisis_keyword = analyze_crisis_level(confession.content)
    
    db_confession = Confession()
    db_confession.content = confession.content
    db_confession.crisis_level = crisis_level
    db_confession.crisis_keyword = crisis_keyword
    
    db.add(db_confession)
    await db.commit()
    await db.refresh(db_confession)
    
    return ApiResponse(
        success=True,
        message="倾诉已发布" if crisis_level == "正常" else f"检测到{crisis_level}风险，建议及时寻求专业帮助",
        data={"crisis_level": crisis_level}
    )


@router.post("/api/confessions/{confession_id}/reply", response_model=ApiResponse)
async def reply_confession(confession_id: int, content: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Confession).where(Confession.id == confession_id)
    )
    confession = result.scalar_one_or_none()
    
    if not confession:
        raise HTTPException(status_code=404, detail="倾诉不存在")
    
    reply = Reply()
    reply.confession_id = confession_id
    reply.content = content
    
    db.add(reply)
    await db.commit()
    
    return ApiResponse(success=True, message="回复已发布")


@router.get("/scl90", response_class=HTMLResponse)
async def scl90_page(request: Request):
    return templates.TemplateResponse("scl90.html", {"request": request})


def calculate_scl90_scores(answers: List[str]) -> dict:
    factors = {
        '躯体化': [1, 4, 12, 27, 40, 42, 48, 49, 52, 53, 56, 58],
        '强迫症状': [3, 9, 10, 28, 38, 45, 46, 51, 55, 65],
        '人际关系敏感': [6, 21, 34, 36, 37, 41, 61, 69, 73],
        '抑郁': [5, 14, 15, 20, 22, 26, 29, 30, 31, 32, 54, 71, 79],
        '焦虑': [2, 17, 23, 33, 39, 57, 72, 78, 80, 86],
        '敌对': [11, 24, 63, 67, 74, 81],
        '恐怖': [13, 25, 47, 50, 70, 75, 82],
        '偏执': [8, 18, 43, 68, 76, 83],
        '精神病性': [7, 16, 35, 62, 77, 84, 85, 87, 88, 90],
        '其他': [19, 44, 59, 60, 64, 66, 89]
    }
    
    scores = {}
    for factor, questions in factors.items():
        total = sum(int(answers[q-1]) for q in questions)
        scores[factor] = round(total / len(questions), 2)
    
    return scores


@router.post("/api/scl90/test")
async def scl90_test(answers: List[str], db: AsyncSession = Depends(get_db)):
    if len(answers) != 90:
        raise HTTPException(status_code=400, detail="需要90道题的答案")
    
    scores = calculate_scl90_scores(answers)
    max_score = max(scores.values())
    
    test = SCL90Test(
        answers=",".join(answers),
        scores=str(scores)
    )
    db.add(test)
    await db.commit()
    
    return {
        "scores": scores,
        "max_score": max_score
    }


@router.get("/scl90/result", response_class=HTMLResponse)
async def scl90_result_page(request: Request):
    return templates.TemplateResponse("scl90_result.html", {"request": request})


@router.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        await manager.join_room(room_id, client_id)
        
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "webrtc_signal":
                await manager.handle_webrtc_signal(
                    room_id=room_id,
                    from_client=client_id,
                    signal_data=data.get("data", {})
                )
            elif message_type == "chat_message":
                await manager.handle_chat_message(
                    room_id=room_id,
                    from_client=client_id,
                    content=data.get("content", "")
                )
            elif message_type == "ping":
                await manager.send_personal_message({"type": "pong"}, client_id)
    
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
