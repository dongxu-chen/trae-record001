class SparseGrid {
  constructor(width, height, cellSize) {
    this.cellSize = cellSize;
    this.cols = Math.ceil(width / cellSize);
    this.rows = Math.ceil(height / cellSize);
    this.grid = new Array(this.cols * this.rows).fill(null).map(() => []);
  }

  _key(col, row) {
    return row * this.cols + col;
  }

  _getCells(x, y, w, h) {
    const minCol = Math.max(0, Math.floor(x / this.cellSize));
    const maxCol = Math.min(this.cols - 1, Math.floor((x + w) / this.cellSize));
    const minRow = Math.max(0, Math.floor(y / this.cellSize));
    const maxRow = Math.min(this.rows - 1, Math.floor((y + h) / this.cellSize));
    return { minCol, maxCol, minRow, maxRow };
  }

  insert(rect) {
    const { minCol, maxCol, minRow, maxRow } = this._getCells(rect.x, rect.y, rect.width, rect.height);
    for (let row = minRow; row <= maxRow; row++) {
      for (let col = minCol; col <= maxCol; col++) {
        this.grid[this._key(col, row)].push(rect);
      }
    }
  }

  collides(rect) {
    const { minCol, maxCol, minRow, maxRow } = this._getCells(rect.x, rect.y, rect.width, rect.height);
    const checked = new Set();

    for (let row = minRow; row <= maxRow; row++) {
      for (let col = minCol; col <= maxCol; col++) {
        const cell = this.grid[this._key(col, row)];
        for (const placed of cell) {
          if (checked.has(placed)) continue;
          checked.add(placed);

          if (
            rect.x < placed.x + placed.width &&
            rect.x + rect.width > placed.x &&
            rect.y < placed.y + placed.height &&
            rect.y + rect.height > placed.y
          ) {
            return true;
          }
        }
      }
    }
    return false;
  }

  clear() {
    this.grid.fill(null).forEach((_, i) => { this.grid[i] = []; });
  }
}

class ShapeMask {
  constructor(shape, width, height) {
    this.shape = shape;
    this.width = width;
    this.height = height;
    this.centerX = width / 2;
    this.centerY = height / 2;
    this.mask = null;
    this.build();
  }

  build() {
    this.mask = new Uint8Array(this.width * this.height);
    const cx = this.centerX;
    const cy = this.centerY;
    const rx = this.width * 0.45;
    const ry = this.height * 0.45;

    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < this.width; x++) {
        const nx = (x - cx) / rx;
        const ny = (y - cy) / ry;
        let inside = false;

        switch (this.shape) {
          case 'circle':
            inside = nx * nx + ny * ny <= 1;
            break;
          case 'square':
            inside = Math.abs(nx) <= 1 && Math.abs(ny) <= 1;
            break;
          case 'heart': {
            const hx = nx * 1.2;
            const hy = -ny * 1.2 - 0.3;
            inside = Math.pow(hx * hx + hy * hy - 1, 3) - hx * hx * hy * hy * hy <= 0;
            break;
          }
        }

        this.mask[y * this.width + x] = inside ? 1 : 0;
      }
    }
  }

  isInside(x, y, w, h) {
    const padding = 2;
    const checkPoints = [
      [x + padding, y + padding],
      [x + w - padding, y + padding],
      [x + padding, y + h - padding],
      [x + w - padding, y + h - padding],
      [x + w / 2, y + h / 2]
    ];

    for (const [px, py] of checkPoints) {
      const ix = Math.floor(px);
      const iy = Math.floor(py);
      if (ix < 0 || ix >= this.width || iy < 0 || iy >= this.height) return false;
      if (this.mask[iy * this.width + ix] === 0) return false;
    }
    return true;
  }
}

class WordCloud {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.options = {
      width: options.width || 800,
      height: options.height || 600,
      fontFamily: options.fontFamily || 'Microsoft YaHei, Arial',
      minFontSize: options.minFontSize || 12,
      maxFontSize: options.maxFontSize || 80,
      colorScheme: options.colorScheme || 'vibrant',
      shape: options.shape || 'circle',
      backgroundColor: options.backgroundColor || '#ffffff',
      gridSize: options.gridSize || 10,
      sentimentMode: options.sentimentMode || false,
      animationProgress: options.animationProgress ?? 1.0
    };

    this.sparseGrid = null;
    this.shapeMask = null;
    this.placedWords = [];
    this.lastWordsData = null;

    this.initCanvas();
  }

  initCanvas() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = this.options.width * dpr;
    this.canvas.height = this.options.height * dpr;
    this.canvas.style.width = this.options.width + 'px';
    this.canvas.style.height = this.options.height + 'px';
    this.ctx.scale(dpr, dpr);
  }

  getColor(index, sentiment = 'neutral') {
    if (this.options.sentimentMode) {
      switch (sentiment) {
        case 'positive': return ['#22C55E', '#10B981', '#14B8A6', '#06B6D4'][index % 4];
        case 'negative': return ['#EF4444', '#F97316', '#F43F5E', '#DC2626'][index % 4];
        default: return ['#6B7280', '#9CA3AF', '#71717A', '#78716C'][index % 4];
      }
    }

    const schemes = {
      vibrant: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'],
      warm: ['#FF6B6B', '#FFA07A', '#FFD93D', '#FF8C42', '#FF6F61', '#E74C3C', '#F39C12', '#E67E22'],
      cool: ['#3498DB', '#2ECC71', '#1ABC9C', '#34495E', '#9B59B6', '#2980B9', '#27AE60', '#16A085'],
      pastel: ['#FFB3BA', '#BAFFC9', '#BAE1FF', '#FFFFBA', '#FFD1DC', '#E6E6FA', '#F0E68C', '#98FB98'],
      monochrome: ['#2C3E50', '#34495E', '#5D6D7E', '#7F8C8D', '#95A5A6', '#ABB2B9', '#BDC3C7', '#D5D8DC']
    };
    const colors = schemes[this.options.colorScheme] || schemes.vibrant;
    return colors[index % colors.length];
  }

  measureText(word, fontSize) {
    this.ctx.font = `${fontSize}px "${this.options.fontFamily}"`;
    const metrics = this.ctx.measureText(word);
    return {
      width: metrics.width + 4,
      height: fontSize + 4,
      ascent: metrics.actualBoundingBoxAscent || fontSize * 0.8
    };
  }

  findPosition(wordData, centerX, centerY, maxRadius) {
    const angleStep = 0.3;
    const radiusStep = this.options.gridSize;

    for (let radius = 0; radius < maxRadius; radius += radiusStep) {
      for (let angle = 0; angle < Math.PI * 2; angle += angleStep) {
        const x = Math.round(centerX + radius * Math.cos(angle) - wordData.width / 2);
        const y = Math.round(centerY + radius * Math.sin(angle) - wordData.height / 2);

        const rect = { x, y, width: wordData.width, height: wordData.height };

        if (this.shapeMask && !this.shapeMask.isInside(x, y, wordData.width, wordData.height)) {
          continue;
        }

        if (!this.sparseGrid.collides(rect)) {
          return rect;
        }
      }
    }
    return null;
  }

  interpolateWords(currentWords, targetWords, progress) {
    if (progress >= 1) return targetWords;
    if (progress <= 0 || !this.lastWordsData || this.lastWordsData.length === 0) {
      return targetWords.map(w => ({ ...w, count: w.count * progress }));
    }

    const currentMap = new Map(this.lastWordsData.map(w => [w.word, w.count]));
    const targetMap = new Map(targetWords.map(w => [w.word, w]));
    const allWords = new Set([...currentMap.keys(), ...targetMap.keys()]);

    const result = [];
    allWords.forEach(word => {
      const currentCount = currentMap.get(word) || 0;
      const target = targetMap.get(word);
      const targetCount = target?.count || 0;
      const lerpedCount = currentCount + (targetCount - currentCount) * progress;

      if (lerpedCount > 0.5) {
        result.push({
          word,
          count: Math.max(1, Math.round(lerpedCount)),
          sentiment: target?.sentiment || 'neutral'
        });
      }
    });

    return result.sort((a, b) => b.count - a.count);
  }

  render(words) {
    const { width, height } = this.options;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(width, height) / 2 - 10;
    const progress = this.options.animationProgress ?? 1.0;

    const displayWords = this.interpolateWords(this.lastWordsData || [], words, progress);
    this.lastWordsData = [...words];

    this.ctx.fillStyle = this.options.backgroundColor;
    this.ctx.fillRect(0, 0, width, height);

    if (!displayWords || displayWords.length === 0) return;

    this.sparseGrid = new SparseGrid(width, height, this.options.gridSize);
    this.shapeMask = new ShapeMask(this.options.shape, width, height);
    this.placedWords = [];

    const maxCount = Math.max(...displayWords.map(w => w.count));
    const minCount = Math.min(...displayWords.map(w => w.count));
    const sortedWords = [...displayWords].sort((a, b) => b.count - a.count);

    const t0 = performance.now();
    let placedCount = 0;

    for (let i = 0; i < sortedWords.length; i++) {
      const word = sortedWords[i];
      const normalizedCount = maxCount === minCount
        ? 0.5
        : (word.count - minCount) / (maxCount - minCount);

      const fontSize = Math.floor(
        this.options.minFontSize +
        normalizedCount * (this.options.maxFontSize - this.options.minFontSize)
      );

      const textMetrics = this.measureText(word.word, fontSize);

      const wordData = {
        text: word.word,
        fontSize,
        width: textMetrics.width,
        height: textMetrics.height,
        color: this.getColor(i, word.sentiment || 'neutral')
      };

      const position = this.findPosition(wordData, centerX, centerY, maxRadius);

      if (position) {
        this.ctx.save();
        this.ctx.font = `${fontSize}px "${this.options.fontFamily}"`;
        this.ctx.fillStyle = wordData.color;
        this.ctx.textBaseline = 'top';
        this.ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
        this.ctx.shadowBlur = 2;
        this.ctx.shadowOffsetX = 1;
        this.ctx.shadowOffsetY = 1;
        this.ctx.fillText(word.word, position.x + 2, position.y + 2);
        this.ctx.restore();

        const placed = {
          x: position.x, y: position.y,
          width: textMetrics.width, height: textMetrics.height,
          word: word.word, fontSize, color: wordData.color
        };
        this.sparseGrid.insert(placed);
        this.placedWords.push(placed);
        placedCount++;
      }
    }

    const elapsed = (performance.now() - t0).toFixed(1);
    console.log(`[WordCloud] placed ${placedCount}/${sortedWords.length} in ${elapsed}ms (shape=${this.options.shape}, sentiment=${this.options.sentimentMode})`);

    return { placedCount, elapsed };
  }

  toSVG() {
    const { width, height, fontFamily, backgroundColor } = this.options;
    const dpr = window.devicePixelRatio || 1;
    const svgWidth = width;
    const svgHeight = height;

    let svgContent = '';
    svgContent += `<?xml version="1.0" encoding="UTF-8"?>\n`;
    svgContent += `<svg xmlns="http://www.w3.org/2000/svg" width="${svgWidth}" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}">\n`;
    svgContent += `  <rect width="100%" height="100%" fill="${backgroundColor}"/>\n`;
    svgContent += `  <g font-family="${fontFamily}">\n`;

    for (const w of this.placedWords) {
      svgContent += `    <text x="${w.x + 2}" y="${w.y + 2 + w.fontSize * 0.8}" ` +
                   `font-size="${w.fontSize}" fill="${w.color}" ` +
                   `style="text-shadow: 1px 1px 2px rgba(0,0,0,0.1)">${w.word}</text>\n`;
    }

    svgContent += `  </g>\n`;
    svgContent += `</svg>\n`;

    return svgContent;
  }

  downloadSVG(filename = 'wordcloud.svg') {
    const svgContent = this.toSVG();
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }

  updateOptions(options) {
    if (options.animationProgress === undefined) {
      this.lastWordsData = null;
    }
    this.options = { ...this.options, ...options };
    this.initCanvas();
  }

  toDataURL(type = 'image/png') {
    return this.canvas.toDataURL(type);
  }

  downloadPNG(filename = 'wordcloud.png') {
    const link = document.createElement('a');
    link.download = filename;
    link.href = this.toDataURL();
    link.click();
  }
}

export default WordCloud;
