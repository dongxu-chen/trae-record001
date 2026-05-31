const EdgeDetection = require('./edgeDetection');
const TextureAnalysis = require('./textureAnalysis');

class ImageInpainting {
  constructor(imageData, maskData, width, height, options = {}) {
    this.width = width;
    this.height = height;
    this.imageData = new Uint8ClampedArray(imageData);
    this.maskData = maskData;
    this.result = new Uint8ClampedArray(imageData);
    this.options = {
      edgeWeight: 0.4,
      textureWeight: 0.3,
      colorWeight: 0.3,
      preserveTexture: true,
      guideEdges: true,
      ...options
    };

    if (this.options.guideEdges) {
      this._initEdgeDetection();
    }
    if (this.options.preserveTexture) {
      this._initTextureAnalysis();
    }
  }

  _initEdgeDetection() {
    const edgeDetector = new EdgeDetection(this.imageData, this.width, this.height);
    const edgeData = edgeDetector.cannyEdgeDetection(30, 80);
    this.edges = edgeData.edges;
    this.edgeMagnitude = edgeData.magnitude;
    this.edgeDirection = edgeData.direction;
    this.edgeGx = edgeData.gx;
    this.edgeGy = edgeData.gy;
    this.edgeTangents = edgeDetector.computeEdgeTangents(this.edges, this.edgeDirection);
  }

  _initTextureAnalysis() {
    this.textureAnalyzer = new TextureAnalysis(this.imageData, this.width, this.height);
  }

  isMasked(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return false;
    const idx = (y * this.width + x) * 4;
    return this.maskData[idx] > 128 || this.maskData[idx + 1] > 128 || this.maskData[idx + 2] > 128;
  }

  getPixel(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
      return { r: 0, g: 0, b: 0, a: 255 };
    }
    const idx = (y * this.width + x) * 4;
    return {
      r: this.result[idx],
      g: this.result[idx + 1],
      b: this.result[idx + 2],
      a: this.result[idx + 3]
    };
  }

  setPixel(x, y, r, g, b) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return;
    const idx = (y * this.width + x) * 4;
    this.result[idx] = Math.max(0, Math.min(255, r));
    this.result[idx + 1] = Math.max(0, Math.min(255, g));
    this.result[idx + 2] = Math.max(0, Math.min(255, b));
  }

  _computeEdgeGuideWeight(x, y, nx, ny) {
    if (!this.edges) return 1;

    const idx = (y * this.width + x) * 4;
    const edgeIdx = y * this.width + x;

    let hasNearbyEdge = false;
    let nearestEdgeDist = Infinity;
    let nearestEdgeX = x;
    let nearestEdgeY = y;

    const searchRadius = 8;
    for (let dy = -searchRadius; dy <= searchRadius; dy++) {
      for (let dx = -searchRadius; dx <= searchRadius; dx++) {
        const ex = x + dx;
        const ey = y + dy;
        if (ex < 0 || ex >= this.width || ey < 0 || ey >= this.height) continue;
        if (this.edges[ey * this.width + ex] > 0) {
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < nearestEdgeDist) {
            nearestEdgeDist = dist;
            nearestEdgeX = ex;
            nearestEdgeY = ey;
            hasNearbyEdge = true;
          }
        }
      }
    }

    if (!hasNearbyEdge || nearestEdgeDist > 5) return 1;

    const edgeDir = this.edgeDirection[nearestEdgeY * this.width + nearestEdgeX];
    const perpX = -Math.sin(edgeDir);
    const perpY = Math.cos(edgeDir);

    const vecX = nx - x;
    const vecY = ny - y;
    const vecLen = Math.sqrt(vecX * vecX + vecY * vecY);
    
    if (vecLen < 0.1) return 1;

    const normVecX = vecX / vecLen;
    const normVecY = vecY / vecLen;

    const parallelAlign = Math.abs(normVecX * Math.cos(edgeDir) + normVecY * Math.sin(edgeDir));
    const perpAlign = Math.abs(normVecX * perpX + normVecY * perpY);

    const edgeStrength = Math.min(1, this.edgeMagnitude[nearestEdgeY * this.width + nearestEdgeX] / 100);
    const distanceFactor = Math.max(0, 1 - nearestEdgeDist / 5);

    const directionalFactor = 0.3 + 0.7 * (parallelAlign * 0.8 + perpAlign * 0.2);
    const edgeWeight = edgeStrength * distanceFactor * directionalFactor;

    return 1 + edgeWeight * this.options.edgeWeight;
  }

  _computeTextureGuideWeight(x, y, nx, ny) {
    if (!this.options.preserveTexture || !this.textureAnalyzer) return 1;

    const targetFeatures = this.textureAnalyzer.computeTextureFeatures(x, y, 5);
    const neighborFeatures = this.textureAnalyzer.computeTextureFeatures(nx, ny, 5);
    const textureSimilarity = 1 - this.textureAnalyzer.computeTextureDistance(targetFeatures, neighborFeatures);

    const textureWeight = textureSimilarity * this.options.textureWeight;
    return 1 + textureWeight;
  }

  _findBestTextureMatch(x, y, radius) {
    if (!this.options.preserveTexture || !this.textureAnalyzer) return null;

    return this.textureAnalyzer.findSimilarTextureRegion(x, y, this.maskData, radius * 4);
  }

  _blendWithTextureMatch(x, y, originalColor, radius) {
    const match = this._findBestTextureMatch(x, y, radius);
    if (!match) return originalColor;

    const matchPixel = this.getPixel(match.x, match.y);
    const matchFeatures = match.features;
    const centerFeatures = this.textureAnalyzer.computeTextureFeatures(x, y, 5);
    const similarity = 1 - this.textureAnalyzer.computeTextureDistance(centerFeatures, matchFeatures);

    const localStats = this.textureAnalyzer.computeLocalStatistics(match.x, match.y, 5);

    const blendFactor = Math.min(1, similarity * this.options.textureWeight);

    return {
      r: originalColor.r * (1 - blendFactor) + localStats.mean.r * blendFactor,
      g: originalColor.g * (1 - blendFactor) + localStats.mean.g * blendFactor,
      b: originalColor.b * (1 - blendFactor) + localStats.mean.b * blendFactor
    };
  }

  _computeLocalTexturePattern(x, y, radius) {
    if (!this.textureAnalyzer) return null;
    return this.textureAnalyzer.computeTextureFeatures(x, y, radius * 2 + 1);
  }

  edgeGuidedInpaint(radius = 3) {
    const maxIterations = 80;
    const threshold = 1.5;
    
    for (let iter = 0; iter < maxIterations; iter++) {
      let changed = 0;
      const tempResult = new Uint8ClampedArray(this.result);

      for (let y = 0; y < this.height; y++) {
        for (let x = 0; x < this.width; x++) {
          if (!this.isMasked(x, y)) continue;

          let sumR = 0, sumG = 0, sumB = 0;
          let weightSum = 0;
          let validNeighbors = 0;

          for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
              const nx = x + dx;
              const ny = y + dy;
              
              if (nx === x && ny === y) continue;
              if (this.isMasked(nx, ny)) continue;

              const pixel = this.getPixel(nx, ny);
              const distance = Math.sqrt(dx * dx + dy * dy);
              
              let weight = 1 / (distance + 0.5);
              weight *= this._computeEdgeGuideWeight(x, y, nx, ny);
              weight *= this._computeTextureGuideWeight(x, y, nx, ny);

              sumR += pixel.r * weight;
              sumG += pixel.g * weight;
              sumB += pixel.b * weight;
              weightSum += weight;
              validNeighbors++;
            }
          }

          if (validNeighbors > 0) {
            let newR = sumR / weightSum;
            let newG = sumG / weightSum;
            let newB = sumB / weightSum;

            if (this.options.preserveTexture && validNeighbors > 4) {
              const blended = this._blendWithTextureMatch(x, y, { r: newR, g: newG, b: newB }, radius);
              newR = blended.r;
              newG = blended.g;
              newB = blended.b;
            }

            const idx = (y * this.width + x) * 4;
            const oldR = this.result[idx];
            const oldG = this.result[idx + 1];
            const oldB = this.result[idx + 2];

            const diff = Math.abs(newR - oldR) + Math.abs(newG - oldG) + Math.abs(newB - oldB);
            
            tempResult[idx] = newR;
            tempResult[idx + 1] = newG;
            tempResult[idx + 2] = newB;

            if (diff > threshold) changed++;
          }
        }
      }

      this.result.set(tempResult);
      
      if (changed < this.width * this.height * 0.005) break;
    }

    return this.result;
  }

  texturePreservingInpaint(radius = 3) {
    const maxIterations = 60;
    
    for (let iter = 0; iter < maxIterations; iter++) {
      const tempResult = new Uint8ClampedArray(this.result);

      for (let y = 1; y < this.height - 1; y++) {
        for (let x = 1; x < this.width - 1; x++) {
          if (!this.isMasked(x, y)) continue;

          const neighbors = [];
          for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
              const nx = x + dx;
              const ny = y + dy;
              if (!this.isMasked(nx, ny)) {
                const pixel = this.getPixel(nx, ny);
                const features = this._computeLocalTexturePattern(nx, ny, Math.max(1, Math.floor(radius / 2)));
                neighbors.push({ pixel, dx, dy, features });
              }
            }
          }

          if (neighbors.length < 6) continue;

          const centerFeatures = this._computeLocalTexturePattern(x, y, radius);

          let sumR = 0, sumG = 0, sumB = 0;
          let weightSum = 0;

          for (const n of neighbors) {
            const dist = Math.sqrt(n.dx * n.dx + n.dy * n.dy) + 0.1;
            let weight = 1 / dist;

            if (centerFeatures && n.features) {
              const featureDist = this.textureAnalyzer.computeTextureDistance(
                { localStats: centerFeatures.localStats, haralick: centerFeatures.haralick, gabor: centerFeatures.gabor },
                { localStats: n.features.localStats, haralick: n.features.haralick, gabor: n.features.gabor }
              );
              weight *= (1 - featureDist * 0.5);
            }

            if (this.edges) {
              weight *= this._computeEdgeGuideWeight(x, y, n.dx + x, n.dy + y);
            }

            sumR += n.pixel.r * weight;
            sumG += n.pixel.g * weight;
            sumB += n.pixel.b * weight;
            weightSum += weight;
          }

          if (weightSum > 0) {
            tempResult[(y * this.width + x) * 4] = sumR / weightSum;
            tempResult[(y * this.width + x) * 4 + 1] = sumG / weightSum;
            tempResult[(y * this.width + x) * 4 + 2] = sumB / weightSum;
          }
        }
      }

      this.result.set(tempResult);
    }

    return this.result;
  }

  teleaInpaint(radius = 3) {
    const maxIterations = 100;
    const threshold = 2;
    
    for (let iter = 0; iter < maxIterations; iter++) {
      let changed = 0;
      const tempResult = new Uint8ClampedArray(this.result);

      for (let y = 0; y < this.height; y++) {
        for (let x = 0; x < this.width; x++) {
          if (!this.isMasked(x, y)) continue;

          let sumR = 0, sumG = 0, sumB = 0;
          let count = 0;
          let weightSum = 0;

          for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
              const nx = x + dx;
              const ny = y + dy;
              
              if (nx === x && ny === y) continue;
              if (this.isMasked(nx, ny)) continue;

              const distance = Math.sqrt(dx * dx + dy * dy);
              const weight = 1 / (distance + 0.1);

              const pixel = this.getPixel(nx, ny);
              sumR += pixel.r * weight;
              sumG += pixel.g * weight;
              sumB += pixel.b * weight;
              weightSum += weight;
              count++;
            }
          }

          if (count > 0) {
            const newR = sumR / weightSum;
            const newG = sumG / weightSum;
            const newB = sumB / weightSum;

            const idx = (y * this.width + x) * 4;
            const oldR = this.result[idx];
            const oldG = this.result[idx + 1];
            const oldB = this.result[idx + 2];

            const diff = Math.abs(newR - oldR) + Math.abs(newG - oldG) + Math.abs(newB - oldB);
            
            tempResult[idx] = newR;
            tempResult[idx + 1] = newG;
            tempResult[idx + 2] = newB;

            if (diff > threshold) changed++;
          }
        }
      }

      this.result.set(tempResult);
      
      if (changed < this.width * this.height * 0.001) break;
    }

    return this.result;
  }

  nsInpaint(radius = 3) {
    const maxIterations = 50;
    
    for (let iter = 0; iter < maxIterations; iter++) {
      const tempResult = new Uint8ClampedArray(this.result);

      for (let y = 1; y < this.height - 1; y++) {
        for (let x = 1; x < this.width - 1; x++) {
          if (!this.isMasked(x, y)) continue;

          const neighbors = [];
          for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
              const nx = x + dx;
              const ny = y + dy;
              if (!this.isMasked(nx, ny)) {
                const pixel = this.getPixel(nx, ny);
                neighbors.push({ pixel, dx, dy });
              }
            }
          }

          if (neighbors.length < 4) continue;

          const center = this.getPixel(x, y);
          
          let gradX = 0, gradY = 0;
          let gradXR = 0, gradYR = 0;
          let gradXG = 0, gradYG = 0;
          let gradXB = 0, gradYB = 0;

          for (const n of neighbors) {
            const dist = Math.sqrt(n.dx * n.dx + n.dy * n.dy) + 0.1;
            const weight = 1 / dist;
            
            const dr = n.pixel.r - center.r;
            const dg = n.pixel.g - center.g;
            const db = n.pixel.b - center.b;

            gradXR += (n.dx / dist) * dr * weight;
            gradYR += (n.dy / dist) * dr * weight;
            gradXG += (n.dx / dist) * dg * weight;
            gradYG += (n.dy / dist) * dg * weight;
            gradXB += (n.dx / dist) * db * weight;
            gradYB += (n.dy / dist) * db * weight;
          }

          const lenR = Math.sqrt(gradXR * gradXR + gradYR * gradYR) + 0.001;
          const lenG = Math.sqrt(gradXG * gradXG + gradYG * gradYG) + 0.001;
          const lenB = Math.sqrt(gradXB * gradXB + gradYB * gradYB) + 0.001;

          gradX = (gradXR / lenR + gradXG / lenG + gradXB / lenB) / 3;
          gradY = (gradYR / lenR + gradYG / lenG + gradYB / lenB) / 3;

          const len = Math.sqrt(gradX * gradX + gradY * gradY) + 0.001;
          gradX /= len;
          gradY /= len;

          let sumR = 0, sumG = 0, sumB = 0;
          let weightSum = 0;

          for (const n of neighbors) {
            const dotProduct = n.dx * gradX + n.dy * gradY;
            const dist = Math.sqrt(n.dx * n.dx + n.dy * n.dy) + 0.1;
            const anisotropy = Math.abs(dotProduct) * 0.5 + 0.5;
            let weight = (1 / dist) * anisotropy;

            if (this.edges) {
              weight *= this._computeEdgeGuideWeight(x, y, x + n.dx, y + n.dy);
            }

            sumR += n.pixel.r * weight;
            sumG += n.pixel.g * weight;
            sumB += n.pixel.b * weight;
            weightSum += weight;
          }

          if (weightSum > 0) {
            tempResult[(y * this.width + x) * 4] = sumR / weightSum;
            tempResult[(y * this.width + x) * 4 + 1] = sumG / weightSum;
            tempResult[(y * this.width + x) * 4 + 2] = sumB / weightSum;
          }
        }
      }

      this.result.set(tempResult);
    }

    return this.result;
  }

  hybridInpaint(radius = 3) {
    this.edgeGuidedInpaint(Math.ceil(radius * 1.5));
    
    return this.texturePreservingInpaint(radius);
  }

  advancedInpaint(radius = 3) {
    this.edgeGuidedInpaint(Math.ceil(radius * 2));
    
    this.texturePreservingInpaint(radius);
    
    return this.nsInpaint(radius);
  }

  inpaint(algorithm = 'edge-guided', radius = 3) {
    switch (algorithm) {
      case 'edge-guided':
      case 'edge':
        return this.edgeGuidedInpaint(radius);
      case 'texture-preserving':
      case 'texture':
        return this.texturePreservingInpaint(radius);
      case 'ns':
        return this.nsInpaint(radius);
      case 'hybrid':
        return this.hybridInpaint(radius);
      case 'advanced':
        return this.advancedInpaint(radius);
      case 'telea':
      default:
        return this.teleaInpaint(radius);
    }
  }
}

module.exports = ImageInpainting;
