class WebGPUModelEditor {
    constructor() {
        this.canvas = document.getElementById('renderCanvas');
        this.engine = null;
        this.scene = null;
        this.camera = null;
        this.light = null;
        this.currentModel = null;
        this.currentModelMesh = null;
        this.originalModelMesh = null;
        this.materials = [];
        this.animations = [];
        this.animationGroup = null;
        this.isPlaying = false;
        this.morphTargetManagers = [];
        this.renderJobs = [];
        this.pollIntervals = new Map();
        this.targetFps = 60;
        this.frameTime = 1000 / 60;
        this.lastFrameTime = 0;
        this.skeleton = null;
        this.showSkeleton = false;
        
        this.boneAnimationWorker = null;
        this.gpuSkinningEnabled = true;
        this.rayTracingEnabled = false;
        this.rayTracingQuality = 2;
        
        this.gltfTransform = null;
        
        this.materialPresets = {
            'gold': { albedo: new BABYLON.Color3(1, 0.843, 0), metallic: 1, roughness: 0.3 },
            'silver': { albedo: new BABYLON.Color3(0.753, 0.753, 0.753), metallic: 1, roughness: 0.2 },
            'copper': { albedo: new BABYLON.Color3(0.722, 0.451, 0.2), metallic: 1, roughness: 0.4 },
            'steel': { albedo: new BABYLON.Color3(0.443, 0.475, 0.494), metallic: 1, roughness: 0.35 },
            'plastic-red': { albedo: new BABYLON.Color3(1, 0.267, 0.267), metallic: 0, roughness: 0.4 },
            'plastic-blue': { albedo: new BABYLON.Color3(0.267, 0.267, 1), metallic: 0, roughness: 0.45 },
            'fabric-cotton': { albedo: new BABYLON.Color3(0.91, 0.894, 0.882), metallic: 0, roughness: 0.9 },
            'fabric-denim': { albedo: new BABYLON.Color3(0.082, 0.376, 0.741), metallic: 0, roughness: 0.85 },
            'rubber': { albedo: new BABYLON.Color3(0.2, 0.2, 0.2), metallic: 0, roughness: 0.95 },
            'glass': { albedo: new BABYLON.Color3(0.8, 0.88, 1), metallic: 0, roughness: 0.1, transparency: 0.5 },
            'wood': { albedo: new BABYLON.Color3(0.545, 0.271, 0.075), metallic: 0, roughness: 0.7 },
            'marble': { albedo: new BABYLON.Color3(0.96, 0.96, 0.96), metallic: 0, roughness: 0.2 }
        };

        this.init();
    }

    async init() {
        try {
            await this.initWebGPUEngine();
            this.initWorker();
            this.setupEventListeners();
            this.loadModels();
            this.loadRenderJobs();
            this.initGLTFTransform();
        } catch (error) {
            console.error('Failed to initialize WebGPU, falling back to WebGL:', error);
            this.initWebGLEngine();
            this.initWorker();
            this.setupEventListeners();
            this.loadModels();
            this.loadRenderJobs();
        }
    }

    async initWebGPUEngine() {
        const gpuSupported = BABYLON.WebGPUEngine.IsSupported;
        if (!gpuSupported) {
            throw new Error('WebGPU not supported');
        }

        this.engine = new BABYLON.WebGPUEngine(this.canvas, {
            preserveDrawingBuffer: true,
            antialias: true,
            adaptToDeviceRatio: true,
        });

        await this.engine.initAsync();

        if (this.engine.adapter) {
            const adapterInfo = this.engine.adapterInfo || {};
            document.getElementById('gpuAdapterName').textContent = 
                adapterInfo.description || adapterInfo.vendor || 'WebGPU Adapter';
        }

        this.setupScene();
    }

    initWebGLEngine() {
        this.engine = new BABYLON.Engine(this.canvas, true, {
            preserveDrawingBuffer: true,
            stencil: true
        });

        document.getElementById('webgpuInfo').innerHTML = '<div style="color: #ffaa00;">⚠️ WebGPU not available, using WebGL</div>';
        
        this.setupScene();
    }

    setupScene() {
        this.scene = new BABYLON.Scene(this.engine);
        this.scene.clearColor = new BABYLON.Color4(0.1, 0.1, 0.18, 1);

        this.camera = new BABYLON.ArcRotateCamera('camera', -Math.PI / 2, Math.PI / 4, 10, BABYLON.Vector3.Zero(), this.scene);
        this.camera.attachControl(this.canvas, true);
        this.camera.lowerRadiusLimit = 2;
        this.camera.upperRadiusLimit = 50;
        this.camera.wheelPrecision = 50;

        this.light = new BABYLON.HemisphericLight('light', new BABYLON.Vector3(0, 1, 0), this.scene);
        this.light.intensity = 1;

        const dirLight = new BABYLON.DirectionalLight('dirLight', new BABYLON.Vector3(-1, -2, -1), this.scene);
        dirLight.position = new BABYLON.Vector3(20, 40, 20);
        dirLight.intensity = 0.8;

        this.createGround();
        this.createDefaultCube();

        this.engine.runRenderLoop(() => {
            const now = performance.now();
            if (now - this.lastFrameTime >= this.frameTime) {
                this.scene.render();
                this.lastFrameTime = now;
            }
        });

        window.addEventListener('resize', () => {
            this.engine.resize();
        });
    }

    initWorker() {
        if (typeof Worker !== 'undefined') {
            this.boneAnimationWorker = new Worker('js/workers/boneAnimationWorker.js');
            
            this.boneAnimationWorker.onmessage = (e) => {
                this.handleWorkerMessage(e.data);
            };

            this.boneAnimationWorker.postMessage({
                type: 'setFPS',
                fps: this.targetFps
            });
        }
    }

    handleWorkerMessage(data) {
        switch (data.type) {
            case 'bonesInitialized':
                console.log(`Initialized ${data.boneCount} bones in worker`);
                break;
            case 'clipsInitialized':
                console.log(`Initialized ${data.clipCount} animation clips`);
                break;
            case 'boneMatricesUpdated':
                this.updateBoneMatrices(data.matrices);
                break;
            case 'error':
                console.error('Worker error:', data.message);
                break;
        }
    }

    updateBoneMatrices(matrices) {
        if (!this.currentModelMesh || !this.gpuSkinningEnabled) return;

        const meshes = this.currentModelMesh.getChildMeshes();
        meshes.forEach(mesh => {
            if (mesh.skeleton) {
                const boneMatrices = new Float32Array(matrices);
                for (let i = 0; i < mesh.skeleton.bones.length && i * 16 < boneMatrices.length; i++) {
                    const matrix = BABYLON.Matrix.FromArray(matrices, i * 16);
                    mesh.skeleton.bones[i].setMatrix(matrix);
                }
                mesh.skeleton.prepare();
            }
        });
    }

    async initGLTFTransform() {
        if (window.gltfTransform) {
            this.gltfTransform = {
                WebIO: gltfTransform.WebIO,
                Document: gltfTransform.Document,
                ...gltfTransform.functions
            };
        }
    }

    async optimizeGLTF(buffer) {
        if (!this.gltfTransform) {
            console.log('glTF Transform not available, skipping optimization');
            return buffer;
        }

        try {
            const io = new this.gltfTransform.WebIO();
            const document = await io.readBinary(new Uint8Array(buffer));
            
            this.gltfTransform.decimate({ ratio: 0.5, error: 0.001 })(document);
            this.gltfTransform.textureCompress()(document);
            this.gltfTransform.reorder({ algorithm: 'distance' })(document);
            
            const optimizedBuffer = await io.writeBinary(document);
            return optimizedBuffer.buffer;
        } catch (error) {
            console.error('glTF optimization failed:', error);
            return buffer;
        }
    }

    createGround() {
        const ground = BABYLON.MeshBuilder.CreateGround('ground', { width: 20, height: 20 }, this.scene);
        const groundMaterial = new BABYLON.PBRMaterial('groundMat', this.scene);
        groundMaterial.albedoColor = new BABYLON.Color3(0.15, 0.15, 0.2);
        groundMaterial.metallic = 0.1;
        groundMaterial.roughness = 0.9;
        ground.material = groundMaterial;
    }

    createDefaultCube() {
        const cube = BABYLON.MeshBuilder.CreateBox('defaultCube', { size: 2 }, this.scene);
        const cubeMaterial = new BABYLON.PBRMaterial('cubeMat', this.scene);
        cubeMaterial.albedoColor = new BABYLON.Color3(0.4, 0.6, 1);
        cubeMaterial.metallic = 0.3;
        cubeMaterial.roughness = 0.5;
        cube.material = cubeMaterial;
    }

    setupEventListeners() {
        document.getElementById('uploadBtn').addEventListener('click', () => {
            document.getElementById('uploadModal').style.display = 'block';
        });

        document.getElementById('exportBtn').addEventListener('click', () => {
            if (this.currentModel) {
                this.exportGLTF();
            } else {
                alert('请先选择一个模型');
            }
        });

        document.getElementById('renderBtn').addEventListener('click', () => {
            if (this.currentModel) {
                document.getElementById('renderModal').style.display = 'block';
            } else {
                alert('请先选择一个模型');
            }
        });

        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });

        document.getElementById('uploadForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadModel();
        });

        document.getElementById('renderForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitRenderJob();
        });

        document.getElementById('materialSelect').addEventListener('change', (e) => {
            this.updateMaterialUI(e.target.value);
        });

        document.getElementById('albedoColor').addEventListener('input', (e) => {
            this.updateMaterialProperty('albedoColor', e.target.value);
        });

        document.getElementById('metallic').addEventListener('input', (e) => {
            document.getElementById('metallicValue').textContent = e.target.value;
            this.updateMaterialProperty('metallic', parseFloat(e.target.value));
        });

        document.getElementById('roughness').addEventListener('input', (e) => {
            document.getElementById('roughnessValue').textContent = e.target.value;
            this.updateMaterialProperty('roughness', parseFloat(e.target.value));
        });

        document.querySelectorAll('.material-preset').forEach(preset => {
            preset.addEventListener('click', () => {
                const presetName = preset.dataset.preset;
                this.applyMaterialPreset(presetName);
            });
        });

        document.getElementById('playAnimBtn').addEventListener('click', () => this.playAnimation());
        document.getElementById('pauseAnimBtn').addEventListener('click', () => this.pauseAnimation());
        document.getElementById('stopAnimBtn').addEventListener('click', () => this.stopAnimation());

        document.getElementById('animSpeed').addEventListener('input', (e) => {
            document.getElementById('animSpeedValue').textContent = e.target.value + 'x';
            if (this.animationGroup) {
                this.animationGroup.speedRatio = parseFloat(e.target.value);
            }
        });

        document.getElementById('interpolationMode').addEventListener('change', (e) => {
            this.setAnimationInterpolation(e.target.value);
        });

        document.getElementById('targetFps').addEventListener('change', (e) => {
            this.targetFps = parseInt(e.target.value);
            this.frameTime = 1000 / this.targetFps;
            if (this.boneAnimationWorker) {
                this.boneAnimationWorker.postMessage({ type: 'setFPS', fps: this.targetFps });
            }
        });

        document.getElementById('gpuSkinningEnabled').addEventListener('change', (e) => {
            this.gpuSkinningEnabled = e.target.checked;
        });

        document.getElementById('rayTracingEnabled').addEventListener('change', (e) => {
            this.rayTracingEnabled = e.target.checked;
            if (this.rayTracingEnabled) {
                this.setupRayTracing();
            }
        });

        document.getElementById('rayTracingQuality').addEventListener('input', (e) => {
            this.rayTracingQuality = parseInt(e.target.value);
            document.getElementById('rayTracingQualityValue').textContent = e.target.value;
        });

        document.getElementById('autoBindBtn').addEventListener('click', () => {
            this.autoRigging();
        });

        document.getElementById('boneCount').addEventListener('input', (e) => {
            document.getElementById('boneCountValue').textContent = e.target.value;
        });

        document.getElementById('decimateBtn').addEventListener('click', () => {
            this.decimateModel();
        });

        document.getElementById('resetModelBtn').addEventListener('click', () => {
            this.resetModel();
        });

        document.getElementById('envIntensity').addEventListener('input', (e) => {
            this.light.intensity = parseFloat(e.target.value);
        });

        document.getElementById('bgColor').addEventListener('input', (e) => {
            const color = BABYLON.Color3.FromHexString(e.target.value);
            this.scene.clearColor = new BABYLON.Color4(color.r, color.g, color.b, 1);
        });
    }

    async setupRayTracing() {
        console.log('Ray tracing preview enabled (using BabylonJS PBR for realtime approximation)');
        if (this.engine instanceof BABYLON.WebGPUEngine) {
            this.scene.enableRealTimeRendering = true;
        }
    }

    applyMaterialPreset(presetName) {
        const preset = this.materialPresets[presetName];
        if (!preset) return;

        const select = document.getElementById('materialSelect');
        const material = this.materials[select.value];
        if (!material) {
            alert('请先选择模型材质');
            return;
        }

        material.albedoColor = preset.albedo;
        material.metallic = preset.metallic;
        material.roughness = preset.roughness;
        if (preset.transparency) {
            material.alpha = 1 - preset.transparency * 0.5;
        }

        document.getElementById('albedoColor').value = '#' + preset.albedo.toHexString();
        document.getElementById('metallic').value = preset.metallic;
        document.getElementById('metallicValue').textContent = preset.metallic;
        document.getElementById('roughness').value = preset.roughness;
        document.getElementById('roughnessValue').textContent = preset.roughness;

        document.querySelectorAll('.material-preset').forEach(p => p.classList.remove('active'));
        document.querySelector(`[data-preset="${presetName}"]`).classList.add('active');
    }

    async autoRigging() {
        if (!this.currentModelMesh) {
            alert('请先加载模型');
            return;
        }

        const progressDiv = document.getElementById('bindingProgress');
        const statusSpan = document.getElementById('bindingStatus');
        const progressFill = progressDiv.querySelector('.progress-fill');
        
        progressDiv.style.display = 'block';
        statusSpan.textContent = '分析模型结构...';
        progressFill.style.width = '10%';

        try {
            await this.delay(300);
            statusSpan.textContent = '生成骨骼结构...';
            progressFill.style.width = '30%';

            const boneCount = parseInt(document.getElementById('boneCount').value);
            const bindingType = document.getElementById('bindingType').value;

            this.skeleton = new BABYLON.Skeleton('autoRigSkeleton', 'autoRig', this.scene);
            this.generateSimpleSkeleton(boneCount, bindingType);

            await this.delay(500);
            statusSpan.textContent = '计算蒙皮权重...';
            progressFill.style.width = '60%';

            this.applyAutoWeights();

            await this.delay(300);
            statusSpan.textContent = '应用骨骼绑定...';
            progressFill.style.width = '90%';

            this.applySkeletonToMesh();

            if (this.boneAnimationWorker && this.gpuSkinningEnabled) {
                this.sendBonesToWorker();
            }

            await this.delay(200);
            statusSpan.textContent = '绑定完成!';
            progressFill.style.width = '100%';

            setTimeout(() => {
                progressDiv.style.display = 'none';
            }, 1500);

        } catch (err) {
            console.error('Rigging error:', err);
            statusSpan.textContent = '绑定失败: ' + err.message;
        }
    }

    generateSimpleSkeleton(boneCount, type) {
        const meshes = this.currentModelMesh.getChildMeshes();
        if (meshes.length === 0) return;

        const boundingInfo = meshes[0].getBoundingInfo();
        const min = boundingInfo.minimum;
        const max = boundingInfo.maximum;
        const height = max.y - min.y;

        let parentBone = null;
        for (let i = 0; i < boneCount; i++) {
            const bone = new BABYLON.Bone(`bone_${i}`, this.skeleton, parentBone);
            const yPos = min.y + (i / (boneCount - 1)) * height;
            bone.setPosition(new BABYLON.Vector3(0, yPos, 0));
            parentBone = bone;
        }
    }

    applyAutoWeights() {
        const meshes = this.currentModelMesh.getChildMeshes();
        
        meshes.forEach(mesh => {
            const positions = mesh.getVerticesData(BABYLON.VertexBuffer.PositionKind);
            if (!positions || !this.skeleton) return;

            const boneIndices = [];
            const boneWeights = [];
            const bones = this.skeleton.bones;

            for (let i = 0; i < positions.length; i += 3) {
                const pos = new BABYLON.Vector3(positions[i], positions[i + 1], positions[i + 2]);
                
                const distances = bones.map((bone, idx) => {
                    const bonePos = bone.getPosition();
                    return { idx, dist: BABYLON.Vector3.Distance(pos, bonePos) };
                }).sort((a, b) => a.dist - b.dist);

                const weights = [];
                const totalDist = distances.slice(0, 4).reduce((sum, d) => sum + (1 / (d.dist + 0.001)), 0);
                
                for (let j = 0; j < 4; j++) {
                    if (distances[j]) {
                        const weight = (1 / (distances[j].dist + 0.001)) / totalDist;
                        weights.push({ idx: distances[j].idx, weight });
                    } else {
                        weights.push({ idx: 0, weight: 0 });
                    }
                }

                weights.sort((a, b) => b.idx - a.idx);
                
                for (let j = 0; j < 4; j++) {
                    boneIndices.push(weights[j].idx);
                    boneWeights.push(weights[j].weight);
                }
            }

            mesh.setVerticesData(BABYLON.VertexBuffer.MatricesIndicesKind, boneIndices);
            mesh.setVerticesData(BABYLON.VertexBuffer.MatricesWeightsKind, boneWeights);
        });
    }

    sendBonesToWorker() {
        if (!this.skeleton || !this.boneAnimationWorker) return;

        const bonesData = this.skeleton.bones.map((bone, idx) => ({
            id: idx,
            name: bone.name,
            parentIndex: bone.getParent() ? this.skeleton.bones.indexOf(bone.getParent()) : -1,
            position: bone.getPosition().asArray(),
            rotation: [0, 0, 0, 1],
            scale: [1, 1, 1],
            restMatrix: bone.getRestMatrix().asArray(),
            inverseBindMatrix: bone.getInverseBindMatrix().asArray()
        }));

        this.boneAnimationWorker.postMessage({
            type: 'initBones',
            bones: bonesData
        });
    }

    applySkeletonToMesh() {
        const meshes = this.currentModelMesh.getChildMeshes();
        meshes.forEach(mesh => {
            mesh.skeleton = this.skeleton;
        });
    }

    async decimateModel() {
        if (!this.currentModelMesh) {
            alert('请先加载模型');
            return;
        }

        const targetFaceCountSelect = document.getElementById('targetFaceCount');
        let targetFaces = parseInt(targetFaceCountSelect.value);
        
        const customFaceGroup = document.getElementById('customFaceGroup');
        if (customFaceGroup && customFaceGroup.style.display !== 'none') {
            const customInput = document.getElementById('customFaceCount');
            if (customInput) {
                targetFaces = parseInt(customInput.value);
            }
        }

        if (!this.originalModelMesh) {
            this.originalModelMesh = this.cloneMeshHierarchy(this.currentModelMesh);
        }

        const meshes = this.currentModelMesh.getChildMeshes();
        
        try {
            for (const mesh of meshes) {
                if (mesh.getIndices && mesh.getIndices().length > 0) {
                    const currentFaces = mesh.getIndices().length / 3;
                    const ratio = Math.min(1, targetFaces / currentFaces);
                    
                    if (ratio < 1) {
                        const simplificationSettings = new BABYLON.ISimplificationSettings();
                        simplificationSettings.quality = ratio;
                        simplificationSettings.distance = 0;
                        simplificationSettings.optimizeMesh = true;

                        try {
                            await new Promise((resolve) => {
                                mesh.simplify(simplificationSettings, BABYLON.SimplificationType.QUADRATIC, () => {
                                    resolve();
                                }, true);
                            });
                        } catch (e) {
                            console.log('Using custom decimation for mesh:', mesh.name);
                            this.customDecimate(mesh, ratio);
                        }
                    }
                }
            }

            this.updateModelStats();
        } catch (err) {
            console.error('Decimation error:', err);
            alert('减面优化失败: ' + err.message);
        }
    }

    customDecimate(mesh, ratio) {
        const indices = mesh.getIndices();
        if (!indices) return;

        const targetIndexCount = Math.floor(indices.length * ratio);
        const step = Math.max(1, Math.floor(indices.length / targetIndexCount));

        const newIndices = [];
        for (let i = 0; i < indices.length && newIndices.length < targetIndexCount; i += step * 3) {
            newIndices.push(indices[i]);
            newIndices.push(indices[i + 1] || indices[i]);
            newIndices.push(indices[i + 2] || indices[i]);
        }

        mesh.setIndices(newIndices);
    }

    resetModel() {
        if (this.originalModelMesh) {
            if (this.currentModelMesh) {
                this.currentModelMesh.dispose();
            }
            this.currentModelMesh = this.cloneMeshHierarchy(this.originalModelMesh);
            this.updateModelStats();
        }
    }

    cloneMeshHierarchy(source) {
        return source.clone(source.name + '_clone', source.parent);
    }

    updateModelStats() {
        if (!this.currentModelMesh) return;

        const meshes = this.currentModelMesh.getChildMeshes();
        let totalFaces = 0;
        let totalVertices = 0;

        meshes.forEach(mesh => {
            if (mesh.getTotalVertices) {
                totalVertices += mesh.getTotalVertices();
            }
            if (mesh.getIndices) {
                const indices = mesh.getIndices();
                if (indices) totalFaces += indices.length / 3;
            }
        });

        const facesEl = document.getElementById('currentFaces');
        const verticesEl = document.getElementById('currentVertices');
        
        if (facesEl) facesEl.textContent = Math.round(totalFaces).toLocaleString();
        if (verticesEl) verticesEl.textContent = totalVertices.toLocaleString();
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async loadModels() {
        try {
            const response = await fetch('/api/models');
            const models = await response.json();
            this.renderModelList(models);
        } catch (err) {
            console.error('Error loading models:', err);
        }
    }

    renderModelList(models) {
        const modelList = document.getElementById('modelList');
        if (!modelList) return;
        
        modelList.innerHTML = '';

        models.forEach(model => {
            const item = document.createElement('div');
            item.className = 'model-item';
            item.innerHTML = `
                <div class="model-item-name">${model.name}</div>
                <div class="model-item-type">.${model.fileType}</div>
            `;
            item.addEventListener('click', () => this.loadModel(model));
            modelList.appendChild(item);
        });
    }

    async uploadModel() {
        const formData = new FormData();
        const nameInput = document.getElementById('modelName');
        const fileInput = document.getElementById('modelFile');
        
        formData.append('name', nameInput.value);
        formData.append('model', fileInput.files[0]);

        try {
            const response = await fetch('/api/models/upload', {
                method: 'POST',
                body: formData
            });
            const model = await response.json();
            
            document.getElementById('uploadModal').style.display = 'none';
            document.getElementById('uploadForm').reset();
            
            this.loadModels();
            this.loadModel(model);
        } catch (err) {
            console.error('Error uploading model:', err);
            alert('上传失败: ' + err.message);
        }
    }

    async loadModel(model) {
        this.currentModel = model;
        
        if (this.currentModelMesh) {
            this.currentModelMesh.dispose();
        }

        const modelInfoEl = document.getElementById('modelInfo');
        if (modelInfoEl) modelInfoEl.textContent = `正在加载: ${model.name}...`;

        try {
            let result;
            
            if (model.fileType === 'obj') {
                result = await BABYLON.SceneLoader.ImportMeshAsync('', '', model.filePath, this.scene, null, '.obj');
            } else {
                result = await BABYLON.SceneLoader.ImportMeshAsync('', '', model.filePath, this.scene);
            }

            this.currentModelMesh = new BABYLON.TransformNode('modelRoot', this.scene);
            
            result.meshes.forEach(mesh => {
                if (mesh !== this.currentModelMesh) {
                    mesh.parent = this.currentModelMesh;
                }
            });

            this.materials = [];
            result.meshes.forEach(mesh => {
                if (mesh.material) {
                    if (!this.materials.find(m => m.name === mesh.material.name)) {
                        this.materials.push(mesh.material);
                    }
                    if (!(mesh.material instanceof BABYLON.PBRMaterial)) {
                        const pbrMat = new BABYLON.PBRMaterial(mesh.material.name + '_pbr', this.scene);
                        pbrMat.albedoColor = mesh.material.diffuseColor || new BABYLON.Color3(1, 1, 1);
                        pbrMat.metallic = 0;
                        pbrMat.roughness = 0.5;
                        mesh.material = pbrMat;
                    }
                }
            });

            this.morphTargetManagers = [];
            result.meshes.forEach(mesh => {
                if (mesh.morphTargetManager) {
                    this.morphTargetManagers.push(mesh.morphTargetManager);
                }
            });

            this.animations = result.animationGroups || [];
            this.setupAnimationOptimizations();
            this.updateMaterialSelect();
            this.updateAnimationSelect();
            this.fitCameraToModel(this.currentModelMesh);
            this.updateModelStats();

            if (result.skeletons && result.skeletons.length > 0) {
                this.skeleton = result.skeletons[0];
                if (this.boneAnimationWorker && this.gpuSkinningEnabled) {
                    this.sendBonesToWorker();
                }
            }

            if (modelInfoEl) modelInfoEl.textContent = `模型: ${model.name} | 网格数: ${result.meshes.length} | 材质数: ${this.materials.length}`;
        } catch (err) {
            console.error('Error loading model:', err);
            if (modelInfoEl) modelInfoEl.textContent = `加载失败: ${err.message}`;
        }
    }

    setupAnimationOptimizations() {
        this.animations.forEach(animGroup => {
            animGroup.onAnimationGroupLoopObservable.add(() => {
                this.interpolateMorphTargets();
            });

            animGroup.targetedAnimations.forEach(targetAnim => {
                const anim = targetAnim.animation;
                if (anim) {
                    anim.dataType = BABYLON.Animation.ANIMATIONTYPE_FLOAT;
                    anim.framePerSecond = this.targetFps;
                }
            });
        });

        if (this.animations.length > 0 && this.boneAnimationWorker) {
            const clips = this.animations.map(animGroup => ({
                name: animGroup.name,
                duration: animGroup.getDuration()
            }));
            
            this.boneAnimationWorker.postMessage({
                type: 'initClips',
                clips: clips
            });
        }
    }

    setAnimationInterpolation(mode) {
        this.animations.forEach(animGroup => {
            animGroup.targetedAnimations.forEach(targetAnim => {
                if (targetAnim.animation) {
                    if (mode === 'STEP') {
                        targetAnim.animation.loopMode = BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT;
                    } else if (mode === 'CUBICSPLINE') {
                        targetAnim.animation.loopMode = BABYLON.Animation.ANIMATIONLOOPMODE_RELATIVE;
                    } else {
                        targetAnim.animation.loopMode = BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE;
                    }
                }
            });
        });
    }

    interpolateMorphTargets() {
        if (!this.animationGroup || !this.isPlaying) return;

        this.morphTargetManagers.forEach(manager => {
            for (let i = 0; i < manager.numTargets; i++) {
                const target = manager.getTarget(i);
                if (target.animations.length > 0) {
                    const anim = target.animations[0];
                    const keys = anim.getKeys();
                    
                    if (keys.length >= 2) {
                        const currentFrame = this.animationGroup.getCurrentFrame();
                        let prevKey = keys[0];
                        let nextKey = keys[keys.length - 1];
                        
                        for (let j = 0; j < keys.length - 1; j++) {
                            if (currentFrame >= keys[j].frame && currentFrame <= keys[j + 1].frame) {
                                prevKey = keys[j];
                                nextKey = keys[j + 1];
                                break;
                            }
                        }

                        const frameRange = nextKey.frame - prevKey.frame;
                        if (frameRange > 0) {
                            const t = (currentFrame - prevKey.frame) / frameRange;
                            const interpolatedValue = prevKey.value + t * (nextKey.value - prevKey.value);
                            target.influence = interpolatedValue;
                        }
                    }
                }
            }
        });
    }

    updateMaterialSelect() {
        const select = document.getElementById('materialSelect');
        if (!select) return;
        
        select.innerHTML = '';
        
        this.materials.forEach((mat, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = mat.name;
            select.appendChild(option);
        });

        if (this.materials.length > 0) {
            this.updateMaterialUI(0);
        }
    }

    updateMaterialUI(index) {
        const material = this.materials[index];
        if (!material) return;

        if (material.albedoColor) {
            document.getElementById('albedoColor').value = material.albedoColor.toHexString();
        }
        document.getElementById('metallic').value = material.metallic || 0;
        document.getElementById('metallicValue').textContent = material.metallic || 0;
        document.getElementById('roughness').value = material.roughness || 0.5;
        document.getElementById('roughnessValue').textContent = material.roughness || 0.5;
    }

    updateMaterialProperty(property, value) {
        const select = document.getElementById('materialSelect');
        const material = this.materials[select.value];
        if (!material) return;

        if (property === 'albedoColor' || property === 'emissiveColor') {
            material[property] = BABYLON.Color3.FromHexString(value);
        } else {
            material[property] = value;
        }
    }

    updateAnimationSelect() {
        const select = document.getElementById('animationSelect');
        if (!select) return;
        
        select.innerHTML = '';

        if (this.animations.length === 0) {
            const option = document.createElement('option');
            option.textContent = '无动画';
            select.appendChild(option);
        } else {
            this.animations.forEach((anim, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = anim.name || `动画 ${index + 1}`;
                select.appendChild(option);
            });
        }
    }

    playAnimation() {
        if (this.animations.length === 0) return;

        const select = document.getElementById('animationSelect');
        const animIndex = select.value;

        if (this.animationGroup) {
            this.animationGroup.stop();
        }

        this.animationGroup = this.animations[animIndex];
        this.animationGroup.start(true);
        this.animationGroup.speedRatio = parseFloat(document.getElementById('animSpeed').value);
        this.isPlaying = true;

        if (this.boneAnimationWorker && this.gpuSkinningEnabled) {
            this.boneAnimationWorker.postMessage({
                type: 'play',
                clipName: this.animationGroup.name,
                speed: this.animationGroup.speedRatio
            });
        }
    }

    pauseAnimation() {
        if (this.animationGroup) {
            this.animationGroup.pause();
            this.isPlaying = false;
            
            if (this.boneAnimationWorker) {
                this.boneAnimationWorker.postMessage({ type: 'pause' });
            }
        }
    }

    stopAnimation() {
        if (this.animationGroup) {
            this.animationGroup.stop();
            this.animationGroup.reset();
            this.isPlaying = false;
            
            if (this.boneAnimationWorker) {
                this.boneAnimationWorker.postMessage({ type: 'stop' });
            }
        }
    }

    fitCameraToModel(root) {
        const boundingInfo = root.getHierarchyBoundingVectors();
        const size = boundingInfo.max.subtract(boundingInfo.min);
        const center = BABYLON.Vector3.Center(boundingInfo.min, boundingInfo.max);
        
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov;
        const distance = maxDim / (2 * Math.tan(fov / 2)) * 1.5;

        this.camera.setTarget(center);
        this.camera.radius = distance;
    }

    async exportGLTF() {
        try {
            const modelInfoEl = document.getElementById('modelInfo');
            if (modelInfoEl) modelInfoEl.textContent = '正在导出glTF...';

            const response = await fetch(`/api/models/${this.currentModel._id}/export-gltf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sceneData: { materials: this.materials.map(m => ({ name: m.name })) }
                })
            });

            const result = await response.json();
            
            if (modelInfoEl) modelInfoEl.textContent = `导出成功!`;
            
            if (result.gltfUrl) {
                const link = document.createElement('a');
                link.href = result.gltfUrl;
                link.download = this.currentModel.name + '.gltf';
                link.click();
            }

            setTimeout(() => {
                if (modelInfoEl) modelInfoEl.textContent = `模型: ${this.currentModel.name}`;
            }, 3000);

        } catch (err) {
            console.error('Export error:', err);
            alert('导出失败: ' + err.message);
        }
    }

    async loadRenderJobs() {
        try {
            const response = await fetch('/api/render');
            this.renderJobs = await response.json();
            this.renderRenderJobs();
            
            this.renderJobs.forEach(job => {
                if (job.status === 'pending' || job.status === 'processing') {
                    this.startJobPolling(job._id);
                }
            });
        } catch (err) {
            console.error('Error loading render jobs:', err);
        }
    }

    renderRenderJobs() {
        const container = document.getElementById('renderJobs');
        if (!container) return;
        
        if (this.renderJobs.length === 0) {
            container.innerHTML = '<p style="color: #888; font-size: 12px;">暂无渲染任务</p>';
            return;
        }

        container.innerHTML = this.renderJobs.map(job => `
            <div class="render-job-item status-${job.status}" data-job-id="${job._id}">
                <div class="render-job-name">${job.name}</div>
                <div class="render-job-status">${this.getStatusText(job.status)}</div>
                ${job.status !== 'completed' ? `
                    <div class="render-progress-bar">
                        <div class="render-progress-fill" style="width: ${job.progress || 0}%"></div>
                    </div>
                    <div class="render-progress-text">${job.progress || 0}%</div>
                ` : ''}
            </div>
        `).join('');
    }

    getStatusText(status) {
        const statusMap = {
            'pending': '排队中...',
            'processing': '渲染中...',
            'completed': '已完成',
            'failed': '失败'
        };
        return statusMap[status] || status;
    }

    startJobPolling(jobId) {
        if (this.pollIntervals.has(jobId)) return;

        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/render/${jobId}/poll`);
                const result = await response.json();

                const jobIndex = this.renderJobs.findIndex(j => j._id === jobId);
                if (jobIndex >= 0) {
                    this.renderJobs[jobIndex] = { ...this.renderJobs[jobIndex], ...result };
                    this.renderRenderJobs();
                }

                if (result.status === 'completed' || result.status === 'failed') {
                    clearInterval(interval);
                    this.pollIntervals.delete(jobId);
                    this.loadCompletedRenders();
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 2000);

        this.pollIntervals.set(jobId, interval);
    }

    async loadCompletedRenders() {
        try {
            const response = await fetch('/api/render/completed');
            const completedJobs = await response.json();
            this.renderCompletedRenders(completedJobs);
        } catch (err) {
            console.error('Error loading completed renders:', err);
        }
    }

    renderCompletedRenders(jobs) {
        const container = document.getElementById('renderResults');
        if (!container) return;
        
        if (jobs.length === 0) {
            container.innerHTML = '<p style="color: #888; font-size: 12px;">暂无渲染结果</p>';
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="render-result-item" data-job-id="${job._id}">
                <div class="render-result-header">
                    <span class="render-result-name">${job.name}</span>
                    <span class="render-result-date">${new Date(job.completedAt).toLocaleDateString()}</span>
                </div>
                <div class="render-result-actions">
                    <button class="btn btn-primary btn-small" onclick="editor.downloadRender('${job._id}')">下载</button>
                    <button class="btn btn-secondary btn-small" onclick="editor.shareRender('${job._id}')">分享</button>
                </div>
                <div id="share-link-${job._id}" style="display: none;"></div>
            </div>
        `).join('');
    }

    async downloadRender(jobId) {
        try {
            window.open(`/api/render/${jobId}/download`, '_blank');
        } catch (err) {
            console.error('Download error:', err);
            alert('下载失败: ' + err.message);
        }
    }

    async shareRender(jobId) {
        try {
            const response = await fetch(`/api/render/${jobId}/share`);
            const result = await response.json();
            
            const linkContainer = document.getElementById(`share-link-${jobId}`);
            if (linkContainer) {
                linkContainer.style.display = 'block';
                linkContainer.innerHTML = `
                    <div class="share-link" onclick="navigator.clipboard.writeText('${result.shareUrl}'); alert('链接已复制!');">
                        ${result.shareUrl}
                    </div>
                    <div style="font-size: 10px; color: #666; margin-top: 5px;">点击链接复制</div>
                `;
            }
        } catch (err) {
            console.error('Share error:', err);
            alert('生成分享链接失败: ' + err.message);
        }
    }

    async submitRenderJob() {
        const resolutionEl = document.getElementById('renderResolution');
        const nameEl = document.getElementById('renderName');
        
        if (!resolutionEl || !nameEl) return;
        
        const resolution = resolutionEl.value.split('x');
        const data = {
            modelId: this.currentModel._id,
            name: nameEl.value,
            settings: {
                width: parseInt(resolution[0]),
                height: parseInt(resolution[1]),
                samples: parseInt(document.getElementById('renderSamples')?.value || 64),
                engine: document.getElementById('renderEngine')?.value || 'cycles',
                cameraAngle: {
                    x: this.camera.alpha,
                    y: this.camera.beta,
                    z: this.camera.radius
                }
            }
        };

        try {
            const response = await fetch('/api/render/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            
            document.getElementById('renderModal').style.display = 'none';
            document.getElementById('renderForm').reset();
            
            this.loadRenderJobs();
            this.startJobPolling(result.jobId);
            
            alert(`渲染任务已提交! 任务ID: ${result.jobId}`);
        } catch (err) {
            console.error('Error submitting render job:', err);
            alert('提交渲染任务失败: ' + err.message);
        }
    }
}

let editor;
window.addEventListener('DOMContentLoaded', () => {
    editor = new WebGPUModelEditor();
});
