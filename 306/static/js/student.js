class StudentExam {
    constructor() {
        this.studentId = '';
        this.studentName = '';
        this.examId = '';
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.answers = {};
        this.examStarted = false;
        this.examEnded = false;
        this.examDuration = 3600;
        this.timeRemaining = this.examDuration;
        this.timerInterval = null;
        this.faceVerifyInterval = null;
        this.alertCount = 0;
        this.tabSwitchCount = 0;
        
        this.webRTC = new WebRTCManager();
        this.ws = null;
        
        this.initElements();
        this.initEventListeners();
    }

    initElements() {
        this.videoElement = document.getElementById('localVideo');
        this.loginSection = document.getElementById('loginSection');
        this.faceRegisterSection = document.getElementById('faceRegisterSection');
        this.examSection = document.getElementById('examSection');
        this.resultSection = document.getElementById('resultSection');
        
        this.btnLogin = document.getElementById('btnLogin');
        this.btnRegisterFace = document.getElementById('btnRegisterFace');
        this.btnStartExam = document.getElementById('btnStartExam');
        this.btnPrev = document.getElementById('btnPrev');
        this.btnNext = document.getElementById('btnNext');
        this.btnSubmit = document.getElementById('btnSubmit');
        
        this.registerResult = document.getElementById('registerResult');
        this.faceStatus = document.getElementById('faceStatus');
        this.recStatus = document.getElementById('recStatus');
        this.examTimer = document.getElementById('examTimer');
        this.alertContainer = document.getElementById('alertContainer');
        
        this.questionNumber = document.getElementById('questionNumber');
        this.questionType = document.getElementById('questionType');
        this.questionContent = document.getElementById('questionContent');
        this.questionOptions = document.getElementById('questionOptions');
        this.questionNav = document.getElementById('questionNav');
        
        this.statFace = document.getElementById('statFace');
        this.statSimilarity = document.getElementById('statSimilarity');
        this.statTabSwitch = document.getElementById('statTabSwitch');
        this.statAlerts = document.getElementById('statAlerts');
    }

    initEventListeners() {
        this.btnLogin.addEventListener('click', () => this.handleLogin());
        this.btnRegisterFace.addEventListener('click', () => this.registerFace());
        this.btnStartExam.addEventListener('click', () => this.startExam());
        this.btnPrev.addEventListener('click', () => this.prevQuestion());
        this.btnNext.addEventListener('click', () => this.nextQuestion());
        this.btnSubmit.addEventListener('click', () => this.submitExam());
        
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        window.addEventListener('blur', () => this.handleTabBlur());
        window.addEventListener('focus', () => this.handleTabFocus());
        
        window.addEventListener('beforeunload', (e) => {
            if (this.examStarted && !this.examEnded) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    async handleLogin() {
        this.studentId = document.getElementById('studentId').value.trim();
        this.studentName = document.getElementById('studentName').value.trim();
        
        if (!this.studentId || !this.studentName) {
            this.showAlert('请输入学号和姓名', 'warning');
            return;
        }
        
        try {
            await this.webRTC.startLocalVideo(this.videoElement);
            
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/${this.studentId}`;
            this.ws = new WebSocketClient(wsUrl);
            
            this.ws.onMessage = (data) => this.handleWebSocketMessage(data);
            this.ws.onOpen = () => {
                console.log('WebSocket connected for student:', this.studentId);
            };
            
            await this.ws.connect();
            
            this.loginSection.classList.add('hidden');
            this.faceRegisterSection.classList.remove('hidden');
            
        } catch (error) {
            console.error('Login error:', error);
            this.showAlert('无法访问摄像头，请检查权限设置', 'danger');
        }
    }

    async registerFace() {
        this.btnRegisterFace.disabled = true;
        this.registerResult.className = 'result-message';
        this.registerResult.textContent = '正在注册人脸...';
        
        try {
            const frameData = this.webRTC.captureFrame(this.videoElement);
            
            const response = await fetch('/api/face/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    name: this.studentName,
                    image: frameData
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.registerResult.className = 'result-message success';
                this.registerResult.textContent = '人脸注册成功！相似度: ' + (result.similarity * 100).toFixed(1) + '%';
                this.btnStartExam.classList.remove('hidden');
                this.faceStatus.textContent = '人脸识别: 已验证';
                this.faceStatus.className = 'status-badge status-success';
            } else {
                this.registerResult.className = 'result-message error';
                this.registerResult.textContent = '人脸注册失败: ' + (result.message || '请重试');
            }
            
        } catch (error) {
            console.error('Face registration error:', error);
            this.registerResult.className = 'result-message error';
            this.registerResult.textContent = '注册失败，请重试';
        }
        
        this.btnRegisterFace.disabled = false;
    }

    async startExam() {
        try {
            const response = await fetch('/api/exam/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    name: this.studentName
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.examId = result.exam_id;
                this.questions = result.questions;
                this.examDuration = result.duration || 3600;
                this.timeRemaining = this.examDuration;
                
                this.faceRegisterSection.classList.add('hidden');
                this.examSection.classList.remove('hidden');
                this.examStarted = true;
                
                this.recStatus.textContent = '录屏: 录制中';
                this.recStatus.className = 'status-badge status-success';
                
                this.renderQuestionNav();
                this.renderCurrentQuestion();
                this.startTimer();
                this.startFaceVerification();
                this.initWebRTC();
                
                this.showAlert('考试开始，请认真作答', 'info');
                
            } else {
                this.showAlert('开始考试失败: ' + (result.message || ''), 'danger');
            }
            
        } catch (error) {
            console.error('Start exam error:', error);
            this.showAlert('开始考试失败，请刷新页面重试', 'danger');
        }
    }

    async initWebRTC() {
        try {
            await this.webRTC.createPeerConnection(
                (candidate) => {
                    this.ws.send('ice_candidate', { candidate });
                },
                (stream) => {
                    console.log('Received remote stream');
                }
            );
            
            const offer = await this.webRTC.createOffer();
            const response = await fetch('/api/webrtc/offer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    offer: offer
                })
            });
            
            const result = await response.json();
            if (result.answer) {
                await this.webRTC.handleAnswer(result.answer);
            }
            
        } catch (error) {
            console.error('WebRTC init error:', error);
        }
    }

    startTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();
            
            if (this.timeRemaining <= 0) {
                this.submitExam();
            }
        }, 1000);
    }

    updateTimerDisplay() {
        const hours = Math.floor(this.timeRemaining / 3600);
        const minutes = Math.floor((this.timeRemaining % 3600) / 60);
        const seconds = this.timeRemaining % 60;
        this.examTimer.textContent = `剩余时间: ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        if (this.timeRemaining <= 300) {
            this.examTimer.style.color = '#dc3545';
        }
    }

    startFaceVerification() {
        this.faceVerifyInterval = setInterval(() => {
            this.verifyFace();
        }, 10000);
    }

    async verifyFace() {
        try {
            const frameData = this.webRTC.captureFrame(this.videoElement);
            
            const response = await fetch('/api/face/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    image: frameData
                })
            });
            
            const result = await response.json();
            
            if (result.face_detected) {
                this.statFace.textContent = '已检测';
                this.statFace.style.color = '#28a745';
            } else {
                this.statFace.textContent = '未检测';
                this.statFace.style.color = '#dc3545';
            }
            
            this.statSimilarity.textContent = (result.similarity * 100).toFixed(1) + '%';
            
            if (result.similarity < 0.6 && result.face_detected) {
                this.statSimilarity.style.color = '#dc3545';
                this.showAlert('人脸验证失败，请确保您本人在场', 'danger');
            } else if (result.similarity >= 0.6) {
                this.statSimilarity.style.color = '#28a745';
            }
            
        } catch (error) {
            console.error('Face verification error:', error);
        }
    }

    renderQuestionNav() {
        this.questionNav.innerHTML = '';
        
        for (let i = 0; i < this.questions.length; i++) {
            const item = document.createElement('div');
            item.className = 'nav-item';
            if (i === this.currentQuestionIndex) {
                item.classList.add('current');
            }
            if (this.answers[this.questions[i].id]) {
                item.classList.add('answered');
            }
            item.textContent = i + 1;
            item.addEventListener('click', () => {
                this.currentQuestionIndex = i;
                this.renderCurrentQuestion();
                this.renderQuestionNav();
            });
            this.questionNav.appendChild(item);
        }
        
        if (Object.keys(this.answers).length === this.questions.length) {
            this.btnSubmit.classList.remove('hidden');
        }
    }

    renderCurrentQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        
        this.questionNumber.textContent = `第 ${this.currentQuestionIndex + 1} 题 / 共 ${this.questions.length} 题`;
        
        const typeMap = {
            'single': '单选题',
            'multiple': '多选题',
            'true_false': '判断题',
            'text': '简答题'
        };
        this.questionType.textContent = typeMap[question.type] || question.type;
        
        this.questionContent.textContent = question.content;
        
        this.questionOptions.innerHTML = '';
        
        if (question.type === 'single') {
            question.options.forEach((option, idx) => {
                const label = String.fromCharCode(65 + idx);
                const item = document.createElement('label');
                item.className = 'option-item';
                
                if (this.answers[question.id] === option) {
                    item.classList.add('selected');
                }
                
                item.innerHTML = `
                    <input type="radio" name="question" value="${option}" 
                        ${this.answers[question.id] === option ? 'checked' : ''}>
                    <span>${label}. ${option}</span>
                `;
                
                item.addEventListener('click', () => {
                    this.answers[question.id] = option;
                    this.renderCurrentQuestion();
                    this.renderQuestionNav();
                });
                
                this.questionOptions.appendChild(item);
            });
        } else if (question.type === 'multiple') {
            question.options.forEach((option, idx) => {
                const label = String.fromCharCode(65 + idx);
                const currentAnswers = this.answers[question.id] || [];
                const item = document.createElement('label');
                item.className = 'option-item';
                
                if (currentAnswers.includes(option)) {
                    item.classList.add('selected');
                }
                
                item.innerHTML = `
                    <input type="checkbox" value="${option}" 
                        ${currentAnswers.includes(option) ? 'checked' : ''}>
                    <span>${label}. ${option}</span>
                `;
                
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const current = this.answers[question.id] || [];
                    const index = current.indexOf(option);
                    if (index > -1) {
                        current.splice(index, 1);
                    } else {
                        current.push(option);
                    }
                    this.answers[question.id] = current;
                    this.renderCurrentQuestion();
                    this.renderQuestionNav();
                });
                
                this.questionOptions.appendChild(item);
            });
        } else if (question.type === 'true_false') {
            ['正确', '错误'].forEach((option) => {
                const item = document.createElement('label');
                item.className = 'option-item';
                
                if (this.answers[question.id] === option) {
                    item.classList.add('selected');
                }
                
                item.innerHTML = `
                    <input type="radio" name="question" value="${option}" 
                        ${this.answers[question.id] === option ? 'checked' : ''}>
                    <span>${option}</span>
                `;
                
                item.addEventListener('click', () => {
                    this.answers[question.id] = option;
                    this.renderCurrentQuestion();
                    this.renderQuestionNav();
                });
                
                this.questionOptions.appendChild(item);
            });
        } else if (question.type === 'text') {
            const textarea = document.createElement('textarea');
            textarea.style.width = '100%';
            textarea.style.minHeight = '150px';
            textarea.style.padding = '15px';
            textarea.style.border = '2px solid #e0e0e0';
            textarea.style.borderRadius = '8px';
            textarea.style.fontSize = '1rem';
            textarea.placeholder = '请输入您的答案...';
            textarea.value = this.answers[question.id] || '';
            
            textarea.addEventListener('input', (e) => {
                this.answers[question.id] = e.target.value;
                this.renderQuestionNav();
            });
            
            this.questionOptions.appendChild(textarea);
        }
        
        this.btnPrev.style.visibility = this.currentQuestionIndex === 0 ? 'hidden' : 'visible';
        this.btnNext.style.visibility = this.currentQuestionIndex === this.questions.length - 1 ? 'hidden' : 'visible';
    }

    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.renderCurrentQuestion();
            this.renderQuestionNav();
        }
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.renderCurrentQuestion();
            this.renderQuestionNav();
        }
    }

    async submitExam() {
        if (!confirm('确定要提交试卷吗？')) {
            return;
        }
        
        this.examEnded = true;
        clearInterval(this.timerInterval);
        clearInterval(this.faceVerifyInterval);
        
        try {
            const response = await fetch('/api/exam/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: this.studentId,
                    exam_id: this.examId,
                    answers: this.answers
                })
            });
            
            const result = await response.json();
            
            this.examSection.classList.add('hidden');
            this.resultSection.classList.remove('hidden');
            
            const resultDiv = document.getElementById('examResult');
            resultDiv.innerHTML = `
                <p><strong>考试ID:</strong> ${this.examId}</p>
                <p><strong>提交时间:</strong> ${new Date().toLocaleString()}</p>
                <p><strong>答题数量:</strong> ${Object.keys(this.answers).length} / ${this.questions.length}</p>
                <p><strong>告警次数:</strong> ${this.alertCount}</p>
                <p><strong>切屏次数:</strong> ${this.tabSwitchCount}</p>
                ${result.score !== undefined ? `<p><strong>得分:</strong> ${result.score} 分</p>` : ''}
            `;
            
            this.webRTC.close();
            if (this.ws) {
                this.ws.close();
            }
            
        } catch (error) {
            console.error('Submit exam error:', error);
            this.showAlert('提交失败，请重试', 'danger');
        }
    }

    handleVisibilityChange() {
        if (!this.examStarted || this.examEnded) return;
        
        const isVisible = !document.hidden;
        this.ws.send('visibility_change', { is_visible: isVisible });
        
        if (!isVisible) {
            this.tabSwitchCount++;
            this.statTabSwitch.textContent = this.tabSwitchCount;
            this.showAlert('检测到页面切换，请专注于考试', 'warning');
        }
    }

    handleTabBlur() {
        if (!this.examStarted || this.examEnded) return;
        this.ws.send('tab_blur');
    }

    handleTabFocus() {
        if (!this.examStarted || this.examEnded) return;
        this.ws.send('tab_focus');
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'alert':
                this.showAlert(data.data.message, data.data.level);
                break;
            case 'stats':
                if (data.data) {
                    this.statAlerts.textContent = data.data.alert_count || 0;
                }
                break;
            case 'face_monitor':
                if (data.data) {
                    this.statFace.textContent = data.data.face_detected ? '已检测' : '未检测';
                    this.statSimilarity.textContent = (data.data.similarity * 100).toFixed(1) + '%';
                }
                break;
        }
    }

    showAlert(message, type = 'info') {
        this.alertCount++;
        this.statAlerts.textContent = this.alertCount;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-item ${type}`;
        alertDiv.textContent = message;
        
        this.alertContainer.appendChild(alertDiv);
        
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            alertDiv.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 300);
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.examApp = new StudentExam();
});
