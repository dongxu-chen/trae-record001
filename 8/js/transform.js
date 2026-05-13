const GIZMO_VS = `
attribute vec3 aPosition;
attribute vec3 aColor;

uniform mat4 uModelViewProjection;
varying vec3 vColor;

void main() {
    vColor = aColor;
    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);
    gl_PointSize = 10.0;
}
`;

const GIZMO_FS = `
precision mediump float;
varying vec3 vColor;

void main() {
    gl_FragColor = vec4(vColor, 1.0);
}
`;

const GizmoType = {
    TRANSLATE: 'translate',
    ROTATE: 'rotate',
    SCALE: 'scale'
};

const Axis = {
    X: 'x',
    Y: 'y',
    Z: 'z',
    XY: 'xy',
    YZ: 'yz',
    XZ: 'xz',
    CENTER: 'center'
};

class TransformGizmo {
    constructor(gl) {
        this.gl = gl;
        this.type = GizmoType.TRANSLATE;
        this.targetNode = null;
        this.visible = false;
        this.activeAxis = null;
        this.isDragging = false;
        this.startPosition = { x: 0, y: 0 };
        this.startTransform = null;
        
        this.gizmoScale = 1.0;
        
        this.program = WebGLUtils.createProgram(gl, GIZMO_VS, GIZMO_FS);
        this.aPosition = gl.getAttribLocation(this.program, 'aPosition');
        this.aColor = gl.getAttribLocation(this.program, 'aColor');
        this.uModelViewProjection = gl.getUniformLocation(this.program, 'uModelViewProjection');
        
        this._createGizmoGeometry();
    }

    _createGizmoGeometry() {
        this.translateGizmo = this._createTranslateGizmo();
        this.rotateGizmo = this._createRotateGizmo();
        this.scaleGizmo = this._createScaleGizmo();
    }

    _createTranslateGizmo() {
        const gl = this.gl;
        const axisLength = 2.0;
        const coneHeight = 0.3;
        const coneRadius = 0.08;
        const planeSize = 0.5;
        
        const positions = [];
        const colors = [];
        const indices = [];
        
        const addAxis = (dir, color, indexOffset) => {
            positions.push(0, 0, 0);
            colors.push(...color);
            
            const end = [dir[0] * axisLength, dir[1] * axisLength, dir[2] * axisLength];
            positions.push(...end);
            colors.push(...color);
            
            const segments = 12;
            for (let i = 0; i <= segments; i++) {
                const angle = (i / segments) * Math.PI * 2;
                const perp1 = MathUtils.vec3Normalize(
                    Math.abs(dir[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]
                );
                perp1[0] -= dir[0] * MathUtils.vec3Dot(perp1, dir);
                perp1[1] -= dir[1] * MathUtils.vec3Dot(perp1, dir);
                perp1[2] -= dir[2] * MathUtils.vec3Dot(perp1, dir);
                MathUtils.vec3Normalize(perp1);
                const perp2 = MathUtils.vec3Cross(dir, perp1);
                
                const cosA = Math.cos(angle) * coneRadius;
                const sinA = Math.sin(angle) * coneRadius;
                const basePoint = [
                    end[0] + perp1[0] * cosA + perp2[0] * sinA,
                    end[1] + perp1[1] * cosA + perp2[1] * sinA,
                    end[2] + perp1[2] * cosA + perp2[2] * sinA
                ];
                
                positions.push(...basePoint);
                colors.push(...color);
            }
            
            indices.push(indexOffset, indexOffset + 1);
            
            const coneBaseStart = indexOffset + 2;
            for (let i = 0; i < segments; i++) {
                indices.push(
                    indexOffset + 1,
                    coneBaseStart + i,
                    coneBaseStart + i + 1
                );
                indices.push(
                    coneBaseStart + segments + 1,
                    coneBaseStart + i + 1,
                    coneBaseStart + i
                );
            }
        };
        
        let indexOffset = 0;
        addAxis([1, 0, 0], [1, 0, 0], indexOffset);
        indexOffset += 2 + 13;
        addAxis([0, 1, 0], [0, 1, 0], indexOffset);
        indexOffset += 2 + 13;
        addAxis([0, 0, 1], [0, 0, 1], indexOffset);
        
        const addPlane = (normal, color, offset) => {
            const s = planeSize;
            if (normal[0] === 1) {
                positions.push(s, s, 0); colors.push(...color);
                positions.push(s, -s, 0); colors.push(...color);
                positions.push(s, -s, s); colors.push(...color);
                positions.push(s, s, s); colors.push(...color);
            } else if (normal[1] === 1) {
                positions.push(s, 0, s); colors.push(...color);
                positions.push(-s, 0, s); colors.push(...color);
                positions.push(-s, 0, -s); colors.push(...color);
                positions.push(s, 0, -s); colors.push(...color);
            } else {
                positions.push(s, s, 0); colors.push(...color);
                positions.push(-s, s, 0); colors.push(...color);
                positions.push(-s, -s, 0); colors.push(...color);
                positions.push(s, -s, 0); colors.push(...color);
            }
            
            const base = offset;
            indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
        };
        
        addPlane([1, 0, 0], [0, 1, 1], positions.length / 3);
        addPlane([0, 1, 0], [1, 1, 0], positions.length / 3);
        addPlane([0, 0, 1], [1, 0, 1], positions.length / 3);
        
        return {
            vertexBuffer: WebGLUtils.createBuffer(gl, new Float32Array(positions)),
            colorBuffer: WebGLUtils.createBuffer(gl, new Float32Array(colors)),
            indexBuffer: WebGLUtils.createBuffer(gl, new Uint16Array(indices), gl.ELEMENT_ARRAY_BUFFER),
            vertexCount: positions.length / 3,
            indexCount: indices.length,
            axisData: [
                { axis: Axis.X, startIndex: 0, indexCount: 1 + 24 },
                { axis: Axis.Y, startIndex: 1 + 24, indexCount: 1 + 24 },
                { axis: Axis.Z, startIndex: 2 + 48, indexCount: 1 + 24 },
                { axis: Axis.YZ, startIndex: 3 + 72, indexCount: 6 },
                { axis: Axis.XZ, startIndex: 4 + 72, indexCount: 6 },
                { axis: Axis.XY, startIndex: 5 + 72, indexCount: 6 }
            ]
        };
    }

    _createRotateGizmo() {
        const gl = this.gl;
        const radius = 2.0;
        const segments = 64;
        
        const positions = [];
        const colors = [];
        const indices = [];
        
        const addCircle = (axis, color, indexOffset) => {
            for (let i = 0; i <= segments; i++) {
                const angle = (i / segments) * Math.PI * 2;
                const cosA = Math.cos(angle) * radius;
                const sinA = Math.sin(angle) * radius;
                
                if (axis[0]) {
                    positions.push(0, cosA, sinA);
                } else if (axis[1]) {
                    positions.push(cosA, 0, sinA);
                } else {
                    positions.push(cosA, sinA, 0);
                }
                colors.push(...color);
            }
            
            for (let i = 0; i < segments; i++) {
                indices.push(indexOffset + i, indexOffset + i + 1);
            }
        };
        
        addCircle([1, 0, 0], [1, 0, 0], 0);
        addCircle([0, 1, 0], [0, 1, 0], segments + 1);
        addCircle([0, 0, 1], [0, 0, 1], (segments + 1) * 2);
        
        return {
            vertexBuffer: WebGLUtils.createBuffer(gl, new Float32Array(positions)),
            colorBuffer: WebGLUtils.createBuffer(gl, new Float32Array(colors)),
            indexBuffer: WebGLUtils.createBuffer(gl, new Uint16Array(indices), gl.ELEMENT_ARRAY_BUFFER),
            vertexCount: positions.length / 3,
            indexCount: indices.length,
            axisData: [
                { axis: Axis.X, startIndex: 0, indexCount: segments * 2 },
                { axis: Axis.Y, startIndex: segments * 2, indexCount: segments * 2 },
                { axis: Axis.Z, startIndex: segments * 4, indexCount: segments * 2 }
            ]
        };
    }

    _createScaleGizmo() {
        const gl = this.gl;
        const axisLength = 2.0;
        const cubeSize = 0.15;
        
        const positions = [];
        const colors = [];
        const indices = [];
        
        const addAxis = (dir, color, indexOffset) => {
            positions.push(0, 0, 0);
            colors.push(...color);
            positions.push(dir[0] * axisLength, dir[1] * axisLength, dir[2] * axisLength);
            colors.push(...color);
            
            indices.push(indexOffset, indexOffset + 1);
            
            const end = [dir[0] * axisLength, dir[1] * axisLength, dir[2] * axisLength];
            const cubeStart = indexOffset + 2;
            
            const s = cubeSize;
            const corners = [
                [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
                [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]
            ];
            
            for (const corner of corners) {
                positions.push(
                    end[0] + corner[0],
                    end[1] + corner[1],
                    end[2] + corner[2]
                );
                colors.push(...color);
            }
            
            const faces = [
                [0, 1, 2, 3],
                [5, 4, 7, 6],
                [4, 0, 3, 7],
                [1, 5, 6, 2],
                [3, 2, 6, 7],
                [4, 5, 1, 0]
            ];
            
            for (const face of faces) {
                indices.push(
                    cubeStart + face[0],
                    cubeStart + face[1],
                    cubeStart + face[2],
                    cubeStart + face[0],
                    cubeStart + face[2],
                    cubeStart + face[3]
                );
            }
        };
        
        let indexOffset = 0;
        addAxis([1, 0, 0], [1, 0, 0], indexOffset);
        indexOffset += 2 + 8;
        addAxis([0, 1, 0], [0, 1, 0], indexOffset);
        indexOffset += 2 + 8;
        addAxis([0, 0, 1], [0, 0, 1], indexOffset);
        
        return {
            vertexBuffer: WebGLUtils.createBuffer(gl, new Float32Array(positions)),
            colorBuffer: WebGLUtils.createBuffer(gl, new Float32Array(colors)),
            indexBuffer: WebGLUtils.createBuffer(gl, new Uint16Array(indices), gl.ELEMENT_ARRAY_BUFFER),
            vertexCount: positions.length / 3,
            indexCount: indices.length,
            axisData: [
                { axis: Axis.X, startIndex: 0, indexCount: 2 + 36 },
                { axis: Axis.Y, startIndex: 2 + 36, indexCount: 2 + 36 },
                { axis: Axis.Z, startIndex: 4 + 72, indexCount: 2 + 36 }
            ]
        };
    }

    setTarget(node) {
        this.targetNode = node;
        this.visible = node !== null;
        this.activeAxis = null;
    }

    setType(type) {
        this.type = type;
        this.activeAxis = null;
    }

    _getLocalRotationMatrix(node) {
        if (!node) return MathUtils.mat4Identity();
        
        const q = node.rotation;
        const [x, y, z, w] = q;
        
        const x2 = x + x;
        const y2 = y + y;
        const z2 = z + z;
        const xx = x * x2;
        const xy = x * y2;
        const xz = x * z2;
        const yy = y * y2;
        const yz = y * z2;
        const zz = z * z2;
        const wx = w * x2;
        const wy = w * y2;
        const wz = w * z2;
        
        return [
            1 - (yy + zz), xy - wz, xz + wy, 0,
            xy + wz, 1 - (xx + zz), yz - wx, 0,
            xz - wy, yz + wx, 1 - (xx + yy), 0,
            0, 0, 0, 1
        ];
    }

    getGizmoMatrix(camera) {
        if (!this.targetNode) return MathUtils.mat4Identity();
        
        const worldPos = [
            this.targetNode.worldMatrix[12],
            this.targetNode.worldMatrix[13],
            this.targetNode.worldMatrix[14]
        ];
        
        const distance = MathUtils.vec3Length(
            MathUtils.vec3Sub(worldPos, camera.position)
        );
        
        const scale = distance * 0.003 * 150;
        
        let matrix = MathUtils.mat4Identity();
        matrix = MathUtils.mat4Translate(matrix, worldPos);
        
        if (this.type === GizmoType.ROTATE) {
            const rotMatrix = this._getLocalRotationMatrix(this.targetNode);
            matrix = MathUtils.mat4Multiply(matrix, rotMatrix);
        }
        
        matrix = MathUtils.mat4Scale(matrix, [scale, scale, scale]);
        
        return matrix;
    }

    render(camera) {
        if (!this.visible || !this.targetNode) return;
        
        const gl = this.gl;
        const gizmoMatrix = this.getGizmoMatrix(camera);
        const mvp = MathUtils.mat4Multiply(camera.viewProjection, gizmoMatrix);
        
        gl.useProgram(this.program);
        gl.uniformMatrix4fv(this.uModelViewProjection, false, new Float32Array(mvp));
        
        let gizmo;
        switch (this.type) {
            case GizmoType.TRANSLATE:
                gizmo = this.translateGizmo;
                break;
            case GizmoType.ROTATE:
                gizmo = this.rotateGizmo;
                break;
            case GizmoType.SCALE:
                gizmo = this.scaleGizmo;
                break;
            default:
                gizmo = this.translateGizmo;
        }
        
        gl.bindBuffer(gl.ARRAY_BUFFER, gizmo.vertexBuffer);
        gl.enableVertexAttribArray(this.aPosition);
        gl.vertexAttribPointer(this.aPosition, 3, gl.FLOAT, false, 0, 0);
        
        gl.bindBuffer(gl.ARRAY_BUFFER, gizmo.colorBuffer);
        gl.enableVertexAttribArray(this.aColor);
        gl.vertexAttribPointer(this.aColor, 3, gl.FLOAT, false, 0, 0);
        
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gizmo.indexBuffer);
        
        gl.disable(gl.DEPTH_TEST);
        gl.disable(gl.CULL_FACE);
        
        for (const axisData of gizmo.axisData) {
            gl.drawElements(gl.LINES, axisData.indexCount, gl.UNSIGNED_SHORT, axisData.startIndex * 2);
        }
        
        for (const axisData of gizmo.axisData) {
            if (axisData.indexCount > 2) {
                gl.drawElements(gl.TRIANGLES, axisData.indexCount - 2, gl.UNSIGNED_SHORT, (axisData.startIndex + 2) * 2);
            }
        }
        
        gl.enable(gl.DEPTH_TEST);
    }

    _getScreenGizmoAxes(camera) {
        if (!this.targetNode) return [];
        
        const gizmoMatrix = this.getGizmoMatrix(camera);
        const mvp = MathUtils.mat4Multiply(camera.viewProjection, gizmoMatrix);
        
        const origin = MathUtils.mat4TransformPoint(mvp, [0, 0, 0]);
        const axes = [];
        
        const axisVectors = [
            { axis: Axis.X, dir: [1, 0, 0], color: [1, 0, 0] },
            { axis: Axis.Y, dir: [0, 1, 0], color: [0, 1, 0] },
            { axis: Axis.Z, dir: [0, 0, 1], color: [0, 0, 1] }
        ];
        
        for (const axisData of axisVectors) {
            const end = MathUtils.mat4TransformPoint(mvp, axisData.dir);
            const dir = [end[0] - origin[0], end[1] - origin[1]];
            const len = Math.sqrt(dir[0] * dir[0] + dir[1] * dir[1]);
            if (len > 0) {
                dir[0] /= len;
                dir[1] /= len;
            }
            axes.push({
                axis: axisData.axis,
                dir,
                origin,
                screenDir: dir
            });
        }
        
        return axes;
    }

    hitTest(camera, x, y, viewportWidth, viewportHeight) {
        if (!this.visible || !this.targetNode) return null;
        
        const gizmoMatrix = this.getGizmoMatrix(camera);
        const mvp = MathUtils.mat4Multiply(camera.viewProjection, gizmoMatrix);
        
        const screenOrigin = MathUtils.mat4TransformPoint(mvp, [0, 0, 0]);
        
        const ndcX = (x / viewportWidth) * 2 - 1;
        const ndcY = 1 - (y / viewportHeight) * 2;
        
        const mouseDir = [
            ndcX - screenOrigin[0],
            ndcY - screenOrigin[1]
        ];
        const mouseDist = Math.sqrt(mouseDir[0] * mouseDir[0] + mouseDir[1] * mouseDir[1]);
        
        if (mouseDist < 0.02 || mouseDist > 0.5) {
            return null;
        }
        
        const axes = this._getScreenGizmoAxes(camera);
        let bestAxis = null;
        let bestScore = Infinity;
        
        for (const axis of axes) {
            const axisDir = axis.screenDir;
            const len1 = mouseDist;
            const len2 = 1;
            
            if (len1 === 0 || len2 === 0) continue;
            
            const dot = mouseDir[0] * axisDir[0] + mouseDir[1] * axisDir[1];
            const cosAngle = Math.max(-1, Math.min(1, dot / (len1 * len2)));
            const angleDiff = Math.acos(cosAngle);
            
            const threshold = this.type === GizmoType.ROTATE ? 0.8 : 0.5;
            
            if (angleDiff < threshold && angleDiff < bestScore) {
                bestScore = angleDiff;
                bestAxis = axis.axis;
            }
        }
        
        if (this.type !== GizmoType.ROTATE && bestAxis) {
            const planeAxes = {
                [Axis.X]: Axis.YZ,
                [Axis.Y]: Axis.XZ,
                [Axis.Z]: Axis.XY
            };
        }
        
        return bestAxis;
    }

    startDrag(x, y, camera, viewportWidth, viewportHeight) {
        if (!this.visible || !this.targetNode) return false;
        
        this.activeAxis = this.hitTest(camera, x, y, viewportWidth, viewportHeight);
        
        if (this.activeAxis) {
            this.isDragging = true;
            this.startPosition = { x, y };
            this.startTransform = {
                translation: [...this.targetNode.translation],
                rotation: [...this.targetNode.rotation],
                scale: [...this.targetNode.scale]
            };
            return true;
        }
        
        return false;
    }

    updateDrag(x, y, camera, viewportWidth, viewportHeight) {
        if (!this.isDragging || !this.targetNode || !this.activeAxis) return;
        
        const dx = x - this.startPosition.x;
        const dy = y - this.startPosition.y;
        
        switch (this.type) {
            case GizmoType.TRANSLATE:
                this._updateTranslate(dx, dy, camera);
                break;
            case GizmoType.ROTATE:
                this._updateRotate(dx, dy);
                break;
            case GizmoType.SCALE:
                this._updateScale(dx, dy);
                break;
        }
        
        this.targetNode.updateMatrix();
        this.startPosition = { x, y };
    }

    _updateTranslate(dx, dy, camera) {
        const sensitivity = 0.02;
        let translate = [0, 0, 0];
        
        const worldPos = [
            this.targetNode.worldMatrix[12],
            this.targetNode.worldMatrix[13],
            this.targetNode.worldMatrix[14]
        ];
        
        const distance = MathUtils.vec3Length(
            MathUtils.vec3Sub(worldPos, camera.position)
        );
        
        const amount = sensitivity * distance;
        
        switch (this.activeAxis) {
            case Axis.X:
                translate = [dx * amount, 0, 0];
                break;
            case Axis.Y:
                translate = [0, -dy * amount, 0];
                break;
            case Axis.Z:
                translate = [0, 0, dx * amount];
                break;
            case Axis.XY:
                translate = [dx * amount, -dy * amount, 0];
                break;
            case Axis.XZ:
                translate = [dx * amount, 0, dy * amount];
                break;
            case Axis.YZ:
                translate = [0, -dy * amount, dx * amount];
                break;
            default:
                translate = [dx * amount, -dy * amount, 0];
        }
        
        this.targetNode.translation = MathUtils.vec3Add(
            this.targetNode.translation,
            translate
        );
    }

    _updateRotate(dx, dy) {
        const sensitivity = 0.01;
        const rotateAmount = dx * sensitivity;
        
        let axis;
        switch (this.activeAxis) {
            case Axis.X: axis = [1, 0, 0]; break;
            case Axis.Y: axis = [0, 1, 0]; break;
            case Axis.Z: axis = [0, 0, 1]; break;
            default: axis = [0, 1, 0];
        }
        
        const angle = dx * sensitivity;
        const halfAngle = angle / 2;
        const s = Math.sin(halfAngle);
        const c = Math.cos(halfAngle);
        
        const deltaQuat = [axis[0] * s, axis[1] * s, axis[2] * s, c];
        
        this.targetNode.rotation = this._multiplyQuaternions(deltaQuat, this.targetNode.rotation);
    }

    _multiplyQuaternions(q1, q2) {
        const [x1, y1, z1, w1] = q1;
        const [x2, y2, z2, w2] = q2;
        
        return [
            x1 * w2 + y1 * z2 - z1 * y2 + w1 * x2,
            -x1 * z2 + y1 * w2 + z1 * x2 + w1 * y2,
            x1 * y2 - y1 * x2 + z1 * w2 + w1 * z2,
            -x1 * x2 - y1 * y2 - z1 * z2 + w1 * w2
        ];
    }

    _updateScale(dx, dy) {
        const sensitivity = 0.005;
        let scale = [1, 1, 1];
        
        switch (this.activeAxis) {
            case Axis.X:
                scale = [1 + dx * sensitivity, 1, 1];
                break;
            case Axis.Y:
                scale = [1, 1 - dy * sensitivity, 1];
                break;
            case Axis.Z:
                scale = [1, 1, 1 + dx * sensitivity];
                break;
            default:
                const factor = 1 + (dx + dy) * sensitivity * 0.5;
                scale = [factor, factor, factor];
        }
        
        this.targetNode.scale = [
            this.targetNode.scale[0] * scale[0],
            this.targetNode.scale[1] * scale[1],
            this.targetNode.scale[2] * scale[2]
        ];
    }

    endDrag() {
        this.isDragging = false;
        this.activeAxis = null;
    }
}
