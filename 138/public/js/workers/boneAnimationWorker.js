class BoneAnimationWorker {
    constructor() {
        this.bones = [];
        this.boneMatrices = [];
        this.animationClips = [];
        this.currentAnimation = null;
        this.currentTime = 0;
        this.isPlaying = false;
        this.targetFPS = 60;
        this.lastUpdateTime = 0;
    }

    initBones(bonesData) {
        this.bones = bonesData.map(bone => ({
            id: bone.id,
            name: bone.name,
            parentIndex: bone.parentIndex,
            position: new Float32Array(bone.position),
            rotation: new Float32Array(bone.rotation),
            scale: new Float32Array(bone.scale),
            restMatrix: new Float32Array(bone.restMatrix),
            inverseBindMatrix: new Float32Array(bone.inverseBindMatrix)
        }));

        this.boneMatrices = new Float32Array(this.bones.length * 16);
        this.postMessage({
            type: 'bonesInitialized',
            boneCount: this.bones.length
        });
    }

    initAnimationClips(clips) {
        this.animationClips = clips.map(clip => ({
            name: clip.name,
            duration: clip.duration,
            tracks: clip.tracks.map(track => ({
                boneIndex: track.boneIndex,
                type: track.type,
                times: new Float32Array(track.times),
                values: new Float32Array(track.values),
                interpolation: track.interpolation || 'LINEAR'
            }))
        }));

        this.postMessage({
            type: 'clipsInitialized',
            clipCount: this.animationClips.length
        });
    }

    playAnimation(clipName, speed = 1) {
        const clip = this.animationClips.find(c => c.name === clipName);
        if (!clip) {
            this.postMessage({ type: 'error', message: `Animation clip "${clipName}" not found` });
            return;
        }

        this.currentAnimation = {
            clip,
            speed,
            startTime: performance.now()
        };
        this.isPlaying = true;
        this.currentTime = 0;
        this.scheduleUpdate();
    }

    pauseAnimation() {
        this.isPlaying = false;
    }

    stopAnimation() {
        this.isPlaying = false;
        this.currentTime = 0;
    }

    scheduleUpdate() {
        if (!this.isPlaying) return;

        const now = performance.now();
        const delta = (now - this.lastUpdateTime) / 1000;
        this.lastUpdateTime = now;

        this.updateAnimation(delta);

        setTimeout(() => this.scheduleUpdate(), 1000 / this.targetFPS);
    }

    updateAnimation(deltaTime) {
        if (!this.currentAnimation || !this.isPlaying) return;

        this.currentTime += deltaTime * this.currentAnimation.speed;
        const duration = this.currentAnimation.clip.duration;
        
        if (this.currentTime > duration) {
            this.currentTime = this.currentTime % duration;
        }

        this.currentAnimation.clip.tracks.forEach(track => {
            this.interpolateTrack(track, this.currentTime);
        });

        this.computeBoneMatrices();

        this.postMessage({
            type: 'boneMatricesUpdated',
            matrices: Array.from(this.boneMatrices),
            currentTime: this.currentTime
        });
    }

    interpolateTrack(track, time) {
        const times = track.times;
        const values = track.values;
        const boneIndex = track.boneIndex;
        const bone = this.bones[boneIndex];

        if (!bone) return;

        let keyIndex = 0;
        for (let i = 0; i < times.length - 1; i++) {
            if (time >= times[i] && time <= times[i + 1]) {
                keyIndex = i;
                break;
            }
        }

        const t0 = times[keyIndex];
        const t1 = times[keyIndex + 1] || t0;
        const alpha = t1 !== t0 ? (time - t0) / (t1 - t0) : 0;

        const valueSize = track.type === 'rotation' ? 4 : 3;
        const v0 = values.slice(keyIndex * valueSize, keyIndex * valueSize + valueSize);
        const v1 = values.slice((keyIndex + 1) * valueSize, (keyIndex + 1) * valueSize + valueSize);

        if (track.interpolation === 'STEP') {
            this.applyTrackValue(bone, track.type, v0);
        } else if (track.interpolation === 'CUBICSPLINE') {
            const result = this.cubicSplineInterpolate(v0, v1, alpha);
            this.applyTrackValue(bone, track.type, result);
        } else {
            const result = this.linearInterpolate(v0, v1, alpha);
            this.applyTrackValue(bone, track.type, result);
        }
    }

    linearInterpolate(v0, v1, alpha) {
        const result = new Float32Array(v0.length);
        for (let i = 0; i < v0.length; i++) {
            result[i] = v0[i] * (1 - alpha) + v1[i] * alpha;
        }
        return result;
    }

    cubicSplineInterpolate(v0, v1, alpha) {
        const t2 = alpha * alpha;
        const t3 = t2 * alpha;
        const h0 = 2 * t3 - 3 * t2 + 1;
        const h1 = -2 * t3 + 3 * t2;
        const h2 = t3 - 2 * t2 + alpha;
        const h3 = t3 - t2;

        const result = new Float32Array(v0.length);
        for (let i = 0; i < v0.length; i++) {
            result[i] = h0 * v0[i] + h1 * v1[i];
        }
        return result;
    }

    applyTrackValue(bone, type, value) {
        if (type === 'position') {
            bone.position.set(value);
        } else if (type === 'rotation') {
            bone.rotation.set(value);
        } else if (type === 'scale') {
            bone.scale.set(value);
        }
    }

    computeBoneMatrices() {
        for (let i = 0; i < this.bones.length; i++) {
            const bone = this.bones[i];
            const localMatrix = this.composeMatrix(
                bone.position,
                bone.rotation,
                bone.scale
            );

            if (bone.parentIndex >= 0) {
                const parentMatrix = this.getBoneMatrix(bone.parentIndex);
                this.multiplyMatrices(localMatrix, parentMatrix);
            }

            const skinMatrix = this.multiplyMatricesNew(localMatrix, bone.inverseBindMatrix);

            for (let j = 0; j < 16; j++) {
                this.boneMatrices[i * 16 + j] = skinMatrix[j];
            }
        }
    }

    getBoneMatrix(index) {
        const offset = index * 16;
        return this.boneMatrices.slice(offset, offset + 16);
    }

    composeMatrix(position, rotation, scale) {
        const [x, y, z, w] = rotation;
        const [sx, sy, sz] = scale;
        const [px, py, pz] = position;

        const x2 = x + x, y2 = y + y, z2 = z + z;
        const xx = x * x2, xy = x * y2, xz = x * z2;
        const yy = y * y2, yz = y * z2, zz = z * z2;
        const wx = w * x2, wy = w * y2, wz = w * z2;

        return new Float32Array([
            (1 - (yy + zz)) * sx,
            (xy + wz) * sx,
            (xz - wy) * sx,
            0,
            (xy - wz) * sy,
            (1 - (xx + zz)) * sy,
            (yz + wx) * sy,
            0,
            (xz + wy) * sz,
            (yz - wx) * sz,
            (1 - (xx + yy)) * sz,
            0,
            px, py, pz, 1
        ]);
    }

    multiplyMatrices(a, b) {
        const result = new Float32Array(16);
        for (let i = 0; i < 4; i++) {
            for (let j = 0; j < 4; j++) {
                let sum = 0;
                for (let k = 0; k < 4; k++) {
                    sum += b[i * 4 + k] * a[k * 4 + j];
                }
                result[i * 4 + j] = sum;
            }
        }
        return result;
    }

    multiplyMatricesNew(a, b) {
        const result = new Float32Array(16);
        for (let i = 0; i < 4; i++) {
            for (let j = 0; j < 4; j++) {
                let sum = 0;
                for (let k = 0; k < 4; k++) {
                    sum += b[i * 4 + k] * a[k * 4 + j];
                }
                result[i * 4 + j] = sum;
            }
        }
        return result;
    }

    postMessage(data) {
        self.postMessage(data);
    }
}

const worker = new BoneAnimationWorker();

self.onmessage = function(e) {
    switch (e.data.type) {
        case 'initBones':
            worker.initBones(e.data.bones);
            break;
        case 'initClips':
            worker.initAnimationClips(e.data.clips);
            break;
        case 'play':
            worker.playAnimation(e.data.clipName, e.data.speed);
            break;
        case 'pause':
            worker.pauseAnimation();
            break;
        case 'stop':
            worker.stopAnimation();
            break;
        case 'setFPS':
            worker.targetFPS = e.data.fps;
            break;
    }
};
