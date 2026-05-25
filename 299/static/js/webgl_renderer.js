class WebGLRenderer {
    constructor(map) {
        this.map = map;
        this.gl = null;
        this.program = null;
        this.texture = null;
        this.data = null;
        this.bounds = null;
        this.opacity = 0.7;
        this.visible = true;
        this.canvas = null;
        this.layer = null;
        this.initLayer();
    }

    initLayer() {
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none';

        this.layer = new ol.layer.Image({
            source: new ol.source.ImageCanvas({
                canvasFunction: (extent, resolution, pixelRatio, size, projection) => {
                    this.resizeCanvas(size[0], size[1]);
                    this.render(extent, projection);
                    return this.canvas;
                }
            })
        });

        this.map.addLayer(this.layer);
        this.initWebGL();
    }

    resizeCanvas(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
        if (this.gl) {
            this.gl.viewport(0, 0, width, height);
        }
    }

    initWebGL() {
        this.gl = this.canvas.getContext('webgl', { 
            premultipliedAlpha: false,
            alpha: true,
            antialias: true
        });

        if (!this.gl) {
            console.error('WebGL not supported');
            return;
        }

        const vertexShader = this.compileShader(`
            attribute vec2 a_position;
            attribute vec2 a_texCoord;
            varying vec2 v_texCoord;
            void main() {
                gl_Position = vec4(a_position, 0.0, 1.0);
                v_texCoord = a_texCoord;
            }
        `, this.gl.VERTEX_SHADER);

        const fragmentShader = this.compileShader(`
            precision mediump float;
            varying vec2 v_texCoord;
            uniform sampler2D u_texture;
            uniform float u_opacity;
            
            const float LOG_MAX = 6.2169;
            
            vec3 aqiToColor(float aqi) {
                float t;
                if (aqi < 50.0) {
                    t = aqi / 50.0;
                    return mix(vec3(0.0, 0.7, 0.0), vec3(0.0, 0.894, 0.0), t);
                } else if (aqi < 100.0) {
                    t = (aqi - 50.0) / 50.0;
                    return mix(vec3(0.0, 0.894, 0.0), vec3(1.0, 1.0, 0.0), t);
                } else if (aqi < 150.0) {
                    t = (aqi - 100.0) / 50.0;
                    return mix(vec3(1.0, 1.0, 0.0), vec3(1.0, 0.494, 0.0), t);
                } else if (aqi < 200.0) {
                    t = (aqi - 150.0) / 50.0;
                    return mix(vec3(1.0, 0.494, 0.0), vec3(1.0, 0.0, 0.0), t);
                } else if (aqi < 300.0) {
                    t = (aqi - 200.0) / 100.0;
                    return mix(vec3(1.0, 0.0, 0.0), vec3(0.6, 0.0, 0.298), t);
                } else {
                    t = clamp((aqi - 300.0) / 200.0, 0.0, 1.0);
                    return mix(vec3(0.6, 0.0, 0.298), vec3(0.494, 0.0, 0.137), t);
                }
            }
            
            void main() {
                float normalized = texture2D(u_texture, v_texCoord).r;
                float log_aqi = normalized * LOG_MAX;
                float aqi = exp(log_aqi) - 1.0;
                vec3 color = aqiToColor(aqi);
                gl_FragColor = vec4(color, u_opacity);
            }
        `, this.gl.FRAGMENT_SHADER);

        this.program = this.gl.createProgram();
        this.gl.attachShader(this.program, vertexShader);
        this.gl.attachShader(this.program, fragmentShader);
        this.gl.linkProgram(this.program);

        if (!this.gl.getProgramParameter(this.program, this.gl.LINK_STATUS)) {
            console.error('Program link error:', this.gl.getProgramInfoLog(this.program));
            return;
        }

        this.gl.useProgram(this.program);

        const positions = new Float32Array([
            -1, -1,  0, 1,
             1, -1,  1, 1,
            -1,  1,  0, 0,
             1,  1,  1, 0
        ]);

        const buffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, buffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, positions, this.gl.STATIC_DRAW);

        const positionLoc = this.gl.getAttribLocation(this.program, 'a_position');
        const texCoordLoc = this.gl.getAttribLocation(this.program, 'a_texCoord');

        this.gl.enableVertexAttribArray(positionLoc);
        this.gl.vertexAttribPointer(positionLoc, 2, this.gl.FLOAT, false, 16, 0);

        this.gl.enableVertexAttribArray(texCoordLoc);
        this.gl.vertexAttribPointer(texCoordLoc, 2, this.gl.FLOAT, false, 16, 8);

        this.opacityLoc = this.gl.getUniformLocation(this.program, 'u_opacity');
    }

    compileShader(source, type) {
        const shader = this.gl.createShader(type);
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);
        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            console.error('Shader compile error:', this.gl.getShaderInfoLog(shader));
            return null;
        }
        return shader;
    }

    setData(aqiData, bounds) {
        this.data = aqiData;
        this.bounds = bounds;
        this.updateTexture();
        this.layer.changed();
    }

    updateTexture() {
        if (!this.gl || !this.data) return;

        const ny = this.data.length;
        const nx = this.data[0].length;
        const LOG_MAX = Math.log(500 + 1);

        const pixels = new Float32Array(nx * ny);
        for (let j = 0; j < ny; j++) {
            for (let i = 0; i < nx; i++) {
                const aqi = Math.max(0, Math.min(500, this.data[j][i]));
                pixels[j * nx + i] = Math.log(aqi + 1) / LOG_MAX;
            }
        }

        if (this.texture) {
            this.gl.deleteTexture(this.texture);
        }

        this.texture = this.gl.createTexture();
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);
        this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.LUMINANCE, nx, ny, 0, this.gl.LUMINANCE, this.gl.FLOAT, pixels);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
    }

    render(extent, projection) {
        if (!this.gl || !this.program || !this.texture || !this.visible) return;

        this.gl.clearColor(0, 0, 0, 0);
        this.gl.clear(this.gl.COLOR_BUFFER_BIT);

        this.gl.useProgram(this.program);
        this.gl.uniform1f(this.opacityLoc, this.opacity);

        this.gl.activeTexture(this.gl.TEXTURE0);
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);

        this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, 4);
    }

    setOpacity(opacity) {
        this.opacity = opacity;
        this.layer.changed();
    }

    setVisible(visible) {
        this.visible = visible;
        this.layer.setVisible(visible);
    }

    getLayer() {
        return this.layer;
    }
}

class WindParticles {
    constructor(map) {
        this.map = map;
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.windData = null;
        this.bounds = null;
        this.gradientField = null;
        this.animationId = null;
        this.visible = false;
        this.minParticles = 500;
        this.maxParticles = 2000;
        this.speedScale = 0.5;
        this.layer = null;
        this.initLayer();
    }

    initLayer() {
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none';
        this.ctx = this.canvas.getContext('2d');

        this.layer = new ol.layer.Image({
            source: new ol.source.ImageCanvas({
                canvasFunction: (extent, resolution, pixelRatio, size, projection) => {
                    this.canvas.width = size[0];
                    this.canvas.height = size[1];
                    return this.canvas;
                }
            })
        });

        this.map.addLayer(this.layer);
    }

    setWindData(uData, vData, bounds) {
        this.windData = { u: uData, v: vData };
        this.bounds = bounds;
        this.computeGradientField();
        this.initAdaptiveParticles();
        if (this.visible) {
            this.startAnimation();
        }
    }

    computeGradientField() {
        if (!this.windData) return;

        const nx = this.windData.u[0].length;
        const ny = this.windData.u.length;
        this.gradientField = new Array(ny).fill(null).map(() => new Array(nx).fill(0));

        for (let j = 1; j < ny - 1; j++) {
            for (let i = 1; i < nx - 1; i++) {
                const u = this.windData.u[j][i];
                const v = this.windData.v[j][i];
                const speed = Math.sqrt(u * u + v * v);

                const dudx = (this.windData.u[j][i + 1] - this.windData.u[j][i - 1]) / 2;
                const dudy = (this.windData.u[j + 1][i] - this.windData.u[j - 1][i]) / 2;
                const dvdx = (this.windData.v[j][i + 1] - this.windData.v[j][i - 1]) / 2;
                const dvdy = (this.windData.v[j + 1][i] - this.windData.v[j - 1][i]) / 2;

                const gradient = Math.sqrt(dudx * dudx + dudy * dudy + dvdx * dvdx + dvdy * dvdy);
                const shear = Math.abs(dudx + dvdy);
                const vorticity = Math.abs(dvdx - dudy);

                this.gradientField[j][i] = gradient * 2 + shear * 3 + vorticity * 2;
            }
        }

        let maxGrad = 0;
        for (let j = 0; j < ny; j++) {
            for (let i = 0; i < nx; i++) {
                maxGrad = Math.max(maxGrad, this.gradientField[j][i]);
            }
        }
        if (maxGrad > 0) {
            for (let j = 0; j < ny; j++) {
                for (let i = 0; i < nx; i++) {
                    this.gradientField[j][i] /= maxGrad;
                }
            }
        }
    }

    initAdaptiveParticles() {
        if (!this.bounds || !this.gradientField) return;

        this.particles = [];
        const nx = this.gradientField[0].length;
        const ny = this.gradientField.length;
        const totalCells = nx * ny;
        const targetParticles = Math.min(this.maxParticles, Math.max(this.minParticles, totalCells / 20));

        const quadTree = this.buildQuadTree(
            this.bounds[0], this.bounds[1],
            this.bounds[2], this.bounds[3],
            4
        );

        this.sampleQuadTree(quadTree, targetParticles);

        while (this.particles.length < this.minParticles) {
            this.particles.push({
                x: this.bounds[0] + Math.random() * (this.bounds[2] - this.bounds[0]),
                y: this.bounds[1] + Math.random() * (this.bounds[3] - this.bounds[1]),
                age: Math.random() * 100,
                density: 1
            });
        }
    }

    buildQuadTree(x0, y0, x1, y1, depth) {
        const node = { x0, y0, x1, y1, depth, children: null, maxGradient: 0 };

        const nx = this.gradientField[0].length;
        const ny = this.gradientField.length;
        const i0 = Math.floor((x0 - this.bounds[0]) / (this.bounds[2] - this.bounds[0]) * (nx - 1));
        const j0 = Math.floor((y0 - this.bounds[1]) / (this.bounds[3] - this.bounds[1]) * (ny - 1));
        const i1 = Math.ceil((x1 - this.bounds[0]) / (this.bounds[2] - this.bounds[0]) * (nx - 1));
        const j1 = Math.ceil((y1 - this.bounds[1]) / (this.bounds[3] - this.bounds[1]) * (ny - 1));

        let maxGrad = 0;
        for (let j = Math.max(0, j0); j <= Math.min(ny - 1, j1); j++) {
            for (let i = Math.max(0, i0); i <= Math.min(nx - 1, i1); i++) {
                maxGrad = Math.max(maxGrad, this.gradientField[j][i]);
            }
        }
        node.maxGradient = maxGrad;

        const sizeThreshold = 0.5;
        const gradientThreshold = 0.15;
        const width = x1 - x0;
        const height = y1 - y0;

        if (depth > 0 && (maxGrad > gradientThreshold || (width > sizeThreshold && height > sizeThreshold))) {
            const mx = (x0 + x1) / 2;
            const my = (y0 + y1) / 2;
            node.children = [
                this.buildQuadTree(x0, y0, mx, my, depth - 1),
                this.buildQuadTree(mx, y0, x1, my, depth - 1),
                this.buildQuadTree(x0, my, mx, y1, depth - 1),
                this.buildQuadTree(mx, my, x1, y1, depth - 1)
            ];
        }

        return node;
    }

    sampleQuadTree(node, targetCount) {
        if (!node) return;

        const weight = 1 + node.maxGradient * 3;
        const sampleCount = Math.ceil(targetCount * weight / 10);

        if (!node.children || sampleCount <= 2) {
            const count = Math.max(1, sampleCount);
            for (let i = 0; i < count && this.particles.length < this.maxParticles; i++) {
                this.particles.push({
                    x: node.x0 + Math.random() * (node.x1 - node.x0),
                    y: node.y0 + Math.random() * (node.y1 - node.y0),
                    age: Math.random() * 100,
                    density: weight
                });
            }
            return;
        }

        const childCount = Math.floor(targetCount / 4);
        node.children.forEach(child => {
            this.sampleQuadTree(child, childCount);
        });
    }

    sampleWind(lon, lat) {
        if (!this.windData || !this.bounds) return { u: 0, v: 0 };

        const nx = this.windData.u[0].length;
        const ny = this.windData.u.length;

        const i = ((lon - this.bounds[0]) / (this.bounds[2] - this.bounds[0])) * (nx - 1);
        const j = ((lat - this.bounds[1]) / (this.bounds[3] - this.bounds[1])) * (ny - 1);

        const i0 = Math.floor(Math.max(0, Math.min(nx - 2, i)));
        const j0 = Math.floor(Math.max(0, Math.min(ny - 2, j)));

        const fx = i - i0;
        const fy = j - j0;

        const u = (1 - fx) * (1 - fy) * this.windData.u[j0][i0] +
                  fx * (1 - fy) * this.windData.u[j0][i0 + 1] +
                  (1 - fx) * fy * this.windData.u[j0 + 1][i0] +
                  fx * fy * this.windData.u[j0 + 1][i0 + 1];

        const v = (1 - fx) * (1 - fy) * this.windData.v[j0][i0] +
                  fx * (1 - fy) * this.windData.v[j0][i0 + 1] +
                  (1 - fx) * fy * this.windData.v[j0 + 1][i0] +
                  fx * fy * this.windData.v[j0 + 1][i0 + 1];

        return { u, v };
    }

    getGradientAt(lon, lat) {
        if (!this.gradientField || !this.bounds) return 0;

        const nx = this.gradientField[0].length;
        const ny = this.gradientField.length;

        const i = ((lon - this.bounds[0]) / (this.bounds[2] - this.bounds[0])) * (nx - 1);
        const j = ((lat - this.bounds[1]) / (this.bounds[3] - this.bounds[1])) * (ny - 1);

        const i0 = Math.floor(Math.max(0, Math.min(nx - 2, i)));
        const j0 = Math.floor(Math.max(0, Math.min(ny - 2, j)));

        return this.gradientField[j0][i0];
    }

    animate() {
        if (!this.visible || !this.windData) return;

        const extent = this.map.getView().calculateExtent(this.map.getSize());
        const resolution = this.map.getView().getResolution();
        const width = this.canvas.width;
        const height = this.canvas.height;

        this.ctx.fillStyle = 'rgba(15, 23, 42, 0.12)';
        this.ctx.fillRect(0, 0, width, height);

        const toPixel = (lon, lat) => {
            const x = ((lon - extent[0]) / (extent[2] - extent[0])) * width;
            const y = height - ((lat - extent[1]) / (extent[3] - extent[1])) * height;
            return { x, y };
        };

        this.particles.forEach(p => {
            const wind = this.sampleWind(p.x, p.y);
            const gradient = this.getGradientAt(p.x, p.y);
            const start = toPixel(p.x, p.y);

            p.x += wind.u * this.speedScale * resolution * 0.01;
            p.y += wind.v * this.speedScale * resolution * 0.01;
            p.age += 1;

            const end = toPixel(p.x, p.y);

            if (p.x < this.bounds[0] || p.x > this.bounds[2] || 
                p.y < this.bounds[1] || p.y > this.bounds[3] || p.age > 80) {
                this.replaceParticle(p);
                return;
            }

            const alpha = (1 - p.age / 80) * (0.4 + gradient * 0.6);
            const lineWidth = 1 + gradient * 1.5;

            this.ctx.beginPath();
            this.ctx.globalAlpha = alpha;
            this.ctx.lineWidth = lineWidth;
            this.ctx.strokeStyle = gradient > 0.3 ? 'rgba(100, 200, 255, 0.9)' : 'rgba(255, 255, 255, 0.7)';
            this.ctx.moveTo(start.x, start.y);
            this.ctx.lineTo(end.x, end.y);
            this.ctx.stroke();
        });

        this.ctx.globalAlpha = 1;
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    replaceParticle(p) {
        const useAdaptive = Math.random() < 0.7;

        if (useAdaptive && this.gradientField) {
            const nx = this.gradientField[0].length;
            const ny = this.gradientField.length;
            let attempts = 0;
            while (attempts < 20) {
                const i = Math.floor(Math.random() * nx);
                const j = Math.floor(Math.random() * ny);
                const grad = this.gradientField[j][i];
                if (Math.random() < (0.2 + grad * 0.8)) {
                    const lon = this.bounds[0] + (i / (nx - 1)) * (this.bounds[2] - this.bounds[0]);
                    const lat = this.bounds[1] + (j / (ny - 1)) * (this.bounds[3] - this.bounds[1]);
                    p.x = lon + (Math.random() - 0.5) * (this.bounds[2] - this.bounds[0]) / nx;
                    p.y = lat + (Math.random() - 0.5) * (this.bounds[3] - this.bounds[1]) / ny;
                    p.age = 0;
                    p.density = 1 + grad * 3;
                    return;
                }
                attempts++;
            }
        }

        p.x = this.bounds[0] + Math.random() * (this.bounds[2] - this.bounds[0]);
        p.y = this.bounds[1] + Math.random() * (this.bounds[3] - this.bounds[1]);
        p.age = 0;
        p.density = 1;
    }

    startAnimation() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.animate();
    }

    stopAnimation() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    setVisible(visible) {
        this.visible = visible;
        this.layer.setVisible(visible);
        if (visible && this.windData) {
            this.startAnimation();
        } else {
            this.stopAnimation();
        }
    }

    getLayer() {
        return this.layer;
    }
}
