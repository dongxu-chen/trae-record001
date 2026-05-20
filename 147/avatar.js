class AvatarRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.resize();
        
        this.currentModel = 'cartoon';
        this.scale = 1.0;
        
        this.blendshapes = this.initEmptyBlendshapes();
        this.rotation = { x: 0, y: 0, z: 0 };
        
        this.poseData = null;
        
        this.audioMouthOpen = 0;
        this.audioMouthWidth = 0.5;
        this.useAudioSync = true;
        
        this.mouthSmoothing = 0.8;
        this.smoothedMouthOpen = 0;
        this.smoothedMouthWidth = 0.5;
        
        this.initAvatar();
    }
    
    initEmptyBlendshapes() {
        return {
            eyeBlinkLeft: 0,
            eyeBlinkRight: 0,
            eyeLookDownLeft: 0,
            eyeLookDownRight: 0,
            eyeLookInLeft: 0,
            eyeLookInRight: 0,
            eyeLookOutLeft: 0,
            eyeLookOutRight: 0,
            eyeLookUpLeft: 0,
            eyeLookUpRight: 0,
            eyeSquintLeft: 0,
            eyeSquintRight: 0,
            eyeWideLeft: 0,
            eyeWideRight: 0,
            jawForward: 0,
            jawLeft: 0,
            jawRight: 0,
            jawOpen: 0,
            mouthClose: 0,
            mouthFunnel: 0,
            mouthPucker: 0,
            mouthLeft: 0,
            mouthRight: 0,
            mouthSmileLeft: 0,
            mouthSmileRight: 0,
            mouthFrownLeft: 0,
            mouthFrownRight: 0,
            mouthDimpleLeft: 0,
            mouthDimpleRight: 0,
            mouthStretchLeft: 0,
            mouthStretchRight: 0,
            mouthRollLower: 0,
            mouthRollUpper: 0,
            mouthShrugLower: 0,
            mouthShrugUpper: 0,
            mouthPressLeft: 0,
            mouthPressRight: 0,
            mouthLowerDownLeft: 0,
            mouthLowerDownRight: 0,
            mouthUpperUpLeft: 0,
            mouthUpperUpRight: 0,
            browDownLeft: 0,
            browDownRight: 0,
            browInnerUp: 0,
            browOuterUpLeft: 0,
            browOuterUpRight: 0,
            cheekPuff: 0,
            cheekSquintLeft: 0,
            cheekSquintRight: 0,
            noseSneerLeft: 0,
            noseSneerRight: 0,
            tongueOut: 0
        };
    }
    
    resize() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.width = rect.width;
        this.height = rect.height;
    }
    
    initAvatar() {
        this.avatarParams = {
            headCenterX: this.width / 2,
            headCenterY: this.height * 0.25,
            headRadius: Math.min(this.width, this.height) * 0.15
        };
    }
    
    setModel(modelName) {
        this.currentModel = modelName;
    }
    
    setScale(scale) {
        this.scale = scale;
    }
    
    updateBlendshapes(blendshapes) {
        for (const key in blendshapes) {
            if (this.blendshapes.hasOwnProperty(key)) {
                this.blendshapes[key] = blendshapes[key];
            }
        }
    }
    
    updateFaceData(landmarks) {
        if (!landmarks || landmarks.length === 0) return;
        
        const lm = landmarks[0].keypoints;
        
        const nose = lm[1];
        const leftCheek = lm[234];
        const rightCheek = lm[454];
        
        this.rotation.y = Math.atan2(nose.x - (leftCheek.x + rightCheek.x) / 2, 200);
        this.rotation.x = 0;
    }
    
    updatePoseData(poseData) {
        this.poseData = poseData;
    }
    
    setAudioMouthShape(mouthShape) {
        this.audioMouthOpen = mouthShape.mouthOpen;
        this.audioMouthWidth = mouthShape.mouthWidth;
    }
    
    enableAudioSync(enabled) {
        this.useAudioSync = enabled;
    }
    
    render() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        this.updateSmoothedMouth();
        
        this.ctx.save();
        this.ctx.translate(this.width / 2, this.height * 0.15);
        this.ctx.scale(this.scale, this.scale);
        
        switch (this.currentModel) {
            case 'cartoon':
                this.renderCartoonAvatar();
                break;
            case 'realistic':
                this.renderRealisticAvatar();
                break;
            case 'robot':
                this.renderRobotAvatar();
                break;
            case 'anime':
                this.renderAnimeAvatar();
                break;
            default:
                this.renderCartoonAvatar();
        }
        
        this.ctx.restore();
        
        requestAnimationFrame(() => this.render());
    }
    
    updateSmoothedMouth() {
        let targetMouthOpen = this.blendshapes.jawOpen;
        let targetMouthWidth = 0.5 + this.blendshapes.mouthStretchLeft * 0.2;
        
        if (this.useAudioSync && this.audioMouthOpen > targetMouthOpen) {
            targetMouthOpen = this.audioMouthOpen;
            targetMouthWidth = this.audioMouthWidth;
        }
        
        this.smoothedMouthOpen = this.smoothedMouthOpen * this.mouthSmoothing + 
                                  targetMouthOpen * (1 - this.mouthSmoothing);
        this.smoothedMouthWidth = this.smoothedMouthWidth * this.mouthSmoothing + 
                                   targetMouthWidth * (1 - this.mouthSmoothing);
    }
    
    renderCartoonAvatar() {
        const headY = 0;
        const headRadius = this.avatarParams.headRadius;
        
        this.drawBodyCartoon(headY, headRadius);
        
        this.ctx.beginPath();
        this.ctx.ellipse(this.rotation.y * 20, headY, headRadius * (1 + this.rotation.y * 0.01), headRadius * 1.2, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = '#FFE4C4';
        this.ctx.fill();
        this.ctx.strokeStyle = '#DEB887';
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
        
        this.drawHairCartoon(headY, headRadius);
        this.drawEyesCartoon(headY, headRadius);
        this.drawEyebrowsCartoon(headY, headRadius);
        this.drawMouthCartoon(headY, headRadius);
    }
    
    renderRealisticAvatar() {
        const headY = 0;
        const headRadius = this.avatarParams.headRadius;
        
        this.drawBodyRealistic(headY, headRadius);
        
        const gradient = this.ctx.createRadialGradient(
            this.rotation.y * 10, headY - 20, 0,
            this.rotation.y * 10, headY, headRadius * 1.5
        );
        gradient.addColorStop(0, '#F5DEB3');
        gradient.addColorStop(0.7, '#DEB887');
        gradient.addColorStop(1, '#D2B48C');
        
        this.ctx.beginPath();
        this.ctx.ellipse(this.rotation.y * 15, headY, headRadius * 0.9, headRadius * 1.15, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();
        
        this.drawHairRealistic(headY, headRadius);
        this.drawEyesRealistic(headY, headRadius);
        this.drawNoseRealistic(headY, headRadius);
        this.drawMouthRealistic(headY, headRadius);
    }
    
    renderRobotAvatar() {
        const headY = 0;
        const headRadius = this.avatarParams.headRadius;
        
        this.drawBodyRobot(headY, headRadius);
        
        this.ctx.beginPath();
        this.ctx.roundRect(-headRadius * 0.9, headY - headRadius, headRadius * 1.8, headRadius * 2, 20);
        const metalGradient = this.ctx.createLinearGradient(-headRadius, headY - headRadius, headRadius, headY + headRadius);
        metalGradient.addColorStop(0, '#708090');
        metalGradient.addColorStop(0.5, '#A9A9A9');
        metalGradient.addColorStop(1, '#696969');
        this.ctx.fillStyle = metalGradient;
        this.ctx.fill();
        this.ctx.strokeStyle = '#4A4A4A';
        this.ctx.lineWidth = 4;
        this.ctx.stroke();
        
        this.drawRobotAntenna(headY, headRadius);
        this.drawRobotEyes(headY, headRadius);
        this.drawRobotMouth(headY, headRadius);
    }
    
    renderAnimeAvatar() {
        const headY = 0;
        const headRadius = this.avatarParams.headRadius;
        
        this.drawBodyAnime(headY, headRadius);
        
        this.ctx.beginPath();
        this.ctx.ellipse(this.rotation.y * 10, headY, headRadius * 0.85, headRadius * 1.1, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = '#FFF5EE';
        this.ctx.fill();
        this.ctx.strokeStyle = '#E8E8E8';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        this.drawHairAnime(headY, headRadius);
        this.drawEyesAnime(headY, headRadius);
        this.drawMouthAnime(headY, headRadius);
    }
    
    drawHairCartoon(headY, headRadius) {
        this.ctx.beginPath();
        this.ctx.arc(0, headY - headRadius * 0.3, headRadius * 0.9, Math.PI, 0);
        this.ctx.fillStyle = '#4A3728';
        this.ctx.fill();
        
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.8, headY - headRadius * 0.2);
        this.ctx.quadraticCurveTo(-headRadius * 1.1, headY + headRadius * 0.3, -headRadius * 0.7, headY + headRadius * 0.5);
        this.ctx.lineWidth = 12;
        this.ctx.strokeStyle = '#4A3728';
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(headRadius * 0.8, headY - headRadius * 0.2);
        this.ctx.quadraticCurveTo(headRadius * 1.1, headY + headRadius * 0.3, headRadius * 0.7, headY + headRadius * 0.5);
        this.ctx.stroke();
    }
    
    drawHairRealistic(headY, headRadius) {
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.9, headY - headRadius * 0.3);
        this.ctx.quadraticCurveTo(0, headY - headRadius * 1.3, headRadius * 0.9, headY - headRadius * 0.3);
        this.ctx.quadraticCurveTo(headRadius * 1.1, headY + headRadius * 0.2, headRadius * 0.8, headY + headRadius * 0.6);
        this.ctx.quadraticCurveTo(0, headY + headRadius * 0.4, -headRadius * 0.8, headY + headRadius * 0.6);
        this.ctx.quadraticCurveTo(-headRadius * 1.1, headY + headRadius * 0.2, -headRadius * 0.9, headY - headRadius * 0.3);
        this.ctx.fillStyle = '#2C1810';
        this.ctx.fill();
    }
    
    drawHairAnime(headY, headRadius) {
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 1.2, headY - headRadius * 0.8);
        this.ctx.lineTo(-headRadius * 0.3, headY - headRadius * 1.2);
        this.ctx.lineTo(headRadius * 0.3, headY - headRadius * 1.3);
        this.ctx.lineTo(headRadius * 1.2, headY - headRadius * 0.7);
        this.ctx.lineTo(headRadius * 0.9, headY + headRadius * 0.7);
        this.ctx.lineTo(-headRadius * 0.9, headY + headRadius * 0.7);
        this.ctx.closePath();
        this.ctx.fillStyle = '#1E90FF';
        this.ctx.fill();
        
        for (let i = -3; i <= 3; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(i * headRadius * 0.25, headY - headRadius * 1.1);
            this.ctx.lineTo(i * headRadius * 0.2, headY - headRadius * 0.5);
            this.ctx.lineWidth = 3;
            this.ctx.strokeStyle = '#1E90FF';
            this.ctx.stroke();
        }
    }
    
    drawEyesCartoon(headY, headRadius) {
        const eyeY = headY - headRadius * 0.1;
        const eyeSpacing = headRadius * 0.4;
        const eyeSize = headRadius * 0.25;
        
        const leftBlink = 1 - Math.max(this.blendshapes.eyeBlinkLeft, this.blendshapes.eyeSquintLeft);
        const rightBlink = 1 - Math.max(this.blendshapes.eyeBlinkRight, this.blendshapes.eyeSquintRight);
        
        this.drawCartoonEye(-eyeSpacing, eyeY, eyeSize, leftBlink);
        this.drawCartoonEye(eyeSpacing, eyeY, eyeSize, rightBlink);
    }
    
    drawCartoonEye(x, y, size, openRatio) {
        const height = size * Math.max(0.2, openRatio);
        
        this.ctx.beginPath();
        this.ctx.ellipse(x, y, size, height, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = 'white';
        this.ctx.fill();
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        if (openRatio > 0.3) {
            this.ctx.beginPath();
            this.ctx.arc(x, y, size * 0.5, 0, Math.PI * 2);
            this.ctx.fillStyle = '#4169E1';
            this.ctx.fill();
            
            this.ctx.beginPath();
            this.ctx.arc(x - size * 0.2, y - size * 0.2, size * 0.2, 0, Math.PI * 2);
            this.ctx.fillStyle = 'white';
            this.ctx.fill();
        }
    }
    
    drawEyesRealistic(headY, headRadius) {
        const eyeY = headY - headRadius * 0.05;
        const eyeSpacing = headRadius * 0.4;
        const eyeWidth = headRadius * 0.2;
        
        const leftBlink = 1 - Math.max(this.blendshapes.eyeBlinkLeft, this.blendshapes.eyeSquintLeft);
        const rightBlink = 1 - Math.max(this.blendshapes.eyeBlinkRight, this.blendshapes.eyeSquintRight);
        
        this.drawRealisticEye(-eyeSpacing, eyeY, eyeWidth, leftBlink);
        this.drawRealisticEye(eyeSpacing, eyeY, eyeWidth, rightBlink);
    }
    
    drawRealisticEye(x, y, width, openRatio) {
        const height = width * 0.6 * Math.max(0.2, openRatio);
        
        this.ctx.beginPath();
        this.ctx.ellipse(x, y, width, height, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = 'white';
        this.ctx.fill();
        
        this.ctx.beginPath();
        this.ctx.ellipse(x, y, width * 0.5, height * 0.7, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = '#654321';
        this.ctx.fill();
        
        this.ctx.beginPath();
        this.ctx.arc(x, y, width * 0.25, 0, Math.PI * 2);
        this.ctx.fillStyle = '#000';
        this.ctx.fill();
        
        this.ctx.beginPath();
        this.ctx.arc(x - width * 0.15, y - width * 0.15, width * 0.15, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(255,255,255,0.8)';
        this.ctx.fill();
    }
    
    drawRobotEyes(headY, headRadius) {
        const eyeY = headY - headRadius * 0.1;
        const eyeSpacing = headRadius * 0.4;
        const eyeSize = headRadius * 0.25;
        
        const glowIntensity = 0.5 + Math.sin(Date.now() / 200) * 0.3;
        
        [-1, 1].forEach(side => {
            const x = eyeSpacing * side;
            
            this.ctx.shadowColor = '#00FFFF';
            this.ctx.shadowBlur = 20 * glowIntensity;
            
            this.ctx.beginPath();
            this.ctx.roundRect(x - eyeSize, eyeY - eyeSize * 0.6, eyeSize * 2, eyeSize * 1.2, 5);
            this.ctx.fillStyle = `rgba(0, 255, 255, ${glowIntensity})`;
            this.ctx.fill();
            this.ctx.strokeStyle = '#00CED1';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            this.ctx.shadowBlur = 0;
        });
    }
    
    drawEyesAnime(headY, headRadius) {
        const eyeY = headY - headRadius * 0.05;
        const eyeSpacing = headRadius * 0.42;
        const eyeWidth = headRadius * 0.32;
        
        const leftBlink = 1 - Math.max(this.blendshapes.eyeBlinkLeft, this.blendshapes.eyeSquintLeft);
        const rightBlink = 1 - Math.max(this.blendshapes.eyeBlinkRight, this.blendshapes.eyeSquintRight);
        
        this.drawAnimeEye(-eyeSpacing, eyeY, eyeWidth, leftBlink);
        this.drawAnimeEye(eyeSpacing, eyeY, eyeWidth, rightBlink);
    }
    
    drawAnimeEye(x, y, width, openRatio) {
        const height = width * 0.9 * Math.max(0.15, openRatio);
        
        this.ctx.beginPath();
        this.ctx.ellipse(x, y, width, height, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = 'white';
        this.ctx.fill();
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
        
        if (openRatio > 0.3) {
            const irisGradient = this.ctx.createRadialGradient(x, y, 0, x, y, width * 0.6);
            irisGradient.addColorStop(0, '#9370DB');
            irisGradient.addColorStop(0.7, '#4B0082');
            irisGradient.addColorStop(1, '#2F0A3C');
            
            this.ctx.beginPath();
            this.ctx.ellipse(x, y + height * 0.1, width * 0.55, height * 0.7, 0, 0, Math.PI * 2);
            this.ctx.fillStyle = irisGradient;
            this.ctx.fill();
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, width * 0.25, 0, Math.PI * 2);
            this.ctx.fillStyle = '#000';
            this.ctx.fill();
            
            this.ctx.beginPath();
            this.ctx.ellipse(x - width * 0.2, y - height * 0.25, width * 0.12, width * 0.18, -0.5, 0, Math.PI * 2);
            this.ctx.fillStyle = 'white';
            this.ctx.fill();
        }
    }
    
    drawEyebrowsCartoon(headY, headRadius) {
        const eyeY = headY - headRadius * 0.1;
        const eyeSpacing = headRadius * 0.4;
        const browY = eyeY - headRadius * 0.35;
        
        const innerUp = this.blendshapes.browInnerUp * 15;
        const outerUpLeft = this.blendshapes.browOuterUpLeft * 10;
        const outerUpRight = this.blendshapes.browOuterUpRight * 10;
        
        this.ctx.beginPath();
        this.ctx.moveTo(-eyeSpacing - headRadius * 0.25, browY - outerUpLeft);
        this.ctx.quadraticCurveTo(-eyeSpacing, browY - innerUp - 8, -eyeSpacing + headRadius * 0.25, browY - outerUpLeft);
        this.ctx.strokeStyle = '#4A3728';
        this.ctx.lineWidth = 4;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(eyeSpacing - headRadius * 0.25, browY - outerUpRight);
        this.ctx.quadraticCurveTo(eyeSpacing, browY - innerUp - 8, eyeSpacing + headRadius * 0.25, browY - outerUpRight);
        this.ctx.stroke();
    }
    
    drawNoseRealistic(headY, headRadius) {
        const noseY = headY + headRadius * 0.15;
        
        this.ctx.beginPath();
        this.ctx.moveTo(0, noseY - 15);
        this.ctx.quadraticCurveTo(8, noseY, 0, noseY + 8);
        this.ctx.strokeStyle = 'rgba(139, 90, 43, 0.5)';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }
    
    drawMouthCartoon(headY, headRadius) {
        const mouthY = headY + headRadius * 0.45;
        const mouthOpen = this.smoothedMouthOpen;
        const smile = (this.blendshapes.mouthSmileLeft + this.blendshapes.mouthSmileRight) / 2;
        
        const mouthWidth = headRadius * (0.35 + smile * 0.15);
        const mouthHeight = headRadius * 0.08 * (1 + mouthOpen * 4);
        
        this.ctx.beginPath();
        this.ctx.ellipse(0, mouthY, mouthWidth, mouthHeight, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = '#CD5C5C';
        this.ctx.fill();
        
        if (mouthOpen > 0.2) {
            this.ctx.beginPath();
            this.ctx.ellipse(0, mouthY, mouthWidth * 0.8, mouthHeight * 0.5 * mouthOpen, 0, 0, Math.PI * 2);
            this.ctx.fillStyle = '#8B0000';
            this.ctx.fill();
            
            this.ctx.beginPath();
            this.ctx.ellipse(0, mouthY + mouthHeight * 0.3 * mouthOpen, mouthWidth * 0.5, mouthHeight * 0.25, 0, 0, Math.PI);
            this.ctx.fillStyle = '#FFB6C1';
            this.ctx.fill();
        }
    }
    
    drawMouthRealistic(headY, headRadius) {
        const mouthY = headY + headRadius * 0.5;
        const mouthOpen = this.smoothedMouthOpen;
        
        const mouthWidth = headRadius * 0.35;
        const mouthHeight = headRadius * 0.05 * (1 + mouthOpen * 5);
        
        this.ctx.beginPath();
        this.ctx.ellipse(0, mouthY, mouthWidth, mouthHeight, 0, 0, Math.PI * 2);
        this.ctx.fillStyle = '#C41E3A';
        this.ctx.fill();
        
        if (mouthOpen > 0.15) {
            this.ctx.beginPath();
            this.ctx.ellipse(0, mouthY, mouthWidth * 0.7, mouthHeight * 0.4 * mouthOpen, 0, 0, Math.PI * 2);
            this.ctx.fillStyle = '#5C0011';
            this.ctx.fill();
        }
    }
    
    drawRobotMouth(headY, headRadius) {
        const mouthY = headY + headRadius * 0.5;
        const mouthOpen = this.smoothedMouthOpen;
        
        const segments = 8;
        const segmentWidth = headRadius * 0.08;
        const gap = headRadius * 0.02;
        
        for (let i = 0; i < segments; i++) {
            const x = (i - segments / 2 + 0.5) * (segmentWidth + gap);
            const height = headRadius * (0.05 + mouthOpen * 0.2) * (0.5 + Math.random() * 0.5);
            
            this.ctx.shadowColor = '#FF4500';
            this.ctx.shadowBlur = 10;
            
            this.ctx.fillStyle = mouthOpen > 0.1 ? '#FF4500' : '#4A4A4A';
            this.ctx.fillRect(x - segmentWidth / 2, mouthY - height / 2, segmentWidth, height);
            
            this.ctx.shadowBlur = 0;
        }
    }
    
    drawMouthAnime(headY, headRadius) {
        const mouthY = headY + headRadius * 0.5;
        const mouthOpen = this.smoothedMouthOpen;
        
        if (mouthOpen < 0.2) {
            this.ctx.beginPath();
            this.ctx.moveTo(-headRadius * 0.2, mouthY);
            this.ctx.quadraticCurveTo(0, mouthY + 5, headRadius * 0.2, mouthY);
            this.ctx.strokeStyle = '#CD5C5C';
            this.ctx.lineWidth = 3;
            this.ctx.stroke();
        } else {
            this.ctx.beginPath();
            this.ctx.ellipse(0, mouthY, headRadius * 0.2, headRadius * 0.15 * mouthOpen * 3, 0, 0, Math.PI * 2);
            this.ctx.fillStyle = '#CD5C5C';
            this.ctx.fill();
        }
    }
    
    drawRobotAntenna(headY, headRadius) {
        this.ctx.beginPath();
        this.ctx.moveTo(0, headY - headRadius);
        this.ctx.lineTo(0, headY - headRadius - 30);
        this.ctx.strokeStyle = '#A9A9A9';
        this.ctx.lineWidth = 4;
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.arc(0, headY - headRadius - 30, 8, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgba(255, 0, 0, ${0.5 + Math.sin(Date.now() / 300) * 0.5})`;
        this.ctx.fill();
    }
    
    drawBodyCartoon(headY, headRadius) {
        const bodyStartY = headY + headRadius * 1.3;
        const bodyEndY = this.height * 0.7;
        
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.6, bodyStartY);
        this.ctx.lineTo(-headRadius * 1.2, bodyEndY);
        this.ctx.lineTo(headRadius * 1.2, bodyEndY);
        this.ctx.lineTo(headRadius * 0.6, bodyStartY);
        this.ctx.closePath();
        
        const bodyGradient = this.ctx.createLinearGradient(-headRadius, bodyStartY, headRadius, bodyEndY);
        bodyGradient.addColorStop(0, '#4169E1');
        bodyGradient.addColorStop(1, '#1E3A8A');
        this.ctx.fillStyle = bodyGradient;
        this.ctx.fill();
        
        if (this.poseData && this.poseData.poseLandmarks) {
            this.drawArmsWithPose(headY, headRadius);
        } else {
            this.drawArmsDefault(headY, headRadius);
        }
    }
    
    drawBodyRealistic(headY, headRadius) {
        const bodyStartY = headY + headRadius * 1.25;
        const bodyEndY = this.height * 0.7;
        
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.5, bodyStartY);
        this.ctx.lineTo(-headRadius * 1.0, bodyEndY);
        this.ctx.lineTo(headRadius * 1.0, bodyEndY);
        this.ctx.lineTo(headRadius * 0.5, bodyStartY);
        this.ctx.closePath();
        
        const bodyGradient = this.ctx.createLinearGradient(-headRadius, bodyStartY, headRadius, bodyEndY);
        bodyGradient.addColorStop(0, '#2F4F4F');
        bodyGradient.addColorStop(1, '#1C1C1C');
        this.ctx.fillStyle = bodyGradient;
        this.ctx.fill();
    }
    
    drawBodyRobot(headY, headRadius) {
        const bodyStartY = headY + headRadius * 1.1;
        const bodyEndY = this.height * 0.7;
        
        this.ctx.beginPath();
        this.ctx.roundRect(-headRadius * 0.8, bodyStartY, headRadius * 1.6, bodyEndY - bodyStartY, 15);
        const bodyGradient = this.ctx.createLinearGradient(-headRadius, bodyStartY, headRadius, bodyEndY);
        bodyGradient.addColorStop(0, '#696969');
        bodyGradient.addColorStop(0.5, '#808080');
        bodyGradient.addColorStop(1, '#505050');
        this.ctx.fillStyle = bodyGradient;
        this.ctx.fill();
        this.ctx.strokeStyle = '#4A4A4A';
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
        
        const coreY = bodyStartY + 40;
        this.ctx.beginPath();
        this.ctx.arc(0, coreY, 20, 0, Math.PI * 2);
        this.ctx.shadowColor = '#00FF00';
        this.ctx.shadowBlur = 15;
        this.ctx.fillStyle = '#00FF00';
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
    }
    
    drawBodyAnime(headY, headRadius) {
        const bodyStartY = headY + headRadius * 1.2;
        const bodyEndY = this.height * 0.7;
        
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.4, bodyStartY);
        this.ctx.lineTo(-headRadius * 0.9, bodyEndY);
        this.ctx.lineTo(headRadius * 0.9, bodyEndY);
        this.ctx.lineTo(headRadius * 0.4, bodyStartY);
        this.ctx.closePath();
        
        const bodyGradient = this.ctx.createLinearGradient(-headRadius, bodyStartY, headRadius, bodyEndY);
        bodyGradient.addColorStop(0, '#FF69B4');
        bodyGradient.addColorStop(1, '#DB7093');
        this.ctx.fillStyle = bodyGradient;
        this.ctx.fill();
    }
    
    drawArmsDefault(headY, headRadius) {
        const shoulderY = headY + headRadius * 1.5;
        
        this.ctx.beginPath();
        this.ctx.moveTo(-headRadius * 0.6, shoulderY);
        this.ctx.lineTo(-headRadius * 1.3, shoulderY + 80);
        this.ctx.strokeStyle = '#4169E1';
        this.ctx.lineWidth = 25;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(headRadius * 0.6, shoulderY);
        this.ctx.lineTo(headRadius * 1.3, shoulderY + 80);
        this.ctx.stroke();
    }
    
    drawArmsWithPose(headY, headRadius) {
        const landmarks = this.poseData.poseLandmarks;
        if (!landmarks) return;
        
        const shoulderY = headY + headRadius * 1.5;
        const scale = headRadius * 3;
        
        const leftShoulder = landmarks[11];
        const rightShoulder = landmarks[12];
        const leftElbow = landmarks[13];
        const rightElbow = landmarks[14];
        const leftWrist = landmarks[15];
        const rightWrist = landmarks[16];
        
        if (leftShoulder && leftElbow && leftWrist && rightShoulder && rightElbow && rightWrist) {
            this.ctx.beginPath();
            this.ctx.moveTo(-headRadius * 0.6, shoulderY);
            this.ctx.lineTo(
                -headRadius * 0.6 + (leftElbow.x - leftShoulder.x) * scale * 0.5,
                shoulderY + (leftElbow.y - leftShoulder.y) * scale * 0.5
            );
            this.ctx.lineTo(
                -headRadius * 0.6 + (leftWrist.x - leftShoulder.x) * scale * 0.5,
                shoulderY + (leftWrist.y - leftShoulder.y) * scale * 0.5
            );
            this.ctx.strokeStyle = '#4169E1';
            this.ctx.lineWidth = 25;
            this.ctx.lineCap = 'round';
            this.ctx.stroke();
            
            this.ctx.beginPath();
            this.ctx.moveTo(headRadius * 0.6, shoulderY);
            this.ctx.lineTo(
                headRadius * 0.6 + (rightElbow.x - rightShoulder.x) * scale * 0.5,
                shoulderY + (rightElbow.y - rightShoulder.y) * scale * 0.5
            );
            this.ctx.lineTo(
                headRadius * 0.6 + (rightWrist.x - rightShoulder.x) * scale * 0.5,
                shoulderY + (rightWrist.y - rightShoulder.y) * scale * 0.5
            );
            this.ctx.stroke();
        }
    }
    
    getMouthOpenValue() {
        return this.smoothedMouthOpen;
    }
    
    isBlinking() {
        return (this.blendshapes.eyeBlinkLeft + this.blendshapes.eyeBlinkRight) / 2 > 0.5;
    }
}