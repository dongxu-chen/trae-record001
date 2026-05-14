var productLoader = {
    loader: null,
    productModel: null,
    markerRoot: null,
    groundPlane: null,
    products: {},
    
    init: function() {
        this.loader = new THREE.GLTFLoader();
        
        if (arScene.isInitialized) {
            this.setupInitialProduct();
        } else {
            var self = this;
            window.addEventListener('ar-markers-ready', function() {
                self.setupInitialProduct();
            });
        }
    },
    
    setupInitialProduct: function() {
        if (arScene.markerRoots && arScene.markerRoots.length > 0) {
            this.markerRoot = arScene.markerRoots[0];
        }
    },
    
    createGroundPlane: function(parent) {
        var groundGeometry = new THREE.PlaneGeometry(2, 2);
        var groundMaterial = new THREE.ShadowMaterial({
            opacity: 0.5
        });
        
        var groundPlane = new THREE.Mesh(groundGeometry, groundMaterial);
        groundPlane.receiveShadow = true;
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = -0.01;
        
        if (parent) {
            parent.add(groundPlane);
        }
        
        return groundPlane;
    },
    
    loadDefaultProduct: function() {
        this.createPlaceholderProduct();
    },
    
    createPlaceholderProduct: function(parent, options) {
        options = options || {};
        var color = options.color || 0x4CAF50;
        var scale = options.scale || 0.8;
        
        var group = new THREE.Group();
        
        var geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        var material = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.4,
            metalness: 0.6
        });
        var cube = new THREE.Mesh(geometry, material);
        cube.position.y = 0.25;
        cube.castShadow = true;
        cube.receiveShadow = true;
        group.add(cube);
        
        var roofGeometry = new THREE.ConeGeometry(0.35, 0.3, 4);
        var roofMaterial = new THREE.MeshStandardMaterial({
            color: 0x8B4513,
            roughness: 0.6
        });
        var roof = new THREE.Mesh(roofGeometry, roofMaterial);
        roof.position.y = 0.65;
        roof.rotation.y = Math.PI / 4;
        roof.castShadow = true;
        roof.receiveShadow = true;
        group.add(roof);
        
        var doorGeometry = new THREE.BoxGeometry(0.15, 0.2, 0.05);
        var doorMaterial = new THREE.MeshStandardMaterial({
            color: 0x654321
        });
        var door = new THREE.Mesh(doorGeometry, doorMaterial);
        door.position.set(0, 0.1, 0.28);
        door.castShadow = true;
        door.receiveShadow = true;
        group.add(door);
        
        var windowGeometry = new THREE.BoxGeometry(0.1, 0.1, 0.05);
        var windowMaterial = new THREE.MeshStandardMaterial({
            color: 0x87CEEB,
            metalness: 0.8,
            roughness: 0.2
        });
        var window1 = new THREE.Mesh(windowGeometry, windowMaterial);
        window1.position.set(-0.15, 0.25, 0.28);
        window1.castShadow = true;
        window1.receiveShadow = true;
        group.add(window1);
        
        var window2 = new THREE.Mesh(windowGeometry, windowMaterial);
        window2.position.set(0.15, 0.25, 0.28);
        window2.castShadow = true;
        window2.receiveShadow = true;
        group.add(window2);
        
        group.userData.isProduct = true;
        group.scale.set(scale, scale, scale);
        group.rotation.x = -Math.PI / 2;
        
        if (parent) {
            parent.add(group);
        } else if (this.markerRoot) {
            this.productModel = group;
            this.markerRoot.add(group);
        }
        
        return group;
    },
    
    setupModelShadows: function(model) {
        model.traverse(function(child) {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(function(mat) {
                            if (mat) mat.needsUpdate = true;
                        });
                    } else {
                        child.material.needsUpdate = true;
                    }
                }
            }
        });
    },
    
    loadGLTF: function(url, parent, options) {
        var self = this;
        options = options || {};
        var targetParent = parent || this.markerRoot;
        var productId = options.id || 'default';
        
        return new Promise(function(resolve, reject) {
            self.loader.load(
                url,
                function(gltf) {
                    var model = gltf.scene;
                    model.userData.isProduct = true;
                    
                    self.setupModelShadows(model);
                    
                    var box = new THREE.Box3().setFromObject(model);
                    var size = box.getSize(new THREE.Vector3());
                    var center = box.getCenter(new THREE.Vector3());
                    
                    var maxDim = Math.max(size.x, size.y, size.z);
                    var scale = options.scale || (0.5 / maxDim);
                    model.scale.set(scale, scale, scale);
                    
                    model.position.y = options.yOffset || (-center.y * scale);
                    model.rotation.x = options.rotationX !== undefined ? options.rotationX : -Math.PI / 2;
                    
                    if (targetParent) {
                        targetParent.add(model);
                    }
                    
                    self.products[productId] = model;
                    
                    if (!parent) {
                        self.productModel = model;
                    }
                    
                    resolve(model);
                },
                function(xhr) {
                    console.log((xhr.loaded / xhr.total * 100) + '% 已加载');
                },
                function(error) {
                    console.error('加载模型失败:', error);
                    
                    var fallback = self.createPlaceholderProduct(targetParent, options);
                    self.products[productId] = fallback;
                    
                    if (!parent) {
                        self.productModel = fallback;
                    }
                    
                    reject(error);
                }
            );
        });
    },
    
    loadProductForMarker: function(markerId, url, options) {
        var markerRoot = arScene.getMarkerRootById(markerId);
        if (!markerRoot) {
            console.error('找不到标记:', markerId);
            return null;
        }
        
        options = options || {};
        options.id = markerId;
        
        return this.loadGLTF(url, markerRoot, options);
    },
    
    getProduct: function(id) {
        if (id) {
            return this.products[id];
        }
        return this.productModel;
    },
    
    getAllProducts: function() {
        return this.products;
    },
    
    removeProduct: function(id) {
        var product = this.products[id];
        if (product && product.parent) {
            product.parent.remove(product);
        }
        delete this.products[id];
    },
    
    clearAllProducts: function() {
        var self = this;
        Object.keys(this.products).forEach(function(id) {
            self.removeProduct(id);
        });
    }
};