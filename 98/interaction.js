var interaction = {
    raycaster: null,
    mouse: null,
    isRotating: false,
    rotationSpeed: 0.05,
    autoRotate: false,
    previousTouchX: null,
    
    init: function() {
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.previousTouchX = null;
        
        this.setupEventListeners();
    },
    
    setupEventListeners: function() {
        var container = document.getElementById('container');
        
        container.addEventListener('click', this.onClick.bind(this), false);
        container.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: false });
        container.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
        container.addEventListener('touchend', this.onTouchEnd.bind(this), { passive: false });
        container.addEventListener('touchcancel', this.onTouchEnd.bind(this), { passive: false });
        container.addEventListener('mousedown', this.onMouseDown.bind(this), false);
        container.addEventListener('mousemove', this.onMouseMove.bind(this), false);
        container.addEventListener('mouseup', this.onMouseUp.bind(this), false);
    },
    
    onClick: function(event) {
        event.preventDefault();
        
        this.updateMousePosition(event);
        
        var product = productLoader.getProduct();
        if (!product) return;
        
        var intersects = this.getIntersections(product);
        
        if (intersects.length > 0) {
            this.rotateProduct();
        }
    },
    
    updateMousePosition: function(event) {
        var container = document.getElementById('container');
        var rect = container.getBoundingClientRect();
        
        if (event.touches && event.touches.length > 0) {
            this.mouse.x = ((event.touches[0].clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((event.touches[0].clientY - rect.top) / rect.height) * 2 + 1;
        } else {
            this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        }
    },
    
    getIntersections: function(product) {
        this.raycaster.setFromCamera(this.mouse, arScene.camera);
        return this.raycaster.intersectObject(product, true);
    },
    
    rotateProduct: function() {
        var product = productLoader.getProduct();
        if (!product) return;
        
        product.rotation.y += this.rotationSpeed;
    },
    
    onMouseDown: function(event) {
        this.updateMousePosition(event);
        
        var product = productLoader.getProduct();
        if (!product) return;
        
        var intersects = this.getIntersections(product);
        
        if (intersects.length > 0) {
            this.isRotating = true;
        }
    },
    
    onMouseMove: function(event) {
        if (!this.isRotating) return;
        
        var product = productLoader.getProduct();
        if (!product) return;
        
        var deltaX = event.movementX || 0;
        product.rotation.y += deltaX * 0.01;
    },
    
    onMouseUp: function() {
        this.isRotating = false;
    },
    
    onTouchStart: function(event) {
        event.preventDefault();
        
        if (event.touches.length === 1) {
            this.updateMousePosition(event);
            
            var product = productLoader.getProduct();
            if (!product) return;
            
            var intersects = this.getIntersections(product);
            
            if (intersects.length > 0) {
                this.isRotating = true;
                this.previousTouchX = event.touches[0].clientX;
            }
        }
    },
    
    onTouchMove: function(event) {
        event.preventDefault();
        
        if (!this.isRotating || event.touches.length !== 1) return;
        
        var product = productLoader.getProduct();
        if (!product) return;
        
        var touch = event.touches[0];
        
        if (this.previousTouchX === null) {
            this.previousTouchX = touch.clientX;
            return;
        }
        
        var deltaX = touch.clientX - this.previousTouchX;
        this.previousTouchX = touch.clientX;
        
        product.rotation.y += deltaX * 0.01;
    },
    
    onTouchEnd: function(event) {
        this.isRotating = false;
        this.previousTouchX = null;
    },
    
    toggleAutoRotate: function() {
        this.autoRotate = !this.autoRotate;
        
        if (this.autoRotate) {
            this.startAutoRotate();
        }
    },
    
    startAutoRotate: function() {
        var self = this;
        
        function animate() {
            if (!self.autoRotate) return;
            
            var product = productLoader.getProduct();
            if (product) {
                product.rotation.y += 0.01;
            }
            
            requestAnimationFrame(animate);
        }
        
        animate();
    }
};