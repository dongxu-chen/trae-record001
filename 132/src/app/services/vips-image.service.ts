import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable, from } from 'rxjs';
import { map, catchError, shareReplay } from 'rxjs/operators';

declare var Vips: any;

export interface VipsImage {
  width: number;
  height: number;
  channels: number;
  format: string;
  data: Uint8Array;
}

export interface ProcessOptions {
  width?: number;
  height?: number;
  quality?: number;
  format?: 'jpeg' | 'png' | 'webp' | 'heif' | 'avif';
  crop?: 'centre' | 'entropy' | 'attention' | 'none';
  sharpen?: boolean;
  watermark?: WatermarkOptions;
}

export interface WatermarkOptions {
  text: string;
  font?: string;
  fontSize?: number;
  color?: string;
  opacity?: number;
  position?: 'northwest' | 'northeast' | 'southwest' | 'southeast' | 'centre';
  padding?: number;
}

export interface FaceRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export type ImageFormat = 
  | 'jpeg' | 'png' | 'webp' | 'gif' | 'tiff'
  | 'svg' | 'psd' | 'heic' | 'avif' | 'bmp' | 'raw';

const SUPPORTED_FORMATS: ImageFormat[] = [
  'jpeg', 'png', 'webp', 'gif', 'tiff',
  'svg', 'psd', 'heic', 'avif', 'bmp'
];

@Injectable({
  providedIn: 'root'
})
export class VipsImageService implements OnDestroy {
  private vipsInstance: any = null;
  private isInitialized$ = new BehaviorSubject<boolean>(false);
  private isLoading$ = new BehaviorSubject<boolean>(false);
  private loadProgress$ = new BehaviorSubject<number>(0);

  isInitialized: Observable<boolean> = this.isInitialized$.asObservable();
  isLoading: Observable<boolean> = this.isLoading$.asObservable();
  loadProgress: Observable<number> = this.loadProgress$.asObservable();

  private memoryUsed = 0;
  private maxMemory = 256 * 1024 * 1024; // 256MB 内存限制

  constructor() {
    this.initVips();
  }

  private async initVips(): Promise<void> {
    if (this.vipsInstance) return;
    
    this.isLoading$.next(true);
    this.loadProgress$.next(10);

    try {
      // 动态加载 wasm-vips
      const module = await import('wasm-vips');
      
      this.loadProgress$.next(50);

      // 配置 VIPS 运行时
      this.vipsInstance = await module.default({
        locateFile: (file: string) => {
          return `/assets/wasm-vips/${file}`;
        },
        print: (text: string) => console.log('[VIPS]', text),
        printErr: (text: string) => console.warn('[VIPS]', text),
        onRuntimeInitialized: () => {
          this.loadProgress$.next(80);
        },
        memoryInitializerPrefixURL: '/assets/wasm-vips/',
        wasmMemory: new WebAssembly.Memory({
          initial: 256,
          maximum: 1024,
          shared: true
        })
      });

      // 配置内存限制和并发
      this.vipsInstance.cacheSetMax(0);
      this.vipsInstance.cacheSetMaxMem(this.maxMemory);
      this.vipsInstance.concurrencySet(4);

      this.isInitialized$.next(true);
      this.loadProgress$.next(100);
      console.log('✅ libvips WASM initialized successfully');
      console.log(`   Supported formats: ${this.getSupportedFormats().join(', ')}`);

    } catch (error) {
      console.error('❌ Failed to initialize libvips:', error);
      this.loadProgress$.next(0);
      throw error;
    } finally {
      this.isLoading$.next(false);
    }
  }

  getSupportedFormats(): ImageFormat[] {
    return SUPPORTED_FORMATS;
  }

  private checkInitialized(): void {
    if (!this.vipsInstance) {
      throw new Error('libvips not initialized');
    }
  }

  private trackMemory(operation: string, size: number): void {
    this.memoryUsed += size;
    console.debug(`[VIPS Memory] ${operation}: +${(size/1024/1024).toFixed(2)}MB, total: ${(this.memoryUsed/1024/1024).toFixed(2)}MB`);
  }

  // ==================== 核心处理方法 ====================

  async loadImage(file: File | Blob): Promise<any> {
    this.checkInitialized();
    
    const start = performance.now();
    const buffer = await file.arrayBuffer();
    const uint8 = new Uint8Array(buffer);
    
    this.trackMemory('loadImage', uint8.length);

    const image = this.vipsInstance.Image.newFromBuffer(uint8);
    const duration = performance.now() - start;
    
    console.log(`📷 Loaded ${image.width}x${image.height} in ${duration.toFixed(1)}ms`);
    return image;
  }

  async processImage(
    image: any,
    options: ProcessOptions
  ): Promise<{ blob: Blob; width: number; height: number }> {
    this.checkInitialized();
    
    const start = performance.now();
    let result = image;

    try {
      // 1. 缩放处理
      if (options.width || options.height) {
        const targetWidth = options.width || result.width;
        const targetHeight = options.height || result.height;
        
        if (options.crop && options.crop !== 'none') {
          // 智能裁剪: 使用 entropy/attention 模式保留重要内容
          result = result.thumbnailImage(targetWidth, {
            height: targetHeight,
            crop: this.vipsInstance.Interesting[options.crop.toUpperCase()]
          });
        } else {
          // 常规缩放
          const scale = Math.min(targetWidth / result.width, targetHeight / result.height);
          if (scale < 1) {
            result = result.resize(scale, { kernel: this.vipsInstance.Kernel.LANCZOS3 });
          }
        }
      }

      // 2. 锐化增强
      if (options.sharpen) {
        result = result.sharpen({ sigma: 0.5 });
      }

      // 3. 水印处理
      if (options.watermark && options.watermark.text) {
        result = await this.addWatermark(result, options.watermark);
      }

      // 4. 格式转换与输出
      const outputFormat = options.format || 'jpeg';
      const quality = options.quality || 0.8;
      
      let outputBuffer: Uint8Array;
      const writeOptions: any = { Q: Math.round(quality * 100) };

      switch (outputFormat) {
        case 'jpeg':
          writeOptions.optimizeCoding = true;
          writeOptions.interlace = true;
          writeOptions.subsampleMode = this.vipsInstance.ForeignSubsampleMode.ON;
          outputBuffer = result.writeToBuffer('.jpg', writeOptions);
          break;
        case 'png':
          writeOptions.compression = 6;
          writeOptions.interlace = false;
          outputBuffer = result.writeToBuffer('.png', writeOptions);
          break;
        case 'webp':
          writeOptions.effort = 4;
          writeOptions.lossless = false;
          outputBuffer = result.writeToBuffer('.webp', writeOptions);
          break;
        case 'avif':
          writeOptions.effort = 4;
          outputBuffer = result.writeToBuffer('.avif', writeOptions);
          break;
        case 'heif':
          outputBuffer = result.writeToBuffer('.heic', writeOptions);
          break;
        default:
          outputBuffer = result.writeToBuffer('.jpg', writeOptions);
      }

      const blob = new Blob([outputBuffer], { type: `image/${outputFormat}` });
      const duration = performance.now() - start;

      console.log(`⚡ Processed: ${image.width}x${image.height} → ${result.width}x${result.height}, ${(outputBuffer.length/1024).toFixed(1)}KB in ${duration.toFixed(1)}ms`);

      return {
        blob,
        width: result.width,
        height: result.height
      };

    } finally {
      // 清理内存
      if (result !== image) {
        result.delete?.();
      }
    }
  }

  private async addWatermark(image: any, options: WatermarkOptions): Promise<any> {
    const fontSize = options.fontSize || 32;
    const font = options.font || 'sans-serif';
    const color = options.color || 'white';
    const opacity = options.opacity || 0.5;
    const padding = options.padding || 20;

    // 创建水印文本
    const text = this.vipsInstance.Image.text(options.text, {
      font: `${font} ${fontSize}`,
      align: this.vipsInstance.Align.CENTRE
    });

    // 创建半透明背景
    let watermark = text.embed(
      padding, padding,
      text.width + padding * 2,
      text.height + padding * 2,
      { extend: this.vipsInstance.Extend.BLACK }
    );

    // 添加透明度
    const alpha = watermark.extractBand(0).multiply(opacity);
    watermark = watermark.bandjoin(alpha);

    // 计算水印位置
    let left: number, top: number;
    switch (options.position || 'southeast') {
      case 'northwest':
        left = padding;
        top = padding;
        break;
      case 'northeast':
        left = image.width - watermark.width - padding;
        top = padding;
        break;
      case 'southwest':
        left = padding;
        top = image.height - watermark.height - padding;
        break;
      case 'centre':
        left = (image.width - watermark.width) / 2;
        top = (image.height - watermark.height) / 2;
        break;
      default: // southeast
        left = image.width - watermark.width - padding;
        top = image.height - watermark.height - padding;
    }

    // 合成水印
    const result = image.composite(watermark, this.vipsInstance.BlendMode.OVER, {
      x: Math.round(left),
      y: Math.round(top)
    });

    watermark.delete?.();
    text.delete?.();

    return result;
  }

  // ==================== 智能裁剪 ====================

  async smartCrop(
    image: any,
    targetWidth: number,
    targetHeight: number
  ): Promise<any> {
    this.checkInitialized();

    const start = performance.now();
    
    // 使用 attention 模式进行智能裁剪
    // 自动识别人脸、主体等重要区域
    const cropped = image.thumbnailImage(targetWidth, {
      height: targetHeight,
      crop: this.vipsInstance.Interesting.ATTENTION
    });

    const duration = performance.now() - start;
    console.log(`✂️ Smart crop: ${image.width}x${image.height} → ${cropped.width}x${cropped.height} in ${duration.toFixed(1)}ms`);

    return cropped;
  }

  // ==================== 格式转换批量处理 ====================

  async convertFormat(
    file: File,
    targetFormat: 'jpeg' | 'png' | 'webp' | 'avif',
    quality: number = 0.8
  ): Promise<Blob> {
    const image = await this.loadImage(file);
    
    try {
      const result = await this.processImage(image, {
        format: targetFormat,
        quality
      });
      return result.blob;
    } finally {
      image.delete?.();
    }
  }

  async batchConvert(
    files: File[],
    targetFormat: 'jpeg' | 'png' | 'webp' | 'avif',
    quality: number = 0.8,
    onProgress?: (current: number, total: number) => void
  ): Promise<Blob[]> {
    const results: Blob[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const blob = await this.convertFormat(files[i], targetFormat, quality);
      results.push(blob);
      onProgress?.(i + 1, files.length);
    }

    return results;
  }

  // ==================== PSD/SVG 特殊处理 ====================

  async processPsd(file: File, layerIndex?: number): Promise<any> {
    const image = await this.loadImage(file);
    
    // PSD 可以访问特定图层
    if (layerIndex !== undefined) {
      console.log(`📄 PSD layers: ${image.get('n-pages')}`);
    }

    return image;
  }

  async renderSvg(file: File, scale: number = 1): Promise<any> {
    const buffer = await file.arrayBuffer();
    const uint8 = new Uint8Array(buffer);
    
    // SVG 渲染时可以指定缩放
    const image = this.vipsInstance.Image.newFromBuffer(uint8, {
      scale,
      unlimited: true
    });

    console.log(`🎨 SVG rendered: ${image.width}x${image.height}`);
    return image;
  }

  // ==================== 性能基准测试 ====================

  async benchmark(file: File): Promise<{
    vips: { time: number; size: number };
    canvas: { time: number; size: number };
    improvement: number;
  }> {
    // 测试 VIPS
    const vipsStart = performance.now();
    const vipsResult = await this.convertFormat(file, 'jpeg', 0.8);
    const vipsTime = performance.now() - vipsStart;

    // 测试 Canvas
    const canvasStart = performance.now();
    const canvasResult = await this.canvasCompress(file, 0.8);
    const canvasTime = performance.now() - canvasStart;

    const improvement = canvasTime / vipsTime;

    console.log('📊 Benchmark Results:');
    console.log(`   Canvas: ${canvasTime.toFixed(1)}ms, ${(canvasResult.size/1024).toFixed(1)}KB`);
    console.log(`   VIPS:   ${vipsTime.toFixed(1)}ms, ${(vipsResult.size/1024).toFixed(1)}KB`);
    console.log(`   Speedup: ${improvement.toFixed(1)}x faster`);

    return {
      vips: { time: vipsTime, size: vipsResult.size },
      canvas: { time: canvasTime, size: canvasResult.size },
      improvement
    };
  }

  private async canvasCompress(file: File, quality: number): Promise<Blob> {
    return new Promise(async (resolve) => {
      const bitmap = await createImageBitmap(file);
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(bitmap, 0, 0);
      
      canvas.toBlob(blob => {
        bitmap.close();
        resolve(blob!);
      }, 'image/jpeg', quality);
    });
  }

  // ==================== 内存管理 ====================

  collectGarbage(): void {
    if (this.vipsInstance) {
      this.vipsInstance.collectGarbage();
      this.memoryUsed = 0;
      console.log('🧹 VIPS garbage collected');
    }
  }

  getMemoryStats(): { used: number; max: number; percent: number } {
    const used = this.vipsInstance?.memoryStats()?.mem || this.memoryUsed;
    return {
      used,
      max: this.maxMemory,
      percent: (used / this.maxMemory) * 100
    };
  }

  ngOnDestroy(): void {
    this.collectGarbage();
  }
}
