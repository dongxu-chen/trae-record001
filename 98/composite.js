var composite = {
    markerProducts: {},
    compositeModes: {
        individual: 'individual',
        combine: 'combine',
        sequence: 'sequence'
    },
    currentMode: 'individual',
    visibleMarkerIds: [],
    lastVisibleMarkerIds: [],
    
    productTemplates: {
        hiro: {
            type: 'house',
            color: 0x4CAF50,
            scale: 0.8
        },
        kanji: {
            type: 'sphere',
            color: 0x2196F3,
            scale: 1.0
        },
        a1: {
            type: 'cone',
            color: 0xFF9800,
            scale: 0.9
        },
        a2: {
            type: 'torus',
            color: 0x9C27B0,
            scale: 0.7
        }
    },
    
    init: function() {
        var self = this;
        
        if (arScene.isInitialized) {
            this.setupProducts();
        } else {
            window.addEventListener('ar-markers-ready', function(event) {
                self.setupProducts();
            });
        }
        
        this.setupUI();
        this.startMonitoring();
    },
    
    setupProducts: function() {
        var self = this;
        
        arScene.markerRoots.forEach(function(markerRoot) {
            var markerId = markerRoot.userData.markerId;
            var template = self.productTemplates[markerId];
            
            if (template) {
                var product = self.createProductFromTemplate(template, markerId);
                markerRoot.add(product);
                self.markerProducts[markerId] = product;
            }
        });
        
        this.createGroundPlanes();
    },
    
    createProductFromTemplate: function(template, markerId) {
        var group = new THREE.Group();
        group.userData.markerId = markerId;
        group.userData.template = template;
        
        var geometry;
        var material = new THREE.MeshStandardMaterial({
            color: template.color,
            roughness: 0.4,
            metalness: 0.6
        });
        
        switch(template.type) {
            case 'house':
                var box = new THREE.Mesh(
                    new THREE.BoxGeometry(0.5, 0.5, 0.5),
                    material
                );
                box.position.y = 0.25;
                box.castShadow = true;
                box.receiveShadow = true;
                group.add(box);
                
                var roofMaterial = new THREE.MeshStandardMaterial({
                    color: 0x8B4513,
                    roughness: 0.6
                });
                var roof = new THREE.Mesh(
                    new THREE.ConeGeometry(0.35, 0.3, 4),
                    roofMaterial
                );
                roof.position.y = 0.65;
                roof.rotation.y = Math.PI / 4;
                roof.castShadow = true;
                roof.receiveShadow = true;
                group.add(roof);
                break;
                
            case 'sphere':
                geometry = new THREE.SphereGeometry(0.25, 32, 32);
                var sphere = new THREE.Mesh(geometry, material);
                sphere.position.y = 0.25;
                sphere.castShadow = true;
                sphere.receiveShadow = true;
                group.add(sphere);
                
                var ringGeometry = new THREE.TorusGeometry(0.35, 0.03, 16, 100);
                var ringMaterial = new THREE.MeshStandardMaterial({
                    color: 0xFFFFFF,
                    metalness: 0.9,
                    roughness: 0.1
                });
                var ring = new THREE.Mesh(ringGeometry, ringMaterial);
                ring.rotation.x = Math.PI / 2;
                ring.position.y = 0.25;
                ring.castShadow = true;
                group.add(ring);
                break;
                
            case 'cone':
                geometry = new THREE.ConeGeometry(0.3, 0.6, 32);
                var cone = new THREE.Mesh(geometry, material);
                cone.position.y = 0.3;
                cone.castShadow = true;
                cone.receiveShadow = true;
                group.add(cone);
                
                var baseGeometry = new THREE.CylinderGeometry(0.3, 0.35, 0.1, 32);
                var baseMaterial = new THREE.MeshStandardMaterial({
                    color: 0x5D4037,
                    roughness: 0.8
                });
                var base = new THREE.Mesh(baseGeometry, baseMaterial);
                base.position.y = 0.05;
                base.castShadow = true;
                base.receiveShadow = true;
                group.add(base);
                break;
                
            case 'torus':
                geometry = new THREE.TorusGeometry(0.2, 0.08, 16, 100);
                var torus = new THREE.Mesh(geometry, material);
                torus.position.y = 0.25;
                torus.castShadow = true;
                torus.receiveShadow = true;
                group.add(torus);
                
                var innerGeometry = new THREE.SphereGeometry(0.12, 16, 16);
                var innerMaterial = new THREE.MeshStandardMaterial({
                    color: 0xFFFFFF,
                    emissive: 0x333333,
                    metalness: 0.5,
                    roughness: 0.3
                });
                var inner = new THREE.Mesh(innerGeometry, innerMaterial);
                inner.position.y = 0.25;
                inner.castShadow = true;
                group.add(inner);
                break;
                
            default:
                geometry = new THREE.BoxGeometry(0.3, 0.3, 0.3);
                var defaultMesh = new THREE.Mesh(geometry, material);
                defaultMesh.position.y = 0.15;
                defaultMesh.castShadow = true;
                defaultMesh.receiveShadow = true;
                group.add(defaultMesh);
        }
        
        group.scale.set(template.scale, template.scale, template.scale);
        group.rotation.x = -Math.PI / 2;
        
        return group;
    },
    
    createGroundPlanes: function() {
        arScene.markerRoots.forEach(function(markerRoot) {
            var groundGeometry = new THREE.PlaneGeometry(2, 2);
            var groundMaterial = new THREE.ShadowMaterial({
                opacity: 0.5
            });
            
            var groundPlane = new THREE.Mesh(groundGeometry, groundMaterial);
            groundPlane.receiveShadow = true;
            groundPlane.rotation.x = -Math.PI / 2;
            groundPlane.position.y = -0.01;
            
            markerRoot.add(groundPlane);
        });
    },
    
    setupUI: function() {
        var self = this;
        
        var controlsDiv = document.createElement('div');
        controlsDiv.id = 'composite-controls';
        controlsDiv.style.cssText = `
            position: absolute;
            top: 60px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            padding: 10px;
            border-radius: 5px;
            color: white;
            font-size: 12px;
            z-index: 100;
            max-width: 200px;
        `;
        
        var title = document.createElement('div');
        title.style.cssText = 'font-weight: bold; margin-bottom: 10px;';
        title.textContent = '组合控制';
        controlsDiv.appendChild(title);
        
        var modes = [
            { id: 'individual', label: '独立显示' },
            { id: 'combine', label: '组合显示' },
            { id: 'sequence', label: '序列显示' }
        ];
        
        modes.forEach(function(mode) {
            var label = document.createElement('label');
            label.style.cssText = 'display: block; margin: 5px 0; cursor: pointer;';
            
            var radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'composite-mode';
            radio.value = mode.id;
            radio.checked = mode.id === self.currentMode;
            radio.style.cssText = 'margin-right: 5px;';
            
            radio.addEventListener('change', function() {
                self.setMode(mode.id);
            });
            
            label.appendChild(radio);
            label.appendChild(document.createTextNode(mode.label));
            controlsDiv.appendChild(label);
        });
        
        var statusDiv = document.createElement('div');
        statusDiv.id = 'marker-status';
        statusDiv.style.cssText = 'margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.3);';
        statusDiv.innerHTML = '<div style="margin-bottom: 5px;">检测到的标记:</div><div id="visible-markers">无</div>';
        controlsDiv.appendChild(statusDiv);
        
        document.body.appendChild(controlsDiv);
    },
    
    setMode: function(mode) {
        this.currentMode = mode;
        this.applyVisibilityRules();
    },
    
    startMonitoring: function() {
        var self = this;
        
        function monitor() {
            self.visibleMarkerIds = arScene.getVisibleMarkers().map(function(root) {
                return root.userData.markerId;
            });
            
            self.updateStatus();
            
            var hasChanged = JSON.stringify(self.visibleMarkerIds) !== JSON.stringify(self.lastVisibleMarkerIds);
            if (hasChanged) {
                self.applyVisibilityRules();
                self.lastVisibleMarkerIds = [...self.visibleMarkerIds];
            }
            
            requestAnimationFrame(monitor);
        }
        
        monitor();
    },
    
    updateStatus: function() {
        var statusElement = document.getElementById('visible-markers');
        if (statusElement) {
            if (this.visibleMarkerIds.length === 0) {
                statusElement.textContent = '无';
            } else {
                var names = this.visibleMarkerIds.map(function(id) {
                    var config = arScene.markerConfigs.find(function(c) {
                        return c.id === id;
                    });
                    return config ? config.name : id;
                });
                statusElement.textContent = names.join(', ');
            }
        }
    },
    
    applyVisibilityRules: function() {
        var self = this;
        
        switch(this.currentMode) {
            case this.compositeModes.individual:
                this.applyIndividualMode();
                break;
            case this.compositeModes.combine:
                this.applyCombineMode();
                break;
            case this.compositeModes.sequence:
                this.applySequenceMode();
                break;
        }
    },
    
    applyIndividualMode: function() {
        arScene.markerRoots.forEach(function(root) {
            var product = self.markerProducts[root.userData.markerId];
            if (product) {
                product.visible = root.visible;
            }
        });
    },
    
    applyCombineMode: function() {
        var visibleCount = this.visibleMarkerIds.length;
        
        if (visibleCount >= 2) {
            this.showCombinedProduct();
        } else if (visibleCount === 1) {
            this.applyIndividualMode();
        } else {
            arScene.markerRoots.forEach(function(root) {
                var product = self.markerProducts[root.userData.markerId];
                if (product) {
                    product.visible = false;
                }
            });
        }
    },
    
    showCombinedProduct: function() {
        this.hideAllProducts();
        
        var firstMarker = arScene.getMarkerRootById(this.visibleMarkerIds[0]);
        if (firstMarker) {
            var combinedProduct = this.createCombinedProduct();
            firstMarker.add(combinedProduct);
            
            setTimeout(function() {
                firstMarker.remove(combinedProduct);
            }, 3000);
        }
    },
    
    createCombinedProduct: function() {
        var group = new THREE.Group();
        group.userData.isCombined = true;
        
        var colors = [0x4CAF50, 0x2196F3, 0xFF9800, 0x9C27B0];
        
        for (var i = 0; i < 4; i++) {
            var geometry = new THREE.BoxGeometry(0.15, 0.15, 0.15);
            var material = new THREE.MeshStandardMaterial({
                color: colors[i],
                roughness: 0.3,
                metalness: 0.7
            });
            var cube = new THREE.Mesh(geometry, material);
            cube.castShadow = true;
            cube.receiveShadow = true;
            
            var angle = (i / 4) * Math.PI * 2;
            cube.position.x = Math.cos(angle) * 0.15;
            cube.position.z = Math.sin(angle) * 0.15;
            cube.position.y = 0.15;
            
            group.add(cube);
        }
        
        var coreGeometry = new THREE.IcosahedronGeometry(0.12, 1);
        var coreMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFFFFF,
            emissive: 0x444444,
            metalness: 0.8,
            roughness: 0.2
        });
        var core = new THREE.Mesh(coreGeometry, coreMaterial);
        core.position.y = 0.15;
        core.castShadow = true;
        group.add(core);
        
        group.rotation.x = -Math.PI / 2;
        
        return group;
    },
    
    applySequenceMode: function() {
        this.hideAllProducts();
        
        if (this.visibleMarkerIds.length > 0) {
            var firstId = this.visibleMarkerIds[0];
            var product = this.markerProducts[firstId];
            if (product) {
                product.visible = true;
            }
        }
    },
    
    hideAllProducts: function() {
        Object.values(this.markerProducts).forEach(function(product) {
            if (product) {
                product.visible = false;
            }
        });
    },
    
    showProduct: function(markerId) {
        var product = this.markerProducts[markerId];
        if (product) {
            product.visible = true;
        }
    },
    
    hideProduct: function(markerId) {
        var product = this.markerProducts[markerId];
        if (product) {
            product.visible = false;
        }
    },
    
    toggleProduct: function(markerId) {
        var product = this.markerProducts[markerId];
        if (product) {
            product.visible = !product.visible;
        }
    },
    
    getProducts: function() {
        return this.markerProducts;
    },
    
    getProduct: function(markerId) {
        return this.markerProducts[markerId];
    }
};