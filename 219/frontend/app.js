const API_BASE = '';

let map;
let heatmapImageLayer;
let heatmapImageLayerBack;
let congestionLayer;
let congestionSource;
let heatmapData = null;
let currentWindowIndex = 0;
let isPlaying = false;
let playInterval = null;
let playSpeed = 1000;
let heatmapBounds = null;
let imageCache = {};
let preloadBuffer = {};
let preloadInProgress = {};
let useTileMode = true;
let preGenerationProgress = 0;
let isPreGenerationComplete = false;
let progressInterval = null;

let alertLayer;
let alertSource;
let routeLayer;
let routeSource;
let comparisonLayer;
let comparisonLayer2;
let alertThreshold = 0.7;
let compareMode = false;
let compareWindowIndex1 = 0;
let compareWindowIndex2 = 1;
let currentRouteId = null;
let alertInterval = null;

function initMap() {
    congestionSource = new ol.source.Vector();
    
    congestionLayer = new ol.layer.Vector({
        source: congestionSource,
        style: function(feature) {
            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 8,
                    fill: new ol.style.Fill({ color: '#ff00ff' }),
                    stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                }),
                text: new ol.style.Text({
                    text: feature.get('label') || '',
                    font: 'bold 12px sans-serif',
                    fill: new ol.style.Fill({ color: '#000000' }),
                    offsetY: -15
                })
            });
        }
    });

    alertSource = new ol.source.Vector();
    alertLayer = new ol.layer.Vector({
        source: alertSource,
        style: function(feature) {
            const level = feature.get('alert_level');
            const color = level === 'high' ? '#ff0000' : '#ff8800';
            const radius = level === 'high' ? 15 : 10;
            
            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: radius,
                    fill: new ol.style.Fill({ color: color }),
                    stroke: new ol.style.Stroke({ color: '#ffff00', width: 3 })
                }),
                text: new ol.style.Text({
                    text: '⚠️',
                    font: 'bold 16px sans-serif',
                    offsetY: -radius - 5
                })
            });
        },
        zIndex: 50
    });

    routeSource = new ol.source.Vector();
    routeLayer = new ol.layer.Vector({
        source: routeSource,
        style: function(feature) {
            return new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: '#0066ff',
                    width: 6
                }),
                image: new ol.style.Circle({
                    radius: 7,
                    fill: new ol.style.Fill({ color: '#0066ff' }),
                    stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                })
            });
        },
        zIndex: 40
    });

    map = new ol.Map({
        target: 'map',
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            }),
            congestionLayer,
            routeLayer,
            alertLayer
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([116.40, 39.91]),
            zoom: 13
        })
    });

    map.on('click', function(evt) {
        const feature = map.forEachFeatureAtPixel(evt.pixel, function(f) { return f; });
        if (feature) {
            const props = feature.getProperties();
            if (props.count !== undefined) {
                alert(`网格信息:\n车辆数: ${props.count}\n密度: ${(props.density * 100).toFixed(1)}%\n位置: ${props.center_lon.toFixed(4)}, ${props.center_lat.toFixed(4)}`);
            } else if (props.route_id) {
                alert(`拥堵路段:\n线路: ${props.route_id}\n车辆数: ${props.count}\n拥堵比例: ${(props.ratio * 100).toFixed(1)}%`);
            }
        }
    });
}

function createHeatmapImageLayer() {
    if (heatmapImageLayer) {
        map.removeLayer(heatmapImageLayer);
    }
    
    heatmapImageLayer = new ol.layer.Image({
        opacity: 0.8,
        zIndex: 10
    });
    
    map.addLayer(heatmapImageLayer);
    map.getLayers().getArray().splice(1, 0, map.getLayers().pop());
}

function createBackBufferLayer() {
    if (heatmapImageLayerBack) {
        map.removeLayer(heatmapImageLayerBack);
    }
    
    heatmapImageLayerBack = new ol.layer.Image({
        opacity: 0,
        zIndex: 9
    });
    
    map.addLayer(heatmapImageLayerBack);
}

function updateHeatmapImage(windowIndex, callback) {
    if (!heatmapBounds) return;
    
    const cacheKey = windowIndex;
    
    const applyImage = function(imgUrl) {
        const extent = ol.proj.transformExtent(
            [heatmapBounds.lon_min, heatmapBounds.lat_min, heatmapBounds.lon_max, heatmapBounds.lat_max],
            'EPSG:4326',
            'EPSG:3857'
        );
        
        const imageSource = new ol.source.ImageStatic({
            url: imgUrl,
            imageExtent: extent,
            projection: 'EPSG:3857'
        });
        
        if (heatmapImageLayerBack) {
            heatmapImageLayerBack.setSource(imageSource);
            
            let opacity = 0;
            const fadeInterval = setInterval(function() {
                opacity += 0.1;
                if (opacity >= 0.8) {
                    opacity = 0.8;
                    clearInterval(fadeInterval);
                    
                    if (heatmapImageLayer) {
                        map.removeLayer(heatmapImageLayer);
                    }
                    heatmapImageLayer = heatmapImageLayerBack;
                    heatmapImageLayer.setOpacity(0.8);
                    heatmapImageLayer.setZIndex(10);
                    createBackBufferLayer();
                    
                    if (callback) callback();
                } else {
                    heatmapImageLayerBack.setOpacity(opacity);
                }
            }, 30);
        } else {
            heatmapImageLayer.setSource(imageSource);
            if (callback) callback();
        }
        
        imageCache[cacheKey] = imgUrl;
    };
    
    if (imageCache[cacheKey]) {
        applyImage(imageCache[cacheKey]);
        return;
    }
    
    if (preloadBuffer[cacheKey]) {
        applyImage(preloadBuffer[cacheKey]);
        return;
    }
    
    const imageUrl = `${API_BASE}/api/heatmap/image/${windowIndex}?use_cache=true`;
    applyImage(imageUrl);
}

function preloadNextImages(currentIndex, count) {
    if (!heatmapData) return;
    
    const totalWindows = heatmapData.time_windows.length;
    const toPreload = [];
    
    for (let i = 1; i <= count; i++) {
        const nextIndex = (currentIndex + i) % totalWindows;
        if (!imageCache[nextIndex] && !preloadBuffer[nextIndex] && !preloadInProgress[nextIndex]) {
            toPreload.push(nextIndex);
        }
    }
    
    toPreload.forEach(function(index) {
        preloadInProgress[index] = true;
        
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = function() {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            preloadBuffer[index] = canvas.toDataURL('image/png');
            delete preloadInProgress[index];
        };
        img.onerror = function() {
            delete preloadInProgress[index];
        };
        img.src = `${API_BASE}/api/heatmap/image/${index}?use_cache=true`;
    });
}

function cleanupOldCache(currentIndex) {
    const keepCount = 5;
    const totalWindows = heatmapData ? heatmapData.time_windows.length : 0;
    
    Object.keys(imageCache).forEach(function(key) {
        const idx = parseInt(key);
        const diff = Math.abs(idx - currentIndex);
        const wrappedDiff = totalWindows - diff;
        const minDiff = Math.min(diff, wrappedDiff);
        
        if (minDiff > keepCount && idx !== currentIndex) {
            delete imageCache[key];
        }
    });
    
    Object.keys(preloadBuffer).forEach(function(key) {
        const idx = parseInt(key);
        const diff = Math.abs(idx - currentIndex);
        const wrappedDiff = totalWindows - diff;
        const minDiff = Math.min(diff, wrappedDiff);
        
        if (minDiff > keepCount && idx !== currentIndex) {
            delete preloadBuffer[key];
        }
    });
}

function updateCongestionMarkers(windowData) {
    congestionSource.clear();

    if (!windowData || !windowData.congestion_segments) return;

    const congestionFeatures = [];
    windowData.congestion_segments.forEach(function(seg, idx) {
        const feature = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.fromLonLat([seg.center_lon, seg.center_lat])),
            route_id: seg.route_id,
            count: seg.count,
            ratio: seg.ratio,
            label: idx < 3 ? seg.route_id : ''
        });
        congestionFeatures.push(feature);
    });

    congestionSource.addFeatures(congestionFeatures);
}

function updateTimeDisplay(windowData) {
    if (!windowData) return;

    const start = new Date(windowData.time_start);
    const end = new Date(windowData.time_end);
    
    const formatTime = function(d) {
        return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    };

    document.getElementById('currentTime').textContent = formatTime(start);
    document.getElementById('endTime').textContent = formatTime(end);
    document.getElementById('windowIndex').textContent = currentWindowIndex + 1;
}

function updateCongestionList(allCongestion) {
    const listEl = document.getElementById('congestionList');
    
    if (!allCongestion || allCongestion.length === 0) {
        listEl.innerHTML = '<p class="text-muted">暂无拥堵数据</p>';
        return;
    }

    let html = '<div class="congestion-items">';
    allCongestion.slice(0, 10).forEach(function(seg, idx) {
        const time = new Date(seg.time_start).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        html += `
            <div class="congestion-item">
                <div class="congestion-header">
                    <span class="rank">#${idx + 1}</span>
                    <span class="route">${seg.route_id}</span>
                    <span class="time">${time}</span>
                </div>
                <div class="congestion-details">
                    <span>车辆: ${seg.count}</span>
                    <span>拥堵率: ${(seg.ratio * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    listEl.innerHTML = html;
}

function updatePreGenerationProgress() {
    const progressEl = document.getElementById('preGenProgress');
    if (progressEl) {
        progressEl.textContent = `预生成进度: ${preGenerationProgress}%`;
        
        if (isPreGenerationComplete) {
            progressEl.textContent += ' ✓ 完成';
        }
    }
}

async function pollPreGenerationProgress() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(async function() {
        try {
            const response = await fetch(`${API_BASE}/api/heatmap/progress`);
            const data = await response.json();
            
            preGenerationProgress = data.progress;
            isPreGenerationComplete = data.complete;
            updatePreGenerationProgress();
            
            if (isPreGenerationComplete) {
                clearInterval(progressInterval);
            }
        } catch (e) {
            console.error('获取进度失败:', e);
        }
    }, 1000);
}

async function uploadData() {
    const fileInput = document.getElementById('fileInput');
    const city = document.getElementById('cityInput').value;
    const statusEl = document.getElementById('uploadStatus');

    if (!city) {
        statusEl.textContent = '请输入城市名称';
        statusEl.className = 'status status-error';
        return;
    }

    if (!fileInput.files || fileInput.files.length === 0) {
        statusEl.textContent = '请选择数据文件';
        statusEl.className = 'status status-error';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    statusEl.textContent = '上传中...';
    statusEl.className = 'status';

    try {
        const response = await fetch(`${API_BASE}/api/upload?city=${encodeURIComponent(city)}`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            statusEl.textContent = result.message;
            statusEl.className = 'status status-success';
            document.getElementById('cityName').textContent = city;
            await loadDataInfo();
        } else {
            statusEl.textContent = result.detail || '上传失败';
            statusEl.className = 'status status-error';
        }
    } catch (error) {
        statusEl.textContent = '网络错误: ' + error.message;
        statusEl.className = 'status status-error';
    }
}

async function loadSampleData() {
    const city = document.getElementById('cityInput').value || '北京';
    const statusEl = document.getElementById('uploadStatus');

    statusEl.textContent = '加载示例数据中...';
    statusEl.className = 'status';

    try {
        const response = await fetch('data/sample_bus_data.json');
        const data = await response.json();

        const uploadResponse = await fetch(`${API_BASE}/api/upload/json?city=${encodeURIComponent(city)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await uploadResponse.json();

        if (uploadResponse.ok) {
            statusEl.textContent = result.message;
            statusEl.className = 'status status-success';
            document.getElementById('cityName').textContent = city;
            await loadDataInfo();
        } else {
            statusEl.textContent = result.detail || '加载失败';
            statusEl.className = 'status status-error';
        }
    } catch (error) {
        statusEl.textContent = '网络错误: ' + error.message;
        statusEl.className = 'status status-error';
    }
}

async function loadDataInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/data/info`);
        const data = await response.json();

        if (data.has_data) {
            const statsEl = document.getElementById('statsInfo');
            const timeStart = new Date(data.time_range.start).toLocaleString('zh-CN');
            const timeEnd = new Date(data.time_range.end).toLocaleString('zh-CN');
            
            statsEl.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">记录数:</span>
                    <span class="stat-value">${data.total_records}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">公交车:</span>
                    <span class="stat-value">${data.unique_buses}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">线路数:</span>
                    <span class="stat-value">${data.unique_routes}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">时间范围:</span>
                </div>
                <div class="stat-time">
                    <div>起: ${timeStart}</div>
                    <div>止: ${timeEnd}</div>
                </div>
                ${data.auto_calculated_bounds ? '<div class="stat-note">✓ 已自动计算网格边界</div>' : ''}
            `;

            if (data.bounds) {
                const centerLon = (data.bounds.lon_min + data.bounds.lon_max) / 2;
                const centerLat = (data.bounds.lat_min + data.bounds.lat_max) / 2;
                map.getView().setCenter(ol.proj.fromLonLat([centerLon, centerLat]));
                map.getView().setZoom(13);
            }
        }
    } catch (error) {
        console.error('加载数据信息失败:', error);
    }
}

async function generateHeatmap() {
    const gridSize = parseFloat(document.getElementById('gridSize').value);
    const windowMinutes = parseInt(document.getElementById('windowMinutes').value);
    const congestionThreshold = parseFloat(document.getElementById('congestionThreshold').value);
    const statusEl = document.getElementById('uploadStatus');

    statusEl.innerHTML = '生成热力图中... <span id="preGenProgress"></span>';
    statusEl.className = 'status';

    try {
        const params = new URLSearchParams({
            grid_size: gridSize,
            window_minutes: windowMinutes,
            congestion_threshold: congestionThreshold,
            pre_generate: true
        });

        const response = await fetch(`${API_BASE}/api/heatmap?${params}`);
        const result = await response.json();

        if (response.ok) {
            heatmapData = result;
            heatmapBounds = result.bounds;
            currentWindowIndex = 0;
            imageCache = {};
            preloadBuffer = {};
            preloadInProgress = {};

            createHeatmapImageLayer();
            createBackBufferLayer();

            document.getElementById('totalWindows').textContent = result.time_windows.length;
            document.getElementById('timeSlider').max = result.time_windows.length - 1;
            document.getElementById('timeSlider').value = 0;

            const formatTime = function(d) {
                return new Date(d).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            };
            document.getElementById('sliderStart').textContent = formatTime(result.time_range.start);
            document.getElementById('sliderEnd').textContent = formatTime(result.time_range.end);

            await new Promise(function(resolve) {
                updateHeatmapImage(0, resolve);
            });
            updateCongestionMarkers(result.time_windows[0]);
            updateTimeDisplay(result.time_windows[0]);

            preloadNextImages(0, 3);
            await loadCongestionRoutes(windowMinutes);

            await loadRoutesList();
            await loadAlerts(0);
            initCompareSelectors();

            if (result.pre_generation_started) {
                pollPreGenerationProgress();
            }

            statusEl.innerHTML = `热力图生成成功，共 ${result.time_windows.length} 个时间窗口 <span id="preGenProgress"></span>`;
            statusEl.className = 'status status-success';
            updatePreGenerationProgress();
        } else {
            statusEl.textContent = result.detail || '生成失败';
            statusEl.className = 'status status-error';
        }
    } catch (error) {
        statusEl.textContent = '网络错误: ' + error.message;
        statusEl.className = 'status status-error';
    }
}

async function loadCongestionRoutes(windowMinutes) {
    try {
        const response = await fetch(`${API_BASE}/api/congestion/routes?top_n=20&window_minutes=${windowMinutes}`);
        const result = await response.json();

        if (response.ok) {
            updateCongestionList(result.top_congestion);
        }
    } catch (error) {
        console.error('加载拥堵路段失败:', error);
    }
}

function changeWindow(index) {
    if (!heatmapData || index < 0 || index >= heatmapData.time_windows.length) return;

    currentWindowIndex = index;
    document.getElementById('timeSlider').value = index;

    const windowData = heatmapData.time_windows[index];
    
    updateHeatmapImage(index, function() {
        preloadNextImages(index, 3);
        cleanupOldCache(index);
    });
    
    updateCongestionMarkers(windowData);
    updateTimeDisplay(windowData);
    loadAlerts(index);
}

function togglePlay() {
    if (isPlaying) {
        stopPlay();
    } else {
        startPlay();
    }
}

function startPlay() {
    if (!heatmapData || heatmapData.time_windows.length <= 1) return;

    isPlaying = true;
    document.getElementById('playBtn').textContent = '⏸️';

    playInterval = setInterval(function() {
        let nextIndex = currentWindowIndex + 1;
        if (nextIndex >= heatmapData.time_windows.length) {
            nextIndex = 0;
        }
        changeWindow(nextIndex);
    }, playSpeed);
}

function stopPlay() {
    isPlaying = false;
    document.getElementById('playBtn').textContent = '▶️';

    if (playInterval) {
        clearInterval(playInterval);
        playInterval = null;
    }
}

function prevWindow() {
    if (!heatmapData) return;
    let prevIndex = currentWindowIndex - 1;
    if (prevIndex < 0) {
        prevIndex = heatmapData.time_windows.length - 1;
    }
    changeWindow(prevIndex);
}

function nextWindow() {
    if (!heatmapData) return;
    let nextIndex = currentWindowIndex + 1;
    if (nextIndex >= heatmapData.time_windows.length) {
        nextIndex = 0;
    }
    changeWindow(nextIndex);
}

function initEventListeners() {
    document.getElementById('uploadBtn').addEventListener('click', uploadData);
    document.getElementById('loadSampleBtn').addEventListener('click', loadSampleData);
    document.getElementById('generateBtn').addEventListener('click', generateHeatmap);

    document.getElementById('prevBtn').addEventListener('click', prevWindow);
    document.getElementById('playBtn').addEventListener('click', togglePlay);
    document.getElementById('nextBtn').addEventListener('click', nextWindow);

    document.getElementById('playSpeed').addEventListener('change', function(e) {
        playSpeed = parseInt(e.target.value);
        if (isPlaying) {
            stopPlay();
            startPlay();
        }
    });

    document.getElementById('timeSlider').addEventListener('input', function(e) {
        const index = parseInt(e.target.value);
        changeWindow(index);
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft') prevWindow();
        if (e.key === 'ArrowRight') nextWindow();
        if (e.key === ' ') {
            e.preventDefault();
            togglePlay();
        }
    });
}

async function loadAlerts(windowIndex) {
    try {
        const response = await fetch(`${API_BASE}/api/alerts/current?window_index=${windowIndex}&alert_threshold=${alertThreshold}`);
        const result = await response.json();
        
        if (response.ok) {
            updateAlertMarkers(result.alerts);
            updateAlertPanel(result);
        }
    } catch (error) {
        console.error('加载告警失败:', error);
    }
}

function updateAlertMarkers(alerts) {
    alertSource.clear();
    
    alerts.forEach(function(alert) {
        const feature = new ol.Feature({
            geometry: new ol.geom.Point(
                ol.proj.fromLonLat([alert.center_lon, alert.center_lat])
            ),
            ...alert
        });
        alertSource.addFeature(feature);
    });
    
    if (alerts.length > 0) {
        document.title = `⚠️ ${alerts.length} 条拥堵告警`;
        if (isPlaying) {
            stopPlay();
        }
    } else {
        document.title = '交通流量热力图';
    }
}

function updateAlertPanel(result) {
    const panel = document.getElementById('alertPanel');
    const list = document.getElementById('alertList');
    
    if (result.alert_count > 0) {
        panel.style.display = 'block';
        list.innerHTML = result.alerts.slice(0, 5).map(function(a) {
            return `
                <div class="alert-item ${a.alert_level}">
                    <span class="alert-icon">${a.alert_level === 'high' ? '🔴' : '🟠'}</span>
                    <span class="alert-text">
                        <strong>${a.alert_level === 'high' ? '严重拥堵' : '中度拥堵'}</strong><br>
                        <small>车辆数: ${a.vehicle_count} | 密度: ${(a.density * 100).toFixed(0)}%</small>
                    </span>
                </div>
            `;
        }).join('');
    } else {
        panel.style.display = 'none';
    }
}

async function loadRoutesList() {
    try {
        const response = await fetch(`${API_BASE}/api/routes/list`);
        const result = await response.json();
        
        if (response.ok) {
            updateRouteSelector(result.routes);
        }
    } catch (error) {
        console.error('加载线路列表失败:', error);
    }
}

function updateRouteSelector(routes) {
    const select = document.getElementById('routeSelector');
    select.innerHTML = '<option value="">选择线路...</option>';
    
    routes.slice(0, 20).forEach(function(route) {
        const option = document.createElement('option');
        option.value = route.route_id;
        option.textContent = `线路 ${route.route_id} (${route.vehicle_count}辆车)`;
        select.appendChild(option);
    });
}

async function showRouteTrajectory(routeId) {
    if (!routeId) {
        routeSource.clear();
        currentRouteId = null;
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/routes/trajectory/${routeId}`);
        const result = await response.json();
        
        if (response.ok && result.exists) {
            drawRouteTrajectory(result);
            currentRouteId = routeId;
        }
    } catch (error) {
        console.error('加载线路轨迹失败:', error);
    }
}

function drawRouteTrajectory(trajectory) {
    routeSource.clear();
    
    trajectory.bus_trajectories.forEach(function(busData) {
        if (busData.points.length > 1) {
            const coordinates = busData.points.map(function(p) {
                return ol.proj.fromLonLat([p.longitude, p.latitude]);
            });
            
            const lineFeature = new ol.Feature({
                geometry: new ol.geom.LineString(coordinates),
                bus_id: busData.bus_id
            });
            routeSource.addFeature(lineFeature);
            
            const firstPoint = new ol.Feature({
                geometry: new ol.geom.Point(coordinates[0]),
                label: '起点'
            });
            routeSource.addFeature(firstPoint);
        }
    });
    
    const ext = routeSource.getExtent();
    if (ext && ext[0] !== Infinity) {
        map.getView().fit(ext, { padding: [50, 50, 50, 50], duration: 1000 });
    }
}

function toggleCompareMode() {
    compareMode = !compareMode;
    
    if (compareMode) {
        document.getElementById('compareControls').style.display = 'block';
        document.getElementById('compareModeBtn').textContent = '关闭对比模式';
        loadComparison();
    } else {
        document.getElementById('compareControls').style.display = 'none';
        document.getElementById('compareModeBtn').textContent = '开启对比模式';
        clearComparison();
    }
}

function loadComparison() {
    if (!heatmapData) return;
    
    if (!comparisonLayer) {
        comparisonLayer = new ol.layer.Image({ opacity: 0.5, zIndex: 15 });
        map.addLayer(comparisonLayer);
    }
    
    updateComparisonImage();
}

function updateComparisonImage() {
    if (!heatmapBounds || !compareMode) return;
    
    const extent = ol.proj.transformExtent(
        [heatmapBounds.lon_min, heatmapBounds.lat_min, heatmapBounds.lon_max, heatmapBounds.lat_max],
        'EPSG:4326', 'EPSG:3857'
    );
    
    const imageUrl = `${API_BASE}/api/compare/image?window_index1=${compareWindowIndex1}&window_index2=${compareWindowIndex2}`;
    
    const imageSource = new ol.source.ImageStatic({
        url: imageUrl,
        imageExtent: extent,
        projection: 'EPSG:3857'
    });
    
    comparisonLayer.setSource(imageSource);
    updateCompareSummary();
}

async function updateCompareSummary() {
    try {
        const response = await fetch(`${API_BASE}/api/compare/windows?window_index1=${compareWindowIndex1}&window_index2=${compareWindowIndex2}`);
        const result = await response.json();
        
        if (response.ok) {
            const summary = document.getElementById('compareSummary');
            summary.innerHTML = `
                <div class="compare-stat">
                    <span class="compare-label">窗口1车辆数:</span>
                    <span class="compare-value">${result.window1.total_count}</span>
                </div>
                <div class="compare-stat">
                    <span class="compare-label">窗口2车辆数:</span>
                    <span class="compare-value">${result.window2.total_count}</span>
                </div>
                <div class="compare-stat increase">
                    <span class="compare-label">流量增加:</span>
                    <span class="compare-value">${result.summary.total_increase} 网格</span>
                </div>
                <div class="compare-stat decrease">
                    <span class="compare-label">流量减少:</span>
                    <span class="compare-value">${result.summary.total_decrease} 网格</span>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载对比数据失败:', error);
    }
}

function clearComparison() {
    if (comparisonLayer) {
        map.removeLayer(comparisonLayer);
        comparisonLayer = null;
    }
}

function setCompareWindow1(index) {
    compareWindowIndex1 = index;
    updateComparisonImage();
}

function setCompareWindow2(index) {
    compareWindowIndex2 = index;
    updateComparisonImage();
}

function initCompareSelectors() {
    if (!heatmapData) return;
    
    const sel1 = document.getElementById('compareWindow1');
    const sel2 = document.getElementById('compareWindow2');
    
    sel1.innerHTML = '';
    sel2.innerHTML = '';
    
    const formatTime = function(d) {
        return new Date(d).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    };
    
    heatmapData.time_windows.forEach(function(w, i) {
        const opt1 = new Option(`窗口 ${i+1} (${formatTime(w.time_start)})`, i);
        const opt2 = new Option(`窗口 ${i+1} (${formatTime(w.time_start)})`, i);
        sel1.add(opt1);
        sel2.add(opt2);
    });
    
    sel1.value = 0;
    sel2.value = Math.min(1, heatmapData.time_windows.length - 1);
    compareWindowIndex1 = 0;
    compareWindowIndex2 = parseInt(sel2.value);
}

function initAdvancedEventListeners() {
    document.getElementById('alertThreshold').addEventListener('input', function(e) {
        alertThreshold = parseFloat(e.target.value);
        document.getElementById('alertThresholdValue').textContent = alertThreshold.toFixed(2);
    });
    
    document.getElementById('alertThreshold').addEventListener('change', function(e) {
        alertThreshold = parseFloat(e.target.value);
        if (heatmapData) {
            loadAlerts(currentWindowIndex);
        }
    });
    
    document.getElementById('routeSelector').addEventListener('change', function(e) {
        showRouteTrajectory(e.target.value);
    });
    
    document.getElementById('compareModeBtn').addEventListener('click', toggleCompareMode);
    
    document.getElementById('compareWindow1').addEventListener('change', function(e) {
        setCompareWindow1(parseInt(e.target.value));
    });
    
    document.getElementById('compareWindow2').addEventListener('change', function(e) {
        setCompareWindow2(parseInt(e.target.value));
    });
    
    document.getElementById('clearRouteBtn').addEventListener('click', function() {
        document.getElementById('routeSelector').value = '';
        showRouteTrajectory('');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initMap();
    initEventListeners();
    initAdvancedEventListeners();
});
