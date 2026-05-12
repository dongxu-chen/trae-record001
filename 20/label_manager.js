const LabelManager = (function() {
    let scene = null;
    let camera = null;
    let engine = null;
    let labelContainer = null;
    let infoPanel = null;
    const labels = new Map();
    const trackedPositions = [];
    let currentSelected = null;

    function init(sceneContext, cameraContext, engineContext) {
        scene = sceneContext;
        camera = cameraContext;
        engine = engineContext;

        labelContainer = document.createElement('div');
        labelContainer.id = 'labelContainer';
        labelContainer.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
            z-index: 10;
        `;
        document.body.appendChild(labelContainer);

        createInfoPanel();
        createStarMap();

        return {
            addLabel,
            removeLabel,
            updateLabels,
            showInfo,
            hideInfo,
            updateStarMap,
            dispose
        };
    }

    function createInfoPanel() {
        infoPanel = document.createElement('div');
        infoPanel.id = 'infoPanel';
        infoPanel.style.cssText = `
            position: absolute;
            top: 100px;
            right: 20px;
            width: 320px;
            max-width: 90vw;
            background: rgba(10, 15, 30, 0.95);
            border: 1px solid rgba(79, 195, 247, 0.3);
            border-radius: 12px;
            padding: 20px;
            color: white;
            font-family: 'Segoe UI', system-ui, sans-serif;
            pointer-events: auto;
            transform: translateX(400px);
            transition: transform 0.3s ease-out, opacity 0.3s ease-out;
            opacity: 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(79, 195, 247, 0.1);
            backdrop-filter: blur(10px);
            z-index: 100;
        `;

        infoPanel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 id="infoTitle" style="margin: 0; color: #4fc3f7; font-size: 20px;"></h3>
                <span id="infoType" style="color: #90caf9; font-size: 12px; background: rgba(79, 195, 247, 0.15); padding: 4px 10px; border-radius: 12px;"></span>
            </div>
            <p id="infoDescription" style="color: #b0bec5; line-height: 1.6; margin: 0 0 15px 0; font-size: 13px;"></p>
            <div id="infoFacts" style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 15px;"></div>
            <button id="focusBtn" style="
                margin-top: 15px;
                width: 100%;
                padding: 10px 16px;
                background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 100%);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                font-weight: 500;
            ">🎯 聚焦此天体</button>
        `;

        document.body.appendChild(infoPanel);

        document.getElementById('focusBtn').addEventListener('click', () => {
            if (currentSelected && currentSelected.onFocus) {
                currentSelected.onFocus(currentSelected.mesh);
            }
        });
    }

    function createStarMap() {
        const starMap = document.createElement('div');
        starMap.id = 'starMap';
        starMap.style.cssText = `
            position: absolute;
            bottom: 20px;
            right: 20px;
            width: 200px;
            height: 200px;
            background: rgba(10, 15, 30, 0.9);
            border: 1px solid rgba(79, 195, 247, 0.3);
            border-radius: 50%;
            overflow: hidden;
            pointer-events: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            z-index: 50;
            cursor: pointer;
        `;

        const mapTitle = document.createElement('div');
        mapTitle.style.cssText = `
            position: absolute;
            bottom: -28px;
            left: 50%;
            transform: translateX(-50%);
            color: #4fc3f7;
            font-size: 12px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            white-space: nowrap;
        `;
        mapTitle.textContent = '星图导航';
        starMap.appendChild(mapTitle);

        document.body.appendChild(starMap);
    }

    function addLabel(mesh, options = {}) {
        const { text = mesh.name, offsetY = 0, showDistance = false } = options;

        const labelElement = document.createElement('div');
        labelElement.className = 'planetLabel';
        labelElement.style.cssText = `
            position: absolute;
            transform: translate(-50%, -50%);
            color: #e3f2fd;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            text-shadow: 0 0 8px rgba(79, 195, 247, 0.6), 0 2px 4px rgba(0, 0, 0, 0.8);
            pointer-events: none;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s;
        `;

        labelElement.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center;">
                <div style="
                    width: 6px;
                    height: 6px;
                    background: #4fc3f7;
                    border-radius: 50%;
                    margin-bottom: 4px;
                    box-shadow: 0 0 8px #4fc3f7;
                "></div>
                <div style="
                    background: rgba(10, 15, 30, 0.85);
                    padding: 4px 10px;
                    border-radius: 12px;
                    border: 1px solid rgba(79, 195, 247, 0.3);
                ">
                    <span style="font-weight: 500;">${text}</span>
                    ${showDistance ? '<span class="labelDistance" style="color: #90caf9; font-size: 10px; margin-left: 6px;"></span>' : ''}
                </div>
            </div>
        `;

        labelContainer.appendChild(labelElement);

        const labelData = {
            mesh,
            element: labelElement,
            offsetY,
            showDistance,
            text
        };

        labels.set(mesh, labelData);
        trackedPositions.push({
            mesh,
            labelData,
            onStarMap: true
        });

        return labelElement;
    }

    function removeLabel(mesh) {
        const labelData = labels.get(mesh);
        if (labelData) {
            labelData.element.remove();
            labels.delete(mesh);

            const index = trackedPositions.findIndex(t => t.mesh === mesh);
            if (index !== -1) {
                trackedPositions.splice(index, 1);
            }
        }
    }

    function updateLabels() {
        if (!scene || !camera || !engine) return;

        labels.forEach((labelData, mesh) => {
            const position = mesh.position.clone();
            position.y += labelData.offsetY + (mesh._config?.size || 1) * 1.2;

            const screenPos = BABYLON.Vector3.Project(
                position,
                BABYLON.Matrix.Identity(),
                scene.getTransformMatrix(),
                camera.viewport.toGlobal(
                    engine.getRenderWidth(),
                    engine.getRenderHeight()
                )
            );

            const isInFront = screenPos.z >= 0 && screenPos.z <= 1;
            const width = engine.getRenderWidth();
            const height = engine.getRenderHeight();
            const isOnScreen = screenPos.x >= 0 && screenPos.x <= width &&
                               screenPos.y >= 0 && screenPos.y <= height;

            if (isInFront && isOnScreen) {
                labelData.element.style.left = screenPos.x + 'px';
                labelData.element.style.top = screenPos.y + 'px';
                labelData.element.style.opacity = '1';
                labelData.element.style.display = 'block';

                if (labelData.showDistance) {
                    const distanceEl = labelData.element.querySelector('.labelDistance');
                    if (distanceEl) {
                        const dist = BABYLON.Vector3.Distance(camera.position, mesh.position);
                        distanceEl.textContent = `${dist.toFixed(0)} 单位`;
                    }
                }
            } else {
                labelData.element.style.opacity = '0';
                labelData.element.style.display = 'none';
            }
        });
    }

    function showInfo(mesh, onFocusCallback = null) {
        if (!mesh || !mesh._info) {
            hideInfo();
            return;
        }

        const info = mesh._info;
        currentSelected = { mesh, onFocus: onFocusCallback };

        document.getElementById('infoTitle').textContent = mesh.name;
        document.getElementById('infoType').textContent = info.type;
        document.getElementById('infoDescription').textContent = info.description;

        const factsContainer = document.getElementById('infoFacts');
        factsContainer.innerHTML = info.facts.map(fact => `
            <div style="
                display: flex;
                align-items: flex-start;
                margin-bottom: 8px;
                font-size: 12px;
            ">
                <span style="
                    color: #4fc3f7;
                    margin-right: 8px;
                    font-size: 10px;
                ">◆</span>
                <span style="color: #cfd8dc;">${fact}</span>
            </div>
        `).join('');

        infoPanel.style.transform = 'translateX(0)';
        infoPanel.style.opacity = '1';
    }

    function hideInfo() {
        currentSelected = null;
        infoPanel.style.transform = 'translateX(400px)';
        infoPanel.style.opacity = '0';
    }

    function updateStarMap() {
        const starMap = document.getElementById('starMap');
        if (!starMap || !scene || !camera) return;

        if (!starMap._initialized) {
            starMap._markers = [];
            starMap._initialized = true;
        }

        const markers = starMap._markers;
        const mapSize = 200;
        const mapCenter = mapSize / 2;
        const mapRadius = mapSize / 2 - 10;

        trackedPositions.forEach((tracked, index) => {
            let marker = markers[index];

            if (!marker) {
                marker = document.createElement('div');
                marker.style.cssText = `
                    position: absolute;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                    z-index: 1;
                `;

                marker.addEventListener('mouseenter', () => {
                    marker.style.transform = 'translate(-50%, -50%) scale(1.5)';
                });
                marker.addEventListener('mouseleave', () => {
                    marker.style.transform = 'translate(-50%, -50%) scale(1)';
                });
                marker.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const info = tracked.mesh._info;
                    if (info) {
                        showInfo(tracked.mesh);
                        if (tracked.onStarMapClick) {
                            tracked.onStarMapClick(tracked.mesh);
                        }
                    }
                });

                starMap.appendChild(marker);
                markers.push(marker);
            }

            const mesh = tracked.mesh;
            const info = mesh._info;

            let x = 0, y = 0;

            if (mesh.name === '太阳') {
                x = mapCenter;
                y = mapCenter;
            } else {
                const orbitData = mesh._orbitData;
                if (orbitData) {
                    const angle = orbitData.angle || 0;
                    const normalizedRadius = (orbitData.orbitRadius || 30) / 250;
                    const markerRadius = normalizedRadius * mapRadius * 0.9;
                    x = mapCenter + Math.cos(angle) * markerRadius;
                    y = mapCenter + Math.sin(angle) * markerRadius;
                } else {
                    const pos = mesh.position;
                    const maxDist = 250;
                    x = mapCenter + (pos.x / maxDist) * mapRadius * 0.9;
                    y = mapCenter + (pos.z / maxDist) * mapRadius * 0.9;
                }
            }

            marker.style.left = x + 'px';
            marker.style.top = y + 'px';

            const color = info?.color || '#FFFFFF';
            marker.style.background = color;
            marker.style.boxShadow = `0 0 8px ${color}`;
            marker.title = mesh.name;
        });

        for (let i = trackedPositions.length; i < markers.length; i++) {
            markers[i].style.display = 'none';
        }
    }

    function setOrbitDataForStarMap(mesh, orbitData) {
        mesh._orbitData = orbitData;
    }

    function setStarMapClickHandler(mesh, handler) {
        const tracked = trackedPositions.find(t => t.mesh === mesh);
        if (tracked) {
            tracked.onStarMapClick = handler;
        }
    }

    function dispose() {
        if (labelContainer) {
            labelContainer.remove();
        }
        if (infoPanel) {
            infoPanel.remove();
        }
        const starMap = document.getElementById('starMap');
        if (starMap) {
            starMap.remove();
        }
        labels.clear();
        trackedPositions.length = 0;
    }

    return {
        init,
        addLabel,
        removeLabel,
        updateLabels,
        showInfo,
        hideInfo,
        updateStarMap,
        setOrbitDataForStarMap,
        setStarMapClickHandler,
        dispose
    };
})();
