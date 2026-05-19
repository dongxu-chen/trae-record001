let isPlaying = false;
let currentProgress = 0;
let playbackSpeed = 1;
let animationFrameId = null;
let lastTimestamp = 0;
let cachedTotalDuration = 30000;
let velocityChart = null;
let progressMarker = null;

function initAnimation() {
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const speedSelect = document.getElementById('speed-select');
    const progressSlider = document.getElementById('progress-slider');

    playBtn.addEventListener('click', startPlayback);
    pauseBtn.addEventListener('click', pausePlayback);
    resetBtn.addEventListener('click', resetPlayback);
    speedSelect.addEventListener('change', updateSpeed);
    
    progressSlider.addEventListener('input', function() {
        currentProgress = parseFloat(this.value) / 100;
        updatePlayback();
    });

    cachedTotalDuration = getTotalDuration();
    initVelocityChart();
    initHeatmapControls();
    initGPXLoader();
    updateTimeDisplay();
    resetPlayback();
}

function initVelocityChart() {
    const ctx = document.getElementById('velocity-chart');
    if (!ctx) return;
    
    const velocities = getTrailVelocities();
    const labels = velocities.map((_, i) => i);
    
    velocityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '速度 (km/h)',
                data: velocities,
                borderColor: 'rgba(66, 133, 244, 1)',
                backgroundColor: 'rgba(66, 133, 244, 0.2)',
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'km/h'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function updateVelocityChart() {
    if (!velocityChart) return;
    
    const velocities = getTrailVelocities();
    const labels = velocities.map((_, i) => i);
    
    velocityChart.data.labels = labels;
    velocityChart.data.datasets[0].data = velocities;
    velocityChart.update();
}

function updateChartProgressMarker(progress) {
    if (!velocityChart) return;
    
    const velocities = getTrailVelocities();
    const index = Math.floor(progress * (velocities.length - 1));
    
    document.getElementById('current-velocity').textContent = 
        `当前速度: ${velocities[index]?.toFixed(1) || 0} km/h`;
}

function startPlayback() {
    if (isPlaying) return;
    
    isPlaying = true;
    lastTimestamp = performance.now();
    animate();
    
    document.getElementById('play-btn').style.opacity = '0.5';
    document.getElementById('pause-btn').style.opacity = '1';
}

function pausePlayback() {
    isPlaying = false;
    
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
    
    document.getElementById('play-btn').style.opacity = '1';
    document.getElementById('pause-btn').style.opacity = '0.5';
}

function resetPlayback() {
    pausePlayback();
    currentProgress = 0;
    updatePlayback();
    resetMarker();
    
    const map = getMap();
    const coordinates = getTrailCoordinates();
    if (coordinates.length > 0) {
        map.flyTo({
            center: [coordinates[0][0], coordinates[0][1]],
            zoom: 14,
            pitch: 60,
            duration: 1000
        });
    }
}

function updateSpeed() {
    const speedSelect = document.getElementById('speed-select');
    playbackSpeed = parseFloat(speedSelect.value);
}

function animate(timestamp) {
    if (!isPlaying) return;
    
    if (lastTimestamp === 0) {
        lastTimestamp = timestamp;
    }
    
    const deltaTime = timestamp - lastTimestamp;
    lastTimestamp = timestamp;
    
    const totalDuration = getTotalDuration();
    cachedTotalDuration = totalDuration;
    
    const progressIncrement = (deltaTime / totalDuration) * playbackSpeed;
    currentProgress += progressIncrement;
    
    if (currentProgress >= 1) {
        currentProgress = 1;
        pausePlayback();
    }
    
    updatePlayback();
    
    animationFrameId = requestAnimationFrame(animate);
}

function updatePlayback() {
    const progressSlider = document.getElementById('progress-slider');
    progressSlider.value = currentProgress * 100;
    
    updateMarkerPosition(currentProgress);
    updateTrailProgress(currentProgress);
    updateTimeDisplay();
    updateChartProgressMarker(currentProgress);
}

function updateTimeDisplay() {
    const currentTimeElement = document.getElementById('current-time');
    const totalTimeElement = document.getElementById('total-time');
    
    const totalDuration = getTotalDuration();
    const startTime = getStartTime();
    const currentGpsTime = startTime + currentProgress * totalDuration;
    
    currentTimeElement.textContent = formatGpsTime(currentGpsTime);
    totalTimeElement.textContent = formatGpsTime(startTime + totalDuration);
}

function formatGpsTime(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
}

function getCurrentGpsTime() {
    return getStartTime() + currentProgress * getTotalDuration();
}

function syncToGpsTime(gpsTimestamp) {
    const startTime = getStartTime();
    const endTime = getEndTime();
    
    if (gpsTimestamp <= startTime) {
        currentProgress = 0;
    } else if (gpsTimestamp >= endTime) {
        currentProgress = 1;
    } else {
        currentProgress = (gpsTimestamp - startTime) / (endTime - startTime);
    }
    
    updatePlayback();
}