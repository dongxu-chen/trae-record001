import { Component, OnInit } from '@angular/core';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { ImageService, ImageItem, ImageTags } from '../../services/image.service';
import { ImageEditorComponent } from '../image-editor/image-editor.component';
import { SmartImageService, ImageAnalysis } from '../../services/smart-image.service';

@Component({
  selector: 'app-image-list',
  templateUrl: './image-list.component.html',
  styleUrls: ['./image-list.component.scss']
})
export class ImageListComponent implements OnInit {
  images: ImageItem[] = [];
  viewMode: 'grid' | 'list' = 'grid';
  searchText = '';
  sortField = 'createdAt';
  sortOrder = 'descend';
  showNsfwOnly = false;
  isAnalyzing = false;

  constructor(
    private imageService: ImageService,
    private modal: NzModalService,
    private message: NzMessageService,
    private smartImageService: SmartImageService
  ) { }

  ngOnInit(): void {
    this.imageService.images$.subscribe(images => {
      this.images = images;
    });
  }

  get filteredImages(): ImageItem[] {
    let result = [...this.images];

    if (this.showNsfwOnly) {
      result = result.filter(img => img.analysis?.isNsfw);
    }

    if (this.searchText) {
      const search = this.searchText.toLowerCase();
      result = result.filter(img =>
        img.name.toLowerCase().includes(search) ||
        img.format.toLowerCase().includes(search) ||
        img.analysis?.description?.toLowerCase().includes(search)
      );
    }

    result.sort((a, b) => {
      let comparison = 0;
      switch (this.sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'size':
          comparison = a.size - b.size;
          break;
        case 'nsfw':
          comparison = (a.analysis?.nsfwScore || 0) - (b.analysis?.nsfwScore || 0);
          break;
        case 'createdAt':
          comparison = a.createdAt.getTime() - b.createdAt.getTime();
          break;
        default:
          comparison = 0;
      }
      return this.sortOrder === 'ascend' ? comparison : -comparison;
    });

    return result;
  }

  async analyzeAllImages(): Promise<void> {
    this.isAnalyzing = true;
    this.message.loading('正在批量分析图片...', { nzDuration: 0 });

    let analyzedCount = 0;
    for (const image of this.images) {
      if (!image.analysis) {
        try {
          const analysis = await this.smartImageService.analyzeImage(image.url);
          this.imageService.updateImage(image.id, {
            analysis: {
              isNsfw: analysis.nsfw.isNsfw,
              nsfwScore: analysis.nsfw.score,
              hasFace: analysis.faces.length > 0,
              faceCount: analysis.faces.length,
              description: analysis.ocr.text,
              ocrText: analysis.ocr.lines.join(' '),
              categories: []
            }
          });
          analyzedCount++;
        } catch (error) {
          console.error('分析失败:', image.name);
        }
      }
    }

    this.message.remove();
    this.isAnalyzing = false;
    this.message.success(`批量分析完成，共分析 ${analyzedCount} 张图片`);
  }

  getNsfwLabel(score: number): { text: string; color: string } {
    if (score > 0.7) return { text: '高风险', color: 'red' };
    if (score > 0.4) return { text: '中风险', color: 'orange' };
    if (score > 0.2) return { text: '低风险', color: 'gold' };
    return { text: '安全', color: 'green' };
  }

  formatSize(bytes: number): string {
    return this.imageService.formatFileSize(bytes);
  }

  formatDate(date: Date): string {
    return new Date(date).toLocaleString('zh-CN');
  }

  openEditor(image: ImageItem): void {
    const modal = this.modal.create({
      nzTitle: '编辑图片',
      nzContent: ImageEditorComponent,
      nzWidth: '90%',
      nzStyle: { top: '20px' },
      nzData: {
        imageUrl: image.url,
        fileName: image.name
      },
      nzFooter: null
    });

    modal.afterClose.subscribe((result) => {
      if (result) {
        this.imageService.updateImage(image.id, {
          url: result.url,
          thumbnail: result.url,
          width: result.width,
          height: result.height,
          updatedAt: new Date()
        });
        this.message.success('图片更新成功');
      }
    });
  }

  deleteImage(image: ImageItem): void {
    this.modal.confirm({
      nzTitle: '确认删除',
      nzContent: `确定要删除图片 "${image.name}" 吗？此操作不可撤销。`,
      nzOkText: '删除',
      nzOkType: 'primary',
      nzOkDanger: true,
      nzCancelText: '取消',
      nzOnOk: () => {
        this.imageService.deleteImage(image.id);
        this.message.success('图片已删除');
      }
    });
  }

  copyUrl(image: ImageItem): void {
    navigator.clipboard.writeText(image.url).then(() => {
      this.message.success('图片链接已复制到剪贴板');
    }).catch(() => {
      this.message.error('复制失败');
    });
  }

  downloadImage(image: ImageItem): void {
    const link = document.createElement('a');
    link.href = image.url;
    link.download = image.name;
    link.click();
    this.message.success('开始下载图片');
  }

  previewImage(image: ImageItem): void {
    this.modal.create({
      nzTitle: image.name,
      nzContent: `<img src="${image.url}" style="max-width: 100%; max-height: 80vh;">`,
      nzWidth: 'auto',
      nzFooter: null
    });
  }
}
