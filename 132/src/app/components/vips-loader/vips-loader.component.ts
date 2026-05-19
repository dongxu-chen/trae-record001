import { Component, OnInit } from '@angular/core';
import { VipsImageService } from '../../services/vips-image.service';

@Component({
  selector: 'app-vips-loader',
  template: `
    <div *ngIf="isLoading" class="vips-loader-overlay">
      <div class="vips-loader-content">
        <div class="loader-icon">
          <nz-spin nzSimple [nzSize]="'large'"></nz-spin>
        </div>
        <h3>正在加载高性能图片引擎...</h3>
        <p>libvips WebAssembly 初始化中</p>
        <nz-progress 
          [nzPercent]="progress" 
          [nzStatus]="'active'"
          nzStrokeColor="#1890ff"
          style="width: 300px; margin-top: 16px;"
        ></nz-progress>
        <div class="feature-list">
          <div class="feature-item">
            <span nz-icon nzType="thunderbolt" nzTheme="outline"></span>
            10x+ 性能提升
          </div>
          <div class="feature-item">
            <span nz-icon nzType="file-done" nzTheme="outline"></span>
            支持 PSD/SVG/HEIC
          </div>
          <div class="feature-item">
            <span nz-icon nzType="laptop" nzTheme="outline"></span>
            纯客户端处理
          </div>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./vips-loader.component.scss']
})
export class VipsLoaderComponent implements OnInit {
  isLoading = false;
  progress = 0;

  constructor(private vipsService: VipsImageService) {}

  ngOnInit(): void {
    this.vipsService.isLoading.subscribe(loading => {
      this.isLoading = loading;
    });

    this.vipsService.loadProgress.subscribe(progress => {
      this.progress = progress;
    });
  }
}
