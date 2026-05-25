class CompareMode {
    constructor(map) {
        this.map = map;
        this.mode = 'none';
        this.datasetA = null;
        this.datasetB = null;
        this.currentTimeIdx = 0;
        
        this.diffLayer = null;
        this.diffSource = null;
        this.diffData = null;
        this.diffBounds = null;
        
        this.swipeLayerA = null;
        this.swipeLayerB = null;
        this.swipePosition = 0.5;
        this.swipeHandle = null;
        
        this.flickerState = true;
        this.flickerInterval = null;
        this.flickerFrequency = 1000;
        
        this.initDiffLayer();
        this.initSwipeUI();
    }

    initDiffLayer() {
        this.diffCanvas = document.createElement('canvas');
        this.diffCanvas.style.position = 'absolute';
        this.diffCanvas.style.top = '0';
        this.diffCanvas.style.left = '0';
        this.diffCanvas.style.width = '100%';
        this.diffCanvas.style.height = '100%';
        this.diffCanvas.style.pointerEvents = 'none';
        this.diffCtx = this.diffCanvas.getContext('2d');

        this.diffLayer = new ol.layer.Image({
            source: new ol.source.ImageCanvas({
                canvasFunction: (extent, resolution, pixelRatio, size, projection) => {
                    this.diffCanvas.width = size[0];
                    this.diffCanvas.height = size[1];
                    this.renderDiff(extent, resolution);
                    return this.diffCanvas;
                }
            }),
            visible: false,
            opacity: 0.8,
            zIndex: 20
        });

        this.map.addLayer(this.diffLayer);
    }

    initSwipeUI() {
        this.swipeHandle = document.createElement('div');
        this.swipeHandle.style.cssText = `
            position: absolute;
            top: 60px;
            bottom: 80px;
            width: 4px;
            background: var(--primary-color);
            cursor: ew-resize;
            z-index: 1000;
            display: none;
            box-shadow: 0 0 10px rgba(22, 93, 255, 0.5);
        `;

        const label = document.createElement('div');
        label.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--primary-color);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            white-space: nowrap;
            pointer-events: none;
        `;
        label.innerHTML = '◀ 数据集A | 数据集B ▶';
        this.swipeHandle.appendChild(label);

        let isDragging = false;
        this.swipeHandle.addEventListener('mousedown', () => {
            isDragging = true;
        });
        document.addEventListener('mousemove', (e) => {
            if (!isDragging || this.mode !== 'swipe') return;
            const mapRect = this.map.getTargetElement().getBoundingClientRect();
            this.swipePosition = (e.clientX - mapRect.left) / mapRect.width;
            this.swipePosition = Math.max(0.05, Math.min(0.95, this.swipePosition));
            this.updateSwipeClip();
        });
        document.addEventListener('mouseup', () => {
            isDragging = false;
        });

        this.map.getTargetElement().appendChild(this.swipeHandle);
    }

    async loadDatasetB(datasetId) {
        try {
            const response = await fetch(`/api/compare/load/${datasetId}`, { method: 'POST' });
            this.datasetB = await response.json();
            return true;
        } catch (error) {
            console.error('Error loading dataset B:', error);
            return false;
        }
    }

    async setMode(mode) {
        this.mode = mode;
        
        this.diffLayer.setVisible(mode === 'diff');
        this.swipeHandle.style.display = mode === 'swipe' ? 'block' : 'none';
        
        if (this.flickerInterval) {
            clearInterval(this.flickerInterval);
            this.flickerInterval = null;
        }
        
        if (mode === 'swipe') {
            this.updateSwipeClip();
        } else if (mode === 'flicker') {
            this.startFlicker();
        } else if (mode === 'diff') {
            await this.updateDiffData(this.currentTimeIdx);
        }
    }

    setCurrentTime(timeIdx) {
        this.currentTimeIdx = timeIdx;
        if (this.mode === 'diff') {
            this.updateDiffData(timeIdx);
        }
    }

    async updateDiffData(timeIdx) {
        try {
            const response = await fetch(`/api/diff/${timeIdx}`);
            const data = await response.json();
            this.diffData = data.diff_data;
            this.diffBounds = data.bounds;
            this.diffLayer.changed();
        } catch (error) {
            console.error('Error fetching diff data:', error);
        }
    }

    renderDiff(extent, resolution) {
        if (!this.diffData || !this.diffBounds) return;

        const width = this.diffCanvas.width;
        const height = this.diffCanvas.height;
        const ctx = this.diffCtx;

        ctx.clearRect(0, 0, width, height);

        const data_lon_min = this.diffBounds[0];
        const data_lat_min = this.diffBounds[1];
        const data_lon_max = this.diffBounds[2];
        const data_lat_max = this.diffBounds[3];

        const nx = this.diffData[0].length;
        const ny = this.diffData.length;

        const tileCanvas = document.createElement('canvas');
        tileCanvas.width = nx;
        tileCanvas.height = ny;
        const tileCtx = tileCanvas.getContext('2d');
        const imageData = tileCtx.createImageData(nx, ny);

        for (let j = 0; j < ny; j++) {
            for (let i = 0; i < nx; i++) {
                const diff = this.diffData[j][i];
                const idx = (j * nx + i) * 4;
                
                const color = this.diffToColor(diff);
                imageData.data[idx] = color[0];
                imageData.data[idx + 1] = color[1];
                imageData.data[idx + 2] = color[2];
                imageData.data[idx + 3] = color[3];
            }
        }

        tileCtx.putImageData(imageData, 0, 0);

        const x0 = ((data_lon_min - extent[0]) / (extent[2] - extent[0])) * width;
        const y0 = height - ((data_lat_max - extent[1]) / (extent[3] - extent[1])) * height;
        const x1 = ((data_lon_max - extent[0]) / (extent[2] - extent[0])) * width;
        const y1 = height - ((data_lat_min - extent[1]) / (extent[3] - extent[1])) * height;

        ctx.drawImage(tileCanvas, x0, y0, x1 - x0, y1 - y0);
    }

    diffToColor(diff) {
        const maxDiff = 50;
        const normalized = Math.max(-1, Math.min(1, diff / maxDiff));
        
        if (normalized < 0) {
            const t = -normalized;
            return [
                Math.floor(30 + 70 * t),
                Math.floor(100 + 155 * t),
                255,
                Math.floor(100 + 155 * t)
            ];
        } else if (normalized > 0) {
            const t = normalized;
            return [
                255,
                Math.floor(100 + 100 * (1 - t)),
                Math.floor(100 + 100 * (1 - t)),
                Math.floor(100 + 155 * t)
            ];
        } else {
            return [255, 255, 255, 50];
        }
    }

    updateSwipeClip() {
        if (!this.swipeLayerA || !this.swipeLayerB) return;
        
        const mapRect = this.map.getTargetElement().getBoundingClientRect();
        const x = mapRect.left + mapRect.width * this.swipePosition;
        this.swipeHandle.style.left = `${x - mapRect.left - 2}px`;
    }

    setSwipeLayers(layerA, layerB) {
        this.swipeLayerA = layerA;
        this.swipeLayerB = layerB;
    }

    setFlickerLayers(layerA, layerB) {
        this.flickerLayerA = layerA;
        this.flickerLayerB = layerB;
    }

    startFlicker() {
        if (!this.flickerLayerA || !this.flickerLayerB) return;
        
        this.flickerState = true;
        this.flickerInterval = setInterval(() => {
            this.flickerState = !this.flickerState;
            if (this.flickerLayerA) this.flickerLayerA.setVisible(this.flickerState);
            if (this.flickerLayerB) this.flickerLayerB.setVisible(!this.flickerState);
        }, this.flickerFrequency);
    }

    setFlickerFrequency(ms) {
        this.flickerFrequency = ms;
        if (this.mode === 'flicker') {
            this.startFlicker();
        }
    }

    async getCompareStats(timeIdx) {
        try {
            const response = await fetch(`/api/compare/stats/${timeIdx}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching compare stats:', error);
            return null;
        }
    }

    getAvailableDatasets() {
        return [
            { id: 'current', name: '当前预报' },
            { id: 'previous', name: '上一次预报' },
            { id: 'control', name: '控制试验' },
            { id: 'sensitivity', name: '敏感性试验' }
        ];
    }

    setDiffOpacity(opacity) {
        if (this.diffLayer) {
            this.diffLayer.setOpacity(opacity);
        }
    }

    destroy() {
        if (this.flickerInterval) {
            clearInterval(this.flickerInterval);
        }
        if (this.swipeHandle && this.swipeHandle.parentNode) {
            this.swipeHandle.parentNode.removeChild(this.swipeHandle);
        }
    }
}
