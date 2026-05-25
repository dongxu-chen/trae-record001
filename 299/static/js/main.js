class App {
    constructor() {
        this.mapManager = null;
        this.timeController = null;
        this.popup = null;
        this.metadata = null;
        this.diffusionAnimation = null;
        this.compareMode = null;
        this.init();
    }

    async init() {
        try {
            await this.loadMetadata();
            this.initComponents();
            this.bindLayerControls();
            this.bindDiffusionControls();
            this.bindCompareControls();
            this.bindReportControls();
            this.updateCurrentTimeDisplay();
            setInterval(() => this.updateCurrentTimeDisplay(), 1000);
            
            await this.loadTimeData(0);
            
            document.getElementById('loadingOverlay').classList.add('hidden');
        } catch (error) {
            console.error('Error initializing app:', error);
            document.getElementById('loadingOverlay').querySelector('p').textContent = 
                '加载失败，请刷新页面重试';
        }
    }

    async loadMetadata() {
        try {
            const response = await fetch('/api/metadata');
            this.metadata = await response.json();
        } catch (error) {
            console.error('Error loading metadata:', error);
            this.metadata = {
                time_steps: 72,
                start_time: new Date().toISOString(),
                grid_info: {
                    lon_min: 105,
                    lon_max: 125,
                    lat_min: 20,
                    lat_max: 40
                }
            };
        }
    }

    initComponents() {
        this.mapManager = new MapManager();
        
        this.timeController = new TimeController({
            totalSteps: this.metadata.time_steps,
            onTimeChange: (step) => this.onTimeChange(step)
        });
        
        this.timeController.setStartTime(this.metadata.start_time);
        
        this.popup = new PollutantPopup();
        
        const bounds = [
            this.metadata.grid_info.lon_min,
            this.metadata.grid_info.lat_min,
            this.metadata.grid_info.lon_max,
            this.metadata.grid_info.lat_max
        ];
        this.mapManager.fitToBounds(bounds);

        this.diffusionAnimation = new DiffusionAnimation(this.mapManager);
        this.compareMode = new CompareMode(this.mapManager);
    }

    bindLayerControls() {
        const layerAqi = document.getElementById('layerAqi');
        const layerContour = document.getElementById('layerContour');
        const layerWind = document.getElementById('layerWind');
        const opacitySlider = document.getElementById('opacitySlider');
        const opacityValue = document.getElementById('opacityValue');
        const renderModeRadios = document.querySelectorAll('input[name="renderMode"]');
        const speedSelect = document.getElementById('speedSelect');

        layerAqi.addEventListener('change', (e) => {
            this.mapManager.setAqiLayerVisible(e.target.checked);
        });

        layerContour.addEventListener('change', (e) => {
            this.mapManager.setContourLayerVisible(e.target.checked);
            if (e.target.checked) {
                this.mapManager.updateContourData(this.timeController.getCurrentStep());
            }
        });

        layerWind.addEventListener('change', (e) => {
            this.mapManager.setWindLayerVisible(e.target.checked);
            if (e.target.checked) {
                this.mapManager.updateWindData(this.timeController.getCurrentStep());
            }
        });

        opacitySlider.addEventListener('input', (e) => {
            const opacity = e.target.value / 100;
            opacityValue.textContent = `${e.target.value}%`;
            this.mapManager.setOpacity(opacity);
        });

        renderModeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                const useTiles = e.target.value === 'tile';
                this.mapManager.setRenderMode(useTiles);
            });
        });

        speedSelect.addEventListener('change', (e) => {
            this.timeController.setSpeed(parseInt(e.target.value));
        });
    }

    bindDiffusionControls() {
        const enableDiffusion = document.getElementById('enableDiffusion');
        const particleCount = document.getElementById('particleCount');
        const particleCountValue = document.getElementById('particleCountValue');
        const diffusionSpeed = document.getElementById('diffusionSpeed');
        const diffusionSpeedValue = document.getElementById('diffusionSpeedValue');
        const trailEffect = document.getElementById('trailEffect');
        const trailEffectValue = document.getElementById('trailEffectValue');

        enableDiffusion.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.diffusionAnimation.start();
            } else {
                this.diffusionAnimation.stop();
            }
        });

        particleCount.addEventListener('input', (e) => {
            particleCountValue.textContent = e.target.value;
            this.diffusionAnimation.setParticleCount(parseInt(e.target.value));
        });

        diffusionSpeed.addEventListener('input', (e) => {
            diffusionSpeedValue.textContent = `${e.target.value}x`;
            this.diffusionAnimation.setSpeed(parseFloat(e.target.value));
        });

        trailEffect.addEventListener('input', (e) => {
            trailEffectValue.textContent = `${Math.round(e.target.value * 100)}%`;
            this.diffusionAnimation.setTrailEffect(parseFloat(e.target.value));
        });
    }

    bindCompareControls() {
        const enableCompare = document.getElementById('enableCompare');
        const compareModeRadios = document.querySelectorAll('input[name="compareMode"]');
        const compareDataset = document.getElementById('compareDataset');
        const flickerFreq = document.getElementById('flickerFreq');
        const flickerFreqValue = document.getElementById('flickerFreqValue');

        enableCompare.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            
            compareModeRadios.forEach(radio => {
                radio.disabled = !enabled;
            });
            compareDataset.disabled = !enabled;
            flickerFreq.disabled = !enabled;

            if (enabled) {
                this.compareMode.enable();
                this.updateCompareMode();
                this.loadCompareStats();
            } else {
                this.compareMode.disable();
            }
        });

        compareModeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.updateCompareMode();
            });
        });

        compareDataset.addEventListener('change', (e) => {
            this.compareMode.loadDataset(e.target.value);
            this.loadCompareStats();
        });

        flickerFreq.addEventListener('input', (e) => {
            flickerFreqValue.textContent = `${e.target.value}Hz`;
            if (this.compareMode.mode === 'flicker') {
                this.compareMode.setFlickerFrequency(parseFloat(e.target.value));
            }
        });
    }

    updateCompareMode() {
        const mode = document.querySelector('input[name="compareMode"]:checked').value;
        
        const swipeOptions = document.getElementById('swipeOptions');
        const flickerOptions = document.getElementById('flickerOptions');
        const compareStats = document.getElementById('compareStats');

        swipeOptions.classList.add('hidden');
        flickerOptions.classList.add('hidden');
        compareStats.classList.add('hidden');

        this.compareMode.setMode(mode);

        if (mode === 'swipe') {
            swipeOptions.classList.remove('hidden');
        } else if (mode === 'flicker') {
            flickerOptions.classList.remove('hidden');
        } else if (mode === 'difference') {
            compareStats.classList.remove('hidden');
        }
    }

    async loadCompareStats() {
        try {
            const timeIdx = this.timeController.getCurrentStep();
            const response = await fetch(`/api/compare/stats/${timeIdx}`);
            const stats = await response.json();
            
            document.getElementById('statRMSE').textContent = stats.rmse?.toFixed(2) || '--';
            document.getElementById('statCorr').textContent = stats.correlation?.toFixed(3) || '--';
            document.getElementById('statMaxDiff').textContent = stats.max_diff?.toFixed(1) || '--';
        } catch (error) {
            console.error('Error loading compare stats:', error);
        }
    }

    bindReportControls() {
        const exportBtn = document.getElementById('exportReportBtn');
        
        exportBtn.addEventListener('click', async () => {
            await this.exportReport();
        });
    }

    async exportReport() {
        const exportBtn = document.getElementById('exportReportBtn');
        const originalText = exportBtn.innerHTML;
        
        try {
            exportBtn.disabled = true;
            exportBtn.innerHTML = `
                <svg class="loading-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="30" stroke-dashoffset="10"/>
                </svg>
                生成中...
            `;

            const timeIdx = this.timeController.getCurrentStep();
            const response = await fetch('/api/report/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ time_idx: timeIdx })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `aqi_report_${timeIdx}h.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                throw new Error('报告生成失败');
            }
        } catch (error) {
            console.error('Error exporting report:', error);
            alert('报告导出失败，请重试');
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalText;
        }
    }

    async onTimeChange(timeIdx) {
        await this.loadTimeData(timeIdx);
        
        if (document.getElementById('enableCompare').checked) {
            this.compareMode.updateTime(timeIdx);
            this.loadCompareStats();
        }
    }

    async loadTimeData(timeIdx) {
        const promises = [
            this.mapManager.updateAqiData(timeIdx)
        ];

        if (document.getElementById('layerContour').checked) {
            promises.push(this.mapManager.updateContourData(timeIdx));
        }

        if (document.getElementById('layerWind').checked) {
            promises.push(this.mapManager.updateWindData(timeIdx));
        }

        await Promise.all(promises);
    }

    updateCurrentTimeDisplay() {
        const now = new Date();
        const display = document.getElementById('currentTimeDisplay');
        display.textContent = now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
