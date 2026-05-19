from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


class CounselorBase(BaseModel):
    name: str
    title: str
    specialty: Optional[str] = None
    available_times: Optional[str] = None
    online: Optional[bool] = False


class CounselorCreate(CounselorBase):
    pass


class Counselor(CounselorBase):
    id: int
    
    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    student_name: str
    student_id: str
    phone: Optional[str] = None
    counselor_id: int
    appointment_date: date
    appointment_time: str
    reason: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdateStatus(BaseModel):
    status: str


class Appointment(AppointmentBase):
    id: int
    status: str
    video_room_id: Optional[str] = None
    reason_desensitized: Optional[str] = None
    created_at: datetime
    counselor: Optional[Counselor] = None
    
    class Config:
        from_attributes = True


class ConfessionBase(BaseModel):
    content: str


class ConfessionCreate(ConfessionBase):
    pass


class Confession(ConfessionBase):
    id: int
    crisis_level: str
    crisis_keyword: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReplyBase(BaseModel):
    content: str


class ReplyCreate(ReplyBase):
    confession_id: int


class Reply(ReplyBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SCL90TestCreate(BaseModel):
    answers: str


class SCL90TestResult(BaseModel):
    scores: dict
    max_score: float


class VideoRoomJoin(BaseModel):
    room_id: str
    user_type: str = "user"


class WebSocketMessage(BaseModel):
    type: str
    data: dict


class ApiResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None
