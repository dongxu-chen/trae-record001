class ContourLayer {
    constructor(map) {
        this.map = map;
        this.vectorSource = new ol.source.Vector();
        this.vectorLayer = new ol.layer.Vector({
            source: this.vectorSource,
            style: this.createStyle.bind(this),
            visible: false
        });
        this.map.addLayer(this.vectorLayer);
        this.contourData = null;
        this.bounds = null;
    }

    createStyle(feature) {
        const level = feature.get('level');
        const color = this.getLevelColor(level);
        
        return new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: color,
                width: 1.5
            }),
            text: new ol.style.Text({
                font: '12px sans-serif',
                text: level.toString(),
                fill: new ol.style.Fill({ color: '#ffffff' }),
                stroke: new ol.style.Stroke({ color: '#000000', width: 2 }),
                placement: 'line',
                maxAngle: 45
            })
        });
    }

    getLevelColor(level) {
        if (level <= 50) return 'rgba(0, 228, 0, 0.8)';
        if (level <= 100) return 'rgba(255, 255, 0, 0.8)';
        if (level <= 150) return 'rgba(255, 126, 0, 0.8)';
        if (level <= 200) return 'rgba(255, 0, 0, 0.8)';
        if (level <= 300) return 'rgba(153, 0, 76, 0.8)';
        return 'rgba(126, 0, 35, 0.8)';
    }

    setContourData(contours, bounds) {
        this.contourData = contours;
        this.bounds = bounds;
        this.render();
    }

    render() {
        this.vectorSource.clear();

        if (!this.contourData) return;

        this.contourData.forEach(contour => {
            contour.lines.forEach(line => {
                if (line.length >= 2) {
                    const coordinates = line.map(coord => 
                        ol.proj.fromLonLat([coord[0], coord[1]])
                    );
                    
                    const lineString = new ol.geom.LineString(coordinates);
                    const feature = new ol.Feature({
                        geometry: lineString,
                        level: contour.level
                    });
                    
                    this.vectorSource.addFeature(feature);
                }
            });
        });
    }

    setVisible(visible) {
        this.vectorLayer.setVisible(visible);
    }

    getLayer() {
        return this.vectorLayer;
    }
}
