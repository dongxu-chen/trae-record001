import { BackgroundEffect } from '../store/types';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  life: number;
  maxLife: number;
}

interface MatrixChar {
  x: number;
  y: number;
  speed: number;
  char: string;
  opacity: number;
}

interface Star {
  x: number;
  y: number;
  size: number;
  baseAlpha: number;
  twinkleSpeed: number;
  twinkleOffset: number;
}

export class BackgroundEffectEngine {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private width: number = 0;
  private height: number = 0;
  private effect: BackgroundEffect = 'none';
  private effectColor: string = '#00ff88';
  private effectIntensity: number = 50;
  private particles: Particle[] = [];
  private matrixChars: MatrixChar[] = [];
  private stars: Star[] = [];
  private time: number = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not get 2D context');
    this.ctx = ctx;
  }

  resize(width?: number, height?: number) {
    if (width !== undefined && height !== undefined) {
      this.width = width;
      this.height = height;
    } else {
      const rect = this.canvas.getBoundingClientRect();
      this.width = rect.width;
      this.height = rect.height;
    }
    this.initEffect();
  }

  setEffect(effect: BackgroundEffect) {
    this.effect = effect;
    this.initEffect();
  }

  setEffectColor(color: string) {
    this.effectColor = color;
  }

  setEffectIntensity(intensity: number) {
    this.effectIntensity = intensity;
    this.initEffect();
  }

  private initEffect() {
    if (this.width === 0 || this.height === 0) return;

    switch (this.effect) {
      case 'particles':
        this.initParticles();
        break;
      case 'matrix':
        this.initMatrix();
        break;
      case 'starfield':
        this.initStarfield();
        break;
    }
  }

  private initParticles() {
    const count = Math.floor((this.effectIntensity / 100) * 80) + 20;
    this.particles = Array.from({ length: count }, () => ({
      x: Math.random() * this.width,
      y: Math.random() * this.height,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      size: Math.random() * 3 + 1,
      alpha: Math.random() * 0.5 + 0.2,
      life: 1,
      maxLife: Math.random() * 100 + 50
    }));
  }

  private initMatrix() {
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    const columnCount = Math.floor((this.effectIntensity / 100) * 40) + 10;
    const columnWidth = this.width / columnCount;
    
    this.matrixChars = Array.from({ length: columnCount }, (_, i) => ({
      x: i * columnWidth + columnWidth / 2,
      y: Math.random() * -this.height,
      speed: Math.random() * 3 + 1,
      char: chars[Math.floor(Math.random() * chars.length)],
      opacity: 1
    }));
  }

  private initStarfield() {
    const count = Math.floor((this.effectIntensity / 100) * 150) + 50;
    this.stars = Array.from({ length: count }, () => ({
      x: Math.random() * this.width,
      y: Math.random() * this.height,
      size: Math.random() * 2 + 0.5,
      baseAlpha: Math.random() * 0.5 + 0.3,
      twinkleSpeed: Math.random() * 0.02 + 0.01,
      twinkleOffset: Math.random() * Math.PI * 2
    }));
  }

  incrementTime() {
    this.time++;
  }

  render() {
    if (this.effect === 'none') return;

    this.incrementTime();

    switch (this.effect) {
      case 'particles':
        this.renderParticles();
        break;
      case 'matrix':
        this.renderMatrix();
        break;
      case 'neon-glow':
        this.renderNeonGlow();
        break;
      case 'starfield':
        this.renderStarfield();
        break;
    }
  }

  private renderParticles() {
    this.particles.forEach((particle, index) => {
      particle.x += particle.vx;
      particle.y += particle.vy;
      particle.life--;

      if (particle.life <= 0 || particle.x < 0 || particle.x > this.width || particle.y < 0 || particle.y > this.height) {
        this.particles[index] = {
          x: Math.random() * this.width,
          y: Math.random() * this.height,
          vx: (Math.random() - 0.5) * 2,
          vy: (Math.random() - 0.5) * 2,
          size: Math.random() * 3 + 1,
          alpha: Math.random() * 0.5 + 0.2,
          life: 1,
          maxLife: Math.random() * 100 + 50
        };
        return;
      }

      const alpha = (particle.life / particle.maxLife) * particle.alpha;
      
      this.ctx.beginPath();
      this.ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      this.ctx.fillStyle = this.hexToRgba(this.effectColor, alpha);
      this.ctx.fill();

      this.ctx.beginPath();
      this.ctx.arc(particle.x, particle.y, particle.size * 2, 0, Math.PI * 2);
      this.ctx.fillStyle = this.hexToRgba(this.effectColor, alpha * 0.3);
      this.ctx.fill();
    });
  }

  private renderMatrix() {
    const fontSize = 16;
    this.ctx.font = `${fontSize}px monospace`;
    this.ctx.textAlign = 'center';

    this.matrixChars.forEach((char, index) => {
      char.y += char.speed;

      if (Math.random() < 0.05) {
        const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
        char.char = chars[Math.floor(Math.random() * chars.length)];
      }

      if (char.y > this.height + fontSize) {
        char.y = -fontSize;
        char.speed = Math.random() * 3 + 1;
      }

      const distanceFromBottom = this.height - char.y;
      const opacity = Math.min(1, distanceFromBottom / (this.height * 0.3));

      this.ctx.fillStyle = this.hexToRgba(this.effectColor, opacity * 0.8);
      this.ctx.fillText(char.char, char.x, char.y);

      if (Math.random() < 0.1) {
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillText(char.char, char.x, char.y);
      }
    });
  }

  private renderNeonGlow() {
    const centerX = this.width / 2;
    const centerY = this.height / 2;
    const maxRadius = Math.max(this.width, this.height) * 0.6;

    for (let i = 5; i > 0; i--) {
      const radius = (maxRadius / 5) * i + Math.sin(this.time * 0.02 + i) * 20;
      const gradient = this.ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
      gradient.addColorStop(0, this.hexToRgba(this.effectColor, 0.1));
      gradient.addColorStop(0.5, this.hexToRgba(this.effectColor, 0.05));
      gradient.addColorStop(1, 'transparent');

      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(0, 0, this.width, this.height);
    }

    const bars = 5;
    for (let i = 0; i < bars; i++) {
      const y = (this.height / (bars + 1)) * (i + 1) + Math.sin(this.time * 0.03 + i * 2) * 10;
      const gradient = this.ctx.createLinearGradient(0, y, this.width, y);
      gradient.addColorStop(0, 'transparent');
      gradient.addColorStop(0.5, this.hexToRgba(this.effectColor, 0.15));
      gradient.addColorStop(1, 'transparent');

      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(0, y - 2, this.width, 4);
    }
  }

  private renderStarfield() {
    this.stars.forEach((star) => {
      const twinkle = Math.sin(this.time * star.twinkleSpeed + star.twinkleOffset);
      const alpha = star.baseAlpha + twinkle * 0.3;

      this.ctx.beginPath();
      this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
      this.ctx.fillStyle = this.hexToRgba(this.effectColor, Math.max(0, alpha));
      this.ctx.fill();

      if (twinkle > 0.5) {
        this.ctx.beginPath();
        this.ctx.arc(star.x, star.y, star.size * 2, 0, Math.PI * 2);
        this.ctx.fillStyle = this.hexToRgba(this.effectColor, Math.max(0, alpha * 0.3));
        this.ctx.fill();
      }
    });
  }

  private hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
}
