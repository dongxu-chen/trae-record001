const ImageInpainting = require('./inpainting');
const TextDetector = require('./textDetector');

class VideoProcessor {
  constructor(options = {}) {
    this.options = {
      algorithm: 'edge-guided',
      radius: 3,
      temporalWindow: 3,
      consistencyThreshold: 30,
      blendFactor: 0.3,
      detectText: true,
      guideEdges: true,
      preserveTexture: true,
      ...options
    };
    this.processedFrames = [];
    this.frameBuffer = [];
  }

  processFrame(frameData, maskData, width, height, frameIndex) {
    const inpainter = new ImageInpainting(
      frameData,
      maskData,
      width,
      height,
      {
        guideEdges: this.options.guideEdges,
        preserveTexture: this.options.preserveTexture
      }
    );

    let resultData = inpainter.inpaint(this.options.algorithm, this.options.radius);

    if (this.processedFrames.length > 0 && this.options.temporalWindow > 0) {
      resultData = this.applyTemporalConsistency(
        resultData, width, height, frameIndex
      );
    }

    this.processedFrames.push({
      data: new Uint8ClampedArray(resultData),
      width,
      height,
      index: frameIndex
    });

    this.frameBuffer.push({
      data: new Uint8ClampedArray(resultData),
      width,
      height,
      index: frameIndex
    });

    const maxBuffer = this.options.temporalWindow * 2 + 1;
    while (this.frameBuffer.length > maxBuffer) {
      this.frameBuffer.shift();
    }

    return resultData;
  }

  applyTemporalConsistency(currentFrame, width, height, frameIndex) {
    const result = new Uint8ClampedArray(currentFrame);
    const windowSize = Math.min(this.options.temporalWindow, this.processedFrames.length);

    if (windowSize === 0) return result;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4;

        const currentR = currentFrame[idx];
        const currentG = currentFrame[idx + 1];
        const currentB = currentFrame[idx + 2];

        let sumR = currentR;
        let sumG = currentG;
        let sumB = currentB;
        let weightSum = 1;

        for (let w = 1; w <= windowSize; w++) {
          const prevFrameIdx = this.processedFrames.length - w;
          if (prevFrameIdx < 0) break;

          const prevFrame = this.processedFrames[prevFrameIdx];
          const prevIdx = (y * width + x) * 4;

          const prevR = prevFrame.data[prevIdx];
          const prevG = prevFrame.data[prevIdx + 1];
          const prevB = prevFrame.data[prevIdx + 2];

          const diff = Math.abs(currentR - prevR) + Math.abs(currentG - prevG) + Math.abs(currentB - prevB);

          const temporalWeight = 1 / (w + 1);

          if (diff < this.options.consistencyThreshold * 3) {
            const consistencyWeight = temporalWeight * (1 - diff / (this.options.consistencyThreshold * 3));
            sumR += prevR * consistencyWeight;
            sumG += prevG * consistencyWeight;
            sumB += prevB * consistencyWeight;
            weightSum += consistencyWeight;
          }
        }

        const blend = this.options.blendFactor;
        result[idx] = currentR * (1 - blend) + (sumR / weightSum) * blend;
        result[idx + 1] = currentG * (1 - blend) + (sumG / weightSum) * blend;
        result[idx + 2] = currentB * (1 - blend) + (sumB / weightSum) * blend;
      }
    }

    return result;
  }

  detectTextInFrame(frameData, width, height, options = {}) {
    const detector = new TextDetector(frameData, width, height);
    return detector.detectText(options);
  }

  static extractFrameRegions(frameData, width, height, regions) {
    const extracted = [];

    for (const region of regions) {
      const { x, y, width: w, height: h } = region.bbox;
      const regionData = new Uint8ClampedArray(w * h * 4);

      for (let dy = 0; dy < h; dy++) {
        for (let dx = 0; dx < w; dx++) {
          const srcIdx = ((y + dy) * width + (x + dx)) * 4;
          const dstIdx = (dy * w + dx) * 4;

          if (y + dy < height && x + dx < width) {
            regionData[dstIdx] = frameData[srcIdx];
            regionData[dstIdx + 1] = frameData[srcIdx + 1];
            regionData[dstIdx + 2] = frameData[srcIdx + 2];
            regionData[dstIdx + 3] = frameData[srcIdx + 3];
          }
        }
      }

      extracted.push({
        data: regionData,
        bbox: region.bbox,
        confidence: region.confidence
      });
    }

    return extracted;
  }

  static trackRegions(prevRegions, currentFrame, width, height, searchRadius = 10) {
    const trackedRegions = [];

    for (const prevRegion of prevRegions) {
      const { x, y, width: w, height: h } = prevRegion.bbox;
      let bestX = x;
      let bestY = y;
      let bestDiff = Infinity;

      for (let dy = -searchRadius; dy <= searchRadius; dy += 2) {
        for (let dx = -searchRadius; dx <= searchRadius; dx += 2) {
          const nx = x + dx;
          const ny = y + dy;

          if (nx < 0 || ny < 0 || nx + w >= width || ny + h >= height) continue;

          let diff = 0;
          for (let py = 0; py < h; py += 4) {
            for (let px = 0; px < w; px += 4) {
              const idx = ((ny + py) * width + (nx + px)) * 4;
              diff += currentFrame[idx] + currentFrame[idx + 1] + currentFrame[idx + 2];
            }
          }

          if (diff < bestDiff) {
            bestDiff = diff;
            bestX = nx;
            bestY = ny;
          }
        }
      }

      trackedRegions.push({
        ...prevRegion,
        bbox: { x: bestX, y: bestY, width: w, height: h },
        tracked: true
      });
    }

    return trackedRegions;
  }

  reset() {
    this.processedFrames = [];
    this.frameBuffer = [];
  }
}

module.exports = VideoProcessor;
