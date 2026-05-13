import * as THREE from 'three';

const VoxelShader = {
    uniforms: {
        volumeData: { value: null },
        volumeSize: { value: new THREE.Vector3(64, 64, 64) },
        volumeSpacing: { value: new THREE.Vector3(1, 1, 1) },
        volumeOrigin: { value: new THREE.Vector3(0, 0, 0) },
        isoValue: { value: 0.5 },
        color: { value: new THREE.Color(0x00ff88) },
        opacity: { value: 0.8 },
        lightPos: { value: new THREE.Vector3(1, 1, 1) },
        cameraPos: { value: new THREE.Vector3(0, 0, 10) },
        maxSteps: { value: 128 },
        stepSize: { value: 0.015625 }
    },

    vertexShader: `
        varying vec3 vLocalPos;
        varying vec3 vWorldPos;

        void main() {
            vLocalPos = position;
            vec4 worldPos = modelMatrix * vec4(position, 1.0);
            vWorldPos = worldPos.xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,

    fragmentShader: `
        uniform sampler3D volumeData;
        uniform vec3 volumeSize;
        uniform vec3 volumeSpacing;
        uniform vec3 volumeOrigin;
        uniform float isoValue;
        uniform vec3 color;
        uniform float opacity;
        uniform vec3 lightPos;
        uniform vec3 cameraPos;
        uniform int maxSteps;
        uniform float stepSize;

        varying vec3 vLocalPos;
        varying vec3 vWorldPos;

        float sampleVolume(vec3 pos) {
            vec3 uvw = (pos - volumeOrigin) / (volumeSize * volumeSpacing);
            uvw = clamp(uvw, 0.0, 1.0);
            return texture(volumeData, uvw).r;
        }

        vec3 computeGradient(vec3 pos) {
            float delta = 0.01;
            float dx = sampleVolume(pos + vec3(delta, 0, 0)) - sampleVolume(pos - vec3(delta, 0, 0));
            float dy = sampleVolume(pos + vec3(0, delta, 0)) - sampleVolume(pos - vec3(0, delta, 0));
            float dz = sampleVolume(pos + vec3(0, 0, delta)) - sampleVolume(pos - vec3(0, 0, delta));
            return normalize(vec3(dx, dy, dz));
        }

        vec3 computeLighting(vec3 pos, vec3 normal) {
            vec3 lightDir = normalize(lightPos - pos);
            vec3 viewDir = normalize(cameraPos - pos);
            vec3 halfDir = normalize(lightDir + viewDir);

            float ambient = 0.3;
            float diffuse = max(dot(normal, lightDir), 0.0) * 0.6;
            float specular = pow(max(dot(normal, halfDir), 0.0), 32.0) * 0.3;

            return vec3(ambient + diffuse + specular);
        }

        float findIsoSurface(vec3 rayStart, vec3 rayDir, float maxDist) {
            float t = 0.0;
            float prevDensity = sampleVolume(rayStart);

            for (int i = 0; i < 256; i++) {
                if (i >= maxSteps) break;
                if (t >= maxDist) break;

                vec3 pos = rayStart + rayDir * t;
                float density = sampleVolume(pos);

                if ((prevDensity - isoValue) * (density - isoValue) < 0.0) {
                    float tLow = t - stepSize;
                    float tHigh = t;

                    for (int j = 0; j < 8; j++) {
                        float tMid = (tLow + tHigh) * 0.5;
                        vec3 posMid = rayStart + rayDir * tMid;
                        float dMid = sampleVolume(posMid);

                        if ((prevDensity - isoValue) * (dMid - isoValue) < 0.0) {
                            tHigh = tMid;
                        } else {
                            tLow = tMid;
                        }
                    }

                    return (tLow + tHigh) * 0.5;
                }

                prevDensity = density;
                t += stepSize;
            }

            return -1.0;
        }

        void main() {
            vec3 localRayStart = vLocalPos;
            vec3 worldRayStart = vWorldPos;
            vec3 worldRayDir = normalize(vWorldPos - cameraPos);

            vec3 minBounds = volumeOrigin;
            vec3 maxBounds = volumeOrigin + volumeSize * volumeSpacing;

            vec3 invDir = 1.0 / worldRayDir;
            vec3 tMin = (minBounds - worldRayStart) * invDir;
            vec3 tMax = (maxBounds - worldRayStart) * invDir;

            vec3 tNear = min(tMin, tMax);
            vec3 tFar = max(tMin, tMax);

            float tEnter = max(max(tNear.x, tNear.y), tNear.z);
            float tExit = min(min(tFar.x, tFar.y), tFar.z);

            if (tEnter >= tExit || tExit < 0.0) {
                discard;
            }

            tEnter = max(tEnter, 0.0);
            vec3 enterPoint = worldRayStart + worldRayDir * tEnter;

            float hitDist = findIsoSurface(enterPoint, worldRayDir, tExit - tEnter);

            if (hitDist < 0.0) {
                discard;
            }

            vec3 hitPoint = enterPoint + worldRayDir * hitDist;
            vec3 normal = computeGradient(hitPoint);

            if (dot(normal, -worldRayDir) < 0.0) {
                normal = -normal;
            }

            vec3 lighting = computeLighting(hitPoint, normal);
            vec3 finalColor = color * lighting;

            gl_FragColor = vec4(finalColor, opacity);
        }
    `
};

const SliceShader = {
    uniforms: {
        volumeData: { value: null },
        volumeSize: { value: new THREE.Vector3(64, 64, 64) },
        volumeSpacing: { value: new THREE.Vector3(1, 1, 1) },
        volumeOrigin: { value: new THREE.Vector3(0, 0, 0) },
        sliceAxis: { value: 2 },
        sliceIndex: { value: 32 },
        colorMap: { value: 0 }
    },

    vertexShader: `
        varying vec2 vUv;

        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,

    fragmentShader: `
        uniform sampler3D volumeData;
        uniform vec3 volumeSize;
        uniform vec3 volumeSpacing;
        uniform vec3 volumeOrigin;
        uniform int sliceAxis;
        uniform float sliceIndex;
        uniform int colorMap;

        varying vec2 vUv;

        vec3 jetColormap(float value) {
            vec3 c;
            if (value < 0.25) {
                c = vec3(0.0, 4.0 * value, 1.0);
            } else if (value < 0.5) {
                c = vec3(0.0, 1.0, 1.0 - 4.0 * (value - 0.25));
            } else if (value < 0.75) {
                c = vec3(4.0 * (value - 0.5), 1.0, 0.0);
            } else {
                c = vec3(1.0, 1.0 - 4.0 * (value - 0.75), 0.0);
            }
            return c;
        }

        vec3 grayscaleColormap(float value) {
            return vec3(value);
        }

        vec3 hotColormap(float value) {
            vec3 c;
            if (value < 0.33) {
                c = vec3(3.0 * value, 0.0, 0.0);
            } else if (value < 0.66) {
                c = vec3(1.0, 3.0 * (value - 0.33), 0.0);
            } else {
                c = vec3(1.0, 1.0, 3.0 * (value - 0.66));
            }
            return c;
        }

        void main() {
            vec3 uvw;

            if (sliceAxis == 0) {
                uvw = vec3(sliceIndex / volumeSize.x, vUv.x, vUv.y);
            } else if (sliceAxis == 1) {
                uvw = vec3(vUv.x, sliceIndex / volumeSize.y, vUv.y);
            } else {
                uvw = vec3(vUv.x, vUv.y, sliceIndex / volumeSize.z);
            }

            uvw = clamp(uvw, 0.0, 1.0);
            float density = texture(volumeData, uvw).r;

            vec3 color;
            if (colorMap == 0) {
                color = grayscaleColormap(density);
            } else if (colorMap == 1) {
                color = jetColormap(density);
            } else {
                color = hotColormap(density);
            }

            gl_FragColor = vec4(color, 1.0);
        }
    `
};

export { VoxelShader, SliceShader };
