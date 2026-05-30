import { IconConfig, RenderContext } from './types';
import { renderOutline } from './styles/outline';
import { renderFilled } from './styles/filled';
import { renderGradient } from './styles/gradient';
import { render3D } from './styles/threeD';

export class IconGenerator {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;

  constructor(canvas?: HTMLCanvasElement) {
    if (canvas) {
      this.setCanvas(canvas);
    }
  }

  setCanvas(canvas: HTMLCanvasElement): void {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
  }

  generate(config: IconConfig): void {
    if (!this.canvas || !this.ctx) return;

    this.canvas.width = config.size;
    this.canvas.height = config.size;

    const context: RenderContext = {
      ctx: this.ctx,
      config,
      width: config.size,
      height: config.size,
    };

    switch (config.style) {
      case 'outline':
        renderOutline(context);
        break;
      case 'filled':
        renderFilled(context);
        break;
      case 'gradient':
        renderGradient(context);
        break;
      case '3d':
        render3D(context);
        break;
      default:
        renderFilled(context);
    }
  }

  toDataUrl(type: 'png' | 'jpeg' = 'png', quality: number = 1): string {
    if (!this.canvas) return '';
    return this.canvas.toDataURL(type === 'png' ? 'image/png' : 'image/jpeg', quality);
  }

  toSvg(config: IconConfig): string {
    const size = config.size;
    return `
      <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <foreignObject width="100%" height="100%">
          <div xmlns="http://www.w3.org/1999/xhtml" style="width:${size}px;height:${size}px;">
            <img src="${this.toDataUrl('png')}" width="${size}" height="${size}" style="display:block;"/>
          </div>
        </foreignObject>
      </svg>
    `.trim();
  }

  static generateFromConfig(config: IconConfig): string {
    const canvas = document.createElement('canvas');
    const generator = new IconGenerator(canvas);
    generator.generate(config);
    return generator.toDataUrl();
  }

  static generateBatch(configs: IconConfig[]): Promise<{ config: IconConfig; dataUrl: string }[]> {
    return Promise.resolve(
      configs.map((config) => ({
        config,
        dataUrl: IconGenerator.generateFromConfig(config),
      }))
    );
  }
}
