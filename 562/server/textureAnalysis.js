class TextureAnalysis {
  constructor(imageData, width, height) {
    this.imageData = imageData;
    this.width = width;
    this.height = height;
  }

  getPixel(x, y, channel = 0) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return 0;
    const idx = (y * this.width + x) * 4;
    return this.imageData[idx + channel];
  }

  getRGB(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
      return { r: 0, g: 0, b: 0 };
    }
    const idx = (y * this.width + x) * 4;
    return {
      r: this.imageData[idx],
      g: this.imageData[idx + 1],
      b: this.imageData[idx + 2]
    };
  }

  computeLocalStatistics(x, y, windowSize = 7) {
    const half = Math.floor(windowSize / 2);
    let sumR = 0, sumG = 0, sumB = 0;
    let sumSqR = 0, sumSqG = 0, sumSqB = 0;
    let count = 0;

    for (let dy = -half; dy <= half; dy++) {
      for (let dx = -half; dx <= half; dx++) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;

        const pixel = this.getRGB(nx, ny);
        sumR += pixel.r;
        sumG += pixel.g;
        sumB += pixel.b;
        sumSqR += pixel.r * pixel.r;
        sumSqG += pixel.g * pixel.g;
        sumSqB += pixel.b * pixel.b;
        count++;
      }
    }

    const meanR = sumR / count;
    const meanG = sumG / count;
    const meanB = sumB / count;
    const varR = (sumSqR / count) - meanR * meanR;
    const varG = (sumSqG / count) - meanG * meanG;
    const varB = (sumSqB / count) - meanB * meanB;

    return {
      mean: { r: meanR, g: meanG, b: meanB },
      variance: { r: varR, g: varG, b: varB },
      stdDev: { r: Math.sqrt(varR), g: Math.sqrt(varG), b: Math.sqrt(varB) }
    };
  }

  computeCooccurrenceMatrix(x, y, windowSize = 7, dx = 1, dy = 0, levels = 8) {
    const half = Math.floor(windowSize / 2);
    const matrix = new Array(levels).fill(null).map(() => new Array(levels).fill(0));

    for (let wy = -half; wy <= half; wy++) {
      for (let wx = -half; wx <= half; wx++) {
        const nx = x + wx;
        const ny = y + wy;
        const nx2 = nx + dx;
        const ny2 = ny + dy;

        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;
        if (nx2 < 0 || nx2 >= this.width || ny2 < 0 || ny2 >= this.height) continue;

        const p1 = this.getRGB(nx, ny);
        const p2 = this.getRGB(nx2, ny2);

        const gray1 = Math.floor((0.299 * p1.r + 0.587 * p1.g + 0.114 * p1.b) / (256 / levels));
        const gray2 = Math.floor((0.299 * p2.r + 0.587 * p2.g + 0.114 * p2.b) / (256 / levels));

        matrix[gray1][gray2]++;
        matrix[gray2][gray1]++;
      }
    }

    let total = 0;
    for (let i = 0; i < levels; i++) {
      for (let j = 0; j < levels; j++) {
        total += matrix[i][j];
      }
    }

    if (total > 0) {
      for (let i = 0; i < levels; i++) {
        for (let j = 0; j < levels; j++) {
          matrix[i][j] /= total;
        }
      }
    }

    return matrix;
  }

  computeHaralickFeatures(matrix, levels = 8) {
    let energy = 0;
    let entropy = 0;
    let contrast = 0;
    let homogeneity = 0;
    let correlation = 0;
    let meanI = 0, meanJ = 0;
    let varI = 0, varJ = 0;

    for (let i = 0; i < levels; i++) {
      for (let j = 0; j < levels; j++) {
        const val = matrix[i][j];
        if (val === 0) continue;

        energy += val * val;
        entropy -= val * Math.log2(val);
        contrast += (i - j) * (i - j) * val;
        homogeneity += val / (1 + Math.abs(i - j));
        meanI += i * val;
        meanJ += j * val;
      }
    }

    for (let i = 0; i < levels; i++) {
      for (let j = 0; j < levels; j++) {
        const val = matrix[i][j];
        if (val === 0) continue;
        varI += (i - meanI) * (i - meanI) * val;
        varJ += (j - meanJ) * (j - meanJ) * val;
        correlation += (i - meanI) * (j - meanJ) * val;
      }
    }

    const stdDevI = Math.sqrt(varI) + 0.001;
    const stdDevJ = Math.sqrt(varJ) + 0.001;
    correlation /= (stdDevI * stdDevJ);

    return { energy, entropy, contrast, homogeneity, correlation };
  }

  computeGaborResponse(x, y, wavelength = 4, orientation = 0, sigma = 2) {
    const half = Math.floor(sigma * 3);
    let realResponse = 0;
    let imagResponse = 0;
    let weightSum = 0;

    const theta = orientation * Math.PI / 180;
    const cosTheta = Math.cos(theta);
    const sinTheta = Math.sin(theta);

    for (let dy = -half; dy <= half; dy++) {
      for (let dx = -half; dx <= half; dx++) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;

        const xPrime = dx * cosTheta + dy * sinTheta;
        const yPrime = -dx * sinTheta + dy * cosTheta;

        const gaussian = Math.exp(-(xPrime * xPrime + yPrime * yPrime) / (2 * sigma * sigma));
        const sinusoidReal = Math.cos(2 * Math.PI * xPrime / wavelength);
        const sinusoidImag = Math.sin(2 * Math.PI * xPrime / wavelength);

        const weight = gaussian;
        const pixel = this.getRGB(nx, ny);
        const gray = 0.299 * pixel.r + 0.587 * pixel.g + 0.114 * pixel.b;

        realResponse += gray * weight * sinusoidReal;
        imagResponse += gray * weight * sinusoidImag;
        weightSum += weight;
      }
    }

    if (weightSum > 0) {
      realResponse /= weightSum;
      imagResponse /= weightSum;
    }

    const magnitude = Math.sqrt(realResponse * realResponse + imagResponse * imagResponse);
    const phase = Math.atan2(imagResponse, realResponse);

    return { real: realResponse, imag: imagResponse, magnitude, phase };
  }

  computeTextureFeatures(x, y, windowSize = 7) {
    const stats = this.computeLocalStatistics(x, y, windowSize);
    
    const coocMat = this.computeCooccurrenceMatrix(x, y, windowSize);
    const haralick = this.computeHaralickFeatures(coocMat);

    const orientations = [0, 45, 90, 135];
    const gaborResponses = orientations.map(angle => 
      this.computeGaborResponse(x, y, 4, angle, 2)
    );

    let maxGaborMagnitude = 0;
    let dominantOrientation = 0;
    gaborResponses.forEach((resp, idx) => {
      if (resp.magnitude > maxGaborMagnitude) {
        maxGaborMagnitude = resp.magnitude;
        dominantOrientation = orientations[idx];
      }
    });

    const avgStdDev = (stats.stdDev.r + stats.stdDev.g + stats.stdDev.b) / 3;

    return {
      localStats: stats,
      haralick,
      gabor: {
        responses: gaborResponses,
        maxMagnitude: maxGaborMagnitude,
        dominantOrientation
      },
      roughness: avgStdDev,
      complexity: haralick.entropy,
      directionality: dominantOrientation
    };
  }

  generateTextureMap() {
    const map = new Array(this.height).fill(null).map(() => 
      new Array(this.width).fill(null)
    );

    const step = 2;
    for (let y = 0; y < this.height; y += step) {
      for (let x = 0; x < this.width; x += step) {
        const features = this.computeTextureFeatures(x, y, 5);
        for (let dy = 0; dy < step && y + dy < this.height; dy++) {
          for (let dx = 0; dx < step && x + dx < this.width; dx++) {
            map[y + dy][x + dx] = features;
          }
        }
      }
    }

    return map;
  }

  findSimilarTextureRegion(targetX, targetY, maskData, searchRadius = 30) {
    const targetFeatures = this.computeTextureFeatures(targetX, targetY, 7);
    const halfSearch = Math.floor(searchRadius / 2);

    let bestMatch = null;
    let bestDistance = Infinity;

    for (let dy = -halfSearch; dy <= halfSearch; dy += 2) {
      for (let dx = -halfSearch; dx <= halfSearch; dx += 2) {
        const nx = targetX + dx;
        const ny = targetY + dy;

        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;

        const maskIdx = (ny * this.width + nx) * 4;
        if (maskData[maskIdx] > 128 || maskData[maskIdx + 1] > 128 || maskData[maskIdx + 2] > 128) continue;

        const features = this.computeTextureFeatures(nx, ny, 7);
        const distance = this.computeTextureDistance(targetFeatures, features);

        if (distance < bestDistance) {
          bestDistance = distance;
          bestMatch = { x: nx, y: ny, features, distance };
        }
      }
    }

    return bestMatch;
  }

  computeTextureDistance(f1, f2) {
    let distance = 0;

    const meanDist = Math.sqrt(
      Math.pow(f1.localStats.mean.r - f2.localStats.mean.r, 2) +
      Math.pow(f1.localStats.mean.g - f2.localStats.mean.g, 2) +
      Math.pow(f1.localStats.mean.b - f2.localStats.mean.b, 2)
    ) / (255 * Math.sqrt(3));
    distance += meanDist * 0.3;

    const stdDist = Math.sqrt(
      Math.pow(f1.localStats.stdDev.r - f2.localStats.stdDev.r, 2) +
      Math.pow(f1.localStats.stdDev.g - f2.localStats.stdDev.g, 2) +
      Math.pow(f1.localStats.stdDev.b - f2.localStats.stdDev.b, 2)
    ) / (255 * Math.sqrt(3));
    distance += stdDist * 0.2;

    const haralickDist = Math.sqrt(
      Math.pow(f1.haralick.contrast - f2.haralick.contrast, 2) +
      Math.pow(f1.haralick.entropy - f2.haralick.entropy, 2) +
      Math.pow(f1.haralick.homogeneity - f2.haralick.homogeneity, 2)
    ) / Math.sqrt(3);
    distance += haralickDist * 0.3;

    const gaborDist = Math.abs(f1.gabor.maxMagnitude - f2.gabor.maxMagnitude) / 255;
    distance += gaborDist * 0.2;

    return distance;
  }

  detectTexturePatterns() {
    const patterns = [];
    const step = 10;
    const visited = new Set();

    for (let y = 0; y < this.height; y += step) {
      for (let x = 0; x < this.width; x += step) {
        if (visited.has(`${x},${y}`)) continue;

        const seedFeatures = this.computeTextureFeatures(x, y, 7);
        const pattern = {
          centerX: x,
          centerY: y,
          features: seedFeatures,
          points: [{ x, y }],
          boundingBox: { minX: x, maxX: x, minY: y, maxY: y }
        };

        const queue = [{ x, y }];
        visited.add(`${x},${y}`);

        while (queue.length > 0) {
          const current = queue.shift();

          for (let dy = -step; dy <= step; dy += step) {
            for (let dx = -step; dx <= step; dx += step) {
              if (dx === 0 && dy === 0) continue;

              const nx = current.x + dx;
              const ny = current.y + dy;
              const key = `${nx},${ny}`;

              if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;
              if (visited.has(key)) continue;

              const features = this.computeTextureFeatures(nx, ny, 7);
              const distance = this.computeTextureDistance(seedFeatures, features);

              if (distance < 0.2) {
                visited.add(key);
                queue.push({ x: nx, y: ny });
                pattern.points.push({ x: nx, y: ny });
                pattern.boundingBox.minX = Math.min(pattern.boundingBox.minX, nx);
                pattern.boundingBox.maxX = Math.max(pattern.boundingBox.maxX, nx);
                pattern.boundingBox.minY = Math.min(pattern.boundingBox.minY, ny);
                pattern.boundingBox.maxY = Math.max(pattern.boundingBox.maxY, ny);
              }
            }
          }
        }

        if (pattern.points.length > 5) {
          patterns.push(pattern);
        }
      }
    }

    return patterns;
  }

  computeTextureContinuity(x, y, direction, step = 1) {
    const dx = Math.cos(direction) * step;
    const dy = Math.sin(direction) * step;

    const features1 = this.computeTextureFeatures(x, y, 5);
    const features2 = this.computeTextureFeatures(x + dx * 3, y + dy * 3, 5);

    return 1 - this.computeTextureDistance(features1, features2);
  }
}

module.exports = TextureAnalysis;
