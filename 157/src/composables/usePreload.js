import LRUCache from '../utils/LRUCache';
import RequestQueue from '../utils/RequestQueue';
import { getImageDecoderManager } from '../services/ImageDecoderManager';

const textureCache = new LRUCache(20);
const loadingPages = new Set();
const PRELOAD_COUNT = 3;

let decoderManager = null;
let initPromise = null;

async function ensureDecoderManager() {
  if (!initPromise) {
    initPromise = (async () => {
      decoderManager = getImageDecoderManager();
      await decoderManager.waitForReady();
      return decoderManager;
    })();
  }
  return initPromise;
}

export function usePreload() {
  async function preloadPages(currentIndex, imageUrls, options = {}) {
    await ensureDecoderManager();
    
    const preloadIndices = [];
    
    for (let i = 1; i <= PRELOAD_COUNT; i++) {
      const nextIndex = currentIndex + i;
      if (nextIndex < imageUrls.length) {
        preloadIndices.push(nextIndex);
      }
    }
    
    for (let i = 1; i <= PRELOAD_COUNT; i++) {
      const prevIndex = currentIndex - i;
      if (prevIndex >= 0) {
        preloadIndices.push(prevIndex);
      }
    }
    
    console.log(`[WebCodecs] 计划预加载 ${preloadIndices.length} 页:`, preloadIndices);
    
    for (const index of preloadIndices) {
      if (!textureCache.has(index) && !loadingPages.has(index)) {
        loadingPages.add(index);
        
        decodePage(index, imageUrls[index], options).then(texture => {
          if (texture) {
            textureCache.set(index, texture);
            console.log(`[WebCodecs] 页面 ${index + 1} 解码完成并缓存`);
          }
        }).catch(error => {
          console.error(`[WebCodecs] 页面 ${index + 1} 解码失败:`, error);
        }).finally(() => {
          loadingPages.delete(index);
        });
      }
    }
  }
  
  async function decodePage(index, url, options = {}) {
    try {
      const texture = await decoderManager.decodeToTexture(url, {
        mipmap: options.mipmap ?? false,
        scaleMode: options.scaleMode,
        onProgress: (progress, status) => {
          if (options.onProgress) {
            options.onProgress(index, progress, status);
          }
        }
      });
      
      return texture;
    } catch (error) {
      console.warn(`页面 ${index + 1} WebCodecs解码失败:`, error);
      return null;
    }
  }
  
  async function loadPage(index, url, options = {}) {
    await ensureDecoderManager();
    
    if (textureCache.has(index)) {
      return textureCache.get(index);
    }
    
    if (loadingPages.has(index)) {
      return new Promise(resolve => {
        const checkInterval = setInterval(() => {
          if (!loadingPages.has(index)) {
            clearInterval(checkInterval);
            resolve(textureCache.get(index));
          }
        }, 50);
      });
    }
    
    loadingPages.add(index);
    
    try {
      const texture = await decodePage(index, url, options);
      if (texture) {
        textureCache.set(index, texture);
      }
      return texture;
    } finally {
      loadingPages.delete(index);
    }
  }
  
  function getTexture(index) {
    return textureCache.get(index);
  }
  
  function hasTexture(index) {
    return textureCache.has(index);
  }
  
  function setTexture(index, texture) {
    textureCache.set(index, texture);
  }
  
  function getCacheStats() {
    const decoderStats = decoderManager ? decoderManager.getStats() : {};
    
    return {
      cacheSize: textureCache.size(),
      maxCacheSize: 20,
      loading: loadingPages.size,
      ...decoderStats
    };
  }
  
  function clearCache() {
    if (decoderManager) {
      decoderManager.clearQueue();
    }
    loadingPages.clear();
    textureCache.clear();
  }
  
  async function getDecodeStats() {
    await ensureDecoderManager();
    return decoderManager.getStats();
  }
  
  function isWebCodecsSupported() {
    return decoderManager ? decoderManager.supportsWebCodecs : false;
  }
  
  function isAVIFSupported() {
    return decoderManager ? decoderManager.supportsAVIF : false;
  }
  
  return {
    preloadPages,
    loadPage,
    getTexture,
    hasTexture,
    setTexture,
    getCacheStats,
    clearCache,
    getDecodeStats,
    isWebCodecsSupported,
    isAVIFSupported,
    textureCache
  };
}
