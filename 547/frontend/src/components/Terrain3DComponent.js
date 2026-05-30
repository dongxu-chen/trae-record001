import React, { useEffect, useRef, useState, useCallback } from 'react';
import axios from 'axios';

function Terrain3DComponent({ contours, bounds, settings }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const [demData, setDemData] = useState(null);
  const [viewMode, setViewMode] = useState('terrain');
  const [showContours, setShowContours] = useState(true);
  const [verticalScale, setVerticalScale] = useState(2);
  const [isLoading3D, setIsLoading3D] = useState(false);

  const loadDemData = useCallback(async () => {
    try {
      const response = await axios.post('http://localhost:3002/api/sample-dem', {
        width: 150,
        height: 150
      });
      setDemData(response.data);
    } catch (error) {
      console.error('加载DEM数据失败:', error);
    }
  }, []);

  useEffect(() => {
    if (!demData) {
      loadDemData();
    }
  }, [demData, loadDemData]);

  useEffect(() => {
    if (!demData || !containerRef.current) return;
    if (typeof window.THREE === 'undefined') return;

    setIsLoading3D(true);

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    const THREE = window.THREE;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.set(3, 3, 3);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const demWidth = demData.width;
    const demHeight = demData.height;
    const demValues = demData.data;
    const minElev = Math.min(...demValues);
    const maxElev = Math.max(...demValues);
    const elevRange = maxElev - minElev || 1;

    const geometry = new THREE.PlaneGeometry(
      4,
      4,
      demWidth - 1,
      demHeight - 1
    );
    geometry.rotateX(-Math.PI / 2);

    const positions = geometry.attributes.position;
    const colors = new Float32Array(positions.count * 3);

    for (let i = 0; i < positions.count; i++) {
      const x = i % demWidth;
      const z = Math.floor(i / demWidth);
      const idx = z * demWidth + x;

      if (idx < demValues.length) {
        const normalizedElev = (demValues[idx] - minElev) / elevRange;
        positions.setY(i, normalizedElev * verticalScale);

        const color = getTerrainColor(normalizedElev);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
      }
    }

    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.computeVertexNormals();

    let material;
    if (viewMode === 'wireframe') {
      material = new THREE.MeshBasicMaterial({
        wireframe: true,
        vertexColors: true,
        opacity: 0.8,
        transparent: true
      });
    } else if (viewMode === 'solid') {
      material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        flatShading: true,
        shininess: 10
      });
    } else {
      material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        side: THREE.DoubleSide,
        shininess: 30
      });
    }

    const terrain = new THREE.Mesh(geometry, material);
    scene.add(terrain);

    const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
    directionalLight.position.set(5, 10, 5);
    scene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0x8888ff, 0.3);
    directionalLight2.position.set(-5, 5, -5);
    scene.add(directionalLight2);

    const contourGroup = new THREE.Group();
    scene.add(contourGroup);

    if (showContours && contours && contours.features) {
      contours.features.forEach(feature => {
        if (feature.geometry.type !== 'LineString') return;

        const coords = feature.geometry.coordinates;
        const elevation = feature.properties.elevation;
        const normalizedElev = (elevation - minElev) / elevRange;
        const y = normalizedElev * verticalScale;

        const points = [];
        for (const coord of coords) {
          const nx = ((coord[0] - demData.bounds.west) / (demData.bounds.east - demData.bounds.west)) * 4 - 2;
          const nz = -(((coord[1] - demData.bounds.south) / (demData.bounds.north - demData.bounds.south)) * 4 - 2);
          points.push(new THREE.Vector3(nx, y + 0.01, nz));
        }

        if (points.length < 2) return;

        const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
        const lineColor = getContourLineColor(normalizedElev);
        const isMajor = elevation % (settings.interval * 5) === 0;
        const lineMaterial = new THREE.LineBasicMaterial({
          color: lineColor,
          linewidth: isMajor ? 2 : 1,
          opacity: isMajor ? 1.0 : 0.7,
          transparent: true
        });
        const line = new THREE.Line(lineGeometry, lineMaterial);
        contourGroup.add(line);
      });
    }

    const gridHelper = new THREE.GridHelper(4, 20, 0x333366, 0x222244);
    gridHelper.position.y = -0.1;
    scene.add(gridHelper);

    sceneRef.current = { scene, camera, renderer, terrain, contourGroup };

    let isDragging = false;
    let previousMouse = { x: 0, y: 0 };
    let rotationX = 0.8;
    let rotationY = 0;
    let distance = 5;

    const updateCamera = () => {
      camera.position.x = distance * Math.sin(rotationY) * Math.cos(rotationX);
      camera.position.y = distance * Math.sin(rotationX);
      camera.position.z = distance * Math.cos(rotationY) * Math.cos(rotationX);
      camera.lookAt(0, 0.5, 0);
    };

    updateCamera();

    const onMouseDown = (e) => {
      isDragging = true;
      previousMouse = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const dx = e.clientX - previousMouse.x;
      const dy = e.clientY - previousMouse.y;
      rotationY += dx * 0.01;
      rotationX = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, rotationX + dy * 0.01));
      previousMouse = { x: e.clientX, y: e.clientY };
      updateCamera();
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      distance = Math.max(2, Math.min(15, distance + e.deltaY * 0.01));
      updateCamera();
    };

    const animate = () => {
      renderer.render(scene, camera);
      sceneRef.current.animFrameId = requestAnimationFrame(animate);
    };

    container.addEventListener('mousedown', onMouseDown);
    container.addEventListener('mousemove', onMouseMove);
    container.addEventListener('mouseup', onMouseUp);
    container.addEventListener('mouseleave', onMouseUp);
    container.addEventListener('wheel', onWheel, { passive: false });

    animate();
    setIsLoading3D(false);

    return () => {
      container.removeEventListener('mousedown', onMouseDown);
      container.removeEventListener('mousemove', onMouseMove);
      container.removeEventListener('mouseup', onMouseUp);
      container.removeEventListener('mouseleave', onMouseUp);
      container.removeEventListener('wheel', onWheel);
      if (sceneRef.current && sceneRef.current.animFrameId) {
        cancelAnimationFrame(sceneRef.current.animFrameId);
      }
      renderer.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, [demData, contours, settings, viewMode, showContours, verticalScale]);

  const getTerrainColor = (normalizedElev) => {
    if (normalizedElev < 0.15) return { r: 0.1, g: 0.3 + normalizedElev * 2, b: 0.1 };
    if (normalizedElev < 0.3) return { r: 0.2, g: 0.5 + normalizedElev, b: 0.15 };
    if (normalizedElev < 0.5) return { r: 0.6 + normalizedElev * 0.3, g: 0.7 + normalizedElev * 0.2, b: 0.2 };
    if (normalizedElev < 0.7) return { r: 0.6, g: 0.4 + normalizedElev * 0.3, b: 0.15 };
    if (normalizedElev < 0.85) return { r: 0.5, g: 0.35, b: 0.2 };
    return { r: 0.9 + normalizedElev * 0.1, g: 0.9 + normalizedElev * 0.1, b: 0.95 };
  };

  const getContourLineColor = (normalizedElev) => {
    if (normalizedElev < 0.2) return 0x2ecc71;
    if (normalizedElev < 0.4) return 0xf1c40f;
    if (normalizedElev < 0.6) return 0xe67e22;
    if (normalizedElev < 0.8) return 0xe74c3c;
    return 0xffffff;
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="terrain3d-controls">
        <button
          className={`btn-3d ${viewMode === 'terrain' ? 'active' : ''}`}
          onClick={() => setViewMode('terrain')}
          title="地形渲染"
        >
          🏔️ 地形
        </button>
        <button
          className={`btn-3d ${viewMode === 'wireframe' ? 'active' : ''}`}
          onClick={() => setViewMode('wireframe')}
          title="网格模式"
        >
          🔲 网格
        </button>
        <button
          className={`btn-3d ${viewMode === 'solid' ? 'active' : ''}`}
          onClick={() => setViewMode('solid')}
          title="平面着色"
        >
          📦 实体
        </button>
        <span style={{ margin: '0 8px', color: '#aaa', fontSize: '12px' }}>|</span>
        <label className="checkbox-label" style={{ fontSize: '12px', color: '#ccc' }}>
          <input
            type="checkbox"
            checked={showContours}
            onChange={(e) => setShowContours(e.target.checked)}
          />
          等高线
        </label>
        <span style={{ margin: '0 8px', color: '#aaa', fontSize: '12px' }}>|</span>
        <label style={{ fontSize: '12px', color: '#ccc', display: 'flex', alignItems: 'center', gap: '4px' }}>
          Z×{verticalScale.toFixed(1)}
          <input
            type="range"
            min="0.5"
            max="5"
            step="0.5"
            value={verticalScale}
            onChange={(e) => setVerticalScale(Number(e.target.value))}
            style={{ width: '80px' }}
          />
        </label>
      </div>
      <div
        ref={containerRef}
        style={{ flex: 1, cursor: 'grab', minHeight: 0 }}
      />
      {isLoading3D && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          color: '#fff', fontSize: '14px'
        }}>
          🔄 加载3D地形...
        </div>
      )}
    </div>
  );
}

export default Terrain3DComponent;
