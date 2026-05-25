class DiffusionAnimation {
    constructor(map) {
        this.map = map;
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.windData = null;
        this.bounds = null;
        this.animationId = null;
        this.visible = false;
        this.isPlaying = false;
        this.speedScale = 1.0;
        this.particleCount = 2000;
        this.trailLength = 30;
        this.trailCanvas = null;
        this.trailCtx = null;
        this.timeIdx = 0;
        this.maxTimeIdx = 72;
        this.interpFactor = 0;
        
        this.emissionSources = [
            { x: 116.4, y: 39.9, rate: 5, name: '北京' },
            { x: 121.5, y: 31.2, rate: 4, name: '上海' },
            { x: 113.3, y: 23.1, rate: 3, name: '广州' },
            { x: 114.1, y: 22.3, rate: 2, name: '深圳' },
            { x: 104.1, y: 30.7, rate: 2, name: '成都' },
        ];
        
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

        this.trailCanvas = document.createElement('canvas');
        this.trailCtx = this.trailCanvas.getContext('2d');

        this.layer = new ol.layer.Image({
            source: new ol.source.ImageCanvas({
                canvasFunction: (extent, resolution, pixelRatio, size, projection) => {
                    this.canvas.width = size[0];
                    this.canvas.height = size[1];
                    this.trailCanvas.width = size[0];
                    this.trailCanvas.height = size[1];
                    return this.canvas;
                }
            }),
            zIndex: 10
        });

        this.map.addLayer(this.layer);
    }

    setWindData(uData, vData, bounds) {
        this.windData = { u: uData, v: vData };
        this.bounds = bounds;
    }

    setTimeIndex(timeIdx, interpFactor = 0) {
        this.timeIdx = timeIdx;
        this.interpFactor = interpFactor;
    }

    initParticles() {
        if (!this.bounds) return;

        this.particles = [];
        this.trailCtx.clearRect(0, 0, this.trailCanvas.width, this.trailCanvas.height);

        for (let i = 0; i < this.particleCount; i++) {
            const source = this.emissionSources[Math.floor(Math.random() * this.emissionSources.length)];
            this.particles.push(this.createParticle(source));
        }
    }

    createParticle(source) {
        return {
            x: source.x + (Math.random() - 0.5) * 0.5,
            y: source.y + (Math.random() - 0.5) * 0.5,
            age: 0,
            maxAge: 100 + Math.random() * 100,
            size: 2 + Math.random() * 3,
            concentration: 0.3 + Math.random() * 0.7,
            sourceIndex: this.emissionSources.indexOf(source),
            trail: []
        };
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

    animate() {
        if (!this.visible || !this.windData) return;

        const extent = this.map.getView().calculateExtent(this.map.getSize());
        const resolution = this.map.getView().getResolution();
        const width = this.canvas.width;
        const height = this.canvas.height;

        this.trailCtx.fillStyle = 'rgba(15, 23, 42, 0.05)';
        this.trailCtx.fillRect(0, 0, width, height);

        const toPixel = (lon, lat) => {
            const x = ((lon - extent[0]) / (extent[2] - extent[0])) * width;
            const y = height - ((lat - extent[1]) / (extent[3] - extent[1])) * height;
            return { x, y };
        };

        this.emissionSources.forEach(source => {
            if (Math.random() < source.rate * 0.1) {
                for (let i = 0; i < 2; i++) {
                    if (this.particles.length < this.particleCount * 1.5) {
                        this.particles.push(this.createParticle(source));
                    }
                }
            }
        });

        this.particles.forEach((p, index) => {
            const wind = this.sampleWind(p.x, p.y);
            const pos = toPixel(p.x, p.y);

            const turbX = (Math.random() - 0.5) * 0.05;
            const turbY = (Math.random() - 0.5) * 0.05;

            p.x += (wind.u * 0.005 + turbX) * this.speedScale;
            p.y += (wind.v * 0.005 + turbY) * this.speedScale;
            p.age += this.speedScale;
            p.concentration *= 0.998;

            const newPos = toPixel(p.x, p.y);

            if (p.age > 1) {
                this.trailCtx.beginPath();
                this.trailCtx.globalAlpha = p.concentration * 0.3;
                this.trailCtx.strokeStyle = this.getParticleColor(p);
                this.trailCtx.lineWidth = p.size * 0.5;
                this.trailCtx.moveTo(pos.x, pos.y);
                this.trailCtx.lineTo(newPos.x, newPos.y);
                this.trailCtx.stroke();
            }

            if (p.x < this.bounds[0] - 5 || p.x > this.bounds[2] + 5 || 
                p.y < this.bounds[1] - 5 || p.y > this.bounds[3] + 5 || 
                p.age > p.maxAge || p.concentration < 0.05) {
                this.particles.splice(index, 1);
                return;
            }

            this.trailCtx.beginPath();
            this.trailCtx.globalAlpha = p.concentration * 0.8;
            this.trailCtx.fillStyle = this.getParticleColor(p);
            this.trailCtx.arc(newPos.x, newPos.y, p.size, 0, Math.PI * 2);
            this.trailCtx.fill();
        });

        this.ctx.clearRect(0, 0, width, height);
        this.ctx.drawImage(this.trailCanvas, 0, 0);

        this.emissionSources.forEach(source => {
            const pos = toPixel(source.x, source.y);
            const pulse = 0.7 + 0.3 * Math.sin(Date.now() * 0.005);
            
            this.ctx.beginPath();
            this.ctx.globalAlpha = 0.8 * pulse;
            this.ctx.fillStyle = '#FF4444';
            this.ctx.arc(pos.x, pos.y, 6 * pulse, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.beginPath();
            this.ctx.globalAlpha = 0.3 * pulse;
            this.ctx.fillStyle = '#FF6666';
            this.ctx.arc(pos.x, pos.y, 12 * pulse, 0, Math.PI * 2);
            this.ctx.fill();
        });

        this.ctx.globalAlpha = 1;
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    getParticleColor(p) {
        const colors = [
            'rgba(255, 100, 100, ',
            'rgba(100, 200, 255, ',
            'rgba(100, 255, 100, ',
            'rgba(255, 200, 100, ',
            'rgba(200, 100, 255, ',
        ];
        return colors[p.sourceIndex % colors.length] + p.concentration + ')';
    }

    start() {
        if (this.isPlaying) return;
        this.isPlaying = true;
        this.initParticles();
        this.animate();
    }

    stop() {
        this.isPlaying = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    setVisible(visible) {
        this.visible = visible;
        this.layer.setVisible(visible);
        if (visible && this.windData) {
            this.start();
        } else {
            this.stop();
        }
    }

    setSpeed(speed) {
        this.speedScale = speed;
    }

    setParticleCount(count) {
        this.particleCount = count;
        if (this.isPlaying) {
            this.initParticles();
        }
    }

    setTrailLength(length) {
        this.trailLength = length;
    }

    toggleSource(index, enabled) {
        this.emissionSources[index].enabled = enabled;
    }

    getLayer() {
        return this.layer;
    }
}
