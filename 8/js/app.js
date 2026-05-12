const SCENE_VS = `
attribute vec3 aPosition;
attribute vec3 aNormal;

uniform mat4 uModelMatrix;
uniform mat4 uViewProjection;
uniform mat3 uNormalMatrix;

varying vec3 vNormal;
varying vec3 vWorldPos;

void main() {
    vec4 worldPos = uModelMatrix * vec4(aPosition, 1.0);
    vWorldPos = worldPos.xyz;
    vNormal = uNormalMatrix * aNormal;
    gl_Position = uViewProjection * worldPos;
}
`;

const SCENE_FS = `
precision mediump float;

varying vec3 vNormal;
varying vec3 vWorldPos;

uniform vec4 uBaseColor;
uniform vec3 uLightPos;
uniform vec3 uCameraPos;
uniform float uMetallic;
uniform float uRoughness;
uniform vec3 uEmissive;
uniform bool uSelected;

void main() {
    vec3 normal = normalize(vNormal);
    vec3 lightDir = normalize(uLightPos - vWorldPos);
    vec3 viewDir = normalize(uCameraPos - vWorldPos);
    vec3 halfDir = normalize(lightDir + viewDir);
    
    float diff = max(dot(normal, lightDir), 0.0);
    float shininess = mix(32.0, 128.0, 1.0 - uRoughness);
    float spec = pow(max(dot(normal, halfDir), 0.0), shininess);
    
    vec3 baseColor = uBaseColor.rgb;
    
    vec3 F0 = mix(vec3(0.04), baseColor, uMetallic);
    float specularStrength = uMetallic + (1.0 - uMetallic) * uRoughness;
    
    vec3 ambient = baseColor * 0.3;
    vec3 diffuse = baseColor * diff * 0.7 * (1.0 - uMetallic);
    vec3 specular = F0 * spec * 0.5 * specularStrength;
    
    vec3 finalColor = ambient + diffuse + specular + uEmissive;
    
    if (uSelected) {
        finalColor = mix(finalColor, vec3(1.0, 0.8, 0.2), 0.4);
    }
    
    gl_FragColor = vec4(finalColor, uBaseColor.a);
}
`;

class Camera {
    constructor() {
        this.position = [5, 5, 5];
        this.target = [0, 0, 0];
        this.up = [0, 1, 0];
        this.fov = Math.PI / 4;
        this.near = 0.1;
        this.far = 1000;
        this.aspect = 1;
        
        this.viewMatrix = MathUtils.mat4Identity();
        this.projectionMatrix = MathUtils.mat4Identity();
        this.viewProjection = MathUtils.mat4Identity();
        
        this.theta = Math.PI / 4;
        this.phi = Math.PI / 4;
        this.radius = 8.66;
        
        this.updatePosition();
    }

    updatePosition() {
        const x = this.radius * Math.sin(this.phi) * Math.cos(this.theta);
        const y = this.radius * Math.cos(this.phi);
        const z = this.radius * Math.sin(this.phi) * Math.sin(this.theta);
        
        this.position = [
            this.target[0] + x,
            this.target[1] + y,
            this.target[2] + z
        ];
        
        this.update();
    }

    update() {
        this.viewMatrix = MathUtils.lookAt(this.position, this.target, this.up);
        this.projectionMatrix = MathUtils.perspective(this.fov, this.aspect, this.near, this.far);
        this.viewProjection = MathUtils.mat4Multiply(this.projectionMatrix, this.viewMatrix);
    }

    setAspect(aspect) {
        this.aspect = aspect;
        this.update();
    }

    orbit(dx, dy) {
        this.theta += dx * 0.01;
        this.phi = MathUtils.clamp(this.phi + dy * 0.01, 0.1, Math.PI - 0.1);
        this.updatePosition();
    }

    pan(dx, dy) {
        const right = MathUtils.vec3Normalize([
            this.viewMatrix[0],
            this.viewMatrix[4],
            this.viewMatrix[8]
        ]);
        const up = MathUtils.vec3Normalize([
            this.viewMatrix[1],
            this.viewMatrix[5],
            this.viewMatrix[9]
        ]);
        
        const sensitivity = this.radius * 0.001;
        this.target = MathUtils.vec3Sub(
            this.target,
            MathUtils.vec3Add(
                MathUtils.vec3Scale(right, dx * sensitivity),
                MathUtils.vec3Scale(up, -dy * sensitivity)
            )
        );
        this.updatePosition();
    }

    zoom(delta) {
        this.radius = MathUtils.clamp(this.radius * (1 + delta * 0.001), 0.5, 1000);
        this.updatePosition();
    }
}

class Renderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.gl = canvas.getContext('webgl', { antialias: true });
        
        if (!this.gl) {
            throw new Error('WebGL 不支持');
        }
        
        this.program = WebGLUtils.createProgram(this.gl, SCENE_VS, SCENE_FS);
        
        this.aPosition = this.gl.getAttribLocation(this.program, 'aPosition');
        this.aNormal = this.gl.getAttribLocation(this.program, 'aNormal');
        
        this.uModelMatrix = this.gl.getUniformLocation(this.program, 'uModelMatrix');
        this.uViewProjection = this.gl.getUniformLocation(this.program, 'uViewProjection');
        this.uNormalMatrix = this.gl.getUniformLocation(this.program, 'uNormalMatrix');
        this.uBaseColor = this.gl.getUniformLocation(this.program, 'uBaseColor');
        this.uLightPos = this.gl.getUniformLocation(this.program, 'uLightPos');
        this.uCameraPos = this.gl.getUniformLocation(this.program, 'uCameraPos');
        this.uMetallic = this.gl.getUniformLocation(this.program, 'uMetallic');
        this.uRoughness = this.gl.getUniformLocation(this.program, 'uRoughness');
        this.uEmissive = this.gl.getUniformLocation(this.program, 'uEmissive');
        this.uSelected = this.gl.getUniformLocation(this.program, 'uSelected');
        
        this.resize();
    }

    resize() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }

    getWidth() {
        return this.canvas.width;
    }

    getHeight() {
        return this.canvas.height;
    }

    render(sceneGraph, camera, selectedNode = null, gizmo = null) {
        const gl = this.gl;
        
        gl.clearColor(0.15, 0.15, 0.18, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.DEPTH_TEST);
        
        gl.useProgram(this.program);
        
        gl.uniformMatrix4fv(this.uViewProjection, false, new Float32Array(camera.viewProjection));
        gl.uniform3fv(this.uLightPos, [10, 20, 10]);
        gl.uniform3fv(this.uCameraPos, camera.position);
        
        const meshes = sceneGraph.getVisibleMeshes();
        
        for (const { node, mesh, worldMatrix } of meshes) {
            const isSelected = selectedNode && selectedNode.id === node.id;
            
            gl.uniformMatrix4fv(this.uModelMatrix, false, new Float32Array(worldMatrix));
            
            const normalMatrix = this._computeNormalMatrix(worldMatrix);
            gl.uniformMatrix3fv(this.uNormalMatrix, false, new Float32Array(normalMatrix));
            
            gl.uniform1i(this.uSelected, isSelected ? 1 : 0);
            
            for (const primitive of mesh.primitives) {
                const material = primitive.material || {};
                
                const alphaMode = material.alphaMode || 'OPAQUE';
                const doubleSided = !!material.doubleSided;
                
                if (alphaMode === 'BLEND') {
                    gl.enable(gl.BLEND);
                    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
                    gl.depthMask(false);
                } else {
                    gl.disable(gl.BLEND);
                    gl.depthMask(true);
                }
                
                if (doubleSided) {
                    gl.disable(gl.CULL_FACE);
                } else {
                    gl.enable(gl.CULL_FACE);
                }
                
                gl.uniform4fv(this.uBaseColor, material.baseColorFactor || [1, 1, 1, 1]);
                gl.uniform1f(this.uMetallic, material.metallicFactor !== undefined ? material.metallicFactor : 0);
                gl.uniform1f(this.uRoughness, material.roughnessFactor !== undefined ? material.roughnessFactor : 1);
                gl.uniform3fv(this.uEmissive, material.emissiveFactor || [0, 0, 0]);
                
                if (primitive.vertexBuffer) {
                    gl.bindBuffer(gl.ARRAY_BUFFER, primitive.vertexBuffer);
                    gl.enableVertexAttribArray(this.aPosition);
                    gl.vertexAttribPointer(this.aPosition, 3, gl.FLOAT, false, 0, 0);
                }
                
                if (primitive.normalBuffer) {
                    gl.bindBuffer(gl.ARRAY_BUFFER, primitive.normalBuffer);
                    gl.enableVertexAttribArray(this.aNormal);
                    gl.vertexAttribPointer(this.aNormal, 3, gl.FLOAT, false, 0, 0);
                } else {
                    gl.disableVertexAttribArray(this.aNormal);
                    gl.vertexAttrib3f(this.aNormal, 0, 0, 1);
                }
                
                const drawMode = material.wireframe ? gl.LINES : primitive.drawMode;
                
                if (primitive.indexBuffer) {
                    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, primitive.indexBuffer);
                    gl.drawElements(drawMode, primitive.indexCount, gl.UNSIGNED_SHORT, 0);
                } else {
                    gl.drawArrays(drawMode, 0, primitive.vertexCount);
                }
            }
        }
        
        gl.disable(gl.BLEND);
        gl.depthMask(true);
        gl.enable(gl.CULL_FACE);
        
        if (gizmo) {
            gizmo.render(camera);
        }
    }

    _computeNormalMatrix(m) {
        const inv = MathUtils.mat4Inverse(m);
        const trans = MathUtils.mat4Transpose(inv);
        return [
            trans[0], trans[1], trans[2],
            trans[4], trans[5], trans[6],
            trans[8], trans[9], trans[10]
        ];
    }
}

class App {
    constructor() {
        this.canvas = document.getElementById('gl-canvas');
        this.renderer = new Renderer(this.canvas);
        this.camera = new Camera();
        this.sceneGraph = new SceneGraph();
        this.gltfLoader = new GLTFLoader(this.renderer.gl);
        this.picker = new Picker(this.renderer.gl);
        this.gizmo = new TransformGizmo(this.renderer.gl);
        this.materialPanel = new MaterialPanel('material-panel-container');
        
        this.selectedNode = null;
        
        this.isDragging = false;
        this.dragMode = null;
        this.lastMousePos = { x: 0, y: 0 };
        this.lastClickTime = 0;
        this.lastClickPos = { x: 0, y: 0 };
        
        this.animationId = null;
        this.frameCount = 0;
        this.lastFPSUpdate = performance.now();
        
        this._initUI();
        this._initEventListeners();
        this._createDemoScene();
        this._updateCameraAspect();
        this.start();
    }

    _initUI() {
        this.fileInput = document.getElementById('file-input');
        this.btnLoad = document.getElementById('btn-load');
        this.btnDeselect = document.getElementById('btn-deselect');
        this.transformMode = document.getElementById('transform-mode');
        this.sceneTree = document.getElementById('scene-tree');
        this.propertiesContent = document.getElementById('properties-content');
        this.selectionInfo = document.getElementById('selection-info');
        this.stats = document.getElementById('stats');
        this.statusText = document.getElementById('status-text');
        this.modelInfo = document.getElementById('model-info');
    }

    _initEventListeners() {
        window.addEventListener('resize', () => this._onResize());
        
        this.btnLoad.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this._onFileLoad(e));
        
        this.btnDeselect.addEventListener('click', () => this._deselect());
        this.transformMode.addEventListener('change', (e) => {
            this.gizmo.setType(e.target.value);
        });
        
        this.canvas.addEventListener('mousedown', (e) => this._onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this._onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        this.canvas.addEventListener('dblclick', (e) => this._onDoubleClick(e));
        
        document.addEventListener('keydown', (e) => this._onKeyDown(e));
    }

    _createDemoScene() {
        const loader = this.gltfLoader;
        const gl = this.renderer.gl;
        
        const cubeMesh = loader.createPrimitiveGeometry(gl, 'cube');
        const sphereMesh = loader.createPrimitiveGeometry(gl, 'sphere');
        const cylinderMesh = loader.createPrimitiveGeometry(gl, 'cylinder');
        
        const cubeNode = new SceneNode('Cube');
        cubeNode.meshes = [cubeMesh];
        cubeNode.setTranslation(-2, 0, 0);
        cubeNode.setScale(0.8, 0.8, 0.8);
        cubeNode.meshes[0].primitives[0].material = new Material(Material.Presets.Gold);
        
        const sphereNode = new SceneNode('Sphere');
        sphereNode.meshes = [sphereMesh];
        sphereNode.setTranslation(2, 0, 0);
        sphereNode.setScale(0.8, 0.8, 0.8);
        sphereNode.meshes[0].primitives[0].material = new Material(Material.Presets.Chrome);
        
        const cylinderNode = new SceneNode('Cylinder');
        cylinderNode.meshes = [cylinderMesh];
        cylinderNode.setTranslation(0, 0, 2);
        cylinderNode.setScale(0.6, 1, 0.6);
        cylinderNode.meshes[0].primitives[0].material = new Material(Material.Presets.Glass);
        
        const groupNode = new SceneNode('Group');
        groupNode.addChild(cubeNode);
        groupNode.addChild(sphereNode);
        
        this.sceneGraph.addNode(groupNode);
        this.sceneGraph.addNode(cylinderNode);
        
        this._updateSceneTree();
        this._updateModelInfo();
    }

    _onResize() {
        this.renderer.resize();
        this._updateCameraAspect();
        this.picker.resize(this.renderer.getWidth(), this.renderer.getHeight());
    }

    _updateCameraAspect() {
        const rect = this.canvas.getBoundingClientRect();
        this.camera.setAspect(rect.width / rect.height);
    }

    _onFileLoad(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        this.statusText.textContent = `加载中: ${file.name}...`;
        
        this.gltfLoader.loadFromFile(file).then((scene) => {
            this.sceneGraph.clear();
            SceneNode.nextId = 0;
            
            for (const child of scene.root.children) {
                this.sceneGraph.addNode(child);
            }
            
            this._deselect();
            this._updateSceneTree();
            this._updateModelInfo();
            this.statusText.textContent = `已加载: ${file.name}`;
            
            this._frameScene();
        }).catch((err) => {
            console.error('加载失败:', err);
            this.statusText.textContent = `加载失败: ${err.message}`;
        });
        
        e.target.value = '';
    }

    _frameScene() {
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;
        
        this.sceneGraph.traverse((node) => {
            for (const mesh of node.meshes) {
                for (const primitive of mesh.primitives) {
                    const bb = primitive.boundingBox;
                    const worldMin = MathUtils.mat4TransformPoint(node.worldMatrix, bb.min);
                    const worldMax = MathUtils.mat4TransformPoint(node.worldMatrix, bb.max);
                    
                    minX = Math.min(minX, worldMin[0], worldMax[0]);
                    maxX = Math.max(maxX, worldMin[0], worldMax[0]);
                    minY = Math.min(minY, worldMin[1], worldMax[1]);
                    maxY = Math.max(maxY, worldMin[1], worldMax[1]);
                    minZ = Math.min(minZ, worldMin[2], worldMax[2]);
                    maxZ = Math.max(maxZ, worldMin[2], worldMax[2]);
                }
            }
        });
        
        if (minX !== Infinity) {
            const center = [(minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2];
            const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
            
            this.camera.target = center;
            this.camera.radius = size * 2;
            this.camera.updatePosition();
        }
    }

    _onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) * window.devicePixelRatio;
        const y = (e.clientY - rect.top) * window.devicePixelRatio;
        
        if (e.button === 2) {
            this.dragMode = 'orbit';
            this.isDragging = true;
            this.lastMousePos = { x: e.clientX, y: e.clientY };
        } else if (e.button === 1 || (e.button === 0 && e.altKey)) {
            this.dragMode = 'pan';
            this.isDragging = true;
            this.lastMousePos = { x: e.clientX, y: e.clientY };
        } else if (e.button === 0) {
            const rect = this.canvas.getBoundingClientRect();
            const canvasX = e.clientX - rect.left;
            const canvasY = e.clientY - rect.top;
            const viewportWidth = this.renderer.getWidth();
            const viewportHeight = this.renderer.getHeight();
            
            if (this.gizmo.visible && this.gizmo.startDrag(canvasX, canvasY, this.camera, viewportWidth, viewportHeight)) {
                this.dragMode = 'gizmo';
                this.isDragging = true;
                this.lastMousePos = { x: e.clientX, y: e.clientY };
            } else {
                const pickedNode = this.picker.pick(
                    this.sceneGraph,
                    this.camera,
                    x,
                    y
                );
                
                if (pickedNode) {
                    this._selectNode(pickedNode);
                    this.dragMode = 'gizmo';
                    this.gizmo.startDrag(canvasX, canvasY, this.camera, viewportWidth, viewportHeight);
                } else {
                    this._deselect();
                    this.dragMode = 'orbit';
                }
                this.isDragging = true;
                this.lastMousePos = { x: e.clientX, y: e.clientY };
            }
        }
    }

    _onMouseMove(e) {
        if (!this.isDragging) return;
        
        const dx = e.clientX - this.lastMousePos.x;
        const dy = e.clientY - this.lastMousePos.y;
        
        if (this.dragMode === 'orbit') {
            this.camera.orbit(dx, dy);
        } else if (this.dragMode === 'pan') {
            this.camera.pan(dx, dy);
        } else if (this.dragMode === 'gizmo' && this.gizmo.isDragging) {
            const rect = this.canvas.getBoundingClientRect();
            const canvasX = e.clientX - rect.left;
            const canvasY = e.clientY - rect.top;
            const viewportWidth = this.renderer.getWidth();
            const viewportHeight = this.renderer.getHeight();
            this.gizmo.updateDrag(canvasX, canvasY, this.camera, viewportWidth, viewportHeight);
            this._updatePropertiesPanel();
            this._updateSceneTree();
        }
        
        this.lastMousePos = { x: e.clientX, y: e.clientY };
    }

    _onMouseUp(e) {
        this.isDragging = false;
        this.gizmo.endDrag();
        this.dragMode = null;
    }

    _onWheel(e) {
        e.preventDefault();
        this.camera.zoom(e.deltaY);
    }

    _onDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) * window.devicePixelRatio;
        const y = (e.clientY - rect.top) * window.devicePixelRatio;
        
        const pickedNode = this.picker.pick(
            this.sceneGraph,
            this.camera,
            x,
            y
        );
        
        if (pickedNode) {
            this._selectNode(pickedNode);
            if (this.materialPanel) {
                this.materialPanel.setMaterialFromNode(pickedNode);
            }
        }
    }

    _onKeyDown(e) {
        switch (e.key.toLowerCase()) {
            case 't':
                this.transformMode.value = 'translate';
                this.gizmo.setType('translate');
                break;
            case 'r':
                this.transformMode.value = 'rotate';
                this.gizmo.setType('rotate');
                break;
            case 's':
                this.transformMode.value = 'scale';
                this.gizmo.setType('scale');
                break;
            case 'escape':
                this._deselect();
                break;
            case 'f':
                this._frameScene();
                break;
        }
    }

    _selectNode(node) {
        this.selectedNode = node;
        this.gizmo.setTarget(node);
        this.selectionInfo.textContent = `已选择: ${node.name}`;
        this._updatePropertiesPanel();
        this._updateSceneTree();
    }

    _deselect() {
        this.selectedNode = null;
        this.gizmo.setTarget(null);
        this.selectionInfo.textContent = '未选择物体';
        this.propertiesContent.innerHTML = '<div class="empty-state">选择物体查看属性</div>';
        if (this.materialPanel) {
            this.materialPanel.setMaterial(null);
        }
        this._updateSceneTree();
    }

    _updateSceneTree() {
        this.sceneTree.innerHTML = '';
        this._renderTree(this.sceneGraph.root, this.sceneTree);
    }

    _renderTree(node, container) {
        if (node.id === this.sceneGraph.root.id && node.children.length === 0) {
            return;
        }
        
        const hasChildren = node.children.length > 0;
        
        const nodeEl = document.createElement('div');
        nodeEl.className = 'tree-node' + (this.selectedNode && this.selectedNode.id === node.id ? ' selected' : '');
        nodeEl.dataset.nodeId = node.id;
        
        if (hasChildren) {
            const toggle = document.createElement('span');
            toggle.className = 'toggle expanded';
            toggle.onclick = (e) => {
                e.stopPropagation();
                const childrenEl = nodeEl.nextElementSibling;
                if (childrenEl) {
                    childrenEl.style.display = childrenEl.style.display === 'none' ? 'block' : 'none';
                    toggle.className = childrenEl.style.display === 'none' ? 'toggle collapsed' : 'toggle expanded';
                }
            };
            nodeEl.appendChild(toggle);
        } else if (node.id !== this.sceneGraph.root.id) {
            const spacing = document.createElement('span');
            spacing.style.display = 'inline-block';
            spacing.style.width = '12px';
            spacing.style.marginRight = '4px';
            nodeEl.appendChild(spacing);
        }
        
        const text = document.createElement('span');
        text.textContent = node.name || `Node_${node.id}`;
        nodeEl.appendChild(text);
        
        if (node.id !== this.sceneGraph.root.id) {
            nodeEl.onclick = () => this._selectNode(node);
        }
        
        if (node.id !== this.sceneGraph.root.id) {
            container.appendChild(nodeEl);
        }
        
        if (hasChildren) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'tree-children';
            container.appendChild(nodeEl);
            container.appendChild(childrenContainer);
            for (const child of node.children) {
                this._renderTree(child, childrenContainer);
            }
        }
    }

    _updatePropertiesPanel() {
        if (!this.selectedNode) {
            this.propertiesContent.innerHTML = '<div class="empty-state">选择物体查看属性</div>';
            return;
        }
        
        const node = this.selectedNode;
        const euler = this.gizmo._quaternionToEuler(node.rotation);
        
        this.propertiesContent.innerHTML = `
            <div class="property-group">
                <h3>基本信息</h3>
                <div class="property-row">
                    <label>名称</label>
                    <input type="text" value="${node.name}" id="prop-name">
                </div>
                <div class="property-row">
                    <label>ID</label>
                    <input type="text" value="${node.id}" disabled>
                </div>
            </div>
            <div class="property-group">
                <h3>位置</h3>
                <div class="property-row">
                    <label>X</label>
                    <input type="number" step="0.1" value="${node.translation[0].toFixed(3)}" class="pos-x">
                </div>
                <div class="property-row">
                    <label>Y</label>
                    <input type="number" step="0.1" value="${node.translation[1].toFixed(3)}" class="pos-y">
                </div>
                <div class="property-row">
                    <label>Z</label>
                    <input type="number" step="0.1" value="${node.translation[2].toFixed(3)}" class="pos-z">
                </div>
            </div>
            <div class="property-group">
                <h3>旋转 (弧度)</h3>
                <div class="property-row">
                    <label>X</label>
                    <input type="number" step="0.1" value="${euler[0].toFixed(3)}" class="rot-x">
                </div>
                <div class="property-row">
                    <label>Y</label>
                    <input type="number" step="0.1" value="${euler[1].toFixed(3)}" class="rot-y">
                </div>
                <div class="property-row">
                    <label>Z</label>
                    <input type="number" step="0.1" value="${euler[2].toFixed(3)}" class="rot-z">
                </div>
            </div>
            <div class="property-group">
                <h3>缩放</h3>
                <div class="property-row">
                    <label>X</label>
                    <input type="number" step="0.1" value="${node.scale[0].toFixed(3)}" class="scale-x">
                </div>
                <div class="property-row">
                    <label>Y</label>
                    <input type="number" step="0.1" value="${node.scale[1].toFixed(3)}" class="scale-y">
                </div>
                <div class="property-row">
                    <label>Z</label>
                    <input type="number" step="0.1" value="${node.scale[2].toFixed(3)}" class="scale-z">
                </div>
            </div>
        `;
        
        const setupInput = (selector, getter, setter) => {
            const input = this.propertiesContent.querySelector(selector);
            if (input) {
                input.addEventListener('change', (e) => {
                    const values = getter();
                    const index = ['x', 'y', 'z'].indexOf(selector.split('-')[1]);
                    if (index !== -1) {
                        values[index] = parseFloat(e.target.value);
                        setter(...values);
                    }
                });
            }
        };
        
        setupInput('.pos-x', () => node.translation, (x, y, z) => node.setTranslation(x, y, z));
        setupInput('.pos-y', () => node.translation, (x, y, z) => node.setTranslation(x, y, z));
        setupInput('.pos-z', () => node.translation, (x, y, z) => node.setTranslation(x, y, z));
        
        setupInput('.rot-x', () => euler, (x, y, z) => node.setRotationEuler(x, y, z));
        setupInput('.rot-y', () => euler, (x, y, z) => node.setRotationEuler(x, y, z));
        setupInput('.rot-z', () => euler, (x, y, z) => node.setRotationEuler(x, y, z));
        
        setupInput('.scale-x', () => node.scale, (x, y, z) => node.setScale(x, y, z));
        setupInput('.scale-y', () => node.scale, (x, y, z) => node.setScale(x, y, z));
        setupInput('.scale-z', () => node.scale, (x, y, z) => node.setScale(x, y, z));
        
        const nameInput = this.propertiesContent.querySelector('#prop-name');
        if (nameInput) {
            nameInput.addEventListener('change', (e) => {
                node.name = e.target.value;
                this._updateSceneTree();
            });
        }
    }

    _updateModelInfo() {
        let nodeCount = 0;
        let meshCount = 0;
        let triangleCount = 0;
        
        this.sceneGraph.traverse((node) => {
            nodeCount++;
            for (const mesh of node.meshes) {
                meshCount++;
                for (const primitive of mesh.primitives) {
                    if (primitive.indexCount > 0) {
                        triangleCount += primitive.indexCount / 3;
                    } else {
                        triangleCount += primitive.vertexCount / 3;
                    }
                }
            }
        });
        
        this.modelInfo.textContent = `节点: ${nodeCount} | 网格: ${meshCount} | 三角形: ${Math.floor(triangleCount)}`;
    }

    start() {
        this._onResize();
        this.animate();
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        this.render();
        
        this.frameCount++;
        const now = performance.now();
        if (now - this.lastFPSUpdate >= 1000) {
            this.stats.textContent = `FPS: ${this.frameCount}`;
            this.frameCount = 0;
            this.lastFPSUpdate = now;
        }
    }

    render() {
        this.renderer.render(this.sceneGraph, this.camera, this.selectedNode, this.gizmo);
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
}

const app = new App();
