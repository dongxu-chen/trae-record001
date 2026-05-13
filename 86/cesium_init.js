let viewer = null;
let satelliteManager = null;
let orbitManager = null;
let timelineManager = null;
let satelliteListUI = null;
let groundStationManager = null;

const sampleSatellites = [
    {
        name: 'ISS (国际空间站)',
        category: '空间站',
        tle1: '1 25544U 98067A   26133.50000000  .00005000  00000-0  12144-3 0  9993',
        tle2: '2 25544  51.6400  30.0000 0006700  80.0000  90.0000 15.49958000  1234'
    },
    {
        name: '中国空间站 (CSS)',
        category: '空间站',
        tle1: '1 48274U 21035A   26133.50000000  .00005000  00000-0  12000-3 0  9994',
        tle2: '2 48274  41.4700  45.0000 0005000  100.0000  250.0000 15.50000000  1234'
    },
    {
        name: '星链-1007',
        category: '通信卫星',
        tle1: '1 44713U 19074A   26133.50000000  .00001000  00000-0  20000-4 0  9999',
        tle2: '2 44713  53.0000  60.0000 0001000  45.0000  80.0000 15.10000000  1234'
    },
    {
        name: '风云-2H',
        category: '气象卫星',
        tle1: '1 42815U 17041A   26133.50000000  .00000100  00000-0  10000-4 0  9991',
        tle2: '2 42815   0.0500 120.0000 0001000  30.0000  90.0000  1.00270000  1234'
    },
    {
        name: '北斗-3G1',
        category: '导航卫星',
        tle1: '1 44231U 19026A   26133.50000000  .00000200  00000-0  50000-5 0  9998',
        tle2: '2 44231   2.5000  85.0000 0002000  120.0000  180.0000  1.00270000  1234'
    },
    {
        name: 'NOAA-19',
        category: '气象卫星',
        tle1: '1 33591U 09005A   26133.50000000  .00001000  00000-0  25000-4 0  9997',
        tle2: '2 33591  99.0000  40.0000 0001500  80.0000  100.0000 14.10000000  1234'
    }
];

const satelliteColorMap = {
    '空间站': Cesium.Color.RED,
    '通信卫星': Cesium.Color.CYAN,
    '气象卫星': Cesium.Color.YELLOW,
    '导航卫星': Cesium.Color.GREEN,
    '遥感卫星': Cesium.Color.MAGENTA,
    '其他': Cesium.Color.WHITE
};

const sampleGroundStations = [
    {
        name: '北京地面站',
        longitude: 116.4074,
        latitude: 39.9042,
        height: 100,
        elevation: 5,
        beamAngle: 45,
        maxRange: 3000000,
        color: Cesium.Color.RED
    },
    {
        name: '海南文昌',
        longitude: 110.9510,
        latitude: 19.6144,
        height: 20,
        elevation: 3,
        beamAngle: 60,
        maxRange: 4000000,
        color: Cesium.Color.BLUE
    },
    {
        name: '酒泉卫星中心',
        longitude: 100.1700,
        latitude: 40.9500,
        height: 50,
        elevation: 4,
        beamAngle: 30,
        maxRange: 2500000,
        color: Cesium.Color.GREEN
    },
    {
        name: '西昌卫星中心',
        longitude: 102.0200,
        latitude: 28.2500,
        height: 80,
        elevation: 6,
        beamAngle: 50,
        maxRange: 3500000,
        color: Cesium.Color.CYAN
    }
];

function initCesium() {
    Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJiYjMxMTMxMS02Mzk3LTQ2MzYtYjM1MC00MjZjNjI4ZDZkYTEiLCJpZCI6MTI2MTEzLCJpYXQiOjE2NzY3OTgxNzN9.3S3zG6cFjKvYw5vL9XqM7XqM7XqM7XqM7XqM7XqM7XqM';
    
    viewer = new Cesium.Viewer('cesiumContainer', {
        animation: false,
        timeline: false,
        baseLayerPicker: true,
        geocoder: false,
        homeButton: true,
        sceneModePicker: true,
        navigationHelpButton: false,
        fullscreenButton: true,
        infoBox: true,
        selectionIndicator: true,
        skyBox: new Cesium.SkyBox({
            sources: {
                positiveX: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_px.jpg',
                negativeX: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_mx.jpg',
                positiveY: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_py.jpg',
                negativeY: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_my.jpg',
                positiveZ: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_pz.jpg',
                negativeZ: 'https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Assets/Textures/SkyBox/tycho2t3_80_mz.jpg'
            }
        })
    });

    setupAtmosphere();
    
    satelliteManager = new SatelliteManager();
    orbitManager = new OrbitManager(viewer);
    timelineManager = new TimelineManager(viewer, updateSatellites);
    groundStationManager = new GroundStationManager(viewer);
    
    loadSampleSatellites();
    loadGroundStations();
    
    setupControls();
    
    satelliteListUI = new SatelliteListUI(
        satelliteManager,
        viewer,
        {
            onSelect: (satellite, index) => {
                if (satellite && satellite.entity) {
                    viewer.flyTo(satellite.entity, {
                        duration: 1.5,
                        offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-45), 2500000)
                    });
                }
            },
            onToggleVisibility: (satellite, visible) => {
                if (satellite.entity) {
                    satellite.entity.show = visible;
                }
                orbitManager.setOrbitVisibility(satellite.name, visible);
            },
            onToggleOrbit: (satellite, visible) => {
                orbitManager.setOrbitVisibility(satellite.name, visible);
            }
        }
    );
    
    timelineManager.start();
}

function setupAtmosphere() {
    const scene = viewer.scene;
    
    scene.globe.enableLighting = true;
    scene.skyAtmosphere.show = true;
    
    scene.skyAtmosphere.brightnessShift = 0.1;
    scene.skyAtmosphere.saturationShift = 0.0;
    scene.skyAtmosphere.hueShift = 0.0;
    
    scene.fog.enabled = true;
    scene.fog.density = 0.0002;
    scene.fog.screenSpaceErrorFactor = 2.0;
    
    scene.sun.show = true;
    scene.moon.show = true;
    
    if (scene.sunBlink) {
        scene.sunBlink.show = true;
    }
    
    const ellipsoid = Cesium.Ellipsoid.WGS84;
    
    const atmosphereEntity = viewer.entities.add({
        name: 'Atmosphere Effect',
        position: Cesium.Cartesian3.fromDegrees(0, 0, 0),
        ellipse: {
            height: 100000,
            semiMajorAxis: ellipsoid.maximumRadius + 100000,
            semiMinorAxis: ellipsoid.minimumRadius + 100000,
            material: new Cesium.ColorMaterialProperty(
                Cesium.Color.fromCssColorString('rgba(64, 156, 255, 0.15)')
            ),
            outline: false
        }
    });
    
    viewer.entities.add({
        name: 'Atmosphere Scatter',
        position: Cesium.Cartesian3.fromDegrees(0, 0, 0),
        ellipse: {
            height: 50000,
            semiMajorAxis: ellipsoid.maximumRadius + 50000,
            semiMinorAxis: ellipsoid.minimumRadius + 50000,
            material: new Cesium.ColorMaterialProperty(
                Cesium.Color.fromCssColorString('rgba(100, 180, 255, 0.1)')
            ),
            outline: false
        }
    });
}

function loadSampleSatellites() {
    sampleSatellites.forEach((sat, index) => {
        const satellite = satelliteManager.addSatellite(sat.name, sat.tle1, sat.tle2);
        satellite.category = sat.category || '其他';
        satellite.color = satelliteColorMap[satellite.category] || Cesium.Color.WHITE;
        
        createSatelliteEntity(satellite, index);
        
        const orbit = satellite.getOrbitPoints(150);
        orbitManager.addOrbit(sat.name, orbit, satellite.color);
    });
}

function loadGroundStations() {
    if (!groundStationManager) return;
    
    sampleGroundStations.forEach(station => {
        groundStationManager.addStation({
            name: station.name,
            position: {
                longitude: station.longitude,
                latitude: station.latitude,
                height: station.height
            },
            elevation: station.elevation,
            beamAngle: station.beamAngle,
            maxRange: station.maxRange,
            color: station.color
        });
    });
}

function createSatelliteEntity(satellite, index) {
    const position = satellite.getPosition(new Date());
    
    satellite.entity = viewer.entities.add({
        name: satellite.name,
        position: position,
        point: {
            pixelSize: 14,
            color: satellite.color,
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2
        },
        label: {
            text: satellite.name,
            font: '12pt sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -18),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 20000000)
        },
        path: {
            leadTime: 0,
            trailTime: 7200,
            width: 3,
            material: satellite.color.withAlpha(0.8),
            resolution: 1
        }
    });
    
    satellite.entity.properties = new Cesium.PropertyBag({
        satelliteIndex: index,
        category: satellite.category || '其他'
    });
}

function updateSatellites(currentTime) {
    const satellites = satelliteManager.getAllSatellites();
    
    satellites.forEach(satellite => {
        if (satellite.entity) {
            const position = satellite.getPosition(currentTime);
            satellite.entity.position = position;
            
            const velocity = satellite.getVelocity(currentTime);
            
            const sampledPosition = new Cesium.SampledPositionProperty();
            
            const now = currentTime.getTime();
            for (let i = -120; i <= 120; i++) {
                const time = new Date(now + i * 30000);
                const pos = satellite.getPosition(time);
                sampledPosition.addSample(Cesium.JulianDate.fromDate(time), pos);
            }
            
            satellite.entity.position = sampledPosition;
        }
    });
    
    if (groundStationManager) {
        groundStationManager.updateBeams(currentTime, satellites);
    }
    
    updateTimeDisplay(currentTime);
    
    if (satelliteListUI && satelliteListUI.update && typeof satelliteListUI.update === 'function') {
        satelliteListUI.update();
    }
}

function updateTimeDisplay(currentTime) {
    const display = document.getElementById('timeDisplay');
    if (display) {
        display.innerHTML = `当前时间: ${currentTime.toLocaleString('zh-CN')}<br>
                            UTC: ${currentTime.toISOString().replace('T', ' ').substring(0, 19)}`;
    }
}

function setupControls() {
    const speedSlider = document.getElementById('speedSlider');
    const speedDisplay = document.getElementById('speedDisplay');
    
    if (speedSlider && speedDisplay) {
        speedSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            let speed = value;
            
            if (value > 0 && value <= 10) {
                speed = value;
            } else if (value > 10) {
                speed = Math.pow(10, (value - 10) / 15);
            } else if (value < 0 && value >= -10) {
                speed = value;
            } else if (value < -10) {
                speed = -Math.pow(10, (-value - 10) / 15);
            }
            
            timelineManager.setSpeed(speed);
            speedDisplay.textContent = formatSpeedDisplay(speed);
        });
    }
}

function formatSpeedDisplay(speed) {
    if (Math.abs(speed) < 1) {
        return speed.toFixed(2) + 'x';
    } else if (Math.abs(speed) < 10) {
        return speed.toFixed(1) + 'x';
    } else {
        return Math.round(speed) + 'x';
    }
}

function togglePlay() {
    if (timelineManager) {
        timelineManager.toggle();
    }
}

function resetTime() {
    if (timelineManager) {
        timelineManager.reset();
    }
}

window.addEventListener('load', initCesium);
