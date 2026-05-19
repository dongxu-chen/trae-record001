class ThreeJSAvatar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        
        this.avatars = [];
        this.maxAvatars = 4;
        this.currentModel = 'default';
        this.showSkeleton = false;
        this.showWireframe = false;
        this.scale = 1;
        
        this.isInitialized = false;
        this.animationId = null;
        
        this.init();
    }
    
    init() {
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createLights();
        this.createControls();
        this.createGround();
        
        for (let i = 0; i < this.maxAvatars; i++) {
            this.createAvatar(i);
        }
        
        this.isInitialized = true;
        this.animate();
        this.log('Three.js 场景初始化完成');
    }
    
    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x87CEEB);
        this.scene.fog = new THREE.Fog(0x87CEEB, 10, 50);
    }
    
    createCamera() {
        const { clientWidth, clientHeight } = this.container;
        this.camera = new THREE.PerspectiveCamera(
            60,
            clientWidth / clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 1.5, 3);
    }
    
    createRenderer() {
        const { clientWidth, clientHeight } = this.container;
        
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(clientWidth, clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        this.container.appendChild(this.renderer.domElement);
        
        window.addEventListener('resize', () => this.onWindowResize());
    }
    
    createLights() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 7.5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);
        
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.3);
        fillLight.position.set(-5, 5, -5);
        this.scene.add(fillLight);
    }
    
    createControls() {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.target.set(0, 1, 0);
        this.controls.minDistance = 1;
        this.controls.maxDistance = 10;
    }
    
    createGround() {
        const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
        this.scene.add(gridHelper);
        
        const groundGeometry = new THREE.PlaneGeometry(20, 20);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a5f0b,
            roughness: 0.8
        });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);
    }
    
    createAvatar(index) {
        const avatarGroup = new THREE.Group();
        
        const offsetX = (index - 1.5) * 2.5;
        avatarGroup.position.set(offsetX, 0, 0);
        
        const skeleton = this.createSkeleton();
        avatarGroup.add(skeleton);
        
        const meshes = this.createAvatarMesh(this.currentModel, skeleton);
        avatarGroup.add(...meshes);
        
        const colors = [0x3498db, 0xe74c3c, 0x2ecc71, 0xf39c12];
        avatarGroup.traverse((child) => {
            if (child.isMesh && child.material.color) {
                if (index > 0 && this.currentModel === 'default') {
                    child.material.color.setHex(colors[index % colors.length]);
                }
            }
        });
        
        avatarGroup.userData = {
            index,
            skeleton,
            meshes,
            active: index === 0,
            blendshapes: {},
            poseData: null
        };
        
        this.avatars.push(avatarGroup);
        this.scene.add(avatarGroup);
        
        return avatarGroup;
    }
    
    createSkeleton() {
        const boneData = this.getHumanoidBoneStructure();
        const bones = [];
        
        boneData.forEach(data => {
            const bone = new THREE.Bone();
            bone.name = data.name;
            bone.position.set(...data.position);
            bones.push(bone);
        });
        
        boneData.forEach((data, index) => {
            if (data.parent !== null) {
                const parentIndex = boneData.findIndex(b => b.name === data.parent);
                if (parentIndex !== -1) {
                    bones[parentIndex].add(bones[index]);
                }
            }
        });
        
        const skeleton = new THREE.Skeleton(bones);
        
        const skeletonHelper = new THREE.SkeletonHelper(bones[0]);
        skeletonHelper.visible = this.showSkeleton;
        skeletonHelper.name = 'skeletonHelper';
        
        const rootBone = bones[0];
        rootBone.add(skeletonHelper);
        
        return rootBone;
    }
    
    getHumanoidBoneStructure() {
        return [
            { name: 'Hips', parent: null, position: [0, 0.9, 0] },
            { name: 'Spine', parent: 'Hips', position: [0, 0.25, 0] },
            { name: 'Chest', parent: 'Spine', position: [0, 0.25, 0] },
            { name: 'UpperChest', parent: 'Chest', position: [0, 0.2, 0] },
            { name: 'Neck', parent: 'UpperChest', position: [0, 0.15, 0] },
            { name: 'Head', parent: 'Neck', position: [0, 0.2, 0] },
            
            { name: 'LeftShoulder', parent: 'UpperChest', position: [0.2, 0, 0] },
            { name: 'LeftUpperArm', parent: 'LeftShoulder', position: [0.25, 0, 0] },
            { name: 'LeftLowerArm', parent: 'LeftUpperArm', position: [0.3, 0, 0] },
            { name: 'LeftHand', parent: 'LeftLowerArm', position: [0.25, 0, 0] },
            
            { name: 'RightShoulder', parent: 'UpperChest', position: [-0.2, 0, 0] },
            { name: 'RightUpperArm', parent: 'RightShoulder', position: [-0.25, 0, 0] },
            { name: 'RightLowerArm', parent: 'RightUpperArm', position: [-0.3, 0, 0] },
            { name: 'RightHand', parent: 'RightLowerArm', position: [-0.25, 0, 0] },
            
            { name: 'LeftUpperLeg', parent: 'Hips', position: [0.12, -0.1, 0] },
            { name: 'LeftLowerLeg', parent: 'LeftUpperLeg', position: [0, -0.45, 0] },
            { name: 'LeftFoot', parent: 'LeftLowerLeg', position: [0, -0.45, 0] },
            
            { name: 'RightUpperLeg', parent: 'Hips', position: [-0.12, -0.1, 0] },
            { name: 'RightLowerLeg', parent: 'RightUpperLeg', position: [0, -0.45, 0] },
            { name: 'RightFoot', parent: 'RightLowerLeg', position: [0, -0.45, 0] },
        ];
    }
    
    createAvatarMesh(modelType, skeleton) {
        const meshes = [];
        
        switch (modelType) {
            case 'robot':
                meshes.push(...this.createRobotMesh());
                break;
            case 'cartoon':
                meshes.push(...this.createCartoonMesh());
                break;
            case 'skeleton':
                meshes.push(...this.createSkeletonMesh());
                break;
            default:
                meshes.push(...this.createDefaultMesh());
        }
        
        return meshes;
    }
    
    createDefaultMesh() {
        const meshes = [];
        const material = new THREE.MeshStandardMaterial({
            color: 0x3498db,
            roughness: 0.5,
            metalness: 0.1,
            wireframe: this.showWireframe
        });
        
        const headGeo = new THREE.SphereGeometry(0.18, 32, 32);
        const head = new THREE.Mesh(headGeo, material.clone());
        head.position.set(0, 1.7, 0);
        head.castShadow = true;
        head.name = 'Head';
        meshes.push(head);
        
        const bodyGeo = new THREE.CapsuleGeometry(0.15, 0.5, 8, 16);
        const body = new THREE.Mesh(bodyGeo, material.clone());
        body.position.set(0, 1.1, 0);
        body.castShadow = true;
        body.name = 'Body';
        meshes.push(body);
        
        const armGeo = new THREE.CapsuleGeometry(0.05, 0.4, 4, 8);
        const leftArm = new THREE.Mesh(armGeo, material.clone());
        leftArm.position.set(0.35, 1.25, 0);
        leftArm.rotation.z = Math.PI / 6;
        leftArm.castShadow = true;
        leftArm.name = 'LeftArm';
        meshes.push(leftArm);
        
        const rightArm = new THREE.Mesh(armGeo, material.clone());
        rightArm.position.set(-0.35, 1.25, 0);
        rightArm.rotation.z = -Math.PI / 6;
        rightArm.castShadow = true;
        rightArm.name = 'RightArm';
        meshes.push(rightArm);
        
        const legGeo = new THREE.CapsuleGeometry(0.06, 0.55, 4, 8);
        const leftLeg = new THREE.Mesh(legGeo, material.clone());
        leftLeg.position.set(0.12, 0.45, 0);
        leftLeg.castShadow = true;
        leftLeg.name = 'LeftLeg';
        meshes.push(leftLeg);
        
        const rightLeg = new THREE.Mesh(legGeo, material.clone());
        rightLeg.position.set(-0.12, 0.45, 0);
        rightLeg.castShadow = true;
        rightLeg.name = 'RightLeg';
        meshes.push(rightLeg);
        
        return meshes;
    }
    
    createRobotMesh() {
        const meshes = [];
        const metalMaterial = new THREE.MeshStandardMaterial({
            color: 0x607d8b,
            roughness: 0.3,
            metalness: 0.8,
            wireframe: this.showWireframe
        });
        
        const headGeo = new THREE.BoxGeometry(0.2, 0.2, 0.2);
        const head = new THREE.Mesh(headGeo, metalMaterial.clone());
        head.position.set(0, 1.7, 0);
        head.castShadow = true;
        meshes.push(head);
        
        const eyeGeo = new THREE.SphereGeometry(0.03, 16, 16);
        const eyeMaterial = new THREE.MeshStandardMaterial({
            color: 0x00ff00,
            emissive: 0x00ff00,
            emissiveIntensity: 0.5
        });
        const leftEye = new THREE.Mesh(eyeGeo, eyeMaterial);
        leftEye.position.set(0.06, 1.72, 0.09);
        meshes.push(leftEye);
        
        const rightEye = new THREE.Mesh(eyeGeo, eyeMaterial);
        rightEye.position.set(-0.06, 1.72, 0.09);
        meshes.push(rightEye);
        
        const bodyGeo = new THREE.BoxGeometry(0.3, 0.5, 0.2);
        const body = new THREE.Mesh(bodyGeo, metalMaterial.clone());
        body.position.set(0, 1.1, 0);
        body.castShadow = true;
        meshes.push(body);
        
        const limbGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.45, 16);
        
        const leftArm = new THREE.Mesh(limbGeo, metalMaterial.clone());
        leftArm.position.set(0.3, 1.25, 0);
        leftArm.rotation.z = Math.PI / 6;
        leftArm.castShadow = true;
        meshes.push(leftArm);
        
        const rightArm = new THREE.Mesh(limbGeo, metalMaterial.clone());
        rightArm.position.set(-0.3, 1.25, 0);
        rightArm.rotation.z = -Math.PI / 6;
        rightArm.castShadow = true;
        meshes.push(rightArm);
        
        const leftLeg = new THREE.Mesh(limbGeo, metalMaterial.clone());
        leftLeg.position.set(0.12, 0.5, 0);
        leftLeg.castShadow = true;
        meshes.push(leftLeg);
        
        const rightLeg = new THREE.Mesh(limbGeo, metalMaterial.clone());
        rightLeg.position.set(-0.12, 0.5, 0);
        rightLeg.castShadow = true;
        meshes.push(rightLeg);
        
        return meshes;
    }
    
    createCartoonMesh() {
        const meshes = [];
        const skinMaterial = new THREE.MeshStandardMaterial({
            color: 0xffdbac,
            roughness: 0.6,
            wireframe: this.showWireframe
        });
        
        const headGeo = new THREE.SphereGeometry(0.22, 32, 32);
        const head = new THREE.Mesh(headGeo, skinMaterial.clone());
        head.position.set(0, 1.75, 0);
        head.scale.y = 1.1;
        head.castShadow = true;
        meshes.push(head);
        
        const eyeGeo = new THREE.SphereGeometry(0.06, 16, 16);
        const eyeMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff });
        const leftEye = new THREE.Mesh(eyeGeo, eyeMaterial);
        leftEye.position.set(0.08, 1.78, 0.18);
        meshes.push(leftEye);
        
        const rightEye = new THREE.Mesh(eyeGeo, eyeMaterial);
        rightEye.position.set(-0.08, 1.78, 0.18);
        meshes.push(rightEye);
        
        const pupilGeo = new THREE.SphereGeometry(0.025, 16, 16);
        const pupilMaterial = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const leftPupil = new THREE.Mesh(pupilGeo, pupilMaterial);
        leftPupil.position.set(0.08, 1.78, 0.23);
        meshes.push(leftPupil);
        
        const rightPupil = new THREE.Mesh(pupilGeo, pupilMaterial);
        rightPupil.position.set(-0.08, 1.78, 0.23);
        meshes.push(rightPupil);
        
        const bodyGeo = new THREE.CapsuleGeometry(0.15, 0.45, 8, 16);
        const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xff6b6b, roughness: 0.7 });
        const body = new THREE.Mesh(bodyGeo, bodyMaterial);
        body.position.set(0, 1.1, 0);
        body.castShadow = true;
        meshes.push(body);
        
        return meshes;
    }
    
    createSkeletonMesh() {
        const meshes = [];
        const boneMaterial = new THREE.MeshStandardMaterial({
            color: 0xeeeeee,
            roughness: 0.8,
            wireframe: this.showWireframe
        });
        
        const jointGeo = new THREE.SphereGeometry(0.04, 16, 16);
        const limbGeo = new THREE.CylinderGeometry(0.025, 0.025, 0.4, 16);
        
        const jointPositions = [
            [0, 0.9, 0], [0, 1.15, 0], [0, 1.4, 0], [0, 1.6, 0], [0, 1.75, 0],
            [0.4, 1.4, 0], [0.7, 1.35, 0], [1.0, 1.3, 0],
            [-0.4, 1.4, 0], [-0.7, 1.35, 0], [-1.0, 1.3, 0],
            [0.15, 0.6, 0], [0.15, 0.15, 0], [0.15, -0.3, 0],
            [-0.15, 0.6, 0], [-0.15, 0.15, 0], [-0.15, -0.3, 0]
        ];
        
        jointPositions.forEach(pos => {
            const joint = new THREE.Mesh(jointGeo, boneMaterial.clone());
            joint.position.set(...pos);
            meshes.push(joint);
        });
        
        return meshes;
    }
    
    updateAvatarPose(avatarIndex, poseData) {
        const avatar = this.avatars[avatarIndex];
        if (!avatar || !poseData) return;
        
        avatar.userData.poseData = poseData;
        this.applyPoseToSkeleton(avatar.userData.skeleton, poseData);
    }
    
    applyPoseToSkeleton(skeleton, poseData) {
        const landmarks = poseData.smoothed?.pose || poseData.poseLandmarks;
        if (!landmarks) return;
        
        const boneMap = this.getBoneMap(skeleton);
        
        this.updateBodyTransform(boneMap, landmarks);
        this.updateArmTransform(boneMap, landmarks, 'Left');
        this.updateArmTransform(boneMap, landmarks, 'Right');
        this.updateLegTransform(boneMap, landmarks, 'Left');
        this.updateLegTransform(boneMap, landmarks, 'Right');
    }
    
    getBoneMap(skeleton) {
        const boneMap = {};
        skeleton.traverse((bone) => {
            if (bone.isBone) {
                boneMap[bone.name] = bone;
            }
        });
        return boneMap;
    }
    
    updateBodyTransform(boneMap, landmarks) {
        const leftShoulder = landmarks[11];
        const rightShoulder = landmarks[12];
        const leftHip = landmarks[23];
        const rightHip = landmarks[24];
        
        if (leftShoulder && rightShoulder && leftHip && rightHip) {
            const shoulderCenterY = (leftShoulder.y + rightShoulder.y) / 2;
            const hipCenterY = (leftHip.y + rightHip.y) / 2;
            const spineLength = Math.abs(hipCenterY - shoulderCenterY);
            
            const roll = Math.atan2(rightShoulder.x - leftShoulder.x, rightShoulder.z - leftShoulder.z);
            
            if (boneMap['UpperChest']) {
                boneMap['UpperChest'].rotation.z = roll * 0.5;
            }
            if (boneMap['Chest']) {
                boneMap['Chest'].rotation.z = roll * 0.3;
            }
            
            if (boneMap['Head']) {
                const nose = landmarks[0];
                if (nose) {
                    const headY = (1 - nose.y) * 0.3;
                    boneMap['Head'].position.y = 0.2 + headY * 0.1;
                    
                    const headTilt = (rightShoulder.visibility - leftShoulder.visibility) * 0.2;
                    boneMap['Head'].rotation.z = headTilt;
                }
            }
        }
    }
    
    updateArmTransform(boneMap, landmarks, side) {
        const shoulderIdx = side === 'Left' ? 11 : 12;
        const elbowIdx = side === 'Left' ? 13 : 14;
        const wristIdx = side === 'Left' ? 15 : 16;
        
        const shoulder = landmarks[shoulderIdx];
        const elbow = landmarks[elbowIdx];
        const wrist = landmarks[wristIdx];
        
        if (!shoulder || !elbow || !wrist) return;
        
        const sideFactor = side === 'Left' ? 1 : -1;
        
        const upperArmBone = boneMap[`${side}UpperArm`];
        const lowerArmBone = boneMap[`${side}LowerArm`];
        const handBone = boneMap[`${side}Hand`];
        
        if (upperArmBone) {
            const armAngleX = Math.atan2(elbow.y - shoulder.y, elbow.z - shoulder.z);
            const armAngleY = Math.atan2(elbow.x - shoulder.x, elbow.z - shoulder.z);
            
            upperArmBone.rotation.x = armAngleX * 0.5;
            upperArmBone.rotation.y = armAngleY * 0.5 * sideFactor;
            
            const armLength = Math.sqrt(
                Math.pow(elbow.x - shoulder.x, 2) +
                Math.pow(elbow.y - shoulder.y, 2)
            );
            upperArmBone.scale.y = 0.5 + armLength * 0.5;
        }
        
        if (lowerArmBone && upperArmBone) {
            const forearmAngle = Math.atan2(wrist.y - elbow.y, wrist.x - elbow.x) - 
                                 Math.atan2(elbow.y - shoulder.y, elbow.x - shoulder.x);
            lowerArmBone.rotation.x = forearmAngle * 0.3;
        }
    }
    
    updateLegTransform(boneMap, landmarks, side) {
        const hipIdx = side === 'Left' ? 23 : 24;
        const kneeIdx = side === 'Left' ? 25 : 26;
        const ankleIdx = side === 'Left' ? 27 : 28;
        
        const hip = landmarks[hipIdx];
        const knee = landmarks[kneeIdx];
        const ankle = landmarks[ankleIdx];
        
        if (!hip || !knee || !ankle) return;
        
        const upperLegBone = boneMap[`${side}UpperLeg`];
        const lowerLegBone = boneMap[`${side}LowerLeg`];
        
        if (upperLegBone) {
            const legAngle = Math.atan2(hip.y - knee.y, hip.x - knee.x) - Math.PI / 2;
            upperLegBone.rotation.x = legAngle * 0.3;
        }
        
        if (lowerLegBone) {
            const kneeAngle = Math.atan2(knee.y - ankle.y, knee.x - ankle.x) -
                             Math.atan2(hip.y - knee.y, hip.x - knee.x);
            lowerLegBone.rotation.x = kneeAngle * 0.2;
        }
    }
    
    updateFaceBlendshapes(avatarIndex, blendshapes) {
        const avatar = this.avatars[avatarIndex];
        if (!avatar) return;
        
        avatar.userData.blendshapes = blendshapes;
        
        const head = avatar.children.find(c => c.name === 'Head');
        if (head) {
            if (blendshapes.jawOpen) {
                head.scale.y = 1 + blendshapes.jawOpen * 0.1;
            }
            
            if (blendshapes.mouthSmileLeft || blendshapes.mouthSmileRight) {
                const smile = (blendshapes.mouthSmileLeft + blendshapes.mouthSmileRight) / 2;
                head.scale.z = 1 + smile * 0.05;
            }
        }
    }
    
    setAvatarActive(avatarIndex, active) {
        const avatar = this.avatars[avatarIndex];
        if (avatar) {
            avatar.userData.active = active;
            avatar.visible = true;
        }
    }
    
    changeModel(modelType) {
        this.currentModel = modelType;
        
        this.avatars.forEach((avatar, index) => {
            const oldMeshes = avatar.userData.meshes;
            oldMeshes.forEach(mesh => {
                avatar.remove(mesh);
                if (mesh.geometry) mesh.geometry.dispose();
                if (mesh.material) mesh.material.dispose();
            });
            
            const newMeshes = this.createAvatarMesh(modelType, avatar.userData.skeleton);
            avatar.userData.meshes = newMeshes;
            avatar.add(...newMeshes);
        });
        
        this.log(`切换形象模型: ${modelType}`);
    }
    
    setScale(scale) {
        this.scale = scale;
        this.avatars.forEach(avatar => {
            avatar.scale.setScalar(scale);
        });
    }
    
    toggleWireframe() {
        this.showWireframe = !this.showWireframe;
        this.avatars.forEach(avatar => {
            avatar.traverse((child) => {
                if (child.isMesh && child.material) {
                    child.material.wireframe = this.showWireframe;
                }
            });
        });
        return this.showWireframe;
    }
    
    toggleSkeleton() {
        this.showSkeleton = !this.showSkeleton;
        this.avatars.forEach(avatar => {
            const helper = avatar.userData.skeleton.getObjectByName('skeletonHelper');
            if (helper) {
                helper.visible = this.showSkeleton;
            }
        });
        return this.showSkeleton;
    }
    
    resetCamera() {
        this.camera.position.set(0, 1.5, 3);
        this.controls.target.set(0, 1, 0);
        this.controls.update();
    }
    
    onWindowResize() {
        const { clientWidth, clientHeight } = this.container;
        this.camera.aspect = clientWidth / clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(clientWidth, clientHeight);
    }
    
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
    
    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        this.avatars.forEach(avatar => {
            avatar.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(m => m.dispose());
                    } else {
                        child.material.dispose();
                    }
                }
            });
        });
        
        this.renderer.dispose();
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #00bfff">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 5000);
        }
    }
}