class OrbitManager {
    constructor(viewer) {
        this.viewer = viewer;
        this.orbits = new Map();
    }
    
    addOrbit(name, points, color = Cesium.Color.WHITE, options = {}) {
        if (points.length < 2) {
            console.warn('轨道点太少，无法绘制');
            return null;
        }
        
        const width = options.width || 3;
        const glowWidth = options.glowWidth || 6;
        const opacity = options.opacity || 1.0;
        const glowOpacity = options.glowOpacity || 0.25;
        const behindOpacity = options.behindOpacity || 0.15;
        
        const mainMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, opacity)
        );
        const glowMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, glowOpacity)
        );
        const behindMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, behindOpacity)
        );
        const glowBehindMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, glowOpacity * 0.3)
        );
        
        const polylineEntity = this.viewer.entities.add({
            name: `Orbit: ${name}`,
            polyline: {
                positions: points,
                width: width,
                material: mainMaterial,
                depthFailMaterial: behindMaterial,
                clampToGround: false,
                arcType: Cesium.ArcType.NONE
            }
        });
        
        const glowingPolyline = this.viewer.entities.add({
            name: `Orbit Glow: ${name}`,
            polyline: {
                positions: points,
                width: glowWidth,
                material: glowMaterial,
                depthFailMaterial: glowBehindMaterial,
                clampToGround: false,
                arcType: Cesium.ArcType.NONE
            }
        });
        
        const ellipseEntity = null;
        
        this.orbits.set(name, {
            polyline: polylineEntity,
            glow: glowingPolyline,
            ellipse: ellipseEntity,
            points: points,
            color: color,
            visible: true,
            options: {
                width, glowWidth, opacity, glowOpacity, behindOpacity
            }
        });
        
        return polylineEntity;
    }
    
    createOrbitEllipse(points, color) {
        return null;
    }
    
    getOrbitCenter(points) {
        if (points.length === 0) return Cesium.Cartesian3.ZERO;
        
        let sumX = 0, sumY = 0, sumZ = 0;
        points.forEach(point => {
            sumX += point.x;
            sumY += point.y;
            sumZ += point.z;
        });
        
        return new Cesium.Cartesian3(
            sumX / points.length,
            sumY / points.length,
            sumZ / points.length
        );
    }
    
    updateOrbit(name, points) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        orbit.points = points;
        
        if (orbit.polyline && orbit.polyline.polyline) {
            orbit.polyline.polyline.positions = points;
        }
        
        if (orbit.glow && orbit.glow.polyline) {
            orbit.glow.polyline.positions = points;
        }
    }
    
    removeOrbit(name) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        if (orbit.polyline) {
            this.viewer.entities.remove(orbit.polyline);
        }
        
        if (orbit.glow) {
            this.viewer.entities.remove(orbit.glow);
        }
        
        if (orbit.ellipse) {
            this.viewer.entities.remove(orbit.ellipse);
        }
        
        this.orbits.delete(name);
    }
    
    setOrbitVisibility(name, visible) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        if (orbit.polyline) {
            orbit.polyline.show = visible;
        }
        
        if (orbit.glow) {
            orbit.glow.show = visible;
        }
        
        if (orbit.ellipse) {
            orbit.ellipse.show = visible;
        }
        
        orbit.visible = visible;
    }
    
    setOrbitColor(name, color) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        orbit.color = color;
        const options = orbit.options || {};
        
        const mainMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, options.opacity || 1.0)
        );
        const glowMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, options.glowOpacity || 0.25)
        );
        const behindMaterial = new Cesium.ColorMaterialProperty(
            Cesium.Color.fromAlpha(color, options.behindOpacity || 0.15)
        );
        
        if (orbit.polyline && orbit.polyline.polyline) {
            orbit.polyline.polyline.material = mainMaterial;
            orbit.polyline.polyline.depthFailMaterial = behindMaterial;
        }
        
        if (orbit.glow && orbit.glow.polyline) {
            orbit.glow.polyline.material = glowMaterial;
        }
    }
    
    setOrbitStyle(name, options = {}) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        const color = options.color || orbit.color;
        const opacity = options.opacity !== undefined ? options.opacity : orbit.options.opacity;
        const width = options.width || orbit.options.width;
        const glowWidth = options.glowWidth || orbit.options.glowWidth;
        const glowOpacity = options.glowOpacity !== undefined ? options.glowOpacity : orbit.options.glowOpacity;
        const behindOpacity = options.behindOpacity !== undefined ? options.behindOpacity : orbit.options.behindOpacity;
        
        orbit.options = { width, glowWidth, opacity, glowOpacity, behindOpacity };
        
        this.setOrbitColor(name, color);
        
        if (orbit.polyline && orbit.polyline.polyline) {
            orbit.polyline.polyline.width = width;
        }
        
        if (orbit.glow && orbit.glow.polyline) {
            orbit.glow.polyline.width = glowWidth;
        }
    }
    
    clearAllOrbits() {
        this.orbits.forEach((orbit, name) => {
            if (orbit.polyline) {
                this.viewer.entities.remove(orbit.polyline);
            }
            
            if (orbit.glow) {
                this.viewer.entities.remove(orbit.glow);
            }
            
            if (orbit.ellipse) {
                this.viewer.entities.remove(orbit.ellipse);
            }
        });
        
        this.orbits.clear();
    }
    
    getAllOrbits() {
        return Array.from(this.orbits.keys());
    }
    
    getOrbitPoints(name) {
        const orbit = this.orbits.get(name);
        return orbit ? orbit.points : null;
    }
    
    showAllOrbits() {
        this.orbits.forEach((orbit, name) => {
            this.setOrbitVisibility(name, true);
        });
    }
    
    hideAllOrbits() {
        this.orbits.forEach((orbit, name) => {
            this.setOrbitVisibility(name, false);
        });
    }
    
    toggleOrbitVisibility(name) {
        const orbit = this.orbits.get(name);
        if (!orbit) return;
        
        this.setOrbitVisibility(name, !orbit.visible);
    }
}

class OrbitHelper {
    static createGroundTrack(viewer, points, color) {
        const groundPositions = points.map(point => {
            const cartographic = Cesium.Cartographic.fromCartesian(point);
            return Cesium.Cartesian3.fromRadians(
                cartographic.longitude,
                cartographic.latitude,
                0
            );
        });
        
        return viewer.entities.add({
            name: 'Ground Track',
            polyline: {
                positions: groundPositions,
                width: 2,
                material: new Cesium.ColorMaterialProperty(color),
                clampToGround: true
            }
        });
    }
    
    static createOrbitPlane(viewer, points, color) {
        if (points.length < 3) return null;
        
        const center = OrbitHelper.calculateOrbitCenter(points);
        const normal = OrbitHelper.calculateOrbitNormal(points);
        
        const centerPosition = Cesium.Cartesian3.fromRadians(0, 0, 0);
        
        const plane = new Cesium.Plane(normal, 0);
        const planeOrientation = Cesium.Transforms.headingPitchRollQuaternion(
            centerPosition,
            new Cesium.HeadingPitchRoll(0, 0, 0)
        );
        
        return viewer.entities.add({
            name: 'Orbit Plane',
            position: centerPosition,
            orientation: planeOrientation,
            plane: {
                plane: plane,
                dimensions: new Cesium.Cartesian2(20000000, 20000000),
                material: color.withAlpha(0.1),
                outline: true,
                outlineColor: color,
                outlineWidth: 1
            }
        });
    }
    
    static calculateOrbitCenter(points) {
        if (points.length === 0) return Cesium.Cartesian3.ZERO;
        
        let sumX = 0, sumY = 0, sumZ = 0;
        points.forEach(point => {
            sumX += point.x;
            sumY += point.y;
            sumZ += point.z;
        });
        
        return new Cesium.Cartesian3(
            sumX / points.length,
            sumY / points.length,
            sumZ / points.length
        );
    }
    
    static calculateOrbitNormal(points) {
        if (points.length < 3) return Cesium.Cartesian3.UNIT_Z;
        
        const center = OrbitHelper.calculateOrbitCenter(points);
        
        const v1 = Cesium.Cartesian3.subtract(points[0], center, new Cesium.Cartesian3());
        const v2 = Cesium.Cartesian3.subtract(points[Math.floor(points.length / 3)], center, new Cesium.Cartesian3());
        
        const normal = Cesium.Cartesian3.cross(v1, v2, new Cesium.Cartesian3());
        Cesium.Cartesian3.normalize(normal, normal);
        
        return normal;
    }
}
