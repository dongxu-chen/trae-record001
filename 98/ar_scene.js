var arScene = {
    scene: null,
    camera: null,
    renderer: null,
    arToolkitSource: null,
    arToolkitContext: null,
    markerRoots: [],
    markerControlsList: [],
    ambientLight: null,
    directionalLight: null,
    defaultAmbientIntensity: 1.5,
    defaultDirectionalIntensity: 1,
    isInitialized: false,
    
    markerConfigs: [
        {
            id: 'hiro',
            type: 'pattern',
            patternUrl: 'https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.7/three.js/examples/marker-training/examples/data/patt.hiro',
            name: 'Hiro 标记'
        },
        {
            id: 'kanji',
            type: 'pattern',
            patternUrl: 'https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.7/three.js/examples/marker-training/examples/data/patt.kanji',
            name: 'Kanji 标记'
        },
        {
            id: 'a1',
            type: 'barcode',
            barcodeValue: 0,
            name: '条码标记 0'
        },
        {
            id: 'a2',
            type: 'barcode',
            barcodeValue: 1,
            name: '条码标记 1'
        }
    ],
    
    init: function() {
        var self = this;
        
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            logarithmicDepthBuffer: true,
            preserveDrawingBuffer: true
        });
        this.renderer.setClearColor(new THREE.Color('lightgrey'), 0);
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.style.position = 'absolute';
        this.renderer.domElement.style.top = '0px';
        this.renderer.domElement.style.left = '0px';
        this.renderer.domElement.id = 'ar-canvas';
        document.getElementById('container').appendChild(this.renderer.domElement);

        this.scene = new THREE.Scene();
        
        this.ambientLight = new THREE.AmbientLight(0x404040, this.defaultAmbientIntensity);
        this.scene.add(this.ambientLight);
        
        this.directionalLight = new THREE.DirectionalLight(0xffffff, this.defaultDirectionalIntensity);
        this.directionalLight.position.set(1, 1, 1);
        this.directionalLight.castShadow = true;
        this.directionalLight.shadow.mapSize.width = 1024;
        this.directionalLight.shadow.mapSize.height = 1024;
        this.directionalLight.shadow.camera.near = 0.1;
        this.directionalLight.shadow.camera.far = 10;
        this.directionalLight.shadow.camera.left = -1;
        this.directionalLight.shadow.camera.right = 1;
        this.directionalLight.shadow.camera.top = 1;
        this.directionalLight.shadow.camera.bottom = -1;
        this.scene.add(this.directionalLight);

        this.camera = new THREE.Camera();
        this.scene.add(this.camera);

        this.arToolkitSource = new THREEx.ArToolkitSource({
            sourceType: 'webcam',
            sourceWidth: 640,
            sourceHeight: 480
        });

        this.arToolkitSource.init(function onReady() {
            setTimeout(function() {
                arScene.onResize();
            }, 1000);
        });

        this.arToolkitContext = new THREEx.ArToolkitContext({
            cameraParametersUrl: 'https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.7/three.js/examples/marker-training/examples/data/camera_para.dat',
            detectionMode: 'mono_and_matrix',
            canvasWidth: 640,
            canvasHeight: 480,
            matrixCodeType: '3x3'
        });

        this.arToolkitContext.init(function onCompleted() {
            arScene.camera.projectionMatrix.copy(arScene.arToolkitContext.getProjectionMatrix());
            self.initMarkers();
        });

        this.scene.visible = false;

        window.addEventListener('resize', function() {
            arScene.onResize();
        });

        this.animate();
    },
    
    initMarkers: function() {
        var self = this;
        
        this.markerConfigs.forEach(function(config, index) {
            var markerRoot = new THREE.Group();
            markerRoot.userData.markerId = config.id;
            markerRoot.userData.markerName = config.name;
            markerRoot.userData.isARMarkerRoot = true;
            markerRoot.visible = false;
            self.scene.add(markerRoot);
            self.markerRoots.push(markerRoot);
            
            var controlOptions = {
                changeMatrixMode: 'cameraTransformMatrix'
            };
            
            if (config.type === 'pattern') {
                controlOptions.type = 'pattern';
                controlOptions.patternUrl = config.patternUrl;
            } else if (config.type === 'barcode') {
                controlOptions.type = 'barcode';
                controlOptions.barcodeValue = config.barcodeValue;
            }
            
            var markerControls = new THREEx.ArMarkerControls(
                self.arToolkitContext, 
                markerRoot, 
                controlOptions
            );
            self.markerControlsList.push(markerControls);
        });
        
        this.isInitialized = true;
        
        window.dispatchEvent(new CustomEvent('ar-markers-ready', {
            detail: {
                markerRoots: this.markerRoots,
                markerConfigs: this.markerConfigs
            }
        }));
    },

    onResize: function() {
        this.arToolkitSource.onResizeElement();
        this.arToolkitSource.copyElementSizeTo(this.renderer.domElement);
        
        if (this.arToolkitContext.arController !== null) {
            this.arToolkitSource.copyElementSizeTo(this.arToolkitContext.arController.canvas);
        }
        
        if (this.arToolkitContext.arController !== null) {
            this.arToolkitContext.arController.canvas.width = this.arToolkitSource.domElement.videoWidth || this.arToolkitSource.domElement.video.videoWidth;
            this.arToolkitContext.arController.canvas.height = this.arToolkitSource.domElement.videoHeight || this.arToolkitSource.domElement.video.videoHeight;
        }
    },
    
    updateLighting: function(ambientIntensity, directionalIntensity, color) {
        if (ambientIntensity !== undefined && this.ambientLight) {
            this.ambientLight.intensity = Math.max(0, Math.min(3, ambientIntensity));
        }
        if (directionalIntensity !== undefined && this.directionalLight) {
            this.directionalLight.intensity = Math.max(0, Math.min(3, directionalIntensity));
        }
        if (color !== undefined) {
            if (this.ambientLight) {
                this.ambientLight.color.set(color);
            }
            if (this.directionalLight) {
                this.directionalLight.color.set(color);
            }
        }
    },
    
    resetLighting: function() {
        this.updateLighting(
            this.defaultAmbientIntensity,
            this.defaultDirectionalIntensity,
            0xffffff
        );
    },
    
    getVisibleMarkers: function() {
        return this.markerRoots.filter(function(root) {
            return root.visible;
        });
    },
    
    getMarkerRootById: function(id) {
        return this.markerRoots.find(function(root) {
            return root.userData.markerId === id;
        });
    },

    animate: function() {
        var self = this;
        
        requestAnimationFrame(function() {
            self.animate();
        });

        if (this.arToolkitSource.ready === false) return;

        this.arToolkitContext.update(this.arToolkitSource.domElement);
        
        var anyVisible = this.markerRoots.some(function(root) {
            return root.visible;
        });
        
        if (anyVisible) {
            this.scene.visible = true;
        }
        
        this.renderer.render(this.scene, this.camera);
    }
};