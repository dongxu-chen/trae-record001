import React, { useState, useCallback } from 'react';
import ConfigPanel from './components/ConfigPanel';
import PreviewPanel from './components/PreviewPanel';
import BatchPanel from './components/BatchPanel';

const ANIMATION_TYPES = [
  { value: 'none', label: '无动画' },
  { value: 'shimmer', label: '✨ 微光闪烁' },
  { value: 'pulse', label: '💓 脉冲呼吸' },
  { value: 'blink', label: '👁️ 闪烁' },
  { value: 'wave', label: '🌊 波浪' },
  { value: 'gradient', label: '🌈 渐变流动' }
];

function App() {
  const [config, setConfig] = useState({
    url: '',
    device: 'desktop',
    backgroundColor: '',
    highlightColor: '',
    animation: true,
    animationType: 'shimmer',
    animationSpeed: 1.5,
    removeImages: true,
    removeText: true,
    autoColor: true
  });
  
  const [activeTab, setActiveTab] = useState('single');
  const [skeletonData, setSkeletonData] = useState(null);
  const [extractedColors, setExtractedColors] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [batchUrls, setBatchUrls] = useState([]);
  const [batchResults, setBatchResults] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [sitemapLoading, setSitemapLoading] = useState(false);
  
  const [debugMode, setDebugMode] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);

  const handleConfigChange = useCallback((key, value) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const generateSkeleton = useCallback(async () => {
    if (!config.url) {
      setError('请输入页面URL');
      return;
    }

    setLoading(true);
    setError(null);
    setExtractedColors(null);
    setSkeletonData(null);
    
    try {
      const requestOptions = {
        device: config.device,
        animation: config.animation,
        animationType: config.animationType,
        animationSpeed: config.animationSpeed,
        removeImages: config.removeImages,
        removeText: config.removeText
      };
      
      if (!config.autoColor) {
        requestOptions.backgroundColor = config.backgroundColor;
        requestOptions.highlightColor = config.highlightColor;
      }
      
      const response = await fetch('/api/generate-skeleton', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: config.url,
          options: requestOptions
        })
      });

      if (!response.ok) {
        throw new Error('生成失败，请检查URL是否正确');
      }

      const data = await response.json();
      setSkeletonData(data);
      
      if (data.extractedColors) {
        setExtractedColors(data.extractedColors);
        if (config.autoColor) {
          setConfig(prev => ({
            ...prev,
            backgroundColor: data.extractedColors.backgroundColor,
            highlightColor: data.extractedColors.highlightColor
          }));
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [config]);

  const useExtractedColors = useCallback(() => {
    if (extractedColors) {
      setConfig(prev => ({
        ...prev,
        backgroundColor: extractedColors.backgroundColor,
        highlightColor: extractedColors.highlightColor,
        autoColor: true
      }));
      regenerateWithNewColors(extractedColors.backgroundColor, extractedColors.highlightColor);
    }
  }, [extractedColors]);

  const regenerateWithNewColors = useCallback((bgColor = config.backgroundColor, hlColor = config.highlightColor) => {
    if (!skeletonData) return;
    
    const { layoutData } = skeletonData;
    
    const regenerateCSS = (options) => {
      const { backgroundColor, highlightColor, animation, animationType, animationSpeed, device } = options;
      
      let animationCSS = '';
      let backgroundStyle = `background: ${highlightColor};`;
      
      if (animation && animationType !== 'none') {
        const speed = animationSpeed || 1.5;
        
        switch (animationType) {
          case 'pulse':
            animationCSS = `
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
`;
            backgroundStyle = `background: ${highlightColor}; animation: skeleton-pulse ${speed}s ease-in-out infinite;`;
            break;
            
          case 'blink':
            animationCSS = `
@keyframes skeleton-blink {
  0%, 50%, 100% { opacity: 1; }
  25%, 75% { opacity: 0.3; }
}
`;
            backgroundStyle = `background: ${highlightColor}; animation: skeleton-blink ${speed}s step-start infinite;`;
            break;
            
          case 'wave':
            animationCSS = `
@keyframes skeleton-wave {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.skeleton-item {
  overflow: hidden;
  position: relative;
}
.skeleton-item::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, ${backgroundColor}, transparent);
  animation: skeleton-wave ${speed}s ease-in-out infinite;
}
`;
            backgroundStyle = `background: ${highlightColor};`;
            break;
            
          case 'gradient':
            animationCSS = `
@keyframes skeleton-gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
`;
            backgroundStyle = `background: linear-gradient(270deg, ${backgroundColor}, ${highlightColor}, ${backgroundColor}); background-size: 400% 400%; animation: skeleton-gradient ${speed * 2}s ease infinite;`;
            break;
            
          case 'shimmer':
          default:
            animationCSS = `
@keyframes skeleton-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
`;
            backgroundStyle = `background: linear-gradient(90deg, ${backgroundColor} 25%, ${highlightColor} 50%, ${backgroundColor} 75%); background-size: 200% 100%; animation: skeleton-shimmer ${speed}s infinite;`;
            break;
        }
      }
      
      const mobileStyles = device === 'mobile' ? `
@media (max-width: 480px) {
  .skeleton-container {
    width: 100% !important;
    max-width: 100%;
    overflow-x: hidden;
  }
  
  .skeleton-item {
    box-sizing: border-box;
  }
}
` : '';
      
      return `
${animationCSS}

* {
  box-sizing: border-box;
}

.skeleton-container {
  overflow: hidden;
  background: ${backgroundColor};
}

.skeleton-item {
  ${backgroundStyle}
  border-radius: 4px;
  box-sizing: border-box;
}

.skeleton-image {
  border-radius: 8px;
}

.skeleton-avatar {
  border-radius: 50%;
}

.skeleton-text-line {
  border-radius: 4px;
  height: 14px !important;
  min-height: 14px;
}

.skeleton-text-block {
  border-radius: 4px;
}

.skeleton-button {
  border-radius: 6px;
}

.skeleton-input {
  border-radius: 6px;
  border: 1px solid rgba(0,0,0,0.1);
}

.skeleton-card {
  border-radius: 12px;
  overflow: hidden;
}

.skeleton-header,
.skeleton-footer,
.skeleton-navigation,
.skeleton-sidebar,
.skeleton-list {
  background: transparent;
  animation: none;
}

.skeleton-container-block {
  background: transparent;
  animation: none;
}

.skeleton-list-item {
  border-radius: 4px;
}

${mobileStyles}
`.trim();
    };

    const regenerateHTML = (pageData, options) => {
      const { pageWidth, pageHeight, body, viewportMeta } = pageData;
      const { backgroundColor, device: genDevice } = options;
      
      function renderElement(element, parentHasAbsolute = false) {
        if (!element) return '';
        
        const { type, rect, absoluteRect, style, id } = element;
        
        const isAbsolute = style.position === 'absolute' || style.position === 'fixed';
        const useAbsolute = parentHasAbsolute || isAbsolute;
        const useRect = useAbsolute ? absoluteRect : rect;
        
        const posStyle = useAbsolute 
          ? `position: absolute; top: ${useRect.top}px; left: ${useRect.left}px;`
          : `position: relative;`;
        
        const sizeStyle = `width: ${useRect.width}px; height: ${useRect.height}px;`;
        
        let elementStyle = `${posStyle} ${sizeStyle}`;
        
        if (style.borderRadius && style.borderRadius !== '0px') {
          elementStyle += ` border-radius: ${style.borderRadius};`;
        }
        
        let className = 'skeleton-item';
        if (type === 'image') {
          className += ' skeleton-image';
        } else if (type === 'avatar') {
          className += ' skeleton-avatar';
        } else if (type === 'text-line' || type === 'heading') {
          className += ' skeleton-text-line';
        } else if (type === 'text-block') {
          className += ' skeleton-text-block';
        } else if (type === 'button') {
          className += ' skeleton-button';
        } else if (type === 'input') {
          className += ' skeleton-input';
        } else if (type === 'card') {
          className += ' skeleton-card';
        } else if (type === 'navigation') {
          className += ' skeleton-navigation';
        } else if (type === 'header') {
          className += ' skeleton-header';
        } else if (type === 'footer') {
          className += ' skeleton-footer';
        } else if (type === 'sidebar') {
          className += ' skeleton-sidebar';
        } else if (type === 'list') {
          className += ' skeleton-list';
        } else if (type === 'list-item') {
          className += ' skeleton-list-item';
        } else if (type === 'container') {
          className += ' skeleton-container-block';
        }
        
        let childrenHTML = '';
        if (element.children && element.children.length > 0) {
          childrenHTML = element.children
            .map(child => renderElement(child, useAbsolute))
            .join('');
        }
        
        const isWrapper = type === 'container' || type === 'navigation' || 
                           type === 'header' || type === 'footer' || 
                           type === 'sidebar' || type === 'card' || type === 'list';
        
        const dataAttrs = `data-element-id="${id}" data-element-type="${type}"`;
        
        if (isWrapper) {
          return `<div class="${className}" ${dataAttrs} style="${elementStyle}">${childrenHTML}</div>`;
        } else {
          return `<div class="${className}" ${dataAttrs} style="${elementStyle}"></div>${childrenHTML}`;
        }
      }
      
      const bodyHTML = body ? renderElement(body, false) : '';
      
      const viewportTag = genDevice === 'mobile' 
        ? `<meta name="viewport" content="${viewportMeta || 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'}">`
        : '';
      
      return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  ${viewportTag}
  <title>Skeleton Screen</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      overflow-x: hidden;
    }
  </style>
</head>
<body>
<div class="skeleton-container" style="width: ${pageWidth}px; min-height: ${pageHeight}px; position: relative; background: ${backgroundColor};">
  ${bodyHTML}
</div>
</body>
</html>
      `.trim();
    };

    const newOptions = {
      backgroundColor: bgColor,
      highlightColor: hlColor,
      animation: config.animation,
      animationType: config.animationType,
      animationSpeed: config.animationSpeed,
      device: config.device
    };
    
    const newHTML = regenerateHTML(layoutData, newOptions);
    const newCSS = regenerateCSS(newOptions);
    
    setSkeletonData(prev => ({
      ...prev,
      html: newHTML,
      css: newCSS
    }));
  }, [skeletonData, config]);

  const parseSitemap = useCallback(async () => {
    if (!sitemapUrl) {
      setError('请输入站点地图URL');
      return;
    }
    
    setSitemapLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/parse-sitemap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ sitemapUrl })
      });
      
      if (!response.ok) {
        throw new Error('解析站点地图失败');
      }
      
      const data = await response.json();
      setBatchUrls(data.urls);
    } catch (err) {
      setError(err.message);
    } finally {
      setSitemapLoading(false);
    }
  }, [sitemapUrl]);

  const batchGenerate = useCallback(async () => {
    if (batchUrls.length === 0) {
      setError('请添加URLs');
      return;
    }
    
    setBatchLoading(true);
    setError(null);
    setBatchResults([]);
    
    try {
      const requestOptions = {
        device: config.device,
        animation: config.animation,
        animationType: config.animationType,
        animationSpeed: config.animationSpeed,
        removeImages: config.removeImages,
        removeText: config.removeText
      };
      
      if (!config.autoColor) {
        requestOptions.backgroundColor = config.backgroundColor;
        requestOptions.highlightColor = config.highlightColor;
      }
      
      const response = await fetch('/api/batch-generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          urls: batchUrls,
          options: requestOptions
        })
      });
      
      if (!response.ok) {
        throw new Error('批量生成失败');
      }
      
      const data = await response.json();
      setBatchResults(data.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchLoading(false);
    }
  }, [batchUrls, config]);

  const updateElement = useCallback((elementId, updates) => {
    if (!skeletonData) return;
    
    const updateElementInTree = (element) => {
      if (!element) return null;
      
      if (element.id === elementId) {
        return { ...element, ...updates };
      }
      
      if (element.children) {
        return {
          ...element,
          children: element.children.map(updateElementInTree).filter(Boolean)
        };
      }
      
      return element;
    };
    
    const newLayoutData = {
      ...skeletonData.layoutData,
      body: updateElementInTree(skeletonData.layoutData.body)
    };
    
    setSkeletonData(prev => ({
      ...prev,
      layoutData: newLayoutData
    }));
    
    regenerateWithNewColors();
  }, [skeletonData, regenerateWithNewColors]);

  const deleteElement = useCallback((elementId) => {
    if (!skeletonData) return;
    
    const deleteElementFromTree = (element) => {
      if (!element) return null;
      
      if (element.id === elementId) {
        return null;
      }
      
      if (element.children) {
        return {
          ...element,
          children: element.children.map(deleteElementFromTree).filter(Boolean)
        };
      }
      
      return element;
    };
    
    const newLayoutData = {
      ...skeletonData.layoutData,
      body: deleteElementFromTree(skeletonData.layoutData.body)
    };
    
    setSkeletonData(prev => ({
      ...prev,
      layoutData: newLayoutData
    }));
    
    regenerateWithNewColors();
  }, [skeletonData, regenerateWithNewColors]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎨 网页骨架屏生成器</h1>
        <p>输入页面URL，自动生成高质量骨架屏代码</p>
      </header>
      
      <div className="app-tabs">
        <button 
          className={`app-tab ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          单页生成
        </button>
        <button 
          className={`app-tab ${activeTab === 'batch' ? 'active' : ''}`}
          onClick={() => setActiveTab('batch')}
        >
          批量生成
        </button>
      </div>
      
      <div className="app-content">
        {activeTab === 'single' ? (
          <>
            <ConfigPanel
              config={config}
              onConfigChange={handleConfigChange}
              onGenerate={generateSkeleton}
              loading={loading}
              error={error}
              onRegenerateColors={() => regenerateWithNewColors()}
              onUseExtractedColors={useExtractedColors}
              hasData={!!skeletonData}
              extractedColors={extractedColors}
              animationTypes={ANIMATION_TYPES}
              debugMode={debugMode}
              onDebugModeChange={setDebugMode}
            />
            
            <PreviewPanel
              skeletonData={skeletonData}
              device={config.device}
              loading={loading}
              debugMode={debugMode}
              selectedElement={selectedElement}
              onSelectElement={setSelectedElement}
              onUpdateElement={updateElement}
              onDeleteElement={deleteElement}
            />
          </>
        ) : (
          <BatchPanel
            config={config}
            onConfigChange={handleConfigChange}
            batchUrls={batchUrls}
            onBatchUrlsChange={setBatchUrls}
            batchResults={batchResults}
            onBatchGenerate={batchGenerate}
            batchLoading={batchLoading}
            sitemapUrl={sitemapUrl}
            onSitemapUrlChange={setSitemapUrl}
            onParseSitemap={parseSitemap}
            sitemapLoading={sitemapLoading}
            error={error}
            animationTypes={ANIMATION_TYPES}
          />
        )}
      </div>
      
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>正在分析页面并生成骨架屏...</p>
        </div>
      )}
    </div>
  );
}

export default App;
