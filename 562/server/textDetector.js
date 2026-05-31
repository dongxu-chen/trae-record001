class TextDetector {
  constructor(imageData, width, height) {
    this.imageData = imageData;
    this.width = width;
    this.height = height;
  }

  toGrayScale() {
    const gray = new Float32Array(this.width * this.height);
    for (let i = 0; i < this.width * this.height; i++) {
      const idx = i * 4;
      gray[i] = 0.299 * this.imageData[idx] + 0.587 * this.imageData[idx + 1] + 0.114 * this.imageData[idx + 2];
    }
    return gray;
  }

  adaptiveThreshold(gray, blockSize = 15, c = 10) {
    const binary = new Uint8Array(this.width * this.height);
    const half = Math.floor(blockSize / 2);

    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < this.width; x++) {
        let sum = 0;
        let count = 0;

        for (let dy = -half; dy <= half; dy++) {
          for (let dx = -half; dx <= half; dx++) {
            const nx = x + dx;
            const ny = y + dy;
            if (nx >= 0 && nx < this.width && ny >= 0 && ny < this.height) {
              sum += gray[ny * this.width + nx];
              count++;
            }
          }
        }

        const mean = sum / count;
        const idx = y * this.width + x;
        binary[idx] = gray[idx] < (mean - c) ? 1 : 0;
      }
    }

    return binary;
  }

  connectedComponents(binary) {
    const labels = new Int32Array(this.width * this.height);
    let currentLabel = 0;
    const components = [];
    const equivalences = new Map();

    const findRoot = (label) => {
      while (equivalences.has(label) && equivalences.get(label) !== label) {
        label = equivalences.get(label);
      }
      return label;
    };

    const union = (a, b) => {
      const rootA = findRoot(a);
      const rootB = findRoot(b);
      if (rootA !== rootB) {
        equivalences.set(Math.max(rootA, rootB), Math.min(rootA, rootB));
      }
    };

    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < this.width; x++) {
        const idx = y * this.width + x;
        if (binary[idx] === 0) continue;

        const neighbors = [];
        if (x > 0 && labels[idx - 1] > 0) neighbors.push(labels[idx - 1]);
        if (y > 0 && labels[idx - this.width] > 0) neighbors.push(labels[idx - this.width]);
        if (x > 0 && y > 0 && labels[idx - this.width - 1] > 0) neighbors.push(labels[idx - this.width - 1]);
        if (x < this.width - 1 && y > 0 && labels[idx - this.width + 1] > 0) neighbors.push(labels[idx - this.width + 1]);

        if (neighbors.length === 0) {
          currentLabel++;
          labels[idx] = currentLabel;
          equivalences.set(currentLabel, currentLabel);
        } else {
          const minLabel = Math.min(...neighbors);
          labels[idx] = minLabel;
          for (const n of neighbors) {
            union(minLabel, n);
          }
        }
      }
    }

    for (let i = 0; i < labels.length; i++) {
      if (labels[i] > 0) {
        labels[i] = findRoot(labels[i]);
      }
    }

    const componentMap = new Map();
    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < this.width; x++) {
        const idx = y * this.width + x;
        const label = labels[idx];
        if (label === 0) continue;

        if (!componentMap.has(label)) {
          componentMap.set(label, {
            pixels: [],
            minX: x, maxX: x,
            minY: y, maxY: y
          });
        }

        const comp = componentMap.get(label);
        comp.pixels.push({ x, y });
        comp.minX = Math.min(comp.minX, x);
        comp.maxX = Math.max(comp.maxX, x);
        comp.minY = Math.min(comp.minY, y);
        comp.maxY = Math.max(comp.maxY, y);
      }
    }

    for (const [label, comp] of componentMap) {
      components.push({
        label,
        bbox: {
          x: comp.minX,
          y: comp.minY,
          width: comp.maxX - comp.minX + 1,
          height: comp.maxY - comp.minY + 1
        },
        pixelCount: comp.pixels.length,
        pixels: comp.pixels
      });
    }

    return components;
  }

  filterTextComponents(components) {
    const minArea = 20;
    const maxArea = this.width * this.height * 0.3;
    const minAspectRatio = 0.1;
    const maxAspectRatio = 15;
    const minFillRatio = 0.05;
    const maxFillRatio = 0.95;

    return components.filter(comp => {
      const area = comp.pixelCount;
      if (area < minArea || area > maxArea) return false;

      const bboxArea = comp.bbox.width * comp.bbox.height;
      if (bboxArea === 0) return false;

      const aspectRatio = comp.bbox.width / comp.bbox.height;
      if (aspectRatio < minAspectRatio || aspectRatio > maxAspectRatio) return false;

      const fillRatio = area / bboxArea;
      if (fillRatio < minFillRatio || fillRatio > maxFillRatio) return false;

      return true;
    });
  }

  groupTextRegions(components, maxHorizontalGap = 20, maxVerticalGap = 10) {
    if (components.length === 0) return [];

    const sorted = [...components].sort((a, b) => {
      if (Math.abs(a.bbox.y - b.bbox.y) > maxVerticalGap) {
        return a.bbox.y - b.bbox.y;
      }
      return a.bbox.x - b.bbox.x;
    });

    const groups = [];
    let currentGroup = [sorted[0]];

    for (let i = 1; i < sorted.length; i++) {
      const prev = currentGroup[currentGroup.length - 1];
      const curr = sorted[i];

      const prevCenter = {
        x: prev.bbox.x + prev.bbox.width / 2,
        y: prev.bbox.y + prev.bbox.height / 2
      };
      const currCenter = {
        x: curr.bbox.x + curr.bbox.width / 2,
        y: curr.bbox.y + curr.bbox.height / 2
      };

      const hGap = curr.bbox.x - (prev.bbox.x + prev.bbox.width);
      const vGap = Math.abs(currCenter.y - prevCenter.y);
      const heightRatio = Math.min(prev.bbox.height, curr.bbox.height) /
                          Math.max(prev.bbox.height, curr.bbox.height);

      const isSameLine = vGap < maxVerticalGap;
      const isHorizontallyClose = hGap >= -5 && hGap < maxHorizontalGap * 3;
      const isSimilarHeight = heightRatio > 0.4;

      if ((isSameLine && isHorizontallyClose) || (isSameLine && isSimilarHeight)) {
        currentGroup.push(curr);
      } else {
        groups.push(currentGroup);
        currentGroup = [curr];
      }
    }

    groups.push(currentGroup);

    return groups.map(group => {
      const minX = Math.min(...group.map(c => c.bbox.x));
      const minY = Math.min(...group.map(c => c.bbox.y));
      const maxX = Math.max(...group.map(c => c.bbox.x + c.bbox.width));
      const maxY = Math.max(...group.map(c => c.bbox.y + c.bbox.height));

      return {
        bbox: {
          x: minX,
          y: minY,
          width: maxX - minX,
          height: maxY - minY
        },
        componentCount: group.length,
        totalPixels: group.reduce((sum, c) => sum + c.pixelCount, 0),
        components: group,
        confidence: this._computeTextConfidence(group)
      };
    });
  }

  _computeTextConfidence(group) {
    if (group.length <= 1) return 0.5;

    const heights = group.map(c => c.bbox.height);
    const avgHeight = heights.reduce((a, b) => a + b, 0) / heights.length;
    const heightVariance = heights.reduce((sum, h) => sum + Math.pow(h - avgHeight, 2), 0) / heights.length;
    const heightCV = Math.sqrt(heightVariance) / (avgHeight + 1);

    const alignmentScore = this._computeAlignment(group);
    const regularityScore = 1 - Math.min(1, heightCV / 0.5);
    const densityScore = Math.min(1, group.length / 5);

    return (alignmentScore * 0.4 + regularityScore * 0.3 + densityScore * 0.3);
  }

  _computeAlignment(group) {
    if (group.length <= 1) return 1;

    const centers = group.map(c => c.bbox.y + c.bbox.height / 2);
    const avgCenter = centers.reduce((a, b) => a + b, 0) / centers.length;
    const maxDeviation = Math.max(...centers.map(c => Math.abs(c - avgCenter)));
    const avgHeight = group.reduce((sum, c) => sum + c.bbox.height, 0) / group.length;

    return Math.max(0, 1 - maxDeviation / (avgHeight + 1));
  }

  detectText(options = {}) {
    const {
      thresholdBlock = 15,
      thresholdC = 10,
      minConfidence = 0.2,
      padding = 5,
      maxHorizontalGap = 30,
      maxVerticalGap = 15
    } = options;

    const gray = this.toGrayScale();
    const binary = this.adaptiveThreshold(gray, thresholdBlock, thresholdC);
    const components = this.connectedComponents(binary);
    const filtered = this.filterTextComponents(components);
    const groups = this.groupTextRegions(filtered, maxHorizontalGap, maxVerticalGap);

    const textRegions = groups
      .filter(g => g.confidence >= minConfidence)
      .map(g => ({
        bbox: {
          x: Math.max(0, g.bbox.x - padding),
          y: Math.max(0, g.bbox.y - padding),
          width: g.bbox.width + padding * 2,
          height: g.bbox.height + padding * 2
        },
        confidence: g.confidence,
        componentCount: g.componentCount,
        totalPixels: g.totalPixels
      }));

    const mask = this.generateMask(textRegions);

    return {
      regions: textRegions,
      mask,
      totalRegions: textRegions.length,
      averageConfidence: textRegions.length > 0
        ? textRegions.reduce((sum, r) => sum + r.confidence, 0) / textRegions.length
        : 0
    };
  }

  generateMask(regions) {
    const mask = new Uint8Array(this.width * this.height * 4);

    for (let i = 3; i < mask.length; i += 4) {
      mask[i] = 255;
    }

    for (const region of regions) {
      const { x, y, width, height } = region.bbox;
      for (let dy = 0; dy < height; dy++) {
        for (let dx = 0; dx < width; dx++) {
          const px = x + dx;
          const py = y + dy;
          if (px < 0 || px >= this.width || py < 0 || py >= this.height) continue;

          const idx = (py * this.width + px) * 4;
          mask[idx] = 255;
          mask[idx + 1] = 255;
          mask[idx + 2] = 255;
          mask[idx + 3] = 255;
        }
      }
    }

    return mask;
  }

  detectTextInROI(roi, options = {}) {
    const { x, y, width, height } = roi;
    const roiData = new Uint8ClampedArray(width * height * 4);

    for (let dy = 0; dy < height; dy++) {
      for (let dx = 0; dx < width; dx++) {
        const srcIdx = ((y + dy) * this.width + (x + dx)) * 4;
        const dstIdx = (dy * width + dx) * 4;
        roiData[dstIdx] = this.imageData[srcIdx];
        roiData[dstIdx + 1] = this.imageData[srcIdx + 1];
        roiData[dstIdx + 2] = this.imageData[srcIdx + 2];
        roiData[dstIdx + 3] = this.imageData[srcIdx + 3];
      }
    }

    const roiDetector = new TextDetector(roiData, width, height);
    const result = roiDetector.detectText(options);

    result.regions = result.regions.map(r => ({
      ...r,
      bbox: {
        x: r.bbox.x + x,
        y: r.bbox.y + y,
        width: r.bbox.width,
        height: r.bbox.height
      }
    }));

    return result;
  }
}

module.exports = TextDetector;
