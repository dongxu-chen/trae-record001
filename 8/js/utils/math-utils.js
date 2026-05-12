const MathUtils = {
    degToRad(deg) {
        return deg * Math.PI / 180;
    },

    radToDeg(rad) {
        return rad * 180 / Math.PI;
    },

    clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    },

    lerp(a, b, t) {
        return a + (b - a) * t;
    },

    vec3Create(x = 0, y = 0, z = 0) {
        return [x, y, z];
    },

    vec3Copy(a) {
        return [a[0], a[1], a[2]];
    },

    vec3Add(a, b) {
        return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
    },

    vec3Sub(a, b) {
        return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    },

    vec3Scale(a, s) {
        return [a[0] * s, a[1] * s, a[2] * s];
    },

    vec3Dot(a, b) {
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    },

    vec3Cross(a, b) {
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]
        ];
    },

    vec3Length(a) {
        return Math.sqrt(this.vec3Dot(a, a));
    },

    vec3Normalize(a) {
        const len = this.vec3Length(a);
        if (len === 0) return [0, 0, 0];
        return this.vec3Scale(a, 1 / len);
    },

    vec4Create(x = 0, y = 0, z = 0, w = 1) {
        return [x, y, z, w];
    },

    mat4Create() {
        return [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ];
    },

    mat4Identity() {
        return this.mat4Create();
    },

    mat4Copy(m) {
        return m.slice();
    },

    mat4Multiply(a, b) {
        const result = new Array(16);
        for (let i = 0; i < 4; i++) {
            for (let j = 0; j < 4; j++) {
                result[i * 4 + j] = 
                    a[i * 4 + 0] * b[0 * 4 + j] +
                    a[i * 4 + 1] * b[1 * 4 + j] +
                    a[i * 4 + 2] * b[2 * 4 + j] +
                    a[i * 4 + 3] * b[3 * 4 + j];
            }
        }
        return result;
    },

    mat4Translate(m, v) {
        const result = this.mat4Copy(m);
        result[12] = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
        result[13] = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
        result[14] = m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14];
        result[15] = m[3] * v[0] + m[7] * v[1] + m[11] * v[2] + m[15];
        return result;
    },

    mat4Scale(m, v) {
        const result = new Array(16);
        result[0] = m[0] * v[0]; result[1] = m[1] * v[0]; result[2] = m[2] * v[0]; result[3] = m[3] * v[0];
        result[4] = m[4] * v[1]; result[5] = m[5] * v[1]; result[6] = m[6] * v[1]; result[7] = m[7] * v[1];
        result[8] = m[8] * v[2]; result[9] = m[9] * v[2]; result[10] = m[10] * v[2]; result[11] = m[11] * v[2];
        result[12] = m[12]; result[13] = m[13]; result[14] = m[14]; result[15] = m[15];
        return result;
    },

    mat4RotateX(m, angle) {
        const c = Math.cos(angle);
        const s = Math.sin(angle);
        const rot = [
            1, 0, 0, 0,
            0, c, s, 0,
            0, -s, c, 0,
            0, 0, 0, 1
        ];
        return this.mat4Multiply(m, rot);
    },

    mat4RotateY(m, angle) {
        const c = Math.cos(angle);
        const s = Math.sin(angle);
        const rot = [
            c, 0, -s, 0,
            0, 1, 0, 0,
            s, 0, c, 0,
            0, 0, 0, 1
        ];
        return this.mat4Multiply(m, rot);
    },

    mat4RotateZ(m, angle) {
        const c = Math.cos(angle);
        const s = Math.sin(angle);
        const rot = [
            c, s, 0, 0,
            -s, c, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ];
        return this.mat4Multiply(m, rot);
    },

    mat4RotationFromEuler(x, y, z) {
        let m = this.mat4Identity();
        m = this.mat4RotateX(m, x);
        m = this.mat4RotateY(m, y);
        m = this.mat4RotateZ(m, z);
        return m;
    },

    mat4Inverse(m) {
        const result = new Array(16);
        const inv = new Array(16);
        
        inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + 
                 m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
        inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - 
                 m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
        inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + 
                 m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
        inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - 
                  m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
        inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - 
                 m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
        inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + 
                 m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
        inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - 
                 m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
        inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + 
                  m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
        inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + 
                 m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
        inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - 
                 m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
        inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + 
                  m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
        inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - 
                  m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
        inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - 
                 m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
        inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + 
                 m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
        inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - 
                  m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
        inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + 
                  m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5];

        let det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
        if (det === 0) return this.mat4Identity();

        det = 1.0 / det;
        for (let i = 0; i < 16; i++) {
            result[i] = inv[i] * det;
        }

        return result;
    },

    mat4Transpose(m) {
        return [
            m[0], m[4], m[8], m[12],
            m[1], m[5], m[9], m[13],
            m[2], m[6], m[10], m[14],
            m[3], m[7], m[11], m[15]
        ];
    },

    perspective(fov, aspect, near, far) {
        const f = 1.0 / Math.tan(fov / 2);
        const nf = 1 / (near - far);
        return [
            f / aspect, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (far + near) * nf, -1,
            0, 0, 2 * far * near * nf, 0
        ];
    },

    lookAt(eye, center, up) {
        const z = this.vec3Normalize(this.vec3Sub(eye, center));
        const x = this.vec3Normalize(this.vec3Cross(up, z));
        const y = this.vec3Cross(z, x);
        
        return [
            x[0], y[0], z[0], 0,
            x[1], y[1], z[1], 0,
            x[2], y[2], z[2], 0,
            -this.vec3Dot(x, eye), -this.vec3Dot(y, eye), -this.vec3Dot(z, eye), 1
        ];
    },

    mat4TransformPoint(m, p) {
        const x = p[0], y = p[1], z = p[2];
        const w = m[3] * x + m[7] * y + m[11] * z + m[15];
        const wInv = 1 / w;
        return [
            (m[0] * x + m[4] * y + m[8] * z + m[12]) * wInv,
            (m[1] * x + m[5] * y + m[9] * z + m[13]) * wInv,
            (m[2] * x + m[6] * y + m[10] * z + m[14]) * wInv
        ];
    },

    decomposeTRS(m) {
        const translation = [m[12], m[13], m[14]];
        
        const sx = Math.sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2]);
        const sy = Math.sqrt(m[4] * m[4] + m[5] * m[5] + m[6] * m[6]);
        const sz = Math.sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10]);
        const scale = [sx, sy, sz];
        
        const rotation = this.mat4Identity();
        for (let i = 0; i < 3; i++) {
            rotation[i] = m[i] / sx;
            rotation[i + 4] = m[i + 4] / sy;
            rotation[i + 8] = m[i + 8] / sz;
        }
        
        const syz = rotation[6];
        let rx, ry, rz;
        
        if (syz !== 1 && syz !== -1) {
            rx = Math.asin(-syz);
            ry = Math.atan2(rotation[2], rotation[10]);
            rz = Math.atan2(rotation[4], rotation[5]);
        } else {
            rz = 0;
            if (syz === -1) {
                rx = Math.PI / 2;
                ry = Math.atan2(rotation[1], rotation[5]);
            } else {
                rx = -Math.PI / 2;
                ry = Math.atan2(-rotation[1], rotation[5]);
            }
        }
        
        const euler = [rx, ry, rz];
        
        return { translation, rotation: euler, scale };
    }
};