class SkeletonMapper {
    constructor() {
        this.poseLandmarkNames = this.getPoseLandmarkNames();
        this.boneRotationOffsets = {};
        this.smoothingFactor = 0.3;
        this.previousRotations = {};
    }
    
    getPoseLandmarkNames() {
        return [
            'nose', 'leftEyeInner', 'leftEye', 'leftEyeOuter',
            'rightEyeInner', 'rightEye', 'rightEyeOuter',
            'leftEar', 'rightEar', 'mouthLeft', 'mouthRight',
            'leftShoulder', 'rightShoulder', 'leftElbow', 'rightElbow',
            'leftWrist', 'rightWrist', 'leftPinky', 'rightPinky',
            'leftIndex', 'rightIndex', 'leftThumb', 'rightThumb',
            'leftHip', 'rightHip', 'leftKnee', 'rightKnee',
            'leftAnkle', 'rightAnkle', 'leftHeel', 'rightHeel',
            'leftFootIndex', 'rightFootIndex'
        ];
    }
    
    mapLandmarksToSkeleton(landmarks) {
        if (!landmarks) return null;
        
        const pose = this.normalizeLandmarks(landmarks);
        const boneTransforms = {};
        
        boneTransforms.spine = this.calculateSpineTransform(pose);
        boneTransforms.leftArm = this.calculateArmTransform(pose, 'left');
        boneTransforms.rightArm = this.calculateArmTransform(pose, 'right');
        boneTransforms.leftLeg = this.calculateLegTransform(pose, 'left');
        boneTransforms.rightLeg = this.calculateLegTransform(pose, 'right');
        boneTransforms.head = this.calculateHeadTransform(pose);
        
        return boneTransforms;
    }
    
    normalizeLandmarks(landmarks) {
        const normalized = landmarks.map(lm => ({
            x: (lm.x - 0.5) * 2,
            y: (1 - lm.y - 0.5) * 2,
            z: -(lm.z - 0.5) * 2,
            visibility: lm.visibility || 1
        }));
        
        const hipCenter = this.averagePoints(normalized[23], normalized[24]);
        const shoulderCenter = this.averagePoints(normalized[11], normalized[12]);
        
        normalized.forEach(lm => {
            lm.x -= hipCenter.x;
            lm.y -= hipCenter.y;
            lm.z -= hipCenter.z;
        });
        
        return normalized;
    }
    
    averagePoints(p1, p2) {
        return {
            x: (p1.x + p2.x) / 2,
            y: (p1.y + p2.y) / 2,
            z: (p1.z + p2.z) / 2
        };
    }
    
    calculateSpineTransform(pose) {
        const leftShoulder = pose[11];
        const rightShoulder = pose[12];
        const leftHip = pose[23];
        const rightHip = pose[24];
        
        const shoulderCenter = this.averagePoints(leftShoulder, rightShoulder);
        const hipCenter = this.averagePoints(leftHip, rightHip);
        
        const spineVector = {
            x: shoulderCenter.x - hipCenter.x,
            y: shoulderCenter.y - hipCenter.y,
            z: shoulderCenter.z - hipCenter.z
        };
        
        const spineLength = Math.sqrt(
            spineVector.x ** 2 + spineVector.y ** 2 + spineVector.z ** 2
        );
        
        const shoulderVector = {
            x: rightShoulder.x - leftShoulder.x,
            y: rightShoulder.y - leftShoulder.y,
            z: rightShoulder.z - leftShoulder.z
        };
        
        const forwardVector = this.crossProduct(shoulderVector, spineVector);
        
        const rotation = this.vectorsToRotation(spineVector, forwardVector);
        
        return {
            position: { x: hipCenter.x, y: hipCenter.y + 0.5, z: hipCenter.z },
            rotation,
            length: spineLength
        };
    }
    
    calculateArmTransform(pose, side) {
        const isLeft = side === 'left';
        const shoulderIdx = isLeft ? 11 : 12;
        const elbowIdx = isLeft ? 13 : 14;
        const wristIdx = isLeft ? 15 : 16;
        
        const shoulder = pose[shoulderIdx];
        const elbow = pose[elbowIdx];
        const wrist = pose[wristIdx];
        
        if (!shoulder || !elbow || !wrist) return null;
        
        const upperArmVector = {
            x: elbow.x - shoulder.x,
            y: elbow.y - shoulder.y,
            z: elbow.z - shoulder.z
        };
        
        const forearmVector = {
            x: wrist.x - elbow.x,
            y: wrist.y - elbow.y,
            z: wrist.z - elbow.z
        };
        
        const upperArmRotation = this.vectorToRotation(upperArmVector);
        const forearmRotation = this.vectorToRotation(forearmVector);
        
        const elbowAngle = this.angleBetweenVectors(upperArmVector, forearmVector);
        
        return {
            shoulder: {
                position: { x: shoulder.x, y: shoulder.y, z: shoulder.z },
                rotation: upperArmRotation
            },
            elbow: {
                angle: elbowAngle,
                rotation: forearmRotation
            },
            wrist: {
                position: { x: wrist.x, y: wrist.y, z: wrist.z }
            }
        };
    }
    
    calculateLegTransform(pose, side) {
        const isLeft = side === 'left';
        const hipIdx = isLeft ? 23 : 24;
        const kneeIdx = isLeft ? 25 : 26;
        const ankleIdx = isLeft ? 27 : 28;
        
        const hip = pose[hipIdx];
        const knee = pose[kneeIdx];
        const ankle = pose[ankleIdx];
        
        if (!hip || !knee || !ankle) return null;
        
        const upperLegVector = {
            x: knee.x - hip.x,
            y: knee.y - hip.y,
            z: knee.z - hip.z
        };
        
        const lowerLegVector = {
            x: ankle.x - knee.x,
            y: ankle.y - knee.y,
            z: ankle.z - knee.z
        };
        
        const upperLegRotation = this.vectorToRotation(upperLegVector);
        const kneeAngle = this.angleBetweenVectors(upperLegVector, lowerLegVector);
        
        return {
            hip: {
                position: { x: hip.x, y: hip.y, z: hip.z },
                rotation: upperLegRotation
            },
            knee: {
                angle: kneeAngle
            },
            ankle: {
                position: { x: ankle.x, y: ankle.y, z: ankle.z }
            }
        };
    }
    
    calculateHeadTransform(pose) {
        const nose = pose[0];
        const leftEye = pose[2];
        const rightEye = pose[5];
        
        if (!nose || !leftEye || !rightEye) return null;
        
        const eyeCenter = this.averagePoints(leftEye, rightEye);
        
        const forwardVector = {
            x: nose.x - eyeCenter.x,
            y: nose.y - eyeCenter.y,
            z: nose.z - eyeCenter.z - 0.1
        };
        
        const eyeVector = {
            x: rightEye.x - leftEye.x,
            y: rightEye.y - leftEye.y,
            z: rightEye.z - leftEye.z
        };
        
        const upVector = this.crossProduct(eyeVector, forwardVector);
        const rotation = this.vectorsToRotation(forwardVector, upVector);
        
        return {
            position: { x: eyeCenter.x, y: eyeCenter.y + 0.1, z: eyeCenter.z },
            rotation,
            lookDirection: forwardVector
        };
    }
    
    vectorToRotation(vector) {
        const length = Math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2);
        if (length === 0) return { x: 0, y: 0, z: 0 };
        
        const normalized = {
            x: vector.x / length,
            y: vector.y / length,
            z: vector.z / length
        };
        
        const pitch = Math.asin(-normalized.y);
        const yaw = Math.atan2(normalized.x, normalized.z);
        
        return { x: pitch, y: yaw, z: 0 };
    }
    
    vectorsToRotation(forward, up) {
        const forwardLen = Math.sqrt(forward.x ** 2 + forward.y ** 2 + forward.z ** 2);
        const forwardNorm = {
            x: forward.x / forwardLen,
            y: forward.y / forwardLen,
            z: forward.z / forwardLen
        };
        
        const right = this.crossProduct(up, forwardNorm);
        const rightLen = Math.sqrt(right.x ** 2 + right.y ** 2 + right.z ** 2);
        const rightNorm = {
            x: right.x / rightLen,
            y: right.y / rightLen,
            z: right.z / rightLen
        };
        
        const upNorm = this.crossProduct(forwardNorm, rightNorm);
        
        const sy = Math.sqrt(rightNorm.x ** 2 + rightNorm.z ** 2);
        const singular = sy < 1e-6;
        
        let x, y, z;
        if (!singular) {
            x = Math.atan2(upNorm.y, forwardNorm.y);
            y = Math.atan2(-rightNorm.y, sy);
            z = Math.atan2(rightNorm.x, rightNorm.z);
        } else {
            x = Math.atan2(-forwardNorm.z, forwardNorm.x);
            y = Math.atan2(-rightNorm.y, sy);
            z = 0;
        }
        
        return { x, y, z };
    }
    
    crossProduct(a, b) {
        return {
            x: a.y * b.z - a.z * b.y,
            y: a.z * b.x - a.x * b.z,
            z: a.x * b.y - a.y * b.x
        };
    }
    
    angleBetweenVectors(a, b) {
        const dot = a.x * b.x + a.y * b.y + a.z * b.z;
        const aLen = Math.sqrt(a.x ** 2 + a.y ** 2 + a.z ** 2);
        const bLen = Math.sqrt(b.x ** 2 + b.y ** 2 + b.z ** 2);
        
        if (aLen === 0 || bLen === 0) return 0;
        
        return Math.acos(Math.max(-1, Math.min(1, dot / (aLen * bLen))));
    }
    
    smoothRotation(boneName, currentRotation) {
        if (!this.previousRotations[boneName]) {
            this.previousRotations[boneName] = { ...currentRotation };
            return currentRotation;
        }
        
        const prev = this.previousRotations[boneName];
        
        const smoothed = {
            x: prev.x * (1 - this.smoothingFactor) + currentRotation.x * this.smoothingFactor,
            y: prev.y * (1 - this.smoothingFactor) + currentRotation.y * this.smoothingFactor,
            z: prev.z * (1 - this.smoothingFactor) + currentRotation.z * this.smoothingFactor
        };
        
        this.previousRotations[boneName] = { ...smoothed };
        return smoothed;
    }
    
    applyBoneLimits(rotation, boneName) {
        const limits = this.getJointLimits(boneName);
        
        return {
            x: Math.max(limits.minX, Math.min(limits.maxX, rotation.x)),
            y: Math.max(limits.minY, Math.min(limits.maxY, rotation.y)),
            z: Math.max(limits.minZ, Math.min(limits.maxZ, rotation.z))
        };
    }
    
    getJointLimits(boneName) {
        const limits = {
            'neck': { minX: -0.5, maxX: 0.5, minY: -1, maxY: 1, minZ: -0.3, maxZ: 0.3 },
            'leftShoulder': { minX: -1.5, maxX: 1.5, minY: -2, maxY: 0.5, minZ: -1, maxZ: 1 },
            'rightShoulder': { minX: -1.5, maxX: 1.5, minY: -0.5, maxY: 2, minZ: -1, maxZ: 1 },
            'leftElbow': { minX: 0, maxX: 2.5, minY: -0.5, maxY: 0.5, minZ: -0.5, maxZ: 0.5 },
            'rightElbow': { minX: 0, maxX: 2.5, minY: -0.5, maxY: 0.5, minZ: -0.5, maxZ: 0.5 },
            'leftHip': { minX: -1, maxX: 1, minY: -1, maxY: 1, minZ: -0.5, maxZ: 0.5 },
            'rightHip': { minX: -1, maxX: 1, minY: -1, maxY: 1, minZ: -0.5, maxZ: 0.5 },
            'leftKnee': { minX: 0, maxX: 2, minY: -0.3, maxY: 0.3, minZ: -0.3, maxZ: 0.3 },
            'rightKnee': { minX: 0, maxX: 2, minY: -0.3, maxY: 0.3, minZ: -0.3, maxZ: 0.3 }
        };
        
        return limits[boneName] || { minX: -Math.PI, maxX: Math.PI, minY: -Math.PI, maxY: Math.PI, minZ: -Math.PI, maxZ: Math.PI };
    }
    
    calculateFaceBlendshapes(faceLandmarks) {
        if (!faceLandmarks || faceLandmarks.length < 468) return {};
        
        const blendshapes = {};
        
        const leftEyeOpen = this.calculateEyeOpenness(faceLandmarks, 'left');
        const rightEyeOpen = this.calculateEyeOpenness(faceLandmarks, 'right');
        blendshapes.eyeBlinkLeft = 1 - leftEyeOpen;
        blendshapes.eyeBlinkRight = 1 - rightEyeOpen;
        blendshapes.eyeWideLeft = Math.max(0, (leftEyeOpen - 0.7) * 3);
        blendshapes.eyeWideRight = Math.max(0, (rightEyeOpen - 0.7) * 3);
        
        blendshapes.jawOpen = this.calculateMouthOpenness(faceLandmarks);
        
        const smile = this.calculateSmile(faceLandmarks);
        blendshapes.mouthSmileLeft = smile.left;
        blendshapes.mouthSmileRight = smile.right;
        
        const browHeight = this.calculateBrowHeight(faceLandmarks);
        blendshapes.browInnerUp = browHeight.inner;
        blendshapes.browOuterUpLeft = browHeight.leftOuter;
        blendshapes.browOuterUpRight = browHeight.rightOuter;
        
        return blendshapes;
    }
    
    calculateEyeOpenness(landmarks, side) {
        const isLeft = side === 'left';
        const topIdx = isLeft ? 386 : 159;
        const bottomIdx = isLeft ? 374 : 145;
        const leftIdx = isLeft ? 362 : 133;
        const rightIdx = isLeft ? 263 : 33;
        
        const top = landmarks[topIdx];
        const bottom = landmarks[bottomIdx];
        const left = landmarks[leftIdx];
        const right = landmarks[rightIdx];
        
        if (!top || !bottom || !left || !right) return 0.5;
        
        const verticalDist = Math.sqrt(
            (top.x - bottom.x) ** 2 +
            (top.y - bottom.y) ** 2
        );
        
        const horizontalDist = Math.sqrt(
            (left.x - right.x) ** 2 +
            (left.y - right.y) ** 2
        );
        
        if (horizontalDist === 0) return 0.5;
        
        return Math.min(1, Math.max(0, verticalDist / horizontalDist));
    }
    
    calculateMouthOpenness(landmarks) {
        const top = landmarks[13];
        const bottom = landmarks[14];
        const left = landmarks[61];
        const right = landmarks[291];
        
        if (!top || !bottom || !left || !right) return 0;
        
        const verticalDist = Math.sqrt(
            (top.x - bottom.x) ** 2 +
            (top.y - bottom.y) ** 2
        );
        
        const horizontalDist = Math.sqrt(
            (left.x - right.x) ** 2 +
            (left.y - right.y) ** 2
        );
        
        if (horizontalDist === 0) return 0;
        
        return Math.min(1, Math.max(0, verticalDist / horizontalDist * 1.5));
    }
    
    calculateSmile(landmarks) {
        const mouthLeft = landmarks[61];
        const mouthRight = landmarks[291];
        const nose = landmarks[1];
        
        if (!mouthLeft || !mouthRight || !nose) return { left: 0, right: 0 };
        
        const referenceY = nose.y;
        const mouthCenterY = (mouthLeft.y + mouthRight.y) / 2;
        
        const normalizedHeight = (referenceY - mouthCenterY) * 10;
        
        return {
            left: Math.min(1, Math.max(0, normalizedHeight + (mouthCenterY - mouthLeft.y) * 5)),
            right: Math.min(1, Math.max(0, normalizedHeight + (mouthCenterY - mouthRight.y) * 5))
        };
    }
    
    calculateBrowHeight(landmarks) {
        const leftBrowInner = landmarks[285];
        const rightBrowInner = landmarks[55];
        const leftBrowOuter = landmarks[300];
        const rightBrowOuter = landmarks[70];
        const noseBridge = landmarks[6];
        
        if (!leftBrowInner || !rightBrowInner || !noseBridge) {
            return { inner: 0, leftOuter: 0, rightOuter: 0 };
        }
        
        const referenceY = noseBridge.y;
        
        const inner = (referenceY - (leftBrowInner.y + rightBrowInner.y) / 2) * 8;
        const leftOuter = (referenceY - leftBrowOuter.y) * 6;
        const rightOuter = (referenceY - rightBrowOuter.y) * 6;
        
        return {
            inner: Math.min(1, Math.max(0, inner)),
            leftOuter: Math.min(1, Math.max(0, leftOuter)),
            rightOuter: Math.min(1, Math.max(0, rightOuter))
        };
    }
}