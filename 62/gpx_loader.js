function parseGPX(xmlString) {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlString, 'application/xml');
    
    const parseError = xmlDoc.querySelector('parsererror');
    if (parseError) {
        throw new Error('Invalid GPX file');
    }
    
    const trkpts = xmlDoc.querySelectorAll('trkpt');
    const coordinates = [];
    const timestamps = [];
    
    trkpts.forEach((trkpt, index) => {
        const lat = parseFloat(trkpt.getAttribute('lat'));
        const lon = parseFloat(trkpt.getAttribute('lon'));
        
        const ele = trkpt.querySelector('ele');
        const altitude = ele ? parseFloat(ele.textContent) : 0;
        
        const time = trkpt.querySelector('time');
        const timestamp = time ? new Date(time.textContent).getTime() : Date.now() + index * 1000;
        
        coordinates.push([lon, lat, altitude]);
        timestamps.push(timestamp);
    });
    
    if (coordinates.length === 0) {
        const wpts = xmlDoc.querySelectorAll('wpt');
        wpts.forEach((wpt, index) => {
            const lat = parseFloat(wpt.getAttribute('lat'));
            const lon = parseFloat(wpt.getAttribute('lon'));
            
            const ele = wpt.querySelector('ele');
            const altitude = ele ? parseFloat(ele.textContent) : 0;
            
            const time = wpt.querySelector('time');
            const timestamp = time ? new Date(time.textContent).getTime() : Date.now() + index * 1000;
            
            coordinates.push([lon, lat, altitude]);
            timestamps.push(timestamp);
        });
    }
    
    return {
        coordinates: coordinates,
        timestamps: timestamps
    };
}

function loadGPXFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            try {
                const result = parseGPX(e.target.result);
                resolve(result);
            } catch (error) {
                reject(error);
            }
        };
        
        reader.onerror = function() {
            reject(new Error('Failed to read file'));
        };
        
        reader.readAsText(file);
    });
}

function updateMapForNewTrail(coordinates) {
    const map = getMap();
    
    if (coordinates.length === 0) return;
    
    const bounds = new mapboxgl.LngLatBounds();
    coordinates.forEach(coord => {
        bounds.extend([coord[0], coord[1]]);
    });
    
    map.fitBounds(bounds, {
        padding: 50,
        pitch: 60,
        duration: 1000
    });
}

function initGPXLoader() {
    const fileInput = document.getElementById('gpx-file');
    const fileInfo = document.getElementById('file-info');
    
    if (!fileInput) return;
    
    fileInput.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        if (!file.name.toLowerCase().endsWith('.gpx')) {
            fileInfo.innerHTML = '<span style="color: red;">请上传 GPX 格式文件</span>';
            return;
        }
        
        try {
            fileInfo.innerHTML = '正在解析...';
            
            const result = await loadGPXFile(file);
            
            if (result.coordinates.length === 0) {
                fileInfo.innerHTML = '<span style="color: red;">未找到轨迹数据</span>';
                return;
            }
            
            resetPlayback();
            updateTrailData(result.coordinates, result.timestamps);
            updateHeatmap();
            
            resetMarker();
            
            if (typeof velocityChart !== 'undefined') {
                updateVelocityChart();
            }
            
            updateMapForNewTrail(result.coordinates);
            
            const distance = getTrailLength();
            const duration = getTotalDuration() / 1000 / 60;
            fileInfo.innerHTML = `
                <div>✅ 加载成功</div>
                <div>轨迹点: ${result.coordinates.length} 个</div>
                <div>总距离: ${distance.toFixed(2)} km</div>
                <div>时长: ${duration.toFixed(1)} 分钟</div>
            `;
            
        } catch (error) {
            console.error('Error loading GPX:', error);
            fileInfo.innerHTML = `<span style="color: red;">解析失败: ${error.message}</span>`;
        }
    });
}