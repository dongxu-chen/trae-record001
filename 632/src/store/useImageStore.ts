import { create } from 'zustand';
import { ImageItem, ProcessingParams, DEFAULT_PARAMS, ComplexityLevel } from '../types';
import { generateId } from '../algorithms/utils';
import { analyzeComplexity, getRecommendedParams, detectContentType, getParamsForContentType } from '../algorithms/complexityAnalyzer';

interface ImageState {
  images: ImageItem[];
  currentImageId: string | null;
  params: ProcessingParams;
  outputFormat: 'png' | 'jpeg' | 'webp';
  outputQuality: number;
  autoParamsEnabled: boolean;
  preClassified: boolean;
  
  addImage: (file: File) => Promise<ImageItem>;
  removeImage: (id: string) => void;
  clearImages: () => void;
  setCurrentImage: (id: string | null) => void;
  updateImage: (id: string, updates: Partial<ImageItem>) => void;
  setParams: (params: Partial<ProcessingParams>) => void;
  resetParams: () => void;
  setOutputFormat: (format: 'png' | 'jpeg' | 'webp') => void;
  setOutputQuality: (quality: number) => void;
  addToBatch: (id: string) => void;
  processBatch: () => void;
  imageDataToUrl: (imageData: ImageData, format: string, quality: number) => string;
  analyzeImageComplexity: (id: string) => void;
  classifyAllImages: () => void;
  applyRecommendedParams: (id: string) => void;
  setAutoParamsEnabled: (enabled: boolean) => void;
  getGroupedByComplexity: () => Record<ComplexityLevel, ImageItem[]>;
}

const loadImageData = (file: File): Promise<{ imageData: ImageData; width: number; height: number }> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get canvas context'));
        return;
      }
      ctx.drawImage(img, 0, 0);
      const imageData = ctx.getImageData(0, 0, img.width, img.height);
      resolve({ imageData, width: img.width, height: img.height });
      URL.revokeObjectURL(img.src);
    };
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(file);
  });
};

export const useImageStore = create<ImageState>((set, get) => ({
  images: [],
  currentImageId: null,
  params: { ...DEFAULT_PARAMS },
  outputFormat: 'png',
  outputQuality: 0.9,
  autoParamsEnabled: true,
  preClassified: false,

  addImage: async (file: File) => {
    const id = generateId();
    const originalUrl = URL.createObjectURL(file);
    const { imageData, width, height } = await loadImageData(file);

    const complexityResult = analyzeComplexity(imageData);
    const complexity = {
      level: complexityResult.level,
      score: complexityResult.score,
      edgeDensity: complexityResult.edgeDensity,
      colorVariance: complexityResult.colorVariance,
      detailLevel: complexityResult.detailLevel
    };

    const contentResult = detectContentType(imageData);

    const complexityParams = getRecommendedParams(complexityResult);
    const contentParams = getParamsForContentType(contentResult.contentType, contentResult.textConfidence);
    const recommendedParams = { ...complexityParams, ...contentParams };

    const newImage: ImageItem = {
      id,
      file,
      name: file.name,
      originalUrl,
      originalData: imageData,
      width,
      height,
      status: 'pending',
      progress: 0,
      complexity,
      useAutoParams: true,
      params: recommendedParams as ProcessingParams,
      contentType: contentResult.contentType,
      textConfidence: contentResult.textConfidence,
      isAnimated: contentResult.isAnimated
    };

    set((state) => ({
      images: [...state.images, newImage],
      currentImageId: state.currentImageId || id,
      params: state.autoParamsEnabled ? { ...state.params, ...recommendedParams } as ProcessingParams : state.params
    }));

    return newImage;
  },

  removeImage: (id: string) => {
    set((state) => {
      const image = state.images.find((img) => img.id === id);
      if (image) {
        URL.revokeObjectURL(image.originalUrl);
        if (image.processedUrl) {
          URL.revokeObjectURL(image.processedUrl);
        }
      }
      const newImages = state.images.filter((img) => img.id !== id);
      return {
        images: newImages,
        currentImageId: state.currentImageId === id 
          ? (newImages.length > 0 ? newImages[0].id : null)
          : state.currentImageId
      };
    });
  },

  clearImages: () => {
    const { images } = get();
    images.forEach((img) => {
      URL.revokeObjectURL(img.originalUrl);
      if (img.processedUrl) {
        URL.revokeObjectURL(img.processedUrl);
      }
    });
    set({ images: [], currentImageId: null, preClassified: false });
  },

  setCurrentImage: (id: string | null) => {
    set({ currentImageId: id });
  },

  updateImage: (id: string, updates: Partial<ImageItem>) => {
    set((state) => ({
      images: state.images.map((img) =>
        img.id === id ? { ...img, ...updates } : img
      )
    }));
  },

  setParams: (params: Partial<ProcessingParams>) => {
    set((state) => ({
      params: { ...state.params, ...params },
      autoParamsEnabled: false
    }));
  },

  resetParams: () => {
    set({ params: { ...DEFAULT_PARAMS }, autoParamsEnabled: false });
  },

  setOutputFormat: (format: 'png' | 'jpeg' | 'webp') => {
    set({ outputFormat: format });
  },

  setOutputQuality: (quality: number) => {
    set({ outputQuality: quality });
  },

  addToBatch: (id: string) => {
    get().updateImage(id, { status: 'pending', progress: 0 });
  },

  processBatch: () => {
    const { images, classifyAllImages } = get();
    classifyAllImages();
    images.forEach((img) => {
      if (img.status === 'pending') {
        get().updateImage(img.id, { status: 'processing', progress: 0 });
      }
    });
  },

  imageDataToUrl: (imageData: ImageData, format: string, quality: number) => {
    const canvas = document.createElement('canvas');
    canvas.width = imageData.width;
    canvas.height = imageData.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to get canvas context');
    ctx.putImageData(imageData, 0, 0);
    
    const mimeType = format === 'jpeg' ? 'image/jpeg' : format === 'webp' ? 'image/webp' : 'image/png';
    return canvas.toDataURL(mimeType, quality);
  },

  analyzeImageComplexity: (id: string) => {
    const image = get().images.find(img => img.id === id);
    if (!image || !image.originalData) return;

    const result = analyzeComplexity(image.originalData);
    get().updateImage(id, {
      complexity: {
        level: result.level,
        score: result.score,
        edgeDensity: result.edgeDensity,
        colorVariance: result.colorVariance,
        detailLevel: result.detailLevel
      }
    });
  },

  classifyAllImages: () => {
    const { images, updateImage } = get();
    for (const img of images) {
      if (!img.originalData) continue;
      const complexity = img.complexity || analyzeComplexity(img.originalData);
      const content = img.contentType ? 
        { contentType: img.contentType, textConfidence: img.textConfidence || 0, isAnimated: img.isAnimated || false } :
        detectContentType(img.originalData);

      const complexityParams = getRecommendedParams({ ...complexity, dominantDirections: [] });
      const contentParams = getParamsForContentType(content.contentType, content.textConfidence);
      const mergedParams = { ...complexityParams, ...contentParams };

      updateImage(img.id, {
        complexity: {
          level: complexity.level,
          score: complexity.score,
          edgeDensity: complexity.edgeDensity,
          colorVariance: complexity.colorVariance,
          detailLevel: complexity.detailLevel
        },
        contentType: content.contentType,
        textConfidence: content.textConfidence,
        isAnimated: content.isAnimated,
        useAutoParams: true,
        params: mergedParams as ProcessingParams
      });
    }
    set({ preClassified: true });
  },

  applyRecommendedParams: (id: string) => {
    const image = get().images.find(img => img.id === id);
    if (!image || !image.originalData) return;

    const complexity = image.complexity || analyzeComplexity(image.originalData);
    const content = image.contentType ? 
      { contentType: image.contentType, textConfidence: image.textConfidence || 0 } :
      detectContentType(image.originalData);

    const complexityParams = getRecommendedParams({ ...complexity, dominantDirections: [] });
    const contentParams = getParamsForContentType(content.contentType, content.textConfidence);
    const mergedParams = { ...complexityParams, ...contentParams };

    set({ 
      params: mergedParams as ProcessingParams, 
      autoParamsEnabled: true 
    });
    get().updateImage(id, { 
      useAutoParams: true, 
      params: mergedParams as ProcessingParams,
      contentType: content.contentType,
      textConfidence: content.textConfidence
    });
  },

  setAutoParamsEnabled: (enabled: boolean) => {
    set({ autoParamsEnabled: enabled });
  },

  getGroupedByComplexity: () => {
    const { images } = get();
    const groups: Record<ComplexityLevel, ImageItem[]> = {
      simple: [],
      medium: [],
      complex: []
    };

    for (const img of images) {
      if (img.complexity) {
        groups[img.complexity.level].push(img);
      }
    }

    return groups;
  }
}));
