class MapManager {
    constructor() {
        this.map = null;
        this.webglRenderer = null;
        this.tileLayer = null;
        this.contourLayer = null;
        this.windParticles = null;
        this.useTileCache = true;
        this.currentTimeIdx = 0;
        this.init();
    }

    init() {
        this.map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        url: 'https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
                        crossOrigin: 'anonymous'
                    }),
                    opacity: 0.6
                })
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([115, 32]),
                zoom: 5,
                minZoom: 4,
                maxZoom: 10
            }),
            controls: ol.control.defaults({
                attribution: false,
                zoom: true
            })
        });

        this.initTileLayer();
        this.webglRenderer = new WebGLRenderer(this.map);
        this.webglRenderer.setVisible(false);
        this.contourLayer = new ContourLayer(this.map);
        this.windParticles = new WindParticles(this.map);

        this.setupInteraction();
    }

    initTileLayer() {
        this.tileLayer = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: `/tiles/{z}/{x}/{y}/${this.currentTimeIdx}.png`,
                tileSize: 256,
                minZoom: 4,
                maxZoom: 10,
                crossOrigin: 'anonymous',
                tileLoadFunction: (imageTile, src) => {
                    const img = imageTile.getImage();
                    img.onload = () => {};
                    img.onerror = () => {
                        img.style.display = 'none';
                    };
                    img.src = src;
                }
            }),
            opacity: 0.7,
            visible: true
        });
        this.map.addLayer(this.tileLayer);
    }

    setupInteraction() {
        this.map.on('singleclick', async (evt) => {
            const coordinate = ol.proj.toLonLat(evt.coordinate);
            const lon = coordinate[0];
            const lat = coordinate[1];
            
            const timeIdx = window.app.timeController.getCurrentStep();
            const bounds = [105, 20, 125, 40];
            
            if (lon >= bounds[0] && lon <= bounds[2] && 
                lat >= bounds[1] && lat <= bounds[3]) {
                const data = await this.fetchPollutantData(timeIdx, lat, lon);
                if (data) {
                    window.app.popup.show(data);
                }
            }
        });

        this.map.on('pointermove', (evt) => {
            const coordinate = ol.proj.toLonLat(evt.coordinate);
            const lon = coordinate[0];
            const lat = coordinate[1];
            const bounds = [105, 20, 125, 40];
            
            if (lon >= bounds[0] && lon <= bounds[2] && 
                lat >= bounds[1] && lat <= bounds[3]) {
                this.map.getViewport().style.cursor = 'pointer';
            } else {
                this.map.getViewport().style.cursor = '';
            }
        });
    }

    async fetchPollutantData(timeIdx, lat, lon) {
        try {
            const response = await fetch(`/api/pollutants/${timeIdx}/${lat}/${lon}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching pollutant data:', error);
            return null;
        }
    }

    async updateAqiData(timeIdx) {
        this.currentTimeIdx = timeIdx;
        
        if (this.useTileCache) {
            this.updateTileLayer(timeIdx);
        } else {
            try {
                const response = await fetch(`/api/aqi/${timeIdx}`);
                const data = await response.json();
                this.webglRenderer.setData(data.aqi_data, data.bounds);
            } catch (error) {
                console.error('Error fetching AQI data:', error);
            }
        }
    }

    updateTileLayer(timeIdx) {
        if (this.tileLayer) {
            const newSource = new ol.source.XYZ({
                url: `/tiles/{z}/{x}/{y}/${timeIdx}.png`,
                tileSize: 256,
                minZoom: 4,
                maxZoom: 10,
                crossOrigin: 'anonymous',
                tileLoadFunction: (imageTile, src) => {
                    const img = imageTile.getImage();
                    img.onload = () => {};
                    img.onerror = () => {
                        img.style.display = 'none';
                    };
                    img.src = src;
                }
            });
            this.tileLayer.setSource(newSource);
        }
    }

    setRenderMode(useTiles) {
        this.useTileCache = useTiles;
        if (this.tileLayer) {
            this.tileLayer.setVisible(useTiles);
        }
        if (this.webglRenderer) {
            this.webglRenderer.setVisible(!useTiles);
        }
        if (!useTiles) {
            this.updateAqiData(this.currentTimeIdx);
        }
    }

    async updateContourData(timeIdx) {
        try {
            const response = await fetch(`/api/contour/${timeIdx}`);
            const data = await response.json();
            this.contourLayer.setContourData(data.contours, data.bounds);
        } catch (error) {
            console.error('Error fetching contour data:', error);
        }
    }

    async updateWindData(timeIdx) {
        try {
            const response = await fetch(`/api/wind/${timeIdx}`);
            const data = await response.json();
            this.windParticles.setWindData(data.u_data, data.v_data, data.bounds);
        } catch (error) {
            console.error('Error fetching wind data:', error);
        }
    }

    setAqiLayerVisible(visible) {
        if (this.useTileCache) {
            if (this.tileLayer) {
                this.tileLayer.setVisible(visible);
            }
        } else {
            this.webglRenderer.setVisible(visible);
        }
    }

    setContourLayerVisible(visible) {
        this.contourLayer.setVisible(visible);
    }

    setWindLayerVisible(visible) {
        this.windParticles.setVisible(visible);
    }

    setOpacity(opacity) {
        if (this.useTileCache) {
            if (this.tileLayer) {
                this.tileLayer.setOpacity(opacity);
            }
        } else {
            this.webglRenderer.setOpacity(opacity);
        }
    }

    fitToBounds(bounds) {
        const extent = ol.proj.transformExtent(bounds, 'EPSG:4326', 'EPSG:3857');
        this.map.getView().fit(extent, {
            padding: [50, 50, 50, 50],
            duration: 1000
        });
    }
}
