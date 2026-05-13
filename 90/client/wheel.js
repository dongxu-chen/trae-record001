class LotteryWheel {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: false });
    this.centerX = this.canvas.width / 2;
    this.centerY = this.canvas.height / 2;
    this.radius = Math.min(this.centerX, this.centerY) - 20;
    this.prizes = options.prizes || [];
    this.currentRotation = 0;
    this.isSpinning = false;
    this.textFont = options.textFont || 'bold 14px Arial';
    this.textColor = options.textColor || '#333';
    this.onComplete = options.onComplete || null;
    this.wheelCanvas = null;
    this.wheelCtx = null;
    this.pointerCanvas = null;
    this.pointerCtx = null;
    this.lastFrameTime = 0;
    this.frameInterval = 1000 / 60;

    if (this.prizes.length > 0) {
      this.cacheWheel();
      this.cachePointer();
    }
  }

  setPrizes(prizes) {
    this.prizes = prizes;
    this.cacheWheel();
    this.draw();
  }

  cacheWheel() {
    this.wheelCanvas = document.createElement('canvas');
    this.wheelCanvas.width = this.radius * 2;
    this.wheelCanvas.height = this.radius * 2;
    this.wheelCtx = this.wheelCanvas.getContext('2d', { willReadFrequently: false });

    const sliceAngle = (2 * Math.PI) / this.prizes.length;
    const cx = this.radius;
    const cy = this.radius;

    this.wheelCtx.clearRect(0, 0, this.wheelCanvas.width, this.wheelCanvas.height);

    this.prizes.forEach((prize, index) => {
      const startAngle = index * sliceAngle - Math.PI / 2;
      const endAngle = startAngle + sliceAngle;

      this.wheelCtx.beginPath();
      this.wheelCtx.moveTo(cx, cy);
      this.wheelCtx.arc(cx, cy, this.radius, startAngle, endAngle);
      this.wheelCtx.closePath();
      this.wheelCtx.fillStyle = prize.color;
      this.wheelCtx.fill();
      this.wheelCtx.strokeStyle = '#fff';
      this.wheelCtx.lineWidth = 2;
      this.wheelCtx.stroke();

      const textAngle = startAngle + sliceAngle / 2;
      const textRadius = this.radius * 0.65;
      const textX = cx + Math.cos(textAngle) * textRadius;
      const textY = cy + Math.sin(textAngle) * textRadius;

      this.wheelCtx.save();
      this.wheelCtx.translate(textX, textY);
      this.wheelCtx.rotate(textAngle + Math.PI / 2);
      this.wheelCtx.fillStyle = this.textColor;
      this.wheelCtx.font = this.textFont;
      this.wheelCtx.textAlign = 'center';
      this.wheelCtx.textBaseline = 'middle';
      this.wheelCtx.fillText(prize.name, 0, 0);
      this.wheelCtx.restore();
    });
  }

  cachePointer() {
    this.pointerCanvas = document.createElement('canvas');
    this.pointerCanvas.width = this.canvas.width;
    this.pointerCanvas.height = this.canvas.height;
    this.pointerCtx = this.pointerCanvas.getContext('2d', { willReadFrequently: false });

    const pointerLength = 30;
    const pointerWidth = 15;

    this.pointerCtx.save();
    this.pointerCtx.translate(this.centerX, this.centerY);

    this.pointerCtx.beginPath();
    this.pointerCtx.moveTo(0, -this.radius - pointerLength);
    this.pointerCtx.lineTo(-pointerWidth / 2, -this.radius + 10);
    this.pointerCtx.lineTo(pointerWidth / 2, -this.radius + 10);
    this.pointerCtx.closePath();
    this.pointerCtx.fillStyle = '#E74C3C';
    this.pointerCtx.fill();
    this.pointerCtx.strokeStyle = '#C0392B';
    this.pointerCtx.lineWidth = 2;
    this.pointerCtx.stroke();

    this.pointerCtx.beginPath();
    this.pointerCtx.arc(0, 0, 25, 0, 2 * Math.PI);
    this.pointerCtx.fillStyle = '#fff';
    this.pointerCtx.fill();
    this.pointerCtx.strokeStyle = '#E74C3C';
    this.pointerCtx.lineWidth = 3;
    this.pointerCtx.stroke();

    this.pointerCtx.fillStyle = '#E74C3C';
    this.pointerCtx.font = 'bold 16px Arial';
    this.pointerCtx.textAlign = 'center';
    this.pointerCtx.textBaseline = 'middle';
    this.pointerCtx.fillText('GO', 0, 0);

    this.pointerCtx.restore();
  }

  draw() {
    if (!this.wheelCanvas) {
      this.cacheWheel();
    }
    if (!this.pointerCanvas) {
      this.cachePointer();
    }

    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    ctx.save();
    ctx.translate(this.centerX, this.centerY);
    ctx.rotate(this.currentRotation);
    ctx.drawImage(this.wheelCanvas, -this.radius, -this.radius);
    ctx.restore();

    ctx.drawImage(this.pointerCanvas, 0, 0);
  }

  spin(targetIndex, callback) {
    if (this.isSpinning) return;
    this.isSpinning = true;

    const sliceAngle = (2 * Math.PI) / this.prizes.length;
    const fullRotations = 5;
    const targetAngle = fullRotations * 2 * Math.PI + (sliceAngle * targetIndex) - (sliceAngle / 2);

    const startAngle = this.currentRotation;
    const finalAngle = startAngle + targetAngle;
    const duration = 4000;
    const startTime = performance.now();

    const animate = (currentTime) => {
      if (!this.isSpinning) return;

      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const easeOutCubic = 1 - Math.pow(1 - progress, 3);
      this.currentRotation = startAngle + (finalAngle - startAngle) * easeOutCubic;
      this.draw();

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        this.isSpinning = false;
        if (callback) callback();
      }
    };

    requestAnimationFrame(animate);
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LotteryWheel;
}
