import { Component, OnInit, ElementRef, ViewChild, Inject } from '@angular/core';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { WatermarkConfig, CropConfig } from '../../services/image.service';
import { SmartImageService, FaceRegion, NsfwResult, OcrResult, ImageAnalysis } from '../../services/smart-image.service';

export type WatermarkPosition = 
  | 'top-left' | 'top-center' | 'top-right'
  | 'middle-left' | 'center' | 'middle-right'
  | 'bottom-left' | 'bottom-center' | 'bottom-right';

@Component({
  selector: 'app-image-editor',
  templateUrl: './image-editor.component.html',
  styleUrls: ['./image-editor.component.scss']
})
export class ImageEditorComponent implements OnInit {
  @ViewChild('canvas', { static: true }) canvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('faceCanvas', { static: false }) faceCanvas!: ElementRef<HTMLCanvasElement>;

  originalImage!: HTMLImageElement;
  currentScale = 100;
  rotation = 0;
  activeTab = 'scale';
  isAnalyzing = false;
  analysisResult?: ImageAnalysis;
  showFaceRegions = true;

  watermarkConfig: WatermarkConfig & { position: WatermarkPosition } = {
    text: 'CDN',
    fontSize: 32,
    color: '#ffffff',
    opacity: 0.5,
    position: 'bottom-right'
  };

  cropConfig: CropConfig = {
    x: 0,
    y: 0,
    width: 0,
    height: 0
  };

  cropPresets = [
    { label: '自定义', width: 0, height: 0 },
    { label: '1:1 正方形', width: 800, height: 800 },
    { label: '4:3 标准', width: 800, height: 600 },
    { label: '16:9 宽屏', width: 960, height: 540 },
    { label: '头像', width: 400, height: 400 }
  ];
  selectedCropPreset = 0;

  isCropping = false;
  cropStart = { x: 0, y: 0 };

  watermarkPositions: { key: WatermarkPosition; label: string; icon: string }[] = [
    { key: 'top-left', label: '左上', icon: 'border-top' },
    { key: 'top-center', label: '中上', icon: 'border-vertical' },
    { key: 'top-right', label: '右上', icon: 'border-top' },
    { key: 'middle-left', label: '左中', icon: 'border-horizontal' },
    { key: 'center', label: '居中', icon: 'border-inner' },
    { key: 'middle-right', label: '右中', icon: 'border-horizontal' },
    { key: 'bottom-left', label: '左下', icon: 'border-bottom' },
    { key: 'bottom-center', label: '中下', icon: 'border-vertical' },
    { key: 'bottom-right', label: '右下', icon: 'border-bottom' }
  ];

  constructor(
    @Inject(NZ_MODAL_DATA) public data: { imageUrl: string; fileName: string },
    private modalRef: NzModalRef,
    private message: NzMessageService,
    private smartImageService: SmartImageService
  ) { }

  ngOnInit(): void {
    this.loadImage();
  }

  private loadImage(): void {
    this.originalImage = new Image();
    this.originalImage.crossOrigin = 'anonymous';
    this.originalImage.onload = () => {
      this.drawImage();
    };
    this.originalImage.src = this.data.imageUrl;
  }

  private drawImage(): void {
    const canvas = this.canvas.nativeElement;
    const ctx = canvas.getContext('2d')!;

    const scaledWidth = this.originalImage.width * (this.currentScale / 100);
    const scaledHeight = this.originalImage.height * (this.currentScale / 100);

    canvas.width = scaledWidth;
    canvas.height = scaledHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(scaledWidth / 2, scaledHeight / 2);
    ctx.rotate((this.rotation * Math.PI) / 180);
    ctx.drawImage(
      this.originalImage,
      -scaledWidth / 2,
      -scaledHeight / 2,
      scaledWidth,
      scaledHeight
    );
    ctx.restore();

    if (this.showFaceRegions && this.analysisResult?.faces?.length) {
      this.drawFaceRegions(ctx, scaledWidth, scaledHeight);
    }

    if (this.activeTab === 'watermark' && this.watermarkConfig.text) {
      this.drawWatermark(ctx, scaledWidth, scaledHeight);
    }
  }

  private drawFaceRegions(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    const scaleX = width / this.originalImage.width;
    const scaleY = height / this.originalImage.height;

    ctx.save();
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.font = '12px Arial';
    ctx.fillStyle = '#00ff00';

    this.analysisResult?.faces.forEach((face, index) => {
      const x = face.x * scaleX;
      const y = face.y * scaleY;
      const w = face.width * scaleX;
      const h = face.height * scaleY;

      ctx.strokeRect(x, y, w, h);
      ctx.fillText(`人脸 ${index + 1} (${(face.confidence * 100).toFixed(0)}%)`, x, y - 5);
    });

    ctx.restore();
  }

  private drawWatermark(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    ctx.save();
    ctx.font = `${this.watermarkConfig.fontSize}px Arial`;
    ctx.fillStyle = this.watermarkConfig.color;
    ctx.globalAlpha = this.watermarkConfig.opacity;

    const textWidth = ctx.measureText(this.watermarkConfig.text).width;
    const textHeight = this.watermarkConfig.fontSize;
    const padding = 20;

    const pos = this.calculateWatermarkPosition(width, height, textWidth, textHeight, padding);

    ctx.fillText(this.watermarkConfig.text, pos.x, pos.y);
    ctx.restore();
  }

  private calculateWatermarkPosition(
    imgWidth: number,
    imgHeight: number,
    textWidth: number,
    textHeight: number,
    padding: number
  ): { x: number; y: number } {
    switch (this.watermarkConfig.position) {
      case 'top-left':
        return { x: padding, y: padding + textHeight };
      case 'top-center':
        return { x: (imgWidth - textWidth) / 2, y: padding + textHeight };
      case 'top-right':
        return { x: imgWidth - textWidth - padding, y: padding + textHeight };
      case 'middle-left':
        return { x: padding, y: (imgHeight + textHeight) / 2 };
      case 'center':
        return { x: (imgWidth - textWidth) / 2, y: (imgHeight + textHeight) / 2 };
      case 'middle-right':
        return { x: imgWidth - textWidth - padding, y: (imgHeight + textHeight) / 2 };
      case 'bottom-left':
        return { x: padding, y: imgHeight - padding };
      case 'bottom-center':
        return { x: (imgWidth - textWidth) / 2, y: imgHeight - padding };
      case 'bottom-right':
        return { x: imgWidth - textWidth - padding, y: imgHeight - padding };
      default:
        return { x: imgWidth - textWidth - padding, y: imgHeight - padding };
    }
  }

  onScaleChange(): void {
    this.drawImage();
  }

  rotate(angle: number): void {
    this.rotation = (this.rotation + angle) % 360;
    this.drawImage();
  }

  startCrop(event: MouseEvent): void {
    if (!this.isCropping) return;
    const rect = this.canvas.nativeElement.getBoundingClientRect();
    this.cropStart = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  doCrop(event: MouseEvent): void {
    if (!this.isCropping) return;
    const rect = this.canvas.nativeElement.getBoundingClientRect();
    this.cropConfig = {
      x: Math.min(this.cropStart.x, event.clientX - rect.left),
      y: Math.min(this.cropStart.y, event.clientY - rect.top),
      width: Math.abs(event.clientX - rect.left - this.cropStart.x),
      height: Math.abs(event.clientY - rect.top - this.cropStart.y)
    };
  }

  endCrop(): void {
    if (this.cropConfig.width > 10 && this.cropConfig.height > 10) {
      this.applyCrop();
    }
    this.isCropping = false;
  }

  private applyCrop(): void {
    const canvas = this.canvas.nativeElement;
    const ctx = canvas.getContext('2d')!;

    const imageData = ctx.getImageData(
      this.cropConfig.x,
      this.cropConfig.y,
      this.cropConfig.width,
      this.cropConfig.height
    );

    canvas.width = this.cropConfig.width;
    canvas.height = this.cropConfig.height;
    ctx.putImageData(imageData, 0, 0);

    this.message.success('裁剪成功');
    this.cropConfig = { x: 0, y: 0, width: 0, height: 0 };
  }

  toggleCropMode(): void {
    this.isCropping = !this.isCropping;
    if (!this.isCropping) {
      this.cropConfig = { x: 0, y: 0, width: 0, height: 0 };
    }
  }

  async smartCrop(presetIndex: number): Promise<void> {
    const preset = this.cropPresets[presetIndex];
    if (preset.width === 0) {
      this.message.info('请选择裁剪尺寸');
      return;
    }

    this.message.loading('正在进行智能裁剪...', { nzDuration: 0 });
    try {
      const cropRegion = await this.smartImageService.smartCrop(
        this.data.imageUrl,
        preset.width,
        preset.height
      );

      const canvas = this.canvas.nativeElement;
      const ctx = canvas.getContext('2d')!;
      const scale = this.currentScale / 100;

      canvas.width = cropRegion.width * scale;
      canvas.height = cropRegion.height * scale;

      ctx.drawImage(
        this.originalImage,
        cropRegion.x, cropRegion.y, cropRegion.width, cropRegion.height,
        0, 0, cropRegion.width * scale, cropRegion.height * scale
      );

      this.message.remove();
      if (this.analysisResult?.faces?.length) {
        this.message.success(`智能裁剪成功，保留 ${this.analysisResult.faces.length} 个人脸区域`);
      } else {
        this.message.success('智能裁剪成功');
      }
    } catch (error) {
      this.message.remove();
      this.message.error('智能裁剪失败');
    }
  }

  async analyzeImage(): Promise<void> {
    this.isAnalyzing = true;
    this.message.loading('正在分析图片...', { nzDuration: 0 });

    try {
      this.analysisResult = await this.smartImageService.analyzeImage(this.data.imageUrl);
      this.message.remove();

      const result = this.analysisResult;
      let msg = `检测到 ${result.faces.length} 个人脸`;
      if (result.nsfw.isNsfw) {
        msg += ` | ⚠️ 疑似违规图片 (${(result.nsfw.score * 100).toFixed(0)}%)`;
      }
      msg += ` | 描述: ${result.ocr.text}`;
      this.message.success(msg);

      this.drawImage();
    } catch (error) {
      this.message.remove();
      this.message.error('图片分析失败');
    } finally {
      this.isAnalyzing = false;
    }
  }

  getNsfwLabel(score: number): { text: string; color: string } {
    if (score > 0.7) return { text: '高风险', color: 'red' };
    if (score > 0.4) return { text: '中风险', color: 'orange' };
    if (score > 0.2) return { text: '低风险', color: 'gold' };
    return { text: '安全', color: 'green' };
  }

  reset(): void {
    this.currentScale = 100;
    this.rotation = 0;
    this.watermarkConfig = {
      text: 'CDN',
      fontSize: 32,
      color: '#ffffff',
      opacity: 0.5,
      position: 'bottom-right'
    };
    this.analysisResult = undefined;
    this.drawImage();
    this.message.info('已重置');
  }

  private async canvasToBlob(canvas: HTMLCanvasElement, mimeType: string, quality: number): Promise<Blob | null> {
    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => resolve(blob),
        mimeType,
        quality
      );
    });
  }

  async convertToWebP(): Promise<void> {
    const canvas = this.canvas.nativeElement;
    const fileName = this.data.fileName.replace(/\.[^.]+$/, '');

    let blob = await this.canvasToBlob(canvas, 'image/webp', 0.9);
    let finalMimeType = 'image/webp';
    let finalExtension = 'webp';

    if (!blob) {
      this.message.info('WebP 格式不支持，已自动降级为 JPEG 格式');
      blob = await this.canvasToBlob(canvas, 'image/jpeg', 0.9);
      finalMimeType = 'image/jpeg';
      finalExtension = 'jpg';
    }

    if (!blob) {
      this.message.error('图片转换失败');
      return;
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${fileName}.${finalExtension}`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);

    this.message.success(`${finalExtension.toUpperCase()} 转换完成，已开始下载`);
  }

  save(): void {
    const canvas = this.canvas.nativeElement;
    const url = canvas.toDataURL('image/png');

    this.modalRef.close({
      url,
      width: canvas.width,
      height: canvas.height,
      analysis: this.analysisResult
    });
  }

  cancel(): void {
    this.modalRef.close(null);
  }

  onTabChange(tab: string): void {
    this.activeTab = tab;
    this.drawImage();
  }
}
