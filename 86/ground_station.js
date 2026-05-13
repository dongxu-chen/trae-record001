const EARTH_RADIUS_METERS = 6371000;

class GroundStation {
    constructor(stationData, viewer) {
        this.viewer = viewer;
        this.name = stationData.name;
        this.longitude = stationData.position.longitude;
        this.latitude = stationData.position.latitude;
        this.height = stationData.position.height || 0;
        this.elevation = stationData.elevation || 5;
        this.beamAngle = stationData.beamAngle || 45;
        this.maxRange = stationData.maxRange || 3000000;
        this.color = stationData.color || Cesium.Color.CYAN;
        
        this.entities = {};
        this.visible = true;
        this.beamVisible = true;
        
        this.createStation();
    }
    
    createStation() {
        const position = Cesium.Cartesian3.fromDegrees(
            this.longitude,
            this.latitude,
            this.height
        );
        
        this.entities.marker = this.viewer.entities.add({
            name: this.name,
            position: position,
            point: {
                pixelSize: 16,
                color: this.color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 3
            },
            label: {
                text: this.name,
                font: '11pt sans-serif',
                fillColor: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -20),
                distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 15000000)
            }
        });
        
        this.entities.rangeCircle = this.viewer.entities.add({
            name: `${this.name} - Range`,
            position: position,
            ellipse: {
                semiMajorAxis: this.maxRange,
                semiMinorAxis: this.maxRange,
                material: this.color.withAlpha(0.05),
                outline: true,
                outlineColor: this.color.withAlpha(0.5),
                outlineWidth: 2,
                height: 0,
                classificationType: Cesium.ClassificationType.TERRAIN
            }
        });
        
        this.createBeamCone();
    }
    
    createBeamCone() {
        const position = Cesium.Cartesian3.fromDegrees(
            this.longitude,
            this.latitude,
            this.height
        );
        
        const coneHeight = this.maxRange;
        const coneRadius = coneHeight * Math.tan(Cesium.Math.toRadians(this.beamAngle));
        
        const headingPitchRoll = new Cesium.HeadingPitchRoll(
            0,
            -Cesium.Math.PI_OVER_TWO,
            0
        );
        
        const orientation = Cesium.Transforms.headingPitchRollQuaternion(
            position,
            headingPitchRoll
        );
        
        this.entities.beam = this.viewer.entities.add({
            name: `${this.name} - Beam`,
            position: position,
            orientation: orientation,
            ellipsoid: {
                radii: new Cesium.Cartesian3(coneRadius, coneRadius, coneHeight),
                innerRadii: new Cesium.Cartesian3(0, 0, 0),
                material: this.color.withAlpha(0.08),
                outline: true,
                outlineColor: this.color.withAlpha(0.4),
                outlineWidth: 1,
                minimumClock: 0,
                maximumClock: Cesium.Math.TWO_PI,
                minimumCone: 0,
                maximumCone: Cesium.Math.toRadians(this.beamAngle),
                fill: true
            },
            show: this.beamVisible
        });
        
        this.entities.beamLine = this.viewer.entities.add({
            name: `${this.name} - Beam Axis`,
            polyline: {
                positions: [
                    position,
                    Cesium.Cartesian3.fromDegrees(
                        this.longitude,
                        this.latitude,
                        this.height + coneHeight
                    )
                ],
                width: 1,
                material: this.color.withAlpha(0.3),
                show: this.beamVisible
            }
        });
    }
    
    updateBeamForSatellite(satellitePosition) {
        if (!satellitePosition || !this.beamVisible) return;
        
        const stationPosition = Cesium.Cartesian3.fromDegrees(
            this.longitude,
            this.latitude,
            this.height
        );
        
        const direction = Cesium.Cartesian3.subtract(
            satellitePosition,
            stationPosition,
            new Cesium.Cartesian3()
        );
        
        const distance = Cesium.Cartesian3.magnitude(direction);
        
        if (distance > this.maxRange) {
            if (this.entities.satelliteBeam) {
                this.viewer.entities.remove(this.entities.satelliteBeam);
                this.entities.satelliteBeam = null;
            }
            return;
        }
        
        const elevation = this.calculateElevation(stationPosition, satellitePosition);
        
        if (elevation < this.elevation) {
            if (this.entities.satelliteBeam) {
                this.viewer.entities.remove(this.entities.satelliteBeam);
                this.entities.satelliteBeam = null;
            }
            return;
        }
        
        if (this.entities.satelliteBeam) {
            this.viewer.entities.remove(this.entities.satelliteBeam);
        }
        
        const coneHeight = distance;
        const coneRadius = coneHeight * Math.tan(Cesium.Math.toRadians(this.beamAngle / 4));
        
        Cesium.Cartesian3.normalize(direction, direction);
        
        const heading = Math.atan2(direction.y, direction.x);
        const pitch = Math.asin(direction.z);
        
        const headingPitchRoll = new Cesium.HeadingPitchRoll(heading, -pitch, 0);
        const orientation = Cesium.Transforms.headingPitchRollQuaternion(
            stationPosition,
            headingPitchRoll
        );
        
        this.entities.satelliteBeam = this.viewer.entities.add({
            name: `${this.name} - Tracking`,
            position: stationPosition,
            orientation: orientation,
            ellipsoid: {
                radii: new Cesium.Cartesian3(coneRadius, coneRadius, coneHeight),
                innerRadii: new Cesium.Cartesian3(0, 0, 0),
                material: this.color.withAlpha(0.15),
                outline: true,
                outlineColor: this.color.withAlpha(0.6),
                outlineWidth: 1.5,
                minimumClock: 0,
                maximumClock: Cesium.Math.TWO_PI,
                minimumCone: 0,
                maximumCone: Cesium.Math.toRadians(this.beamAngle / 4),
                fill: true
            }
        });
        
        if (!this.entities.connection) {
            this.entities.connection = this.viewer.entities.add({
                name: `${this.name} - Connection`,
                polyline: {
                    positions: [stationPosition, satellitePosition],
                    width: 2,
                    material: this.color.withAlpha(0.6),
                    depthFailMaterial: this.color.withAlpha(0.2)
                }
            });
        } else {
            this.entities.connection.polyline.positions = [stationPosition, satellitePosition];
        }
    }
    
    clearTrackingBeam() {
        if (this.entities.satelliteBeam) {
            this.viewer.entities.remove(this.entities.satelliteBeam);
            this.entities.satelliteBeam = null;
        }
        if (this.entities.connection) {
            this.viewer.entities.remove(this.entities.connection);
            this.entities.connection = null;
        }
    }
    
    calculateElevation(stationPos, satellitePos) {
        const vector = Cesium.Cartesian3.subtract(
            satellitePos,
            stationPos,
            new Cesium.Cartesian3()
        );
        
        const cartographic = Cesium.Cartographic.fromCartesian(stationPos);
        
        const upVector = Cesium.Cartesian3.fromElements(
            Math.cos(cartographic.latitude) * Math.cos(cartographic.longitude),
            Math.cos(cartographic.latitude) * Math.sin(cartographic.longitude),
            Math.sin(cartographic.latitude)
        );
        
        Cesium.Cartesian3.normalize(upVector, upVector);
        Cesium.Cartesian3.normalize(vector, vector);
        
        const dotProduct = Cesium.Cartesian3.dot(upVector, vector);
        const elevationAngle = Math.asin(dotProduct);
        
        return Cesium.Math.toDegrees(elevationAngle);
    }
    
    setVisible(visible) {
        this.visible = visible;
        
        Object.keys(this.entities).forEach(key => {
            if (this.entities[key]) {
                if (key === 'beam' || key === 'beamLine') {
                    this.entities[key].show = visible && this.beamVisible;
                } else {
                    this.entities[key].show = visible;
                }
            }
        });
    }
    
    setBeamVisible(visible) {
        this.beamVisible = visible;
        
        if (this.entities.beam) {
            this.entities.beam.show = this.visible && visible;
        }
        if (this.entities.beamLine) {
            this.entities.beamLine.show = this.visible && visible;
        }
    }
    
    setColor(color) {
        this.color = color;
        
        if (this.entities.marker && this.entities.marker.point) {
            this.entities.marker.point.color = color;
        }
        
        if (this.entities.rangeCircle && this.entities.rangeCircle.ellipse) {
            this.entities.rangeCircle.ellipse.material = color.withAlpha(0.05);
            this.entities.rangeCircle.ellipse.outlineColor = color.withAlpha(0.5);
        }
        
        if (this.entities.beam && this.entities.beam.ellipsoid) {
            this.entities.beam.ellipsoid.material = color.withAlpha(0.08);
            this.entities.beam.ellipsoid.outlineColor = color.withAlpha(0.4);
        }
    }
    
    destroy() {
        Object.keys(this.entities).forEach(key => {
            if (this.entities[key]) {
                this.viewer.entities.remove(this.entities[key]);
            }
        });
        this.entities = {};
    }
}

class GroundStationManager {
    constructor(viewer) {
        this.viewer = viewer;
        this.stations = new Map();
        this.visible = true;
        this.beamsVisible = true;
    }
    
    addStation(stationData) {
        const station = new GroundStation(stationData, this.viewer);
        this.stations.set(station.name, station);
        return station;
    }
    
    removeStation(name) {
        const station = this.stations.get(name);
        if (station) {
            station.destroy();
            this.stations.delete(name);
        }
    }
    
    getStation(name) {
        return this.stations.get(name);
    }
    
    getAllStations() {
        return Array.from(this.stations.values());
    }
    
    updateBeams(currentTime, satellites) {
        this.stations.forEach(station => {
            if (!station.visible || !station.beamVisible) {
                station.clearTrackingBeam();
                return;
            }
            
            let bestSatellite = null;
            let minDistance = Infinity;
            
            satellites.forEach(satellite => {
                if (!satellite.entity || !satellite.entity.show) return;
                
                const satPosition = satellite.entity.position;
                if (!satPosition) return;
                
                let positionValue;
                if (satPosition instanceof Cesium.SampledPositionProperty) {
                    const julianTime = Cesium.JulianDate.fromDate(currentTime);
                    positionValue = satPosition.getValue(julianTime);
                } else if (satPosition instanceof Cesium.ConstantPositionProperty) {
                    positionValue = satPosition.getValue(Cesium.JulianDate.now());
                } else if (satPosition instanceof Cesium.Cartesian3) {
                    positionValue = satPosition;
                }
                
                if (!positionValue) return;
                
                const stationPos = Cesium.Cartesian3.fromDegrees(
                    station.longitude,
                    station.latitude,
                    station.height
                );
                
                const distance = Cesium.Cartesian3.distance(stationPos, positionValue);
                
                const elevation = station.calculateElevation(stationPos, positionValue);
                
                if (distance < station.maxRange && 
                    elevation >= station.elevation && 
                    distance < minDistance) {
                    minDistance = distance;
                    bestSatellite = positionValue;
                }
            });
            
            if (bestSatellite) {
                station.updateBeamForSatellite(bestSatellite);
            } else {
                station.clearTrackingBeam();
            }
        });
    }
    
    setAllVisible(visible) {
        this.visible = visible;
        this.stations.forEach(station => {
            station.setVisible(visible);
        });
    }
    
    setAllBeamsVisible(visible) {
        this.beamsVisible = visible;
        this.stations.forEach(station => {
            station.setBeamVisible(visible);
        });
    }
    
    clearAll() {
        this.stations.forEach(station => {
            station.destroy();
        });
        this.stations.clear();
    }
    
    getStationCount() {
        return this.stations.size;
    }
}

const groundStationStyles = `
    .ground-station-panel {
        position: absolute;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.85);
        color: white;
        padding: 12px 15px;
        border-radius: 8px;
        font-family: Arial, sans-serif;
        z-index: 100;
        font-size: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .ground-station-panel h4 {
        margin: 0 0 10px 0;
        font-size: 13px;
        color: #4db8ff;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 6px;
    }
    
    .ground-station-panel .station-toggle {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        cursor: pointer;
        padding: 4px 6px;
        border-radius: 4px;
        transition: background 0.2s;
    }
    
    .ground-station-panel .station-toggle:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    
    .ground-station-panel .station-color {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    
    .ground-station-panel .station-name {
        flex: 1;
    }
    
    .ground-station-panel .control-row {
        display: flex;
        gap: 8px;
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .ground-station-panel .gs-btn {
        flex: 1;
        padding: 5px 8px;
        border: none;
        border-radius: 4px;
        background: rgba(77, 184, 255, 0.3);
        color: white;
        font-size: 11px;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .ground-station-panel .gs-btn:hover {
        background: rgba(77, 184, 255, 0.5);
    }
`;

(function injectGroundStationStyles() {
    const styleId = 'ground-station-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = groundStationStyles;
        document.head.appendChild(style);
    }
})();
