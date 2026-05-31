import React, { useState } from 'react';
import './App.css';
import ImageEditor from './components/ImageEditor';
import BatchProcessor from './components/BatchProcessor';
import VideoEditor from './components/VideoEditor';

function App() {
  const [activeTab, setActiveTab] = useState('single');

  return (
    <div className="App">
      <header className="App-header">
        <h1>🖼️ 图片文字擦除工具</h1>
        <p className="subtitle">智能识别并擦除文字，背景自动填充</p>
      </header>

      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          单图处理
        </button>
        <button
          className={`tab-btn ${activeTab === 'batch' ? 'active' : ''}`}
          onClick={() => setActiveTab('batch')}
        >
          批量处理
        </button>
        <button
          className={`tab-btn ${activeTab === 'video' ? 'active' : ''}`}
          onClick={() => setActiveTab('video')}
        >
          视频处理
        </button>
      </div>

      <main className="main-content">
        {activeTab === 'single' && <ImageEditor />}
        {activeTab === 'batch' && <BatchProcessor />}
        {activeTab === 'video' && <VideoEditor />}
      </main>

      <footer className="App-footer">
        <p>使用 React + Canvas + 图像修复算法 + 文字检测 构建</p>
      </footer>
    </div>
  );
}

export default App;
