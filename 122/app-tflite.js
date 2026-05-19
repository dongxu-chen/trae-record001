let scene, camera, renderer, canvasMesh;
let strokes = [];
let currentStroke = null;
let isDrawing = false;
let isErasing = false;
let isRotating = false;
let previousRotationAngle = 0;
let currentZoom = 1;
let strokeHistory = [];
let historyIndex = -1;

const ALPHA = 0.3;
let smoothedLandmarks = null;
let smoothedLandmarks2 = null;
let lastGestureState = null;
let lastGestureChangeTime = 0;
const GESTURE_LOCK_DURATION = 200;

let handDetector = null;
let performanceMonitor = null;
let offlineManager = null;
let useTFLite = true;
let isRunning = false;

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

videoCanvas.width = 320;
videoCanvas.height = 240;

async function initDetectionEngine() {
    console.log('初始化手势检测引擎...');
    statusText.textContent = '加载模型中...';

    performanceMonitor = new PerformanceMonitor();
    offlineManager = new OfflineModelManager();

    try {
        if (useTFLite) {
            handDetector = new TFJSHandDetector();
        } else {
            handDetector = new TFJSHandDetector();
        }
        
        await handDetector.init();
        connectionStatusDisplay.textContent = '已就绪 (本地推理)';
        console.log('检测引擎初始化完成！');
    } catch (error) {
        console.error('初始化失败:', error);
        statusText.textContent = '初始化失败，降级到MediaPipe';
        await fallbackToMediaPipe();
    }
}

async function fallbackToMediaPipe() {
    console.log('使用 MediaPipe 作为后备方案');
    
    await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js';
        script.onload = resolve;
        document.head.appendChild(script);
    });
    
    await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js';
        script.onload = resolve;
        document.head.appendChild(script);
    });
    
    await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js';
        script.onload = resolve;
        document.head.appendChild(script);
    });

    const hands = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });

    hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 0,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });

    hands.onResults(onMediaPipeResults);

    const camera = new Camera(video, {
        onFrame: async () => {
            await hands.send({ image: video });
        },
        width: 640,
        height: 480
    });

    camera.start();
    isRunning = true;
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

function smoothLandmarksData(currentLandmarks, smoothedData) {
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

function checkFingerExtended(landmarks, fingerIndex) {
    const tip = landmarks[fingerIndex * 4 + 4];
    const pip = landmarks[fingerIndex * 4 + 2];
    return tip.y < pip.y - 0.02;
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
    }
}

function updateZoom(zoom) {
    currentZoom = Math.max(0.5, Math.min(3, zoom));
    canvasMesh.scale.set(currentZoom, currentZoom, 1);
    zoomSlider.value = currentZoom;
    zoomLevelDisplay.textContent = `缩放: ${Math.round(currentZoom * 100)}%`;
}

async function processFrame() {
    if (!handDetector || !handDetector.isReady()) {
        requestAnimationFrame(processFrame);
        return;
    }

    try {
        const result = await handDetector.detectHands(video);
        
        if (result && result.multiHandLandmarks) {
            onDetectionResults(result);
            performanceMonitor.recordInferenceTime(result.inferenceTime);
        }
        
        performanceMonitor.recordFrame();
        
        if (performanceMonitor.shouldReport()) {
            performanceMonitor.printReport();
        }
    } catch (error) {
        console.error('处理帧失败:', error);
    }

    if (isRunning) {
        requestAnimationFrame(processFrame);
    }
}

function onDetectionResults(results) {
    videoCtx.save();
    videoCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    videoCtx.drawImage(video, 0, 0, videoCanvas.width, videoCanvas.height);

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        statusText.textContent = `检测到${results.multiHandLandmarks.length}只手`;

        if (results.multiHandLandmarks.length === 2) {
            smoothedLandmarks = smoothLandmarksData(results.multiHandLandmarks[0].landmarks, smoothedLandmarks);
            smoothedLandmarks2 = smoothLandmarksData(results.multiHandLandmarks[1].landmarks, smoothedLandmarks2);

            drawHandLandmarks(smoothedLandmarks);
            drawHandLandmarks(smoothedLandmarks2);

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

            const currentDistance = Math.sqrt(
                Math.pow(pinchPoint1.x - pinchPoint2.x, 2) +
                Math.pow(pinchPoint1.y - pinchPoint2.y, 2)
            );
            const currentAngle = Math.atan2(
                pinchPoint2.y - pinchPoint1.y,
                pinchPoint2.x - pinchPoint1.x
            );

            if (previousRotationAngle !== 0) {
                const angleDiff = currentAngle - previousRotationAngle;
                const rotationQuaternion = new THREE.Quaternion();
                rotationQuaternion.setFromAxisAngle(new THREE.Vector3(0, 0, 1), angleDiff * 2);
                canvasMesh.quaternion.multiply(rotationQuaternion);
            }

            previousRotationAngle = currentAngle;
        } else {
            const landmarks = smoothLandmarksData(results.multiHandLandmarks[0].landmarks, smoothedLandmarks);
            drawHandLandmarks(landmarks);

            const indexTip = landmarks[8];
            const indexExtended = checkFingerExtended(landmarks, 1);
            const middleExtended = checkFingerExtended(landmarks, 2);
            const ringExtended = checkFingerExtended(landmarks, 3);
            const pinkyExtended = checkFingerExtended(landmarks, 4);

            const extendedFingers = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

            const rect = threeCanvas.getBoundingClientRect();
            const canvasX = (1 - indexTip.x) * rect.width + rect.left;
            const canvasY = indexTip.y * rect.height + rect.top;
            const position = getCanvasPosition(canvasX, canvasY);

            previousRotationAngle = 0;

            if (indexExtended && middleExtended && ringExtended && !pinkyExtended) {
                if (canChangeGesture('undo')) {
                    undo();
                    statusText.textContent = '撤销!';
                }
            } else if (indexExtended && extendedFingers === 1) {
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
    } else {
        smoothedLandmarks = null;
        smoothedLandmarks2 = null;
        isDrawing = false;
        isErasing = false;
        isRotating = false;
        currentStroke = null;
        previousRotationAngle = 0;
        statusText.textContent = '未检测到手部';
    }

    videoCtx.restore();
}

function drawHandLandmarks(landmarks) {
    const connections = [
        [0, 1], [1, 2], [2, 3], [3, 4],
        [0, 5], [5, 6], [6, 7], [7, 8],
        [5, 9], [9, 10], [10, 11], [11, 12],
        [9, 13], [13, 14], [14, 15], [15, 16],
        [13, 17], [17, 18], [18, 19], [19, 20],
        [0, 17]
    ];

    videoCtx.strokeStyle = '#00FF00';
    videoCtx.lineWidth = 2;
    
    for (const [i, j] of connections) {
        const p1 = landmarks[i];
        const p2 = landmarks[j];
        videoCtx.beginPath();
        videoCtx.moveTo(p1.x * videoCanvas.width, p1.y * videoCanvas.height);
        videoCtx.lineTo(p2.x * videoCanvas.width, p2.y * videoCanvas.height);
        videoCtx.stroke();
    }

    videoCtx.fillStyle = '#FF0000';
    for (const landmark of landmarks) {
        videoCtx.beginPath();
        videoCtx.arc(landmark.x * videoCanvas.width, landmark.y * videoCanvas.height, 3, 0, 2 * Math.PI);
        videoCtx.fill();
    }
}

function onMediaPipeResults(results) {
    videoCtx.save();
    videoCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    videoCtx.drawImage(results.image, 0, 0, videoCanvas.width, videoCanvas.height);

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        statusText.textContent = `检测到${results.multiHandLandmarks.length}只手`;

        for (let handIndex = 0; handIndex < results.multiHandLandmarks.length; handIndex++) {
            const landmarks = results.multiHandLandmarks[handIndex];
            drawConnectors(videoCtx, landmarks, HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
            drawLandmarks(videoCtx, landmarks, { color: '#FF0000', lineWidth: 1, radius: 3 });

            if (results.multiHandLandmarks.length === 2) {
                if (handIndex === 0) {
                    smoothedLandmarks = smoothLandmarksData(landmarks, smoothedLandmarks);
                } else {
                    smoothedLandmarks2 = smoothLandmarksData(landmarks, smoothedLandmarks2);
                }
            } else {
                smoothedLandmarks = smoothLandmarksData(landmarks, smoothedLandmarks);
            }
        }

        if (results.multiHandLandmarks.length === 2) {
            const indexTip1 = smoothedLandmarks[8];
            const indexTip2 = smoothedLandmarks2[8];
            
            const point1 = { x: indexTip1.x, y: indexTip1.y };
            const point2 = { x: indexTip2.x, y: indexTip2.y };
            
            const currentAngle = Math.atan2(point2.y - point1.y, point2.x - point1.x);
            
            if (previousRotationAngle !== 0) {
                const angleDiff = currentAngle - previousRotationAngle;
                const rotationQuaternion = new THREE.Quaternion();
                rotationQuaternion.setFromAxisAngle(new THREE.Vector3(0, 0, 1), angleDiff * 2);
                canvasMesh.quaternion.multiply(rotationQuaternion);
            }
            
            previousRotationAngle = currentAngle;
        } else {
            const landmarks = smoothedLandmarks;
            const indexTip = landmarks[8];
            
            const indexExtended = landmarks[8].y < landmarks[6].y - 0.02;
            const middleExtended = landmarks[12].y < landmarks[10].y - 0.02;
            const ringExtended = landmarks[16].y < landmarks[14].y - 0.02;
            const pinkyExtended = landmarks[20].y < landmarks[18].y - 0.02;

            const extendedFingers = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

            const rect = threeCanvas.getBoundingClientRect();
            const canvasX = (1 - indexTip.x) * rect.width + rect.left;
            const canvasY = indexTip.y * rect.height + rect.top;
            const position = getCanvasPosition(canvasX, canvasY);

            previousRotationAngle = 0;

            if (indexExtended && middleExtended && ringExtended && !pinkyExtended) {
                if (canChangeGesture('undo')) {
                    undo();
                    statusText.textContent = '撤销!';
                }
            } else if (indexExtended && extendedFingers === 1) {
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
    } else {
        smoothedLandmarks = null;
        smoothedLandmarks2 = null;
        isDrawing = false;
        isErasing = false;
        isRotating = false;
        currentStroke = null;
        previousRotationAngle = 0;
        statusText.textContent = '未检测到手部';
    }

    videoCtx.restore();
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
            if (strokes[i].mesh) {
                scene.remove(strokes[i].mesh);
            }
            strokes.splice(i, 1);
        }
    }
}

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: 640,
                height: 480,
                facingMode: 'user'
            }
        });
        
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            video.play();
            isRunning = true;
            processFrame();
        };
    } catch (error) {
        console.error('无法访问摄像头:', error);
        statusText.textContent = '无法访问摄像头';
    }
}

function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}

undoBtn.addEventListener('click', undo);
redoBtn.addEventListener('click', redo);

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
});

async function init() {
    initThreeJS();
    await initDetectionEngine();
    await startCamera();
    animate();
    recordStatusDisplay.textContent = '离线模式就绪';
}

window.addEventListener('load', init);
