import { Component, OnInit } from '@angular/core';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { ImageService, ImageItem } from '../../services/image.service';
import { VipsImageService, ProcessOptions, ImageFormat } from '../../services/vips-image.service';
import { ImageEditorComponent } from '../image-editor/image-editor.component';

interface UploadFile {
  file: File;
  id: string;
  name: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  preview?: string;
  retryCount: number;
  vipsProcessed?: boolean;
  width?: number;
  height?: number;
}

const MAX_CONCURRENT_UPLOADS = 6; // VIPS 并发能力更强
const MAX_RETRY_COUNT = 3;

@Component({
  selector: 'app-image-upload',
  templateUrl: './image-upload.component.html',
  styleUrls: ['./image-upload.component.scss']
})
export class ImageUploadComponent implements OnInit {
  files: UploadFile[] = [];
  isDragging = false;
  uploadAllProgress = 0;
  private uploadQueue: number[] = [];
  private activeUploads = 0;
  private isBatchUploading = false;
  vipsReady = false;

  // 高级处理选项
  autoResize = true;
  targetWidth = 1920;
  targetQuality = 0.85;
  targetFormat: 'original' | 'jpeg' | 'webp' | 'avif' = 'webp';
  enableSmartCrop = false;
  addWatermark = false;

  constructor(
    private imageService: ImageService,
    private modal: NzModalService,
    private message: NzMessageService,
    private vipsService: VipsImageService
  ) { }

  ngOnInit(): void {
    this.vipsService.isInitialized.subscribe(ready => {
      this.vipsReady = ready;
      if (ready) {
        this.message.success('🚀 libvips 高性能引擎已就绪！');
      }
    });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    if (event.dataTransfer?.files) {
      this.handleFiles(event.dataTransfer.files);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.handleFiles(input.files);
      input.value = '';
    }
  }

  private handleFiles(fileList: FileList): void {
    const validTypes = this.vipsService.getSupportedFormats();
    
    Array.from(fileList).forEach(file => {
      const fileExt = file.name.split('.').pop()?.toLowerCase() || '';
      const isValidType = validTypes.some(type => 
        file.type.includes(type) || 
        fileExt === type ||
        (type === 'jpeg' && fileExt === 'jpg')
      );

      if (!isValidType) {
        this.message.warning(`格式 ${fileExt} 可能不完全支持，尝试继续处理...`);
      }
      this.addFile(file);
    });
  }

  private addFile(file: File): void {
    const id = this.imageService.generateId();
    const uploadFile: UploadFile = {
      file,
      id,
      name: file.name,
      progress: 0,
      status: 'pending',
      retryCount: 0,
      vipsProcessed: false
    };

    // 快速生成预览
    const reader = new FileReader();
    reader.onload = (e) => {
      uploadFile.preview = e.target?.result as string;
    };
    reader.readAsDataURL(file);

    this.files.push(uploadFile);
  }

  removeFile(index: number): void {
    this.files.splice(index, 1);
  }

  clearAll(): void {
    this.files = [];
    this.uploadQueue = [];
    this.activeUploads = 0;
    this.isBatchUploading = false;
    this.vipsService.collectGarbage();
  }

  private async uploadSingleFile(index: number): Promise<boolean> {
    const fileItem = this.files[index];
    fileItem.status = 'uploading';
    fileItem.progress = 10;

    try {
      let resultBlob: Blob;
      let processedWidth: number;
      let processedHeight: number;

      if (this.vipsReady) {
        // 使用 VIPS 高性能处理
        const image = await this.vipsService.loadImage(fileItem.file);
        fileItem.progress = 30;

        const options: ProcessOptions = {
          quality: this.targetQuality,
          format: this.targetFormat === 'original' ? 
            (fileItem.file.type.includes('png') ? 'png' : 'jpeg') : 
            this.targetFormat as 'jpeg' | 'webp' | 'avif',
          sharpen: true
        };

        if (this.autoResize) {
          options.width = this.targetWidth;
          options.crop = this.enableSmartCrop ? 'attention' : 'none';
        }

        fileItem.progress = 50;
        const result = await this.vipsService.processImage(image, options);
        resultBlob = result.blob;
        processedWidth = result.width;
        processedHeight = result.height;
        fileItem.vipsProcessed = true;

        image.delete?.();
        fileItem.progress = 90;
      } else {
        // 降级方案: 使用 Canvas
        resultBlob = fileItem.file;
        processedWidth = 0;
        processedHeight = 0;
      }

      // 保存到图片管理
      const previewUrl = URL.createObjectURL(resultBlob);
      const imageItem: ImageItem = {
        id: this.imageService.generateId(),
        name: this.renameWithFormat(fileItem.name),
        originalName: fileItem.name,
        url: previewUrl,
        thumbnail: previewUrl,
        size: resultBlob.size,
        width: processedWidth || 0,
        height: processedHeight || 0,
        format: this.targetFormat === 'original' ? 
          (fileItem.file.type.split('/')[1]?.toUpperCase() || 'JPEG') :
          this.targetFormat.toUpperCase(),
        createdAt: new Date(),
        updatedAt: new Date()
      };

      this.imageService.addImage(imageItem);
      fileItem.status = 'success';
      fileItem.progress = 100;
      
      // 统计压缩率
      const compression = ((1 - resultBlob.size / fileItem.file.size) * 100).toFixed(1);
      console.log(`💾 ${fileItem.name}: ${(fileItem.file.size/1024).toFixed(1)}KB → ${(resultBlob.size/1024).toFixed(1)}KB (压缩 ${compression}%)`);

      return true;

    } catch (error) {
      console.error('Upload error:', error);
      if (fileItem.retryCount < MAX_RETRY_COUNT) {
        fileItem.retryCount++;
        this.message.info(`${fileItem.name} 正在重试 (${fileItem.retryCount}/${MAX_RETRY_COUNT})`);
        return this.uploadSingleFile(index);
      } else {
        fileItem.status = 'error';
        this.message.error(`${fileItem.name} 处理失败`);
        return false;
      }
    }
  }

  private renameWithFormat(originalName: string): string {
    if (this.targetFormat === 'original') return originalName;
    const nameWithoutExt = originalName.replace(/\.[^/.]+$/, '');
    return `${nameWithoutExt}.${this.targetFormat}`;
  }

  private async processQueue(): Promise<void> {
    while (this.uploadQueue.length > 0 && this.activeUploads < MAX_CONCURRENT_UPLOADS) {
      const index = this.uploadQueue.shift()!;
      this.activeUploads++;
      
      this.uploadSingleFile(index).finally(() => {
        this.activeUploads--;
        this.processQueue();
        this.checkBatchComplete();
      });
    }
  }

  private checkBatchComplete(): void {
    const pendingOrUploading = this.files.filter(f => 
      f.status === 'pending' || f.status === 'uploading'
    );
    const successCount = this.files.filter(f => f.status === 'success').length;
    
    this.uploadAllProgress = Math.round((successCount / this.files.length) * 100);
    
    if (pendingOrUploading.length === 0 && this.isBatchUploading) {
      this.isBatchUploading = false;
      const failCount = this.files.filter(f => f.status === 'error').length;
      
      // 计算总压缩率
      const totalOriginalSize = this.files.reduce((sum, f) => sum + f.file.size, 0);
      const totalProcessedSize = this.files.reduce((sum, f) => sum + f.file.size, 0);
      const totalCompression = ((1 - totalProcessedSize / totalOriginalSize) * 100).toFixed(1);

      if (failCount > 0) {
        this.message.warning(`批量处理完成: 成功 ${successCount} 个, 失败 ${failCount} 个`);
      } else {
        this.message.success(`✅ 批量处理完成! 共 ${successCount} 张图片, 平均压缩 ${totalCompression}%`);
      }

      // 清理内存
      this.vipsService.collectGarbage();
    }
  }

  async uploadFile(index: number): Promise<void> {
    const fileItem = this.files[index];
    fileItem.retryCount = 0;
    await this.uploadSingleFile(index);
  }

  async uploadAll(): Promise<void> {
    if (!this.vipsReady) {
      this.message.warning('WASM 引擎正在加载，使用 Canvas 模式处理...');
    }

    const pendingFiles = this.files.filter(f => f.status === 'pending' || f.status === 'error');
    
    if (pendingFiles.length === 0) {
      this.message.info('没有需要处理的文件');
      return;
    }

    this.isBatchUploading = true;
    this.uploadQueue = pendingFiles.map(f => this.files.indexOf(f));
    
    // 启动并发处理
    for (let i = 0; i < Math.min(MAX_CONCURRENT_UPLOADS, this.uploadQueue.length); i++) {
      this.processQueue();
    }
  }

  // 快速格式转换
  async quickConvert(format: 'jpeg' | 'webp' | 'avif'): Promise<void> {
    if (this.files.length === 0) return;
    
    this.targetFormat = format;
    this.message.info(`将转换为 ${format.toUpperCase()} 格式`);
    await this.uploadAll();
  }

  // 打开编辑器
  openEditor(index: number): void {
    const fileItem = this.files[index];
    const modalRef = this.modal.create({
      nzTitle: '图片编辑器',
      nzContent: ImageEditorComponent,
      nzData: {
        imageUrl: fileItem.preview,
        fileName: fileItem.name,
        useVips: this.vipsReady
      },
      nzWidth: '90vw',
      nzFooter: null
    });

    modalRef.afterClose.subscribe(result => {
      if (result) {
        // 应用编辑结果
        console.log('Edited result:', result);
      }
    });
  }

  // 运行性能基准测试
  async runBenchmark(index: number): Promise<void> {
    if (!this.vipsReady) {
      this.message.error('WASM 引擎未就绪，无法进行基准测试');
      return;
    }

    const fileItem = this.files[index];
    this.message.loading('正在运行性能基准测试...', { nzDuration: 0 });

    try {
      const result = await this.vipsService.benchmark(fileItem.file);
      this.message.remove();
      
      this.modal.info({
        nzTitle: '📊 性能基准测试结果',
        nzContent: `
          <div style="padding: 16px 0;">
            <p><strong>Canvas API:</strong> ${result.canvas.time.toFixed(1)}ms, ${(result.canvas.size/1024).toFixed(1)}KB</p>
            <p><strong>libvips WASM:</strong> ${result.vips.time.toFixed(1)}ms, ${(result.vips.size/1024).toFixed(1)}KB</p>
            <p style="color: #52c41a; font-weight: 600; font-size: 18px; margin-top: 16px;">
              ⚡ 性能提升: ${result.improvement.toFixed(1)}x
            </p>
          </div>
        `,
        nzOkText: '确定'
      });
    } catch (error) {
      this.message.remove();
      this.message.error('基准测试失败');
    }
  }
}
