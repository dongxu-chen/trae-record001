import React, { useState, useRef } from 'react';
import MapComponent from './components/MapComponent';
import ControlPanel from './components/ControlPanel';
import Legend from './components/Legend';
import Terrain3DComponent from './components/Terrain3DComponent';
import AnimationComponent from './components/AnimationComponent';
import ExportComponent from './components/ExportComponent';
import axios from 'axios';

function App() {
  const [contours, setContours] = useState(null);
  const [demData, setDemData] = useState(null);
  const [settings, setSettings] = useState({
    interval: 50,
    smoothing: 1,
    enableLabels: true,
    labelInterval: 5,
    minLength: 3,
    adaptiveSmoothing: true
  });
  const [status, setStatus] = useState({ type: '', message: '' });
  const [demFile, setDemFile] = useState(null);
  const [bounds, setBounds] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [viewMode, setViewMode] = useState('2d');
  const fileInputRef = useRef(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setDemFile(file);
      setStatus({ type: 'success', message: `已选择文件: ${file.name}` });
    }
  };

  const handleSettingsChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const generateContours = async () => {
    if (!demFile) {
      setStatus({ type: 'error', message: '请先上传DEM文件' });
      return;
    }

    setIsProcessing(true);
    setStatus({ type: '', message: '正在处理...' });

    const formData = new FormData();
    formData.append('demFile', demFile);
    formData.append('interval', settings.interval);
    formData.append('smoothing', settings.smoothing);
    formData.append('enableLabels', settings.enableLabels);
    formData.append('labelInterval', settings.labelInterval);
    formData.append('minLength', settings.minLength);
    formData.append('adaptiveSmoothing', settings.adaptiveSmoothing);

    try {
      const response = await axios.post('http://localhost:3002/api/generate-contours', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setContours(response.data.contours);
      setBounds(response.data.bounds);
      setStatus({ type: 'success', message: `等高线生成成功！共 ${response.data.contours.features.length} 条等高线` });
    } catch (error) {
      console.error('Error generating contours:', error);
      setStatus({ type: 'error', message: '生成等高线失败: ' + (error.response?.data?.error || error.message) });
    } finally {
      setIsProcessing(false);
    }
  };

  const loadSampleData = async () => {
    setIsProcessing(true);
    setStatus({ type: '', message: '正在加载示例数据...' });

    try {
      const [contourRes, demRes] = await Promise.all([
        axios.post('http://localhost:3002/api/sample-data', {
          interval: settings.interval,
          smoothing: settings.smoothing,
          enableLabels: settings.enableLabels,
          labelInterval: settings.labelInterval,
          minLength: settings.minLength,
          adaptiveSmoothing: settings.adaptiveSmoothing
        }),
        axios.post('http://localhost:3002/api/sample-dem', { width: 150, height: 150 })
      ]);

      setContours(contourRes.data.contours);
      setBounds(contourRes.data.bounds);
      setDemData(demRes.data);
      setDemFile({ name: '示例DEM数据' });
      setStatus({ type: 'success', message: `示例数据加载成功！共 ${contourRes.data.contours.features.length} 条等高线` });
    } catch (error) {
      console.error('Error loading sample data:', error);
      setStatus({ type: 'error', message: '加载示例数据失败: ' + (error.response?.data?.error || error.message) });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app">
      <div className="sidebar">
        <h1>🗻 等高线提取工具</h1>
        <ControlPanel
          settings={settings}
          onSettingsChange={handleSettingsChange}
          onFileUpload={handleFileUpload}
          onGenerate={generateContours}
          onLoadSample={loadSampleData}
          status={status}
          isProcessing={isProcessing}
          demFile={demFile}
          fileInputRef={fileInputRef}
        />
        {contours && (
          <ExportComponent contours={contours} bounds={bounds} />
        )}
      </div>
      <div className="map-container">
        <div className="view-tabs">
          <button
            className={`view-tab ${viewMode === '2d' ? 'active' : ''}`}
            onClick={() => setViewMode('2d')}
          >
            🗺️ 2D 地图
          </button>
          <button
            className={`view-tab ${viewMode === '3d' ? 'active' : ''}`}
            onClick={() => setViewMode('3d')}
          >
            🏔️ 3D 地形
          </button>
          <button
            className={`view-tab ${viewMode === 'anim' ? 'active' : ''}`}
            onClick={() => setViewMode('anim')}
          >
            🎬 动画
          </button>
        </div>

        <div className="view-content">
          {viewMode === '2d' && (
            <>
              <MapComponent contours={contours} bounds={bounds} settings={settings} />
              {contours && <Legend contours={contours} />}
            </>
          )}
          {viewMode === '3d' && (
            <div className="terrain3d-wrapper">
              <Terrain3DComponent
                contours={contours}
                bounds={bounds}
                settings={settings}
              />
              <div className="terrain3d-hint">
                🖱️ 拖拽旋转 | 滚轮缩放
              </div>
            </div>
          )}
          {viewMode === 'anim' && (
            <AnimationComponent
              contours={contours}
              bounds={bounds}
              settings={settings}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
