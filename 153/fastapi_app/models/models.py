from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class Counselor(Base):
    __tablename__ = "counselors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    title = Column(String(100), nullable=False)
    specialty = Column(String(200))
    avatar = Column(String(200), default='default_avatar.png')
    available_times = Column(String(500))
    online = Column(Boolean, default=False)
    
    appointments = relationship("Appointment", back_populates="counselor")


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100), nullable=False)
    student_id = Column(String(50), nullable=False)
    phone = Column(String(20))
    counselor_id = Column(Integer, ForeignKey("counselors.id"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(String(20), nullable=False)
    reason = Column(Text)
    reason_desensitized = Column(Text)
    consultation_notes = Column(Text)
    notes_desensitized = Column(Text)
    status = Column(String(20), default='待确认')
    video_room_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    version = Column(Integer, default=0, nullable=False)
    
    counselor = relationship("Counselor", back_populates="appointments")
    
    __table_args__ = (
        Index('idx_counselor_date', 'counselor_id', 'appointment_date'),
    )


class SCL90Test(Base):
    __tablename__ = "scl90_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    answers = Column(Text, nullable=False)
    scores = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Confession(Base):
    __tablename__ = "confessions"
    
    id = Column(Integer, primary_key=True, index=True)
    content_encrypted = Column(Text, nullable=False)
    crisis_level = Column(String(20), default='正常')
    crisis_keyword = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    replies = relationship("Reply", back_populates="confession")
    
    @property
    def content(self):
        from ..core.security import decrypt_content
        return decrypt_content(self.content_encrypted)
    
    @content.setter
    def content(self, value):
        from ..core.security import encrypt_content
        self.content_encrypted = encrypt_content(value)


class Reply(Base):
    __tablename__ = "replies"
    
    id = Column(Integer, primary_key=True, index=True)
    confession_id = Column(Integer, ForeignKey("confessions.id"), nullable=False)
    content_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    confession = relationship("Confession", back_populates="replies")
    
    @property
    def content(self):
        from ..core.security import decrypt_content
        return decrypt_content(self.content_encrypted)
    
    @content.setter
    def content(self, value):
        from ..core.security import encrypt_content
        self.content_encrypted = encrypt_content(value)


class VideoSession(Base):
    __tablename__ = "video_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(100), unique=True, nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    counselor_id = Column(Integer, ForeignKey("counselors.id"))
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    status = Column(String(20), default='待开始')
