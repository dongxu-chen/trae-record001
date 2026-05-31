const EdgeDetection = require('./edgeDetection');
const TextureAnalysis = require('./textureAnalysis');

class ImageClassifier {
  constructor(imageData, width, height) {
    this.imageData = imageData;
    this.width = width;
    this.height = height;
    this.edgeDetector = new EdgeDetection(imageData, width, height);
    this.textureAnalyzer = new TextureAnalysis(imageData, width, height);
  }

  computeEdgeDensity() {
    const edgeData = this.edgeDetector.cannyEdgeDetection(30, 80);
    let edgeCount = 0;
    
    for (let i = 0; i < edgeData.edges.length; i++) {
      if (edgeData.edges[i] > 0) edgeCount++;
    }
    
    return edgeCount / (this.width * this.height);
  }

  computeColorVariance() {
    let sumR = 0, sumG = 0, sumB = 0;
    let sumSqR = 0, sumSqG = 0, sumSqB = 0;
    const totalPixels = this.width * this.height;

    for (let i = 0; i < totalPixels; i++) {
      const idx = i * 4;
      const r = this.imageData[idx];
      const g = this.imageData[idx + 1];
      const b = this.imageData[idx + 2];
      
      sumR += r; sumG += g; sumB += b;
      sumSqR += r * r; sumSqG += g * g; sumSqB += b * b;
    }

    const meanR = sumR / totalPixels;
    const meanG = sumG / totalPixels;
    const meanB = sumB / totalPixels;
    
    const varR = (sumSqR / totalPixels) - meanR * meanR;
    const varG = (sumSqG / totalPixels) - meanG * meanG;
    const varB = (sumSqB / totalPixels) - meanB * meanB;

    return Math.sqrt((varR + varG + varB) / 3) / 255;
  }

  computeTextureComplexity() {
    const sampleStep = 10;
    let totalEntropy = 0;
    let totalContrast = 0;
    let sampleCount = 0;

    for (let y = sampleStep; y < this.height - sampleStep; y += sampleStep) {
      for (let x = sampleStep; x < this.width - sampleStep; x += sampleStep) {
        const features = this.textureAnalyzer.computeTextureFeatures(x, y, 5);
        totalEntropy += features.haralick.entropy;
        totalContrast += features.haralick.contrast;
        sampleCount++;
      }
    }

    return {
      avgEntropy: sampleCount > 0 ? totalEntropy / sampleCount : 0,
      avgContrast: sampleCount > 0 ? totalContrast / sampleCount : 0
    };
  }

  computeColorCount() {
    const colorBuckets = new Set();
    const bucketSize = 16;

    for (let i = 0; i < this.width * this.height; i += 4) {
      const idx = i * 4;
      const r = Math.floor(this.imageData[idx] / bucketSize);
      const g = Math.floor(this.imageData[idx + 1] / bucketSize);
      const b = Math.floor(this.imageData[idx + 2] / bucketSize);
      colorBuckets.add(`${r},${g},${b}`);
    }

    const maxColors = Math.pow(256 / bucketSize, 3);
    return colorBuckets.size / maxColors;
  }

  computeGradientMagnitude() {
    const sobelData = this.edgeDetector.sobelEdgeDetection();
    let totalMagnitude = 0;
    
    for (let i = 0; i < sobelData.magnitude.length; i++) {
      totalMagnitude += sobelData.magnitude[i];
    }
    
    return totalMagnitude / (this.width * this.height * 255);
  }

  computeFrequencyFeatures() {
    const sampleStep = 20;
    let highFreqEnergy = 0;
    let totalEnergy = 0;
    let count = 0;

    for (let y = sampleStep; y < this.height - sampleStep; y += sampleStep) {
      for (let x = sampleStep; x < this.width - sampleStep; x += sampleStep) {
        const gaborResponses = [0, 45, 90, 135].map(angle => 
          this.textureAnalyzer.computeGaborResponse(x, y, 2, angle, 1.5)
        );
        
        const localEnergy = gaborResponses.reduce((sum, r) => sum + r.magnitude * r.magnitude, 0);
        totalEnergy += localEnergy;
        
        const highFreq = gaborResponses.reduce((sum, r) => sum + r.magnitude, 0);
        highFreqEnergy += highFreq;
        count++;
      }
    }

    return count > 0 ? highFreqEnergy / count : 0;
  }

  classifyComplexity() {
    const edgeDensity = this.computeEdgeDensity();
    const colorVariance = this.computeColorVariance();
    const textureComplexity = this.computeTextureComplexity();
    const colorCount = this.computeColorCount();
    const gradientMagnitude = this.computeGradientMagnitude();
    const frequencyEnergy = this.computeFrequencyFeatures();

    const edgeScore = Math.min(1, edgeDensity * 15);
    const colorVarScore = colorVariance;
    const textureScore = Math.min(1, textureComplexity.avgEntropy / 4);
    const colorCountScore = colorCount;
    const gradientScore = Math.min(1, gradientMagnitude * 2);
    const frequencyScore = Math.min(1, frequencyEnergy / 50);

    const complexityScore = (
      edgeScore * 0.25 +
      colorVarScore * 0.20 +
      textureScore * 0.25 +
      colorCountScore * 0.15 +
      gradientScore * 0.10 +
      frequencyScore * 0.05
    );

    let complexityLevel;
    let recommendedAlgorithm;
    let recommendedRadius;
    let description;

    if (complexityScore < 0.25) {
      complexityLevel = 'simple';
      recommendedAlgorithm = 'telea';
      recommendedRadius = 2;
      description = '简单背景 - 纯色或渐变背景，纹理较少';
    } else if (complexityScore < 0.5) {
      complexityLevel = 'medium';
      recommendedAlgorithm = 'edge-guided';
      recommendedRadius = 3;
      description = '中等复杂度 - 有一定纹理和边缘变化';
    } else if (complexityScore < 0.75) {
      complexityLevel = 'complex';
      recommendedAlgorithm = 'texture-preserving';
      recommendedRadius = 4;
      description = '复杂背景 - 丰富的纹理和图案，需要保持细节';
    } else {
      complexityLevel = 'very-complex';
      recommendedAlgorithm = 'advanced';
      recommendedRadius = 5;
      description = '非常复杂 - 高度细节化的纹理、图案或自然场景';
    }

    return {
      score: complexityScore,
      level: complexityLevel,
      description,
      recommended: {
        algorithm: recommendedAlgorithm,
        radius: recommendedRadius,
        iterations: complexityLevel === 'very-complex' ? 80 : 
                    complexityLevel === 'complex' ? 60 : 
                    complexityLevel === 'medium' ? 50 : 40
      },
      features: {
        edgeDensity,
        colorVariance,
        textureEntropy: textureComplexity.avgEntropy,
        textureContrast: textureComplexity.avgContrast,
        colorCount,
        gradientMagnitude,
        frequencyEnergy
      },
      scores: {
        edgeScore,
        colorVarScore,
        textureScore,
        colorCountScore,
        gradientScore,
        frequencyScore
      }
    };
  }

  static classifyImages(imagesData) {
    const classified = imagesData.map((img, index) => {
      const classifier = new ImageClassifier(img.data, img.width, img.height);
      const classification = classifier.classifyComplexity();
      return {
        index,
        name: img.name || `image_${index}`,
        width: img.width,
        height: img.height,
        ...classification
      };
    });

    const groups = {
      simple: [],
      medium: [],
      complex: [],
      'very-complex': []
    };

    classified.forEach(img => {
      groups[img.level].push(img);
    });

    return {
      images: classified,
      groups,
      groupParams: {
        simple: {
          algorithm: 'telea',
          radius: 2,
          preserveTexture: false,
          guideEdges: false
        },
        medium: {
          algorithm: 'edge-guided',
          radius: 3,
          preserveTexture: true,
          guideEdges: true
        },
        complex: {
          algorithm: 'texture-preserving',
          radius: 4,
          preserveTexture: true,
          guideEdges: true
        },
        'very-complex': {
          algorithm: 'advanced',
          radius: 5,
          preserveTexture: true,
          guideEdges: true
        }
      }
    };
  }
}

module.exports = ImageClassifier;
