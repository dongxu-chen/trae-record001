import os
import sys
import json
import base64
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from io import BytesIO

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from PIL import Image
import cv2

from config import config
from core.monitoring import ExamMonitor, AlertLevel, AlertType
from core.question_bank import QuestionBank
from core.similarity import SimilarityAnalyzer
from core.face_recognition import FaceRecognition
from core.audio import AudioMonitor
from core.remote_monitor import RemoteMonitor
from core.risk_scoring import RiskScorer
from server.websocket import ExamWebSocketManager, websocket_endpoint
from server.webrtc import WebRTCManager

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="基于人脸识别、屏幕录制、切屏检测的智能在线考试防作弊系统"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

exam_monitor = ExamMonitor()
question_bank = QuestionBank()
similarity_analyzer = SimilarityAnalyzer()
face_recognition = FaceRecognition()
audio_monitor = AudioMonitor(
    sample_rate=config.AUDIO_SAMPLE_RATE,
    chunk_size=config.AUDIO_CHUNK_SIZE
)
remote_monitor = RemoteMonitor(
    thumbnail_size=(config.REMOTE_THUMBNAIL_WIDTH, config.REMOTE_THUMBNAIL_HEIGHT),
    max_history=config.REMOTE_MAX_HISTORY,
    quality=config.REMOTE_IMAGE_QUALITY
)
risk_scorer = RiskScorer()
websocket_manager = ExamWebSocketManager(exam_monitor)
webrtc_manager = WebRTCManager(face_recognition)

exam_submissions: Dict[str, List[Dict[str, Any]]] = {}


class StudentLoginRequest(BaseModel):
    student_id: str
    student_name: str = ""
    exam_id: str = "default_exam"


class FaceVerificationRequest(BaseModel):
    student_id: str
    image: str


class ExamStartRequest(BaseModel):
    student_id: str
    exam_id: str = "default_exam"
    question_count: int = 10
    subject: Optional[str] = None
    difficulty: Optional[str] = None


class AnswerSubmitRequest(BaseModel):
    student_id: str
    exam_id: str
    question_id: str
    answer: str
    question_text: str = ""
    question_type: str = "text"


class ExamSubmitRequest(BaseModel):
    student_id: str
    exam_id: str
    answers: List[Dict[str, Any]]


class IceCandidateRequest(BaseModel):
    student_id: str
    candidate: Dict[str, Any]


class OfferRequest(BaseModel):
    student_id: str
    offer: Dict[str, Any]


class AudioChunkRequest(BaseModel):
    student_id: str
    exam_id: str = "default_exam"
    audio_data: List[float]
    sample_rate: int = 16000


@app.on_event("startup")
async def startup_event():
    print(f"[{datetime.now()}] 正在启动 {config.APP_NAME} v{config.APP_VERSION}...")
    exam_monitor.start_background_monitoring()
    print(f"[{datetime.now()}] 后台监控已启动")
    
    webrtc_manager.set_on_frame_callback(on_webrtc_frame)
    webrtc_manager.set_on_new_peer_callback(on_new_peer)
    webrtc_manager.set_on_peer_disconnect_callback(on_peer_disconnect)
    print(f"[{datetime.now()}] WebRTC管理器已初始化")
    
    sample_questions = create_sample_questions()
    for q in sample_questions:
        question_bank.add_question(q)
    print(f"[{datetime.now()}] 已加载 {len(sample_questions)} 道示例题目")
    
    print(f"[{datetime.now()}] 服务启动完成，监听 http://{config.HOST}:{config.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    print(f"[{datetime.now()}] 正在关闭服务...")
    exam_monitor.stop_background_monitoring()
    await websocket_manager.disconnect_all()
    await webrtc_manager.close_all()
    print(f"[{datetime.now()}] 服务已关闭")


def create_sample_questions() -> List[Dict]:
    questions_data = [
        {
            "id": "q001",
            "type": "single",
            "subject": "计算机基础",
            "difficulty": "easy",
            "content": "Python中用于定义函数的关键字是？",
            "options": ["func", "def", "function", "define"],
            "correct_answer": "def",
            "tags": ["Python", "基础语法"]
        },
        {
            "id": "q002",
            "type": "single",
            "subject": "计算机基础",
            "difficulty": "easy",
            "content": "以下哪个不是Python的数据类型？",
            "options": ["int", "string", "float", "char"],
            "correct_answer": "char",
            "tags": ["Python", "数据类型"]
        },
        {
            "id": "q003",
            "type": "single",
            "subject": "计算机基础",
            "difficulty": "medium",
            "content": "在Python中，列表使用以下哪种符号表示？",
            "options": ["{}", "[]", "()", "<>"],
            "correct_answer": "[]",
            "tags": ["Python", "数据结构"]
        },
        {
            "id": "q004",
            "type": "single",
            "subject": "计算机基础",
            "difficulty": "medium",
            "content": "以下哪个方法可以向列表末尾添加元素？",
            "options": ["add()", "append()", "insert()", "push()"],
            "correct_answer": "append()",
            "tags": ["Python", "列表"]
        },
        {
            "id": "q005",
            "type": "single",
            "subject": "计算机基础",
            "difficulty": "hard",
            "content": "Python中用于处理异常的语句是？",
            "options": ["if-else", "try-except", "for-in", "while"],
            "correct_answer": "try-except",
            "tags": ["Python", "异常处理"]
        },
        {
            "id": "q006",
            "type": "single",
            "subject": "计算机网络",
            "difficulty": "easy",
            "content": "HTTP协议默认使用的端口号是？",
            "options": ["21", "22", "80", "443"],
            "correct_answer": "80",
            "tags": ["网络", "HTTP"]
        },
        {
            "id": "q007",
            "type": "single",
            "subject": "计算机网络",
            "difficulty": "medium",
            "content": "HTTPS协议使用的默认端口号是？",
            "options": ["21", "22", "80", "443"],
            "correct_answer": "443",
            "tags": ["网络", "HTTPS"]
        },
        {
            "id": "q008",
            "type": "single",
            "subject": "计算机网络",
            "difficulty": "medium",
            "content": "DNS的主要作用是？",
            "options": ["加密数据", "域名解析", "数据压缩", "负载均衡"],
            "correct_answer": "域名解析",
            "tags": ["网络", "DNS"]
        },
        {
            "id": "q009",
            "type": "text",
            "subject": "计算机基础",
            "difficulty": "medium",
            "content": "请简述Python中列表和元组的区别。",
            "correct_answer": "列表是可变的，使用[]表示，可以添加、删除、修改元素；元组是不可变的，使用()表示，一旦创建就不能修改。",
            "tags": ["Python", "数据结构"]
        },
        {
            "id": "q010",
            "type": "text",
            "subject": "计算机网络",
            "difficulty": "hard",
            "content": "请简述TCP和UDP的区别。",
            "correct_answer": "TCP是面向连接的可靠传输协议，提供确认、重传、流量控制等机制；UDP是无连接的不可靠传输协议，不保证数据可靠到达，但传输速度快。",
            "tags": ["网络", "传输协议"]
        },
        {
            "id": "q011",
            "type": "multiple",
            "subject": "计算机基础",
            "difficulty": "medium",
            "content": "以下哪些是Python的关键字？（多选）",
            "options": ["if", "else", "then", "for", "loop"],
            "correct_answer": ["if", "else", "for"],
            "tags": ["Python", "基础语法"]
        },
        {
            "id": "q012",
            "type": "single",
            "subject": "数据库",
            "difficulty": "easy",
            "content": "SQL中用于查询数据的关键字是？",
            "options": ["INSERT", "UPDATE", "SELECT", "DELETE"],
            "correct_answer": "SELECT",
            "tags": ["数据库", "SQL"]
        },
        {
            "id": "q013",
            "type": "single",
            "subject": "数据库",
            "difficulty": "medium",
            "content": "SQL中用于添加数据的关键字是？",
            "options": ["INSERT", "UPDATE", "SELECT", "DELETE"],
            "correct_answer": "INSERT",
            "tags": ["数据库", "SQL"]
        },
        {
            "id": "q014",
            "type": "text",
            "subject": "操作系统",
            "difficulty": "medium",
            "content": "什么是进程和线程？它们有什么区别？",
            "correct_answer": "进程是资源分配的最小单位，线程是CPU调度的最小单位。一个进程可以包含多个线程，线程共享进程的资源。进程间通信开销大，线程间通信开销小。",
            "tags": ["操作系统", "进程线程"]
        },
        {
            "id": "q015",
            "type": "single",
            "subject": "数据结构",
            "difficulty": "easy",
            "content": "栈的特点是？",
            "options": ["先进先出", "后进先出", "随机访问", "双端操作"],
            "correct_answer": "后进先出",
            "tags": ["数据结构", "栈"]
        }
    ]
    
    return questions_data


def on_webrtc_frame(student_id: str, frame: np.ndarray) -> None:
    try:
        session = exam_monitor.get_session(student_id)
        if session and session.is_active:
            is_paused = exam_monitor.is_exam_paused(student_id)
            
            if is_paused:
                frame_data = webrtc_manager.frame_to_base64(frame)
                if frame_data:
                    asyncio.create_task(
                        websocket_manager.send_message(
                            student_id,
                            {"type": "exam_paused", "reason": session.paused_reason}
                        )
                    )
                return
            
            is_match, similarity, details = exam_monitor.check_face_periodic(student_id, frame)
            
            face_count = details.get('face_count', 0)
            liveness_passed = details.get('liveness_passed', True)
            
            if config.ENABLE_REMOTE_MONITOR:
                remote_monitor.update_frame(
                    student_id, frame,
                    face_details={
                        'face_count': face_count,
                        'is_paused': is_paused
                    }
                )
            
            if config.ENABLE_RISK_SCORING:
                risk_scorer.update_face_score(
                    student_id, session.exam_id,
                    is_match, face_count > 0,
                    liveness_passed, face_count
                )
                report = risk_scorer.get_report(student_id, session.exam_id)
                if report:
                    remote_monitor.update_student_status(
                        student_id,
                        risk_level=report.level.value
                    )
            
            frame_data = webrtc_manager.frame_to_base64(frame)
            if frame_data:
                asyncio.create_task(
                    websocket_manager.send_face_frame(
                        student_id, frame_data, face_count > 0, similarity,
                        details={
                            'face_count': face_count,
                            'liveness_passed': liveness_passed,
                            'is_paused': exam_monitor.is_exam_paused(student_id)
                        }
                    )
                )
    except Exception as e:
        print(f"Error processing WebRTC frame: {e}")


def on_new_peer(student_id: str) -> None:
    print(f"New WebRTC peer connected: {student_id}")
    stats = webrtc_manager.get_all_stats()
    asyncio.create_task(
        websocket_manager.send_monitor_update('peer_connected', {
            'student_id': student_id,
            'stats': stats
        })
    )


def on_peer_disconnect(student_id: str) -> None:
    print(f"WebRTC peer disconnected: {student_id}")
    stats = webrtc_manager.get_all_stats()
    asyncio.create_task(
        websocket_manager.send_monitor_update('peer_disconnected', {
            'student_id': student_id,
            'stats': stats
        })
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/student", response_class=HTMLResponse)
async def student_page(request: Request):
    return templates.TemplateResponse("student.html", {"request": request})


@app.get("/teacher", response_class=HTMLResponse)
async def teacher_page(request: Request):
    return templates.TemplateResponse("teacher.html", {"request": request})


@app.get("/api/config")
async def get_config():
    return {
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION,
        "webrtc_stun_server": config.WEBRTC_STUN_SERVER,
        "features": {
            "face_detection": config.ENABLE_FACE_DETECTION,
            "liveness_detection": config.ENABLE_LIVENESS_DETECTION,
            "single_face_lock": config.ENABLE_SINGLE_FACE_LOCK,
            "auto_pause_on_multiple_faces": config.ENABLE_AUTO_PAUSE_ON_MULTIPLE_FACES,
            "recording": config.ENABLE_RECORDING,
            "tab_detection": config.ENABLE_TAB_DETECTION,
            "fullscreen_detection": config.ENABLE_FULLSCREEN_DETECTION,
            "multi_monitor_detection": config.ENABLE_MULTI_MONITOR_DETECTION,
            "similarity_check": config.ENABLE_SIMILARITY_CHECK,
            "monitoring": config.ENABLE_MONITORING,
            "audio_monitoring": config.ENABLE_AUDIO_MONITORING,
            "remote_monitor": config.ENABLE_REMOTE_MONITOR,
            "risk_scoring": config.ENABLE_RISK_SCORING
        },
        "thresholds": {
            "face_recognition": config.FACE_RECOGNITION_THRESHOLD,
            "similarity": config.SIMILARITY_THRESHOLD,
            "structured_similarity": config.STRUCTURED_SIMILARITY_THRESHOLD,
            "structured_similarity_risk": config.STRUCTURED_SIMILARITY_RISK_THRESHOLD,
            "tab_switch": config.TAB_SWITCH_THRESHOLD,
            "multiple_face_grace_period": config.MULTIPLE_FACE_GRACE_PERIOD,
            "speech_detection": config.SPEECH_DETECTION_THRESHOLD,
            "high_volume": config.HIGH_VOLUME_THRESHOLD,
            "risk_auto_review": config.RISK_AUTO_REVIEW_THRESHOLD,
            "risk_critical": config.RISK_CRITICAL_THRESHOLD,
            "risk_medium": config.RISK_MEDIUM_THRESHOLD
        }
    }


@app.post("/api/auth/login")
async def login(request: StudentLoginRequest):
    return {
        "success": True,
        "student_id": request.student_id,
        "student_name": request.student_name,
        "exam_id": request.exam_id,
        "message": "登录成功"
    }


@app.post("/api/face/register")
async def register_face(
    student_id: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="无效的图片")
        
        success = face_recognition.register_face(student_id, img)
        
        if success:
            return {"success": True, "message": "人脸注册成功"}
        else:
            raise HTTPException(status_code=400, detail="未检测到人脸，注册失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/face/verify")
async def verify_face(request: FaceVerificationRequest):
    try:
        image_data = base64.b64decode(request.image.split(',')[0] if ',' in request.image else request.image)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="无效的图片")
        
        is_match, similarity, details = exam_monitor.verify_student_face(
            request.student_id, img,
            check_liveness=config.ENABLE_LIVENESS_DETECTION,
            check_single=config.ENABLE_SINGLE_FACE_LOCK
        )
        
        return {
            "success": True,
            "is_match": is_match,
            "similarity": similarity,
            "threshold": config.FACE_RECOGNITION_THRESHOLD,
            "details": details
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exam/start")
async def start_exam(request: ExamStartRequest):
    try:
        questions = question_bank.select_random_questions(
            count=request.question_count,
            subject=request.subject,
            difficulty=request.difficulty,
            shuffle_options=True,
            shuffle_questions=True
        )
        
        session = exam_monitor.start_exam_session(
            exam_id=request.exam_id,
            student_id=request.student_id
        )
        
        exam_submissions[f"{request.exam_id}_{request.student_id}"] = []
        
        if config.ENABLE_AUDIO_MONITORING:
            audio_monitor.register_student(request.student_id, request.exam_id)
        
        if config.ENABLE_REMOTE_MONITOR:
            remote_monitor.register_student(request.student_id, request.exam_id)
        
        if config.ENABLE_RISK_SCORING:
            risk_scorer.create_report(request.student_id, request.exam_id)
        
        return {
            "success": True,
            "exam_id": request.exam_id,
            "student_id": request.student_id,
            "session_id": session.exam_id,
            "start_time": session.start_time,
            "questions": [q.to_dict() for q in questions]
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exam/answer")
async def submit_answer(request: AnswerSubmitRequest):
    try:
        key = f"{request.exam_id}_{request.student_id}"
        if key not in exam_submissions:
            exam_submissions[key] = []
        
        submission = {
            "student_id": request.student_id,
            "exam_id": request.exam_id,
            "question_id": request.question_id,
            "question_text": request.question_text,
            "question_type": request.question_type,
            "answer": request.answer,
            "timestamp": datetime.now().isoformat()
        }
        
        exam_submissions[key].append(submission)
        
        session = exam_monitor.get_session(request.student_id)
        if session:
            session.add_event('answer_submitted', {
                'question_id': request.question_id,
                'question_type': request.question_type
            })
        
        return {"success": True, "message": "答案已提交"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exam/submit")
async def submit_exam(request: ExamSubmitRequest):
    try:
        key = f"{request.exam_id}_{request.student_id}"
        
        full_submissions = []
        for ans in request.answers:
            submission = {
                "student_id": request.student_id,
                "exam_id": request.exam_id,
                "question_id": ans.get("question_id", ""),
                "question_text": ans.get("question_text", ""),
                "answer": ans.get("answer", ""),
                "timestamp": datetime.now().isoformat()
            }
            full_submissions.append(submission)
        
        exam_submissions[key] = full_submissions
        
        session = exam_monitor.end_exam_session(request.student_id)
        
        all_submissions = []
        for k, subs in exam_submissions.items():
            if k.startswith(f"{request.exam_id}_"):
                all_submissions.extend(subs)
        
        similarity_result = {}
        if config.ENABLE_SIMILARITY_CHECK and len(all_submissions) > 1:
            similarity_result = exam_monitor.analyze_student_answers(
                request.exam_id, all_submissions
            )
            
            if config.ENABLE_RISK_SCORING:
                student_analysis = similarity_result.get('student_analysis', {})
                if request.student_id in student_analysis:
                    analysis = student_analysis[request.student_id]
                    risk_score = analysis.get('risk_score', 0)
                    matched_students = len(analysis.get('pairwise', {}))
                    risk_scorer.update_similarity_score(
                        request.student_id, request.exam_id,
                        risk_score, matched_students
                    )
        
        report_path = os.path.join(
            config.DATA_DIR,
            "reports",
            f"{request.student_id}_{request.exam_id}_report.json"
        )
        exam_monitor.save_session_report(request.student_id, report_path)
        
        risk_report = None
        if config.ENABLE_RISK_SCORING:
            report = risk_scorer.get_report(request.student_id, request.exam_id)
            if report:
                risk_report = report.to_dict()
        
        if config.ENABLE_AUDIO_MONITORING:
            audio_monitor.unregister_student(request.student_id)
        
        if config.ENABLE_REMOTE_MONITOR:
            remote_monitor.unregister_student(request.student_id)
        
        return {
            "success": True,
            "message": "考试已提交",
            "end_time": session.end_time if session else datetime.now().isoformat(),
            "similarity_analysis": similarity_result,
            "risk_report": risk_report,
            "report_path": report_path
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exam/questions")
async def get_questions(
    count: int = 10,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None
):
    try:
        questions = question_bank.select_random_questions(
            count=count,
            subject=subject,
            difficulty=difficulty,
            shuffle_options=True,
            shuffle_questions=True
        )
        
        return {
            "success": True,
            "count": len(questions),
            "questions": [q.to_dict() for q in questions]
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/stats")
async def get_monitor_stats():
    try:
        stats = exam_monitor.get_all_stats()
        webrtc_stats = webrtc_manager.get_all_stats()
        
        audio_stats = None
        if config.ENABLE_AUDIO_MONITORING:
            audio_stats = audio_monitor.get_all_stats()
        
        remote_stats = None
        if config.ENABLE_REMOTE_MONITOR:
            remote_stats = remote_monitor.get_monitor_stats()
        
        risk_stats = None
        if config.ENABLE_RISK_SCORING:
            risk_stats = risk_scorer.get_risk_summary()
        
        return {
            "success": True,
            "exam_monitor": stats,
            "webrtc": webrtc_stats,
            "audio_monitor": audio_stats,
            "remote_monitor": remote_stats,
            "risk_scoring": risk_stats,
            "connected_students": await websocket_manager.get_connected_students()
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/student/{student_id}")
async def get_student_stats(student_id: str):
    try:
        stats = exam_monitor.get_student_stats(student_id)
        if not stats:
            raise HTTPException(status_code=404, detail="未找到该学生的会话")
        
        webrtc_stats = webrtc_manager.get_peer_stats(student_id)
        
        return {
            "success": True,
            "student_id": student_id,
            "stats": stats,
            "webrtc": webrtc_stats
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/alerts")
async def get_alerts(
    student_id: Optional[str] = None,
    level: Optional[str] = None
):
    try:
        alerts = exam_monitor.get_alerts(student_id=student_id, level=level)
        
        return {
            "success": True,
            "count": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/alert/acknowledge")
async def acknowledge_alert(alert_id: str, student_id: str):
    try:
        success = exam_monitor.acknowledge_alert(alert_id, student_id)
        
        return {
            "success": success,
            "message": "告警已确认" if success else "告警不存在"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/exam/pause")
async def pause_exam(student_id: str, reason: str = "人工暂停"):
    try:
        success = exam_monitor.pause_exam(student_id, reason)
        
        return {
            "success": success,
            "message": "考试已暂停" if success else "暂停失败：会话不存在或已暂停"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/exam/resume")
async def resume_exam(student_id: str, reason: str = "管理员恢复"):
    try:
        success = exam_monitor.resume_exam(student_id, reason)
        
        return {
            "success": success,
            "message": "考试已恢复" if success else "恢复失败：会话不存在或未暂停"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/exam/status/{student_id}")
async def get_exam_status(student_id: str):
    try:
        session = exam_monitor.get_session(student_id)
        if not session:
            raise HTTPException(status_code=404, detail="未找到该学生的会话")
        
        return {
            "success": True,
            "student_id": student_id,
            "is_active": session.is_active,
            "is_paused": session.is_paused,
            "paused_at": session.paused_at,
            "paused_reason": session.paused_reason,
            "pause_count": session.pause_count,
            "total_paused_seconds": session.total_paused_seconds
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/similarity/analyze")
async def analyze_similarity(text1: str, text2: str):
    try:
        similarity = similarity_analyzer.calculate_similarity(text1, text2)
        
        return {
            "success": True,
            "similarity": similarity,
            "threshold": config.SIMILARITY_THRESHOLD,
            "is_suspicious": similarity >= config.SIMILARITY_THRESHOLD
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webrtc/offer")
async def webrtc_offer(request: OfferRequest):
    try:
        answer = await webrtc_manager.handle_offer(request.student_id, request.offer)
        
        if 'error' in answer:
            raise HTTPException(status_code=500, detail=answer['error'])
        
        return {
            "success": True,
            "answer": answer
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webrtc/ice")
async def webrtc_ice(request: IceCandidateRequest):
    try:
        success = await webrtc_manager.add_ice_candidate(request.student_id, request.candidate)
        
        return {
            "success": success
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/webrtc/peer/{student_id}")
async def remove_webrtc_peer(student_id: str):
    try:
        success = await webrtc_manager.remove_peer(student_id)
        
        return {
            "success": success,
            "message": "连接已关闭" if success else "连接不存在"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/chunk")
async def process_audio_chunk(request: AudioChunkRequest):
    try:
        if not config.ENABLE_AUDIO_MONITORING:
            return {"success": True, "message": "语音监测未启用"}
        
        audio_array = np.array(request.audio_data, dtype=np.float32)
        
        analysis = audio_monitor.process_audio_chunk(
            request.student_id, audio_array, request.exam_id
        )
        
        if config.ENABLE_RISK_SCORING:
            stats = audio_monitor.get_student_audio_stats(request.student_id)
            if stats:
                risk_scorer.update_audio_score(
                    request.student_id, request.exam_id,
                    analysis.is_speech,
                    analysis.has_suspicious_sound,
                    stats['speech_detected_count'],
                    stats['suspicious_count']
                )
                report = risk_scorer.get_report(request.student_id, request.exam_id)
                if report and config.ENABLE_REMOTE_MONITOR:
                    remote_monitor.update_student_status(
                        request.student_id,
                        audio_alert=analysis.alert_level in ['high', 'critical'],
                        risk_level=report.level.value
                    )
        
        if analysis.alert_level in ['high', 'critical'] and config.ENABLE_REMOTE_MONITOR:
            remote_monitor.add_alert(
                request.student_id,
                'audio_alert',
                analysis.alert_level,
                f"语音异常: {analysis.suspicious_type or '说话声'}"
            )
        
        return {
            "success": True,
            "analysis": analysis.to_dict()
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/register/{student_id}")
async def register_audio_student(student_id: str, exam_id: str = "default_exam"):
    try:
        success = audio_monitor.register_student(student_id, exam_id)
        
        return {
            "success": success,
            "message": "学生已注册语音监测" if success else "学生已注册"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/unregister/{student_id}")
async def unregister_audio_student(student_id: str):
    try:
        success = audio_monitor.unregister_student(student_id)
        
        return {
            "success": success,
            "message": "学生已注销语音监测" if success else "学生未注册"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/stats")
async def get_audio_stats():
    try:
        stats = audio_monitor.get_all_stats()
        
        return {
            "success": True,
            "stats": stats
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/student/{student_id}")
async def get_student_audio_stats(student_id: str):
    try:
        stats = audio_monitor.get_student_audio_stats(student_id)
        
        return {
            "success": True,
            "student_id": student_id,
            "stats": stats
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/thumbnails")
async def get_remote_thumbnails(view_type: str = "grid", max_items: int = 50):
    try:
        if not config.ENABLE_REMOTE_MONITOR:
            return {"success": True, "thumbnails": [], "total_count": 0}
        
        data = remote_monitor.get_all_thumbnails(view_type=view_type, max_items=max_items)
        
        return {
            "success": True,
            **data
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/thumbnail/{student_id}")
async def get_student_thumbnail(student_id: str):
    try:
        if not config.ENABLE_REMOTE_MONITOR:
            raise HTTPException(status_code=404, detail="远程监控未启用")
        
        frame = remote_monitor.get_thumbnail(student_id)
        if not frame:
            raise HTTPException(status_code=404, detail="未找到该学生的缩略图")
        
        return {
            "success": True,
            "thumbnail": frame
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/stats")
async def get_remote_stats():
    try:
        stats = remote_monitor.get_monitor_stats()
        alert_summary = remote_monitor.get_alert_summary()
        
        return {
            "success": True,
            "monitor": stats,
            "alerts": alert_summary
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/students")
async def get_remote_students():
    try:
        students = remote_monitor.get_student_list()
        
        return {
            "success": True,
            "count": len(students),
            "students": students
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/history/{student_id}")
async def get_student_frame_history(student_id: str, limit: int = 10):
    try:
        history = remote_monitor.get_frame_history(student_id, limit=limit)
        
        return {
            "success": True,
            "student_id": student_id,
            "history_count": len(history),
            "history": history
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/search")
async def search_remote_students(query: str, status: Optional[str] = None):
    try:
        results = remote_monitor.search_students(query, status_filter=status)
        
        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/report/{student_id}")
async def get_risk_report(student_id: str, exam_id: str = ""):
    try:
        if not config.ENABLE_RISK_SCORING:
            raise HTTPException(status_code=404, detail="风险评分未启用")
        
        report = risk_scorer.get_report(student_id, exam_id)
        if not report:
            raise HTTPException(status_code=404, detail="未找到该学生的风险报告")
        
        return {
            "success": True,
            "report": report.to_dict()
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/reports")
async def get_all_risk_reports(min_level: Optional[str] = None):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "reports": [], "count": 0}
        
        reports = risk_scorer.get_all_reports(min_level=min_level)
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/review")
async def get_reports_needing_review():
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "reports": [], "count": 0}
        
        reports = risk_scorer.get_reports_needing_review()
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/summary")
async def get_risk_summary():
    try:
        if not config.ENABLE_RISK_SCORING:
            return {
                "success": True,
                "summary": {
                    "total_reports": 0,
                    "by_level": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                    "needing_review": 0
                }
            }
        
        summary = risk_scorer.get_risk_summary()
        
        return {
            "success": True,
            "summary": summary
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/history/{student_id}")
async def get_risk_history(student_id: str, exam_id: str = "", limit: int = 50):
    try:
        history = risk_scorer.get_history(student_id, exam_id, limit=limit)
        
        return {
            "success": True,
            "student_id": student_id,
            "exam_id": exam_id,
            "history_count": len(history),
            "history": history
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/similarity")
async def update_similarity_risk(student_id: str, exam_id: str,
                                 similarity_risk: float, matched_students: int = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_similarity_score(
            student_id, exam_id, similarity_risk, matched_students
        )
        
        return {
            "success": True,
            "message": "相似度风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/multi_monitor")
async def update_multi_monitor_risk(student_id: str, exam_id: str,
                                    monitor_count: int, cross_screen_events: int = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_multi_monitor_score(
            student_id, exam_id, monitor_count, cross_screen_events
        )
        
        return {
            "success": True,
            "message": "多显示器风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/fullscreen")
async def update_fullscreen_risk(student_id: str, exam_id: str,
                                 fullscreen_count: int, duration: float = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_fullscreen_score(
            student_id, exam_id, fullscreen_count, duration
        )
        
        return {
            "success": True,
            "message": "全屏检测风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/question_bank/stats")
async def get_question_bank_stats():
    try:
        stats = question_bank.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/chunk")
async def process_audio_chunk(request: AudioChunkRequest):
    try:
        if not config.ENABLE_AUDIO_MONITORING:
            return {"success": True, "message": "语音监测未启用"}
        
        audio_array = np.array(request.audio_data, dtype=np.float32)
        
        analysis = audio_monitor.process_audio_chunk(
            request.student_id, audio_array, request.exam_id
        )
        
        return {
            "success": True,
            "analysis": analysis
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/register/{student_id}")
async def register_audio_student(student_id: str, exam_id: str = "default_exam"):
    try:
        success = audio_monitor.register_student(student_id, exam_id)
        
        return {
            "success": success,
            "message": "学生已注册语音监测" if success else "学生已注册"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/unregister/{student_id}")
async def unregister_audio_student(student_id: str):
    try:
        success = audio_monitor.unregister_student(student_id)
        
        return {
            "success": success,
            "message": "学生已注销语音监测" if success else "学生未注册"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/stats")
async def get_audio_stats():
    try:
        stats = audio_monitor.get_all_stats()
        
        return {
            "success": True,
            "stats": stats
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/student/{student_id}")
async def get_student_audio_stats(student_id: str):
    try:
        stats = audio_monitor.get_student_audio_stats(student_id)
        
        return {
            "success": True,
            "student_id": student_id,
            "stats": stats
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/thumbnails")
async def get_remote_thumbnails(view_type: str = "grid", max_items: int = 50):
    try:
        if not config.ENABLE_REMOTE_MONITOR:
            return {"success": True, "thumbnails": [], "total_count": 0}
        
        data = remote_monitor.get_all_thumbnails(view_type=view_type, max_items=max_items)
        
        return {
            "success": True,
            **data
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/thumbnail/{student_id}")
async def get_student_thumbnail(student_id: str):
    try:
        if not config.ENABLE_REMOTE_MONITOR:
            raise HTTPException(status_code=404, detail="远程监控未启用")
        
        frame = remote_monitor.get_thumbnail(student_id)
        if not frame:
            raise HTTPException(status_code=404, detail="未找到该学生的缩略图")
        
        return {
            "success": True,
            "thumbnail": frame
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/stats")
async def get_remote_stats():
    try:
        stats = remote_monitor.get_monitor_stats()
        alert_summary = remote_monitor.get_alert_summary()
        
        return {
            "success": True,
            "monitor": stats,
            "alerts": alert_summary
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/students")
async def get_remote_students():
    try:
        students = remote_monitor.get_student_list()
        
        return {
            "success": True,
            "count": len(students),
            "students": students
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/history/{student_id}")
async def get_student_frame_history(student_id: str, limit: int = 10):
    try:
        history = remote_monitor.get_frame_history(student_id, limit=limit)
        
        return {
            "success": True,
            "student_id": student_id,
            "history_count": len(history),
            "history": history
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/search")
async def search_remote_students(query: str, status: Optional[str] = None):
    try:
        results = remote_monitor.search_students(query, status_filter=status)
        
        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/report/{student_id}")
async def get_risk_report(student_id: str, exam_id: str = ""):
    try:
        if not config.ENABLE_RISK_SCORING:
            raise HTTPException(status_code=404, detail="风险评分未启用")
        
        report = risk_scorer.get_report(student_id, exam_id)
        if not report:
            raise HTTPException(status_code=404, detail="未找到该学生的风险报告")
        
        return {
            "success": True,
            "report": report.to_dict()
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/reports")
async def get_all_risk_reports(min_level: Optional[str] = None):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "reports": [], "count": 0}
        
        reports = risk_scorer.get_all_reports(min_level=min_level)
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/review")
async def get_reports_needing_review():
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "reports": [], "count": 0}
        
        reports = risk_scorer.get_reports_needing_review()
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/summary")
async def get_risk_summary():
    try:
        if not config.ENABLE_RISK_SCORING:
            return {
                "success": True,
                "summary": {
                    "total_reports": 0,
                    "by_level": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                    "needing_review": 0
                }
            }
        
        summary = risk_scorer.get_risk_summary()
        
        return {
            "success": True,
            "summary": summary
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/history/{student_id}")
async def get_risk_history(student_id: str, exam_id: str = "", limit: int = 50):
    try:
        history = risk_scorer.get_history(student_id, exam_id, limit=limit)
        
        return {
            "success": True,
            "student_id": student_id,
            "exam_id": exam_id,
            "history_count": len(history),
            "history": history
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/similarity")
async def update_similarity_risk(student_id: str, exam_id: str,
                                 similarity_risk: float, matched_students: int = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_similarity_score(
            student_id, exam_id, similarity_risk, matched_students
        )
        
        return {
            "success": True,
            "message": "相似度风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/multi_monitor")
async def update_multi_monitor_risk(student_id: str, exam_id: str,
                                    monitor_count: int, cross_screen_events: int = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_multi_monitor_score(
            student_id, exam_id, monitor_count, cross_screen_events
        )
        
        return {
            "success": True,
            "message": "多显示器风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/update/fullscreen")
async def update_fullscreen_risk(student_id: str, exam_id: str,
                                 fullscreen_count: int, duration: float = 0):
    try:
        if not config.ENABLE_RISK_SCORING:
            return {"success": True, "message": "风险评分未启用"}
        
        risk_scorer.update_fullscreen_score(
            student_id, exam_id, fullscreen_count, duration
        )
        
        return {
            "success": True,
            "message": "全屏检测风险已更新"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{student_id}")
async def websocket_route(websocket: WebSocket, student_id: str, role: str = "student"):
    await websocket_endpoint(websocket, student_id, websocket_manager, role)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )
