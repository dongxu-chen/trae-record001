const PICK_VS = `
attribute vec3 aPosition;
uniform mat4 uModelViewProjection;

void main() {
    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);
}
`;

const PICK_FS = `
precision mediump float;
uniform vec3 uPickColor;

void main() {
    gl_FragColor = vec4(uPickColor, 1.0);
}
`;

class Picker {
    constructor(gl) {
        this.gl = gl;
        this.program = WebGLUtils.createProgram(gl, PICK_VS, PICK_FS);
        
        this.aPosition = gl.getAttribLocation(this.program, 'aPosition');
        this.uModelViewProjection = gl.getUniformLocation(this.program, 'uModelViewProjection');
        this.uPickColor = gl.getUniformLocation(this.program, 'uPickColor');
        
        this.width = 1;
        this.height = 1;
        this.framebuffer = null;
        
        this.pickColorMap = new Map();
        this.nextColorId = 1;
        
        this._lastCameraHash = null;
        this._lastSceneHash = null;
        this._cachedPickResult = null;
        this._cachedRectPickResults = new Map();
    }

    resize(width, height) {
        this.width = width;
        this.height = height;
        if (this.framebuffer) {
            WebGLUtils.resizeFramebuffer(this.gl, this.framebuffer, width, height);
        } else {
            this.framebuffer = WebGLUtils.createFramebuffer(this.gl, width, height);
        }
        this._invalidateCache();
    }

    _invalidateCache() {
        this._lastCameraHash = null;
        this._lastSceneHash = null;
        this._cachedPickResult = null;
        this._cachedRectPickResults.clear();
    }

    _hashCamera(camera) {
        return `${camera.position[0].toFixed(2)},${camera.position[1].toFixed(2)},${camera.position[2].toFixed(2)},${camera.target[0].toFixed(2)},${camera.target[1].toFixed(2)},${camera.target[2].toFixed(2)}`;
    }

    _hashScene(sceneGraph) {
        let hash = '';
        sceneGraph.traverse(node => {
            hash += `${node.id}:${node.worldMatrix[12].toFixed(2)},${node.worldMatrix[13].toFixed(2)},${node.worldMatrix[14].toFixed(2)};`;
        });
        return hash;
    }

    getUniqueColor(nodeId) {
        const id = this.nextColorId++;
        const r = ((id >> 16) & 0xFF) / 255.0;
        const g = ((id >> 8) & 0xFF) / 255.0;
        const b = (id & 0xFF) / 255.0;
        this.pickColorMap.set(id, nodeId);
        return [r, g, b];
    }

    idFromColor(r, g, b) {
        return (r << 16) | (g << 8) | b;
    }

    clearColorMap() {
        this.pickColorMap.clear();
        this.nextColorId = 1;
    }

    pick(sceneGraph, camera, x, y) {
        const gl = this.gl;
        
        if (!this.framebuffer) {
            this.framebuffer = WebGLUtils.createFramebuffer(gl, this.width, this.height);
        }

        const cameraHash = this._hashCamera(camera);
        const sceneHash = this._hashScene(sceneGraph);
        
        if (this._lastCameraHash !== cameraHash || this._lastSceneHash !== sceneHash) {
            this._renderPickPass(sceneGraph, camera);
            this._lastCameraHash = cameraHash;
            this._lastSceneHash = sceneHash;
        }

        const pixelX = Math.floor(Math.max(0, Math.min(x, this.width - 1)));
        const pixelY = this.height - Math.floor(Math.max(0, Math.min(y, this.height - 1))) - 1;
        
        const readPixels = new Uint8Array(4);
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer.framebuffer);
        gl.readPixels(pixelX, pixelY, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, readPixels);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        
        const colorId = this.idFromColor(readPixels[0], readPixels[1], readPixels[2]);

        if (colorId === 0) {
            return null;
        }
        
        const nodeId = this.pickColorMap.get(colorId);
        if (nodeId === undefined) {
            return null;
        }
        
        return sceneGraph.getNodeById(nodeId);
    }

    _renderPickPass(sceneGraph, camera) {
        const gl = this.gl;
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer.framebuffer);
        gl.viewport(0, 0, this.width, this.height);
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.DEPTH_TEST);
        gl.enable(gl.CULL_FACE);

        gl.useProgram(this.program);
        
        this.clearColorMap();
        
        const meshes = sceneGraph.getPickableMeshes();
        
        let currentMesh = null;
        let currentMaterial = null;
        
        for (const { node, mesh, worldMatrix } of meshes) {
            const pickColor = this.getUniqueColor(node.id);
            const mvp = MathUtils.mat4Multiply(camera.viewProjection, worldMatrix);
            
            gl.uniformMatrix4fv(this.uModelViewProjection, false, new Float32Array(mvp));
            gl.uniform3fv(this.uPickColor, pickColor);
            
            for (const primitive of mesh.primitives) {
                if (primitive.vertexBuffer !== currentMesh) {
                    gl.bindBuffer(gl.ARRAY_BUFFER, primitive.vertexBuffer);
                    gl.enableVertexAttribArray(this.aPosition);
                    gl.vertexAttribPointer(this.aPosition, 3, gl.FLOAT, false, 0, 0);
                    currentMesh = primitive.vertexBuffer;
                }
                
                if (primitive.indexBuffer) {
                    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, primitive.indexBuffer);
                    gl.drawElements(primitive.drawMode, primitive.indexCount, gl.UNSIGNED_SHORT, 0);
                } else {
                    gl.drawArrays(primitive.drawMode, 0, primitive.vertexCount);
                }
            }
        }
    }

    pickRect(sceneGraph, camera, x1, y1, x2, y2) {
        const minX = Math.min(x1, x2);
        const maxX = Math.max(x1, x2);
        const minY = Math.min(y1, y2);
        const maxY = Math.max(y1, y2);

        const gl = this.gl;
        const cameraHash = this._hashCamera(camera);
        const sceneHash = this._hashScene(sceneGraph);
        
        if (this._lastCameraHash !== cameraHash || this._lastSceneHash !== sceneHash) {
            this._renderPickPass(sceneGraph, camera);
            this._lastCameraHash = cameraHash;
            this._lastSceneHash = sceneHash;
        }

        const width = Math.max(1, Math.floor(maxX - minX + 1));
        const height = Math.max(1, Math.floor(maxY - minY + 1));
        
        const clampedMinX = Math.max(0, Math.min(minX, this.width - 1));
        const clampedMaxX = Math.max(0, Math.min(maxX, this.width - 1));
        const clampedMinY = Math.max(0, Math.min(minY, this.height - 1));
        const clampedMaxY = Math.max(0, Math.min(maxY, this.height - 1));
        
        const clampedWidth = Math.max(1, clampedMaxX - clampedMinX + 1);
        const clampedHeight = Math.max(1, clampedMaxY - clampedMinY + 1);
        
        const actualWidth = Math.min(64, clampedWidth);
        const actualHeight = Math.min(64, clampedHeight);
        
        const stepX = clampedWidth / actualWidth;
        const stepY = clampedHeight / actualHeight;
        
        const pixels = new Uint8Array(actualWidth * actualHeight * 4);
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer.framebuffer);
        
        const readX = Math.floor(clampedMinX);
        const readY = this.height - Math.floor(clampedMaxY) - 1;
        
        for (let py = 0; py < actualHeight; py++) {
            for (let px = 0; px < actualWidth; px++) {
                const sx = Math.floor(clampedMinX + px * stepX);
                const sy = Math.floor(clampedMinY + py * stepY);
                const syFlipped = this.height - sy - 1;
                
                gl.readPixels(sx, syFlipped, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, 
                    new Uint8Array(pixels.buffer, (py * actualWidth + px) * 4, 4));
            }
        }
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        
        const pickedIds = new Set();
        const results = [];
        
        for (let i = 0; i < pixels.length; i += 4) {
            const colorId = this.idFromColor(pixels[i], pixels[i + 1], pixels[i + 2]);
            
            if (colorId === 0) continue;
            
            const nodeId = this.pickColorMap.get(colorId);
            if (nodeId === undefined || pickedIds.has(nodeId)) continue;
            
            pickedIds.add(nodeId);
            const node = sceneGraph.getNodeById(nodeId);
            if (node) {
                results.push(node);
            }
        }
        
        return results;
    }
}
