import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface ImageTags {
  isNsfw: boolean;
  nsfwScore: number;
  hasFace: boolean;
  faceCount: number;
  description: string;
  ocrText: string;
  categories: string[];
}

export interface ImageItem {
  id: string;
  name: string;
  originalName: string;
  url: string;
  thumbnail: string;
  size: number;
  width: number;
  height: number;
  format: string;
  createdAt: Date;
  updatedAt: Date;
  analysis?: ImageTags;
}

export interface WatermarkConfig {
  text: string;
  fontSize: number;
  color: string;
  opacity: number;
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
}

export interface CropConfig {
  x: number;
  y: number;
  width: number;
  height: number;
}

@Injectable({
  providedIn: 'root'
})
export class ImageService {
  private imagesSubject = new BehaviorSubject<ImageItem[]>([]);
  images$ = this.imagesSubject.asObservable();

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    const saved = localStorage.getItem('cdn_images');
    if (saved) {
      const images = JSON.parse(saved).map((img: any) => ({
        ...img,
        createdAt: new Date(img.createdAt),
        updatedAt: new Date(img.updatedAt)
      }));
      this.imagesSubject.next(images);
    }
  }

  private saveToStorage(images: ImageItem[]): void {
    localStorage.setItem('cdn_images', JSON.stringify(images));
  }

  addImage(image: ImageItem): void {
    const images = [...this.imagesSubject.value, image];
    this.imagesSubject.next(images);
    this.saveToStorage(images);
  }

  updateImage(id: string, updates: Partial<ImageItem>): void {
    const images = this.imagesSubject.value.map(img =>
      img.id === id ? { ...img, ...updates, updatedAt: new Date() } : img
    );
    this.imagesSubject.next(images);
    this.saveToStorage(images);
  }

  deleteImage(id: string): void {
    const images = this.imagesSubject.value.filter(img => img.id !== id);
    this.imagesSubject.next(images);
    this.saveToStorage(images);
  }

  getImage(id: string): ImageItem | undefined {
    return this.imagesSubject.value.find(img => img.id === id);
  }

  generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
