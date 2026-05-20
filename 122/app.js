let scene, camera, renderer, canvasMesh;
let strokes = [];
let currentStroke = null;
let isDrawing = false;
let isErasing = false;
let isRotating = false;
let isZooming = false;
let previousRotationAngle = 0;
let previousPinchDistance = 0;
let currentZoom = 1;
let strokeHistory = [];
let historyIndex = -1;

const ALPHA = 0.3;
let smoothedLandmarks = null;
let smoothedLandmarks2 = null;
let lastGestureState = null;
let lastGestureChangeTime = 0;
const GESTURE_LOCK_DURATION = 200;

let threeFingerStartX = null;
let threeFingerStartY = null;
let isThreeFingerSwipe = false;

let currentDetectionConfidence = 0.7;
let currentTrackingConfidence = 0.5;
let handsInstance = null;

let recognition = null;
let isVoiceRecording = false;
let currentVoiceText = '';
let textLabels = [];

let isRecording = false;
let recordedActions = [];
let recordStartTime = 0;
let recordInterval = null;
let isPlaying = false;
let playInterval = null;

let peerConnection = null;
let dataChannel = null;
let isConnected = false;
let localUserId = 'user_' + Math.random().toString(36).substr(2, 9);
let remoteUsers = new Map();

const video = document.getElementById('video');
const videoCanvas = document.getElementById('videoCanvas');
const videoCtx = videoCanvas.getContext('2d');
const threeCanvas = document.getElementById('threeCanvas');
const statusText = document.getElementById('statusText');
const zoomLevelDisplay = document.getElementById('zoomLevel');
const recordStatusDisplay = document.getElementById('recordStatus');
const connectionStatusDisplay = document.getElementById('connectionStatus');
const colorPicker = document.getElementById('colorPicker');
const brushSize = document.getElementById('brushSize');
const zoomSlider = document.getElementById('zoomSlider');
const clearBtn = document.getElementById('clearBtn');
const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
const voiceBtn = document.getElementById('voiceBtn');
const voiceText = document.getElementById('voiceText');
const addTextBtn = document.getElementById('addTextBtn');
const recordBtn = document.getElementById('recordBtn');
const playBtn = document.getElementById('playBtn');
const saveBtn = document.getElementById('saveBtn');
const loadBtn = document.getElementById('loadBtn');
const recordTime = document.getElementById('recordTime');
const roomIdInput = document.getElementById('roomId');
const joinBtn = document.getElementById('joinBtn');
const leaveBtn = document.getElementById('leaveBtn');
const userList = document.getElementById('userList');
const textLabelsContainer = document.getElementById('textLabels');

videoCanvas.width = 320;
videoCanvas.height = 240;

function smoothLandmarks(currentLandmarks, smoothedData) {
    if (!smoothedData) {
        return JSON.parse(JSON.stringify(currentLandmarks));
    }

    const result = [];
    for (let i = 0; i < currentLandmarks.length; i++) {
        result.push({
            x: smoothedData[i].x * (1 - ALPHA) + currentLandmarks[i].x * ALPHA,
            y: smoothedData[i].y * (1 - ALPHA) + currentLandmarks[i].y * ALPHA,
            z: smoothedData[i].z * (1 - ALPHA) + currentLandmarks[i].z * ALPHA
        });
    }

    return result;
}

function resetSmoothing() {
    smoothedLandmarks = null;
    smoothedLandmarks2 = null;
}

function calculateBrightness(imageData) {
    let totalBrightness = 0;
    const data = imageData.data;
    const sampleRate = 10;

    for (let i = 0; i < data.length; i += 4 * sampleRate) {
        const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
        totalBrightness += brightness;
    }

    const pixelCount = data.length / (4 * sampleRate);
    return totalBrightness / pixelCount;
}

function updateDetectionThresholds(brightness) {
    const baseDetection = 0.7;
    const baseTracking = 0.5;
    const minDetection = 0.4;
    const minTracking = 0.3;

    const brightnessFactor = brightness / 255;

    currentDetectionConfidence = Math.max(minDetection, baseDetection * brightnessFactor + minDetection * (1 - brightnessFactor));
    currentTrackingConfidence = Math.max(minTracking, baseTracking * brightnessFactor + minTracking * (1 - brightnessFactor));
}

function canChangeGesture(newState) {
    const now = Date.now();
    if (lastGestureState !== newState && now - lastGestureChangeTime < GESTURE_LOCK_DURATION) {
        return false;
    }
    if (lastGestureState !== newState) {
        lastGestureChangeTime = now;
        lastGestureState = newState;
    }
    return true;
}

function initThreeJS() {
    const container = document.querySelector('.canvas-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a1a);

    camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ canvas: threeCanvas, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    const canvasGeometry = new THREE.PlaneGeometry(8, 6);
    const canvasMaterial = new THREE.MeshStandardMaterial({
        color: 0x1a1a2e,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.3
    });
    canvasMesh = new THREE.Mesh(canvasGeometry, canvasMaterial);
    canvasMesh.quaternion = new THREE.Quaternion();
    scene.add(canvasMesh);

    const gridHelper = new THREE.GridHelper(10, 10, 0x333333, 0x333333);
    gridHelper.rotation.x = Math.PI / 2;
    gridHelper.position.z = -0.01;
    scene.add(gridHelper);

    window.addEventListener('resize', onWindowResize);
}

function onWindowResize() {
    const container = document.querySelector('.canvas-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

function createStroke(color, size) {
    const stroke = {
        points: [],
        color: color,
        size: size,
        mesh: null,
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    };
    return stroke;
}

function updateStrokeMesh(stroke) {
    if (stroke.points.length < 2) return;

    if (stroke.mesh) {
        scene.remove(stroke.mesh);
    }

    const geometry = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];
    const color = new THREE.Color(stroke.color);

    for (let i = 0; i < stroke.points.length; i++) {
        positions.push(stroke.points[i].x, stroke.points[i].y, stroke.points[i].z);
        colors.push(color.r, color.g, color.b);
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.LineBasicMaterial({
        color: stroke.color,
        linewidth: stroke.size,
        vertexColors: true
    });

    stroke.mesh = new THREE.Line(geometry, material);
    scene.add(stroke.mesh);
}

function getCanvasPosition(x, y) {
    const rect = threeCanvas.getBoundingClientRect();
    const normalizedX = ((x - rect.left) / rect.width) * 2 - 1;
    const normalizedY = -((y - rect.top) / rect.height) * 2 + 1;

    const vector = new THREE.Vector3(normalizedX, normalizedY, 0.5);
    vector.unproject(camera);

    const dir = vector.sub(camera.position).normalize();
    const distance = -camera.position.z / dir.z;
    const pos = camera.position.clone().add(dir.multiplyScalar(distance));

    const inverseQuaternion = canvasMesh.quaternion.clone().inverse();
    pos.applyQuaternion(inverseQuaternion);

    pos.x /= currentZoom;
    pos.y /= currentZoom;

    return pos;
}

function isPointNearStroke(point, stroke, threshold = 0.2) {
    for (const p of stroke.points) {
        const dist = Math.sqrt(
            Math.pow(point.x - p.x, 2) +
            Math.pow(point.y - p.y, 2)
        );
        if (dist < threshold) return true;
    }
    return false;
}

function eraseAtPosition(position) {
    for (let i = strokes.length - 1; i >= 0; i--) {
        if (isPointNearStroke(position, strokes[i], 0.3)) {
            const removedStroke = strokes[i];
            if (removedStroke.mesh) {
                scene.remove(removedStroke.mesh);
            }
            strokes.splice(i, 1);
            recordAction({ type: 'erase', strokeId: removedStroke.id });
            sendToCollaborators({ type: 'erase', strokeId: removedStroke.id });
        }
    }
}

function calculateDistance(point1, point2) {
    return Math.sqrt(
        Math.pow(point1.x - point2.x, 2) +
        Math.pow(point1.y - point2.y, 2)
    );
}

function calculateAngle(point1, point2) {
    return Math.atan2(point2.y - point1.y, point2.x - point1.x);
}

function saveToHistory() {
    if (historyIndex < strokeHistory.length - 1) {
        strokeHistory = strokeHistory.slice(0, historyIndex + 1);
    }
    strokeHistory.push(JSON.parse(JSON.stringify(strokes.map(s => ({
        id: s.id,
        points: s.points,
        color: s.color,
        size: s.size
    })))));
    historyIndex++;
}

function undo() {
    if (historyIndex >= 0) {
        for (const stroke of strokes) {
            if (stroke.mesh) {
                scene.remove(stroke.mesh);
            }
        }
        strokes = [];
        
        historyIndex--;
        if (historyIndex >= 0) {
            const historyState = strokeHistory[historyIndex];
            for (const strokeData of historyState) {
                const stroke = createStroke(strokeData.color, strokeData.size);
                stroke.id = strokeData.id;
                stroke.points = strokeData.points;
                updateStrokeMesh(stroke);
                strokes.push(stroke);
            }
        }
        recordAction({ type: 'undo' });
        sendToCollaborators({ type: 'undo' });
    }
}

function redo() {
    if (historyIndex < strokeHistory.length - 1) {
        for (const stroke of strokes) {
            if (stroke.mesh) {
                scene.remove(stroke.mesh);
            }
        }
        strokes = [];
        
        historyIndex++;
        const historyState = strokeHistory[historyIndex];
        for (const strokeData of historyState) {
            const stroke = createStroke(strokeData.color, strokeData.size);
            stroke.id = strokeData.id;
            stroke.points = strokeData.points;
            updateStrokeMesh(stroke);
            strokes.push(stroke);
        }
        recordAction({ type: 'redo' });
        sendToCollaborators({ type: 'redo' });
    }
}

function updateZoom(zoom) {
    currentZoom = Math.max(0.5, Math.min(3, zoom));
    canvasMesh.scale.set(currentZoom, currentZoom, 1);
    zoomSlider.value = currentZoom;
    zoomLevelDisplay.textContent = `缩放: ${Math.round(currentZoom * 100)}%`;
}

function initVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'zh-CN';

        recognition.onstart = () => {
            isVoiceRecording = true;
            voiceBtn.classList.add('recording');
            voiceBtn.textContent = '停止语音';
            voiceText.textContent = '正在听...';
        };

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            currentVoiceText = transcript;
            voiceText.textContent = transcript;
            addTextBtn.disabled = !transcript;
        };

        recognition.onend = () => {
            isVoiceRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.textContent = '开始语音';
        };

        recognition.onerror = (event) => {
            console.error('语音识别错误:', event.error);
            voiceText.textContent = '识别失败，请重试';
            isVoiceRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.textContent = '开始语音';
        };
    } else {
        voiceBtn.disabled = true;
        voiceBtn.textContent = '浏览器不支持';
        voiceText.textContent = '您的浏览器不支持语音识别';
    }
}

function addTextLabel(text, x = 100, y = 100) {
    const label = {
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 9),
        text: text,
        x: x,
        y: y
    };

    const labelElement = document.createElement('div');
    labelElement.className = 'text-label';
    labelElement.textContent = text;
    labelElement.style.left = x + 'px';
    labelElement.style.top = y + 'px';
    labelElement.dataset.id = label.id;

    let isDragging = false;
    let startX, startY, initialX, initialY;

    labelElement.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        initialX = label.x;
        initialY = label.y;
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (isDragging) {
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            label.x = initialX + dx;
            label.y = initialY + dy;
            labelElement.style.left = label.x + 'px';
            labelElement.style.top = label.y + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
    });

    textLabelsContainer.appendChild(labelElement);
    textLabels.push(label);
    recordAction({ type: 'addText', label: label });
    sendToCollaborators({ type: 'addText', label: label });
}

function recordAction(action) {
    if (isRecording) {
        recordedActions.push({
            timestamp: Date.now() - recordStartTime,
            ...action
        });
    }
}

function startRecording() {
    isRecording = true;
    recordedActions = [];
    recordStartTime = Date.now();
    recordBtn.classList.add('recording');
    recordBtn.textContent = '停止录制';
    recordStatusDisplay.textContent = '录制中...';
    playBtn.disabled = true;
    saveBtn.disabled = true;

    let seconds = 0;
    recordInterval = setInterval(() => {
        seconds++;
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        recordTime.textContent = `${mins}:${secs}`;
    }, 1000);
}

function stopRecording() {
    isRecording = false;
    recordBtn.classList.remove('recording');
    recordBtn.textContent = '开始录制';
    recordStatusDisplay.textContent = '已停止';
    playBtn.disabled = recordedActions.length === 0;
    saveBtn.disabled = recordedActions.length === 0;
    if (recordInterval) {
        clearInterval(recordInterval);
        recordInterval = null;
    }
}

function playRecording() {
    if (recordedActions.length === 0) return;

    isPlaying = true;
    playBtn.textContent = '停止播放';
    recordStatusDisplay.textContent = '播放中...';
    
    for (const stroke of strokes) {
        if (stroke.mesh) {
            scene.remove(stroke.mesh);
        }
    }
    strokes = [];

    const labelElements = textLabelsContainer.querySelectorAll('.text-label');
    labelElements.forEach(el => el.remove());
    textLabels = [];

    let actionIndex = 0;
    const startTime = Date.now();

    playInterval = setInterval(() => {
        const currentTime = Date.now() - startTime;

        while (actionIndex < recordedActions.length && 
               recordedActions[actionIndex].timestamp <= currentTime) {
            const action = recordedActions[actionIndex];
            executeAction(action);
            actionIndex++;
        }

        if (actionIndex >= recordedActions.length) {
            stopPlaying();
        }
    }, 16);
}

function stopPlaying() {
    isPlaying = false;
    playBtn.textContent = '播放';
    recordStatusDisplay.textContent = '播放完成';
    if (playInterval) {
        clearInterval(playInterval);
        playInterval = null;
    }
}

function executeAction(action) {
    switch (action.type) {
        case 'draw':
            {
                let stroke = strokes.find(s => s.id === action.strokeId);
                if (!stroke) {
                    stroke = createStroke(action.color, action.size);
                    stroke.id = action.strokeId;
                    strokes.push(stroke);
                }
                stroke.points.push(action.point);
                updateStrokeMesh(stroke);
            }
            break;
        case 'erase':
            for (let i = strokes.length - 1; i >= 0; i--) {
                if (strokes[i].id === action.strokeId) {
                    if (strokes[i].mesh) {
                        scene.remove(strokes[i].mesh);
                    }
                    strokes.splice(i, 1);
                    break;
                }
            }
            break;
        case 'addText':
            {
                const label = action.label;
                const labelElement = document.createElement('div');
                labelElement.className = 'text-label';
                labelElement.textContent = label.text;
                labelElement.style.left = label.x + 'px';
                labelElement.style.top = label.y + 'px';
                labelElement.dataset.id = label.id;
                textLabelsContainer.appendChild(labelElement);
                textLabels.push(label);
            }
            break;
        case 'undo':
            undo();
            break;
        case 'redo':
            redo();
            break;
    }
}

function saveRecording() {
    const data = {
        actions: recordedActions,
        strokes: strokes.map(s => ({
            id: s.id,
            points: s.points,
            color: s.color,
            size: s.size
        })),
        labels: textLabels
    };

    localStorage.setItem('whiteboardRecording', JSON.stringify(data));
    
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'whiteboard_recording.json';
    a.click();
    URL.revokeObjectURL(url);

    alert('录制已保存！');
}

function loadRecording() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                recordedActions = data.actions || [];
                playBtn.disabled = recordedActions.length === 0;
                saveBtn.disabled = recordedActions.length === 0;
                
                for (const stroke of strokes) {
                    if (stroke.mesh) {
                        scene.remove(stroke.mesh);
                    }
                }
                strokes = [];
                
                const labelElements = textLabelsContainer.querySelectorAll('.text-label');
                labelElements.forEach(el => el.remove());
                textLabels = [];
                
                if (data.strokes) {
                    for (const strokeData of data.strokes) {
                        const stroke = createStroke(strokeData.color, strokeData.size);
                        stroke.id = strokeData.id;
                        stroke.points = strokeData.points;
                        updateStrokeMesh(stroke);
                        strokes.push(stroke);
                    }
                }
                
                if (data.labels) {
                    for (const label of data.labels) {
                        addTextLabel(label.text, label.x, label.y);
                    }
                }
                
                alert('录制已加载！');
            } catch (err) {
                alert('加载失败：无效的文件格式');
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

function initWebRTC() {
    const configuration = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' }
        ]
    };

    peerConnection = new RTCPeerConnection(configuration);

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            console.log('ICE候选:', event.candidate);
        }
    };

    peerConnection.onconnectionstatechange = () => {
        console.log('连接状态:', peerConnection.connectionState);
        if (peerConnection.connectionState === 'connected') {
            isConnected = true;
            connectionStatusDisplay.textContent = '已连接';
        } else if (peerConnection.connectionState === 'disconnected') {
            isConnected = false;
            connectionStatusDisplay.textContent = '已断开';
        }
    };

    dataChannel = peerConnection.createDataChannel('whiteboard');
    
    dataChannel.onopen = () => {
        console.log('数据通道已打开');
        isConnected = true;
        connectionStatusDisplay.textContent = '已连接';
        addUser(localUserId, '你');
    };

    dataChannel.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleCollaborationMessage(message);
    };

    dataChannel.onclose = () => {
        console.log('数据通道已关闭');
        isConnected = false;
        connectionStatusDisplay.textContent = '离线';
    };
}

function addUser(userId, name) {
    if (!remoteUsers.has(userId)) {
        remoteUsers.set(userId, name);
        updateUserList();
    }
}

function updateUserList() {
    userList.innerHTML = '';
    remoteUsers.forEach((name, id) => {
        const item = document.createElement('div');
        item.className = 'user-item';
        item.textContent = id === localUserId ? `${name} (你)` : name;
        userList.appendChild(item);
    });
}

function sendToCollaborators(message) {
    if (dataChannel && dataChannel.readyState === 'open') {
        dataChannel.send(JSON.stringify({
            userId: localUserId,
            ...message
        }));
    }
}

function handleCollaborationMessage(message) {
    console.log('收到消息:', message);
    
    switch (message.type) {
        case 'draw':
            {
                let stroke = strokes.find(s => s.id === message.strokeId);
                if (!stroke) {
                    stroke = createStroke(message.color, message.size);
                    stroke.id = message.strokeId;
                    strokes.push(stroke);
                }
                stroke.points.push(message.point);
                updateStrokeMesh(stroke);
            }
            break;
        case 'erase':
            for (let i = strokes.length - 1; i >= 0; i--) {
                if (strokes[i].id === message.strokeId) {
                    if (strokes[i].mesh) {
                        scene.remove(strokes[i].mesh);
                    }
                    strokes.splice(i, 1);
                    break;
                }
            }
            break;
        case 'addText':
            {
                const label = message.label;
                const labelElement = document.createElement('div');
                labelElement.className = 'text-label';
                labelElement.textContent = label.text;
                labelElement.style.left = label.x + 'px';
                labelElement.style.top = label.y + 'px';
                labelElement.dataset.id = label.id;
                textLabelsContainer.appendChild(labelElement);
                textLabels.push(label);
            }
            break;
        case 'userJoin':
            addUser(message.userId, message.userName || '用户');
            break;
    }
}

function joinRoom() {
    const roomId = roomIdInput.value.trim();
    if (!roomId) {
        alert('请输入房间号');
        return;
    }

    if (!peerConnection) {
        initWebRTC();
    }

    joinBtn.disabled = true;
    leaveBtn.disabled = false;
    connectionStatusDisplay.textContent = '连接中...';
    
    setTimeout(() => {
        isConnected = true;
        connectionStatusDisplay.textContent = '已连接';
        addUser(localUserId, '你');
        sendToCollaborators({ type: 'userJoin', userName: '你' });
    }, 1000);
}

function leaveRoom() {
    if (dataChannel) {
        dataChannel.close();
    }
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    
    isConnected = false;
    joinBtn.disabled = false;
    leaveBtn.disabled = true;
    connectionStatusDisplay.textContent = '离线';
    remoteUsers.clear();
    updateUserList();
}

function checkFingerExtended(landmarks, fingerIndex) {
    const tip = landmarks[fingerIndex * 4 + 4];
    const pip = landmarks[fingerIndex * 4 + 2];
    return tip.y < pip.y - 0.02;
}

function checkThreeFingersExtended(landmarks) {
    const indexExtended = checkFingerExtended(landmarks, 1);
    const middleExtended = checkFingerExtended(landmarks, 2);
    const ringExtended = checkFingerExtended(landmarks, 3);
    return indexExtended && middleExtended && ringExtended;
}

function onResults(results) {
    videoCtx.save();
    videoCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    videoCtx.drawImage(results.image, 0, 0, videoCanvas.width, videoCanvas.height);

    const imageData = videoCtx.getImageData(0, 0, videoCanvas.width, videoCanvas.height);
    const brightness = calculateBrightness(imageData);
    updateDetectionThresholds(brightness);

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        statusText.textContent = `检测到${results.multiHandLandmarks.length}只手`;

        if (results.multiHandLandmarks.length === 2) {
            smoothedLandmarks = smoothLandmarks(results.multiHandLandmarks[0], smoothedLandmarks);
            smoothedLandmarks2 = smoothLandmarks(results.multiHandLandmarks[1], smoothedLandmarks2);

            drawConnectors(videoCtx, smoothedLandmarks, HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
            drawLandmarks(videoCtx, smoothedLandmarks, { color: '#FF0000', lineWidth: 1, radius: 3 });
            drawConnectors(videoCtx, smoothedLandmarks2, HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
            drawLandmarks(videoCtx, smoothedLandmarks2, { color: '#FF0000', lineWidth: 1, radius: 3 });

            const indexTip1 = smoothedLandmarks[8];
            const indexTip2 = smoothedLandmarks2[8];
            const thumbTip1 = smoothedLandmarks[4];
            const thumbTip2 = smoothedLandmarks2[4];

            const pinchPoint1 = {
                x: (indexTip1.x + thumbTip1.x) / 2,
                y: (indexTip1.y + thumbTip1.y) / 2
            };
            const pinchPoint2 = {
                x: (indexTip2.x + thumbTip2.x) / 2,
                y: (indexTip2.y + thumbTip2.y) / 2
            };

            const currentDistance = calculateDistance(pinchPoint1, pinchPoint2);
            const currentAngle = calculateAngle(pinchPoint1, pinchPoint2);

            if (previousPinchDistance > 0 && Math.abs(currentDistance - previousPinchDistance) > 0.005) {
                isZooming = true;
                const zoomDelta = (currentDistance - previousPinchDistance) * 5;
                updateZoom(currentZoom + zoomDelta);
                statusText.textContent = '缩放中...';
            } else if (previousRotationAngle !== 0 && Math.abs(currentAngle - previousRotationAngle) > 0.02) {
                isRotating = true;
                isZooming = false;
                statusText.textContent = '旋转画布中...';
                const angleDiff = currentAngle - previousRotationAngle;
                const rotationQuaternion = new THREE.Quaternion();
                rotationQuaternion.setFromAxisAngle(new THREE.Vector3(0, 0, 1), angleDiff * 2);
                canvasMesh.quaternion.multiply(rotationQuaternion);
            }

            previousPinchDistance = currentDistance;
            previousRotationAngle = currentAngle;
        } else {
            smoothedLandmarks = smoothLandmarks(results.multiHandLandmarks[0], smoothedLandmarks);

            drawConnectors(videoCtx, smoothedLandmarks, HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
            drawLandmarks(videoCtx, smoothedLandmarks, { color: '#FF0000', lineWidth: 1, radius: 3 });

            const indexTip = smoothedLandmarks[8];
            const middleTip = smoothedLandmarks[12];
            const ringTip = smoothedLandmarks[16];

            const indexExtended = checkFingerExtended(smoothedLandmarks, 1);
            const middleExtended = checkFingerExtended(smoothedLandmarks, 2);
            const ringExtended = checkFingerExtended(smoothedLandmarks, 3);
            const pinkyExtended = checkFingerExtended(smoothedLandmarks, 4);

            const extendedFingers = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

            const rect = threeCanvas.getBoundingClientRect();
            const canvasX = (1 - indexTip.x) * rect.width + rect.left;
            const canvasY = indexTip.y * rect.height + rect.top;
            const position = getCanvasPosition(canvasX, canvasY);

            isRotating = false;
            isZooming = false;
            previousRotationAngle = 0;
            previousPinchDistance = 0;

            if (indexExtended && middleExtended && ringExtended && !pinkyExtended) {
                const threeFingerX = (indexTip.x + middleTip.x + ringTip.x) / 3;
                const threeFingerY = (indexTip.y + middleTip.y + ringTip.y) / 3;

                if (!isThreeFingerSwipe) {
                    threeFingerStartX = threeFingerX;
                    threeFingerStartY = threeFingerY;
                    isThreeFingerSwipe = true;
                } else {
                    const swipeDistance = threeFingerX - threeFingerStartX;
                    if (Math.abs(swipeDistance) > 0.1) {
                        if (swipeDistance < 0) {
                            undo();
                            statusText.textContent = '撤销!';
                        }
                        isThreeFingerSwipe = false;
                        threeFingerStartX = null;
                        threeFingerStartY = null;
                    }
                }
            } else {
                isThreeFingerSwipe = false;
                threeFingerStartX = null;
                threeFingerStartY = null;

                if (indexExtended && extendedFingers === 1) {
                    if (canChangeGesture('drawing')) {
                        isErasing = false;
                        statusText.textContent = '绘制中...';

                        if (!isDrawing) {
                            isDrawing = true;
                            currentStroke = createStroke(colorPicker.value, parseInt(brushSize.value));
                            strokes.push(currentStroke);
                            saveToHistory();
                        }

                        currentStroke.points.push(position);
                        updateStrokeMesh(currentStroke);
                        recordAction({
                            type: 'draw',
                            strokeId: currentStroke.id,
                            color: currentStroke.color,
                            size: currentStroke.size,
                            point: position
                        });
                        sendToCollaborators({
                            type: 'draw',
                            strokeId: currentStroke.id,
                            color: currentStroke.color,
                            size: currentStroke.size,
                            point: position
                        });
                    }
                } else if (extendedFingers === 0) {
                    if (canChangeGesture('erasing')) {
                        isDrawing = false;
                        isErasing = true;
                        statusText.textContent = '擦除中...';
                        eraseAtPosition(position);
                    }
                } else {
                    if (canChangeGesture('idle')) {
                        isDrawing = false;
                        isErasing = false;
                        currentStroke = null;
                        statusText.textContent = '等待手势...';
                    }
                }
            }
        }
    } else {
        resetSmoothing();
        isDrawing = false;
        isErasing = false;
        isRotating = false;
        isZooming = false;
        isThreeFingerSwipe = false;
        currentStroke = null;
        previousRotationAngle = 0;
        previousPinchDistance = 0;
        threeFingerStartX = null;
        threeFingerStartY = null;
        statusText.textContent = '未检测到手部';
    }

    videoCtx.restore();
}

async function initMediaPipe() {
    handsInstance = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/${file}`;
        }
    });

    handsInstance.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: currentDetectionConfidence,
        minTrackingConfidence: currentTrackingConfidence
    });

    handsInstance.onResults(onResults);

    const camera = new Camera(video, {
        onFrame: async () => {
            await handsInstance.send({ image: video });
        },
        width: 640,
        height: 480
    });

    camera.start();
}

function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}

undoBtn.addEventListener('click', undo);
redoBtn.addEventListener('click', redo);

voiceBtn.addEventListener('click', () => {
    if (!recognition) {
        initVoiceRecognition();
    }
    
    if (isVoiceRecording) {
        recognition.stop();
    } else {
        currentVoiceText = '';
        voiceText.textContent = '正在听...';
        addTextBtn.disabled = true;
        recognition.start();
    }
});

addTextBtn.addEventListener('click', () => {
    if (currentVoiceText) {
        const rect = threeCanvas.getBoundingClientRect();
        addTextLabel(currentVoiceText, rect.width / 2, rect.height / 2);
        currentVoiceText = '';
        voiceText.textContent = '等待语音输入...';
        addTextBtn.disabled = true;
    }
});

recordBtn.addEventListener('click', () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

playBtn.addEventListener('click', () => {
    if (isPlaying) {
        stopPlaying();
    } else {
        playRecording();
    }
});

saveBtn.addEventListener('click', saveRecording);
loadBtn.addEventListener('click', loadRecording);

joinBtn.addEventListener('click', joinRoom);
leaveBtn.addEventListener('click', leaveRoom);

zoomSlider.addEventListener('input', (e) => {
    updateZoom(parseFloat(e.target.value));
});

clearBtn.addEventListener('click', () => {
    for (const stroke of strokes) {
        if (stroke.mesh) {
            scene.remove(stroke.mesh);
        }
    }
    strokes = [];
    saveToHistory();
    recordAction({ type: 'clear' });
    sendToCollaborators({ type: 'clear' });
});

initThreeJS();
initMediaPipe();
initVoiceRecognition();
animate();
