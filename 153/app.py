from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import gc
import re
import jieba
import uuid
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mental-health-app-secret-key-2024-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mental_health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['SOCKETIO_ASYNC_MODE'] = 'eventlet'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

active_rooms = {}
room_lock = Lock()

CRISIS_KEYWORDS = {
    '紧急': ['自杀', '想死', '不想活', '结束生命', '活不下去', '跳楼', '割腕', '自杀计划', '告别', '遗书'],
    '警告': ['抑郁', '绝望', '无助', '痛苦', '崩溃', '想死', '焦虑', '失眠', '暴食', '厌食', '自残', '自伤'],
    '关注': ['压力大', '不开心', '难过', '悲伤', '郁闷', '孤独', '寂寞', '迷茫', '困惑', '自卑']
}

SENSITIVE_PATTERNS = [
    (r'1[3-9]\d{9}', '[电话]'),
    (r'\d{17}[\dXx]', '[身份证]'),
    (r'\d{11,12}', '[学号]'),
    (r'[\u4e00-\u9fa5]{2,4}(?:同学|老师|医生)', '[姓名]'),
    (r'\d{4}-\d{2}-\d{2}', '[日期]'),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]'),
    (r'(?:微信号|微信|QQ|q号)[:：]\s*[a-zA-Z0-9_-]+', '[社交账号]'),
    (r'(?:地址|住址|学校|学院|专业)[:：][^\n,，。；;]+', '[地址]'),
]


def desensitize_text(text):
    if not text:
        return text
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def analyze_crisis_level(content):
    words = jieba.lcut(content)
    word_set = set(words)
    
    for level, keywords in CRISIS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content:
                return level, keyword
    
    word_count = len([w for w in words if len(w.strip()) > 0])
    negative_words = ['不', '没', '无', '难', '累', '苦', '痛', '哭']
    negative_count = sum(1 for w in words if w in negative_words)
    
    if word_count > 50 and negative_count / word_count > 0.1:
        return '关注', '情绪表达较多'
    
    return '正常', None


def get_encryption_key():
    password = app.config['SECRET_KEY'].encode()
    salt = b'mental_health_app_salt_2024'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_content(content):
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(content.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt_content(encrypted_content):
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(encrypted_content.encode('utf-8'))
        decrypted = f.decrypt(encrypted)
        return decrypted.decode('utf-8')
    except Exception:
        return '[内容无法解密]'


class Counselor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(200))
    avatar = db.Column(db.String(200), default='default_avatar.png')
    available_times = db.Column(db.String(500))
    online = db.Column(db.Boolean, default=False)
    appointments = db.relationship('Appointment', backref='counselor', lazy='dynamic')


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    counselor_id = db.Column(db.Integer, db.ForeignKey('counselor.id'), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    reason_desensitized = db.Column(db.Text)
    consultation_notes = db.Column(db.Text)
    notes_desensitized = db.Column(db.Text)
    status = db.Column(db.String(20), default='待确认')
    video_room_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    version = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        db.Index('idx_counselor_date', 'counselor_id', 'appointment_date'),
    )


class SCL90Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answers = db.Column(db.Text, nullable=False)
    scores = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Confession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_encrypted = db.Column(db.Text, nullable=False)
    crisis_level = db.Column(db.String(20), default='正常')
    crisis_keyword = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    replies = db.relationship('Reply', backref='confession', lazy='dynamic')

    @property
    def content(self):
        return decrypt_content(self.content_encrypted)

    @content.setter
    def content(self, value):
        self.content_encrypted = encrypt_content(value)


class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    confession_id = db.Column(db.Integer, db.ForeignKey('confession.id'), nullable=False)
    content_encrypted = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def content(self):
        return decrypt_content(self.content_encrypted)

    @content.setter
    def content(self, value):
        self.content_encrypted = encrypt_content(value)


class VideoSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(100), unique=True, nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    counselor_id = db.Column(db.Integer, db.ForeignKey('counselor.id'))
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='待开始')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/counselors')
def counselors():
    counselor_list = Counselor.query.all()
    return render_template('counselors.html', counselors=counselor_list)


@app.route('/book/<int:counselor_id>', methods=['GET', 'POST'])
def book_appointment(counselor_id):
    counselor = Counselor.query.get_or_404(counselor_id)
    
    if request.method == 'POST':
        appointment_date_str = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        
        try:
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            
            with db.session.begin_nested():
                existing = Appointment.query.filter(
                    Appointment.counselor_id == counselor_id,
                    Appointment.appointment_date == appointment_date,
                    Appointment.appointment_time == appointment_time,
                    Appointment.status.in_(['待确认', '已确认'])
                ).with_for_update().first()
                
                if existing:
                    flash('该时段已被预约，请选择其他时间！', 'danger')
                    return render_template('book.html', counselor=counselor)
                
                reason = request.form['reason']
                reason_desensitized = desensitize_text(reason)
                room_id = str(uuid.uuid4())[:8]
                
                appointment = Appointment(
                    student_name=request.form['student_name'],
                    student_id=request.form['student_id'],
                    phone=request.form['phone'],
                    counselor_id=counselor_id,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    reason=reason,
                    reason_desensitized=reason_desensitized,
                    video_room_id=room_id,
                    version=0
                )
                db.session.add(appointment)
            
            db.session.commit()
            flash('预约成功！请等待确认。视频房间号：' + room_id, 'success')
            return redirect(url_for('appointments'))
            
        except Exception as e:
            db.session.rollback()
            flash('预约失败，请重试！', 'danger')
            app.logger.error(f"Booking error: {str(e)}")
    
    return render_template('book.html', counselor=counselor)


@app.route('/appointments')
def appointments():
    appointment_list = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return render_template('appointments.html', appointments=appointment_list)


@app.route('/video/<room_id>')
def video_room(room_id):
    appointment = Appointment.query.filter_by(video_room_id=room_id).first()
    if not appointment:
        flash('无效的视频房间！', 'danger')
        return redirect(url_for('appointments'))
    return render_template('video.html', room_id=room_id, appointment=appointment)


def calculate_scl90_scores(answers):
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


@app.route('/scl90', methods=['GET', 'POST'])
def scl90():
    if request.method == 'POST':
        answers = []
        for i in range(1, 91):
            answer = request.form.get(f'q{i}', '1')
            answers.append(answer)
        
        scores = calculate_scl90_scores(answers)
        max_score = max(scores.values())
        
        test = SCL90Test(
            answers=','.join(answers),
            scores=str(scores)
        )
        db.session.add(test)
        db.session.commit()
        
        db.session.expunge(test)
        del test
        del answers
        gc.collect()
        
        return render_template('scl90_result.html', scores=scores, max_score=max_score)
    
    return render_template('scl90.html')


@app.route('/confessions', methods=['GET', 'POST'])
def confessions():
    if request.method == 'POST':
        content = request.form['content']
        crisis_level, crisis_keyword = analyze_crisis_level(content)
        
        confession = Confession()
        confession.content = content
        confession.crisis_level = crisis_level
        confession.crisis_keyword = crisis_keyword
        
        db.session.add(confession)
        db.session.commit()
        
        if crisis_level in ['警告', '紧急']:
            flash(f'⚠️ AI预警检测到【{crisis_level}】风险！建议及时寻求专业帮助。', 'warning')
        else:
            flash('倾诉已发布！', 'success')
        return redirect(url_for('confessions'))
    
    confession_list = Confession.query.order_by(Confession.created_at.desc()).all()
    return render_template('confessions.html', confessions=confession_list, CRISIS_KEYWORDS=CRISIS_KEYWORDS)


@app.route('/reply/<int:confession_id>', methods=['POST'])
def reply_confession(confession_id):
    content = request.form['content']
    reply = Reply()
    reply.confession_id = confession_id
    reply.content = content
    db.session.add(reply)
    db.session.commit()
    flash('回复已发布！', 'success')
    return redirect(url_for('confessions'))


@app.route('/appointment/<int:appointment_id>/status/<status>')
def update_status(appointment_id, status):
    try:
        with db.session.begin_nested():
            appointment = Appointment.query.filter(
                Appointment.id == appointment_id
            ).with_for_update().first()
            
            if appointment:
                appointment.status = status
                appointment.version += 1
        
        db.session.commit()
        flash('状态已更新！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('状态更新失败，请重试！', 'danger')
        app.logger.error(f"Status update error: {str(e)}")
    
    return redirect(url_for('appointments'))


@app.route('/api/appointments')
def api_appointments():
    appointment_list = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    return jsonify([{
        'id': a.id,
        'counselor': a.counselor.name,
        'date': str(a.appointment_date),
        'time': a.appointment_time,
        'status': a.status,
        'room_id': a.video_room_id
    } for a in appointment_list])


@app.route('/api/counselors')
def api_counselors():
    counselor_list = Counselor.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'title': c.title,
        'specialty': c.specialty,
        'online': c.online,
        'available_times': c.available_times
    } for c in counselor_list])


@app.route('/api/confessions', methods=['GET', 'POST'])
def api_confessions():
    if request.method == 'POST':
        data = request.get_json()
        content = data.get('content', '')
        crisis_level, crisis_keyword = analyze_crisis_level(content)
        
        confession = Confession()
        confession.content = content
        confession.crisis_level = crisis_level
        confession.crisis_keyword = crisis_keyword
        
        db.session.add(confession)
        db.session.commit()
        
        return jsonify({'success': True, 'crisis_level': crisis_level})
    
    confession_list = Confession.query.order_by(Confession.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': c.id,
        'content': c.content,
        'crisis_level': c.crisis_level,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
    } for c in confession_list])


@socketio.on('join')
def on_join(data):
    room_id = data['room']
    user_type = data.get('user_type', 'user')
    join_room(room_id)
    
    with room_lock:
        if room_id not in active_rooms:
            active_rooms[room_id] = {'users': [], 'started': False}
        active_rooms[room_id]['users'].append(request.sid)
    
    emit('user_joined', {
        'sid': request.sid,
        'user_type': user_type,
        'user_count': len(active_rooms[room_id]['users'])
    }, room=room_id)


@socketio.on('leave')
def on_leave(data):
    room_id = data['room']
    leave_room(room_id)
    
    with room_lock:
        if room_id in active_rooms and request.sid in active_rooms[room_id]['users']:
            active_rooms[room_id]['users'].remove(request.sid)
    
    emit('user_left', {'sid': request.sid}, room=room_id)


@socketio.on('offer')
def on_offer(data):
    emit('offer', {'offer': data['offer'], 'from': request.sid}, room=data['room'], include_self=False)


@socketio.on('answer')
def on_answer(data):
    emit('answer', {'answer': data['answer'], 'from': request.sid}, room=data['room'], include_self=False)


@socketio.on('ice_candidate')
def on_ice_candidate(data):
    emit('ice_candidate', {'candidate': data['candidate'], 'from': request.sid}, room=data['room'], include_self=False)


@socketio.on('chat_message')
def on_chat_message(data):
    emit('chat_message', {
        'message': data['message'],
        'from': request.sid,
        'time': datetime.now().strftime('%H:%M')
    }, room=data['room'])


def init_data():
    if Counselor.query.count() == 0:
        counselors = [
            Counselor(name='张医生', title='心理咨询师', specialty='青少年心理、情绪管理', available_times='周一、周三 9:00-17:00'),
            Counselor(name='李医生', title='高级心理咨询师', specialty='人际关系、学业压力', available_times='周二、周四 10:00-18:00'),
            Counselor(name='王医生', title='心理治疗师', specialty='焦虑抑郁、职业规划', available_times='周五、周六 9:00-16:00'),
            Counselor(name='赵医生', title='心理咨询师', specialty='家庭关系、自我成长', available_times='周一至周五 14:00-20:00')
        ]
        db.session.add_all(counselors)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_data()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
