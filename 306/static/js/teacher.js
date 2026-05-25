class TeacherMonitor {
    constructor() {
        this.ws = null;
        this.students = {};
        this.alerts = [];
        this.currentTab = 'overview';
        
        this.initElements();
        this.initEventListeners();
        this.initWebSocket();
        this.startDataRefresh();
    }

    initElements() {
        this.statStudents = document.getElementById('statStudents');
        this.statWarnings = document.getElementById('statWarnings');
        this.statDangers = document.getElementById('statDangers');
        this.statAvgSimilarity = document.getElementById('statAvgSimilarity');
        
        this.monitorGrid = document.getElementById('monitorGrid');
        this.recentAlerts = document.getElementById('recentAlerts');
        this.activityLog = document.getElementById('activityLog');
        this.studentsList = document.getElementById('studentsList');
        this.alertsList = document.getElementById('alertsList');
        this.analysisResult = document.getElementById('analysisResult');
        this.questionsList = document.getElementById('questionsList');
        
        this.alertModal = document.getElementById('alertModal');
        this.alertModalTitle = document.getElementById('alertModalTitle');
        this.alertModalMessage = document.getElementById('alertModalMessage');
        this.btnAcknowledge = document.getElementById('btnAcknowledge');
        
        this.studentDetailModal = document.getElementById('studentDetailModal');
        this.studentDetailTitle = document.getElementById('studentDetailTitle');
        this.studentDetailContent = document.getElementById('studentDetailContent');
        this.btnCloseDetail = document.getElementById('btnCloseDetail');
        
        this.alertFilter = document.getElementById('alertFilter');
        this.btnClearAlerts = document.getElementById('btnClearAlerts');
        this.btnRunAnalysis = document.getElementById('btnRunAnalysis');
        this.examSelect = document.getElementById('examSelect');
    }

    initEventListeners() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });
        
        this.btnAcknowledge.addEventListener('click', () => this.closeAlertModal());
        this.btnCloseDetail.addEventListener('click', () => this.closeStudentDetail());
        this.alertFilter.addEventListener('change', () => this.renderAlertsList());
        this.btnClearAlerts.addEventListener('click', () => this.clearAcknowledgedAlerts());
        this.btnRunAnalysis.addEventListener('click', () => this.runSimilarityAnalysis());
        
        document.getElementById('btnAddQuestion').addEventListener('click', () => this.showAddQuestionModal());
        document.getElementById('btnImportQuestions').addEventListener('click', () => this.importQuestions());
        document.getElementById('btnGenerateExam').addEventListener('click', () => this.generateExam());
    }

    async initWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/teacher/teacher`;
        
        this.ws = new WebSocketClient(wsUrl);
        
        this.ws.onMessage = (data) => this.handleWebSocketMessage(data);
        this.ws.onOpen = () => {
            console.log('Teacher WebSocket connected');
            this.addActivityLog('已连接到监控系统');
        };
        this.ws.onClose = () => {
            this.addActivityLog('连接断开，正在重连...');
        };
        
        try {
            await this.ws.connect();
        } catch (error) {
            console.error('WebSocket connection error:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'alert':
                this.handleNewAlert(data.data);
                break;
            case 'monitor_update':
                this.handleMonitorUpdate(data);
                break;
            case 'connected':
                console.log('Connected to monitoring system');
                break;
        }
    }

    handleNewAlert(alertData) {
        this.alerts.unshift(alertData);
        if (this.alerts.length > 100) {
            this.alerts.pop();
        }
        
        this.updateStats();
        this.renderRecentAlerts();
        
        if (alertData.level === 'danger') {
            this.showAlertModal(alertData);
        }
        
        this.addActivityLog(`[${alertData.level.toUpperCase()}] ${alertData.student_id}: ${alertData.message}`);
    }

    handleMonitorUpdate(data) {
        if (data.update_type === 'student_status') {
            this.students[data.data.student_id] = data.data;
            this.updateStats();
            
            if (this.currentTab === 'overview') {
                this.renderMonitorGrid();
            } else if (this.currentTab === 'students') {
                this.renderStudentsList();
            }
        } else if (data.update_type === 'frame_update') {
            if (!this.students[data.data.student_id]) {
                this.students[data.data.student_id] = {};
            }
            this.students[data.data.student_id].frame = data.data.frame;
            
            if (this.currentTab === 'overview') {
                this.renderMonitorGrid();
            }
        }
    }

    switchTab(tab) {
        this.currentTab = tab;
        
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tab + 'Tab').classList.add('active');
        
        if (tab === 'overview') {
            this.renderMonitorGrid();
            this.renderRecentAlerts();
        } else if (tab === 'students') {
            this.renderStudentsList();
        } else if (tab === 'alerts') {
            this.renderAlertsList();
        } else if (tab === 'questions') {
            this.loadQuestions();
        }
    }

    updateStats() {
        const activeStudents = Object.values(this.students).filter(s => s.active !== false);
        const warnings = this.alerts.filter(a => a.level === 'warning' && !a.acknowledged).length;
        const dangers = this.alerts.filter(a => a.level === 'danger' && !a.acknowledged).length;
        
        this.statStudents.textContent = activeStudents.length;
        this.statWarnings.textContent = warnings;
        this.statDangers.textContent = dangers;
    }

    renderMonitorGrid() {
        this.monitorGrid.innerHTML = '';
        
        Object.entries(this.students).forEach(([studentId, data]) => {
            const item = document.createElement('div');
            item.className = 'monitor-item';
            
            const imgSrc = data.frame ? `data:image/jpeg;base64,${data.frame}` : '';
            const statusClass = this.getStatusClass(data);
            
            item.innerHTML = `
                <img src="${imgSrc}" alt="${studentId}" style="${imgSrc ? '' : 'display:none'}">
                <div class="monitor-label">
                    ${studentId}
                    <span class="student-status ${statusClass}">${this.getStatusText(data)}</span>
                </div>
            `;
            
            item.addEventListener('click', () => this.showStudentDetail(studentId));
            
            this.monitorGrid.appendChild(item);
        });
        
        if (Object.keys(this.students).length === 0) {
            this.monitorGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #999;">暂无考生在线</p>';
        }
    }

    getStatusClass(studentData) {
        if (!studentData) return 'status-normal';
        
        const dangerAlerts = studentData.stats?.danger_alerts || 0;
        const warningAlerts = studentData.stats?.warning_alerts || 0;
        
        if (dangerAlerts > 0) return 'status-risk';
        if (warningAlerts > 2) return 'status-warn';
        return 'status-normal';
    }

    getStatusText(studentData) {
        const statusClass = this.getStatusClass(studentData);
        if (statusClass === 'status-risk') return '高风险';
        if (statusClass === 'status-warn') return '需关注';
        return '正常';
    }

    renderRecentAlerts() {
        this.recentAlerts.innerHTML = '';
        
        const recentAlerts = this.alerts.slice(0, 10);
        
        if (recentAlerts.length === 0) {
            this.recentAlerts.innerHTML = '<p style="color: #999; text-align: center;">暂无告警</p>';
            return;
        }
        
        recentAlerts.forEach(alert => {
            const item = document.createElement('div');
            item.className = `alert-row ${alert.level}`;
            
            const time = new Date(alert.timestamp).toLocaleTimeString();
            item.innerHTML = `
                <strong>[${time}] ${alert.student_id}</strong><br>
                ${alert.message}
                ${alert.acknowledged ? '<span style="float: right; opacity: 0.6;">已确认</span>' : ''}
            `;
            
            this.recentAlerts.appendChild(item);
        });
    }

    renderStudentsList() {
        this.studentsList.innerHTML = '';
        
        Object.entries(this.students).forEach(([studentId, data]) => {
            const card = document.createElement('div');
            card.className = 'student-card';
            
            const statusClass = this.getStatusClass(data);
            const stats = data.stats || {};
            
            card.innerHTML = `
                <div class="student-header">
                    <div class="student-avatar">${studentId.charAt(0).toUpperCase()}</div>
                    <div class="student-info">
                        <h4>${studentId}</h4>
                        <p>${data.name || '考生'}</p>
                    </div>
                    <span class="student-status ${statusClass}">${this.getStatusText(data)}</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 15px;">
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">
                        <div style="color: #666; font-size: 0.85rem;">人脸检测</div>
                        <div style="font-weight: 600; color: ${stats.face_matches !== stats.face_checks ? '#dc3545' : '#28a745'}">
                            ${stats.face_matches || 0} / ${stats.face_checks || 0}
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">
                        <div style="color: #666; font-size: 0.85rem;">切屏次数</div>
                        <div style="font-weight: 600; color: ${stats.tab_switches > 3 ? '#dc3545' : '#333'}">
                            ${stats.tab_switches || 0}
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">
                        <div style="color: #666; font-size: 0.85rem;">警告</div>
                        <div style="font-weight: 600; color: #ffc107;">${stats.warning_alerts || 0}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">
                        <div style="color: #666; font-size: 0.85rem;">危险</div>
                        <div style="font-weight: 600; color: #dc3545;">${stats.danger_alerts || 0}</div>
                    </div>
                </div>
            `;
            
            card.addEventListener('click', () => this.showStudentDetail(studentId));
            
            this.studentsList.appendChild(card);
        });
        
        if (Object.keys(this.students).length === 0) {
            this.studentsList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #999;">暂无考生在线</p>';
        }
    }

    renderAlertsList() {
        this.alertsList.innerHTML = '';
        
        const filter = this.alertFilter.value;
        let filteredAlerts = this.alerts;
        
        if (filter !== 'all') {
            filteredAlerts = this.alerts.filter(a => a.level === filter);
        }
        
        if (filteredAlerts.length === 0) {
            this.alertsList.innerHTML = '<p style="color: #999; text-align: center; padding: 40px;">暂无告警记录</p>';
            return;
        }
        
        filteredAlerts.forEach(alert => {
            const item = document.createElement('div');
            item.className = `alert-list-item ${alert.level}`;
            if (alert.acknowledged) {
                item.style.opacity = '0.6';
            }
            
            const time = new Date(alert.timestamp).toLocaleString();
            
            item.innerHTML = `
                <div>
                    <strong>${alert.student_id}</strong> - ${alert.message}<br>
                    <span style="color: #999; font-size: 0.85rem;">${time}</span>
                </div>
                <div>
                    ${!alert.acknowledged ? 
                        `<button class="btn btn-secondary btn-sm" onclick="monitorApp.acknowledgeAlert('${alert.id}', '${alert.student_id}')">确认</button>` :
                        '<span style="color: #28a745;">已确认</span>'
                    }
                </div>
            `;
            
            this.alertsList.appendChild(item);
        });
    }

    async acknowledgeAlert(alertId, studentId) {
        try {
            const response = await fetch(`/api/alerts/${alertId}/acknowledge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: studentId })
            });
            
            const result = await response.json();
            if (result.success) {
                const alert = this.alerts.find(a => a.id === alertId);
                if (alert) {
                    alert.acknowledged = true;
                }
                this.updateStats();
                this.renderAlertsList();
                this.renderRecentAlerts();
            }
        } catch (error) {
            console.error('Acknowledge alert error:', error);
        }
    }

    async clearAcknowledgedAlerts() {
        this.alerts = this.alerts.filter(a => !a.acknowledged);
        this.renderAlertsList();
        this.renderRecentAlerts();
    }

    async showStudentDetail(studentId) {
        const student = this.students[studentId];
        if (!student) return;
        
        this.studentDetailTitle.textContent = `考生详情 - ${studentId}`;
        
        const alerts = this.alerts.filter(a => a.student_id === studentId);
        const stats = student.stats || {};
        
        this.studentDetailContent.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>实时监控</h4>
                    <div class="monitor-item" style="aspect-ratio: 4/3;">
                        <img src="${student.frame ? `data:image/jpeg;base64,${student.frame}` : ''}" 
                             alt="${studentId}" 
                             style="${student.frame ? '' : 'display:none'}">
                        <div class="monitor-label">${studentId}</div>
                    </div>
                </div>
                <div>
                    <h4>统计信息</h4>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                        <p><strong>人脸验证:</strong> ${stats.face_matches || 0} / ${stats.face_checks || 0}</p>
                        <p><strong>切屏次数:</strong> ${stats.tab_switches || 0}</p>
                        <p><strong>后台时间:</strong> ${Math.round(stats.background_time || 0)} 秒</p>
                        <p><strong>警告次数:</strong> ${stats.warning_alerts || 0}</p>
                        <p><strong>危险次数:</strong> ${stats.danger_alerts || 0}</p>
                    </div>
                </div>
            </div>
            <h4 style="margin-top: 20px;">告警记录 (${alerts.length})</h4>
            <div style="max-height: 300px; overflow-y: auto;">
                ${alerts.length === 0 ? '<p style="color: #999; text-align: center;">暂无告警</p>' :
                  alerts.map(a => `
                    <div class="alert-row ${a.level}" style="margin-bottom: 10px;">
                        <strong>${new Date(a.timestamp).toLocaleString()}</strong><br>
                        ${a.message}
                        ${a.acknowledged ? '<span style="float: right; opacity: 0.6;">已确认</span>' : ''}
                    </div>
                  `).join('')
                }
            </div>
        `;
        
        this.studentDetailModal.classList.remove('hidden');
    }

    closeStudentDetail() {
        this.studentDetailModal.classList.add('hidden');
    }

    showAlertModal(alertData) {
        this.alertModalTitle.textContent = alertData.level === 'danger' ? '⚠️ 危险告警' : '⚠️ 警告';
        this.alertModalMessage.innerHTML = `
            <strong>考生:</strong> ${alertData.student_id}<br>
            <strong>时间:</strong> ${new Date(alertData.timestamp).toLocaleString()}<br><br>
            <strong>详情:</strong><br>${alertData.message}
        `;
        this.alertModal.classList.remove('hidden');
    }

    closeAlertModal() {
        this.alertModal.classList.add('hidden');
    }

    addActivityLog(message) {
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <span class="activity-time">${new Date().toLocaleTimeString()}</span>
            <br>${message}
        `;
        
        this.activityLog.insertBefore(item, this.activityLog.firstChild);
        
        while (this.activityLog.children.length > 50) {
            this.activityLog.removeChild(this.activityLog.lastChild);
        }
    }

    async startDataRefresh() {
        setInterval(() => {
            this.refreshStudentData();
        }, 5000);
    }

    async refreshStudentData() {
        try {
            const response = await fetch('/api/monitor/stats');
            const data = await response.json();
            
            if (data.students) {
                Object.entries(data.students).forEach(([id, stats]) => {
                    if (!this.students[id]) {
                        this.students[id] = {};
                    }
                    this.students[id].stats = stats.stats;
                    this.students[id].active = stats.active;
                });
                
                this.updateStats();
                
                if (this.currentTab === 'overview') {
                    this.renderMonitorGrid();
                } else if (this.currentTab === 'students') {
                    this.renderStudentsList();
                }
            }
        } catch (error) {
            console.error('Refresh data error:', error);
        }
    }

    async runSimilarityAnalysis() {
        const examId = this.examSelect.value;
        if (!examId) {
            alert('请选择考试');
            return;
        }
        
        try {
            const response = await fetch('/api/analysis/similarity', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exam_id: examId })
            });
            
            const result = await response.json();
            this.renderAnalysisResult(result);
            
        } catch (error) {
            console.error('Similarity analysis error:', error);
            this.analysisResult.innerHTML = '<p style="color: #dc3545;">分析失败，请重试</p>';
        }
    }

    renderAnalysisResult(result) {
        if (!result || !result.success) {
            this.analysisResult.innerHTML = '<p style="color: #dc3545;">分析失败</p>';
            return;
        }
        
        const data = result.data;
        const level = data.max_similarity >= 0.85 ? 'high' : data.max_similarity >= 0.7 ? 'medium' : 'low';
        const levelText = { high: '高风险', medium: '中等风险', low: '低风险' }[level];
        
        this.analysisResult.innerHTML = `
            <h4>分析结果</h4>
            <div class="similarity-score ${level}">
                最高相似度: ${(data.max_similarity * 100).toFixed(1)}%
                <div style="font-size: 1rem; font-weight: normal; margin-top: 10px;">${levelText}</div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 20px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <p><strong>提交人数:</strong> ${data.total_submissions}</p>
                    <p><strong>分析题目数:</strong> ${data.total_questions}</p>
                    <p><strong>平均相似度:</strong> ${(data.average_similarity * 100).toFixed(1)}%</p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <p><strong>分析对数:</strong> ${data.total_pairs_analyzed}</p>
                    <p><strong>可疑对数:</strong> <span style="color: #dc3545; font-weight: bold;">${data.suspicious_pairs_count}</span></p>
                    <p><strong>相似度阈值:</strong> ${(data.threshold * 100)}%</p>
                </div>
            </div>
            
            <h4 style="margin-top: 30px;">可疑答案对</h4>
            ${data.suspicious_pairs.length === 0 ? '<p style="color: #28a745;">未发现高度相似的答案</p>' :
              `
                <div style="max-height: 400px; overflow-y: auto;">
                    ${data.suspicious_pairs.map((pair, idx) => `
                        <div style="padding: 15px; margin-bottom: 10px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong>#${idx + 1} ${pair.student1_id} ↔ ${pair.student2_id}</strong>
                                <span style="color: #dc3545; font-weight: bold;">相似度: ${(pair.similarity * 100).toFixed(1)}%</span>
                            </div>
                            <p style="margin-top: 10px; font-size: 0.9rem;">
                                <strong>题目:</strong> ${pair.question_id}<br>
                                <strong>答案1:</strong> ${pair.answer1}<br>
                                <strong>答案2:</strong> ${pair.answer2}
                            </p>
                        </div>
                    `).join('')}
                </div>
              `
            }
        `;
    }

    async loadQuestions() {
        try {
            const response = await fetch('/api/questions');
            const result = await response.json();
            
            if (result.questions) {
                this.renderQuestionsList(result.questions);
            }
            
            if (result.exams) {
                this.examSelect.innerHTML = '<option value="">选择考试</option>';
                result.exams.forEach(exam => {
                    const option = document.createElement('option');
                    option.value = exam.id;
                    option.textContent = `${exam.id} (${new Date(exam.created_at).toLocaleString()})`;
                    this.examSelect.appendChild(option);
                });
            }
            
        } catch (error) {
            console.error('Load questions error:', error);
        }
    }

    renderQuestionsList(questions) {
        this.questionsList.innerHTML = '';
        
        if (questions.length === 0) {
            this.questionsList.innerHTML = '<p style="color: #999; text-align: center; padding: 40px;">暂无题目</p>';
            return;
        }
        
        questions.forEach(q => {
            const item = document.createElement('div');
            item.className = 'question-item';
            
            const difficultyClass = { easy: 'badge-easy', medium: 'badge-medium', hard: 'badge-hard' }[q.difficulty] || 'badge-medium';
            const typeText = { single: '单选题', multiple: '多选题', true_false: '判断题', text: '简答题' }[q.type] || q.type;
            
            item.innerHTML = `
                <div class="question-item-header">
                    <span><strong>${typeText}</strong> | ${q.subject}</span>
                    <span class="question-badge ${difficultyClass}">${q.difficulty}</span>
                </div>
                <p style="margin: 10px 0;">${q.content}</p>
                ${q.options && q.options.length > 0 ? `
                    <div style="color: #666; font-size: 0.9rem;">
                        选项: ${q.options.map((opt, i) => `${String.fromCharCode(65 + i)}. ${opt}`).join(' | ')}
                    </div>
                ` : ''}
                <div style="margin-top: 10px; color: #999; font-size: 0.85rem;">
                    标签: ${q.tags.join(', ') || '无'} | ${new Date(q.created_at).toLocaleString()}
                </div>
            `;
            
            this.questionsList.appendChild(item);
        });
    }

    showAddQuestionModal() {
        const content = prompt('请输入题目内容:');
        if (!content) return;
        
        const type = prompt('请输入题目类型 (single/multiple/true_false/text):', 'single');
        const subject = prompt('请输入科目:', '');
        const difficulty = prompt('请输入难度 (easy/medium/hard):', 'medium');
        
        let options = [];
        if (type === 'single' || type === 'multiple') {
            const optionsStr = prompt('请输入选项，用英文逗号分隔:');
            if (optionsStr) {
                options = optionsStr.split(',').map(o => o.trim());
            }
        }
        
        const correctAnswer = prompt('请输入正确答案:');
        
        const question = {
            type,
            subject,
            difficulty,
            content,
            options,
            correct_answer: correctAnswer,
            tags: []
        };
        
        this.addQuestion(question);
    }

    async addQuestion(question) {
        try {
            const response = await fetch('/api/questions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(question)
            });
            
            const result = await response.json();
            if (result.success) {
                alert('题目添加成功');
                this.loadQuestions();
            } else {
                alert('添加失败: ' + (result.message || ''));
            }
        } catch (error) {
            console.error('Add question error:', error);
            alert('添加失败');
        }
    }

    async importQuestions() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            try {
                const text = await file.text();
                const questions = JSON.parse(text);
                
                const response = await fetch('/api/questions/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ questions })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert(`成功导入 ${result.count} 道题目`);
                    this.loadQuestions();
                } else {
                    alert('导入失败');
                }
            } catch (error) {
                console.error('Import error:', error);
                alert('导入失败，请检查文件格式');
            }
        };
        
        input.click();
    }

    async generateExam() {
        const subject = prompt('请输入科目 (留空为全部):', '');
        const count = parseInt(prompt('请输入题目数量:', '10')) || 10;
        const difficulty = prompt('请输入难度 (easy/medium/hard，留空为全部):', '');
        
        try {
            const response = await fetch('/api/exam/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: subject || undefined,
                    count,
                    difficulty: difficulty || undefined
                })
            });
            
            const result = await response.json();
            if (result.success) {
                alert(`试卷生成成功！考试ID: ${result.exam_id}\n共 ${result.count} 道题`);
                this.loadQuestions();
            } else {
                alert('生成失败: ' + (result.message || ''));
            }
        } catch (error) {
            console.error('Generate exam error:', error);
            alert('生成失败');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.monitorApp = new TeacherMonitor();
});
