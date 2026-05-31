class EdgeDetection {
  constructor(imageData, width, height) {
    this.imageData = imageData;
    this.width = width;
    this.height = height;
    this.grayImage = this.toGrayScale();
  }

  toGrayScale() {
    const gray = new Float32Array(this.width * this.height);
    for (let i = 0; i < this.width * this.height; i++) {
      const idx = i * 4;
      gray[i] = 0.299 * this.imageData[idx] + 0.587 * this.imageData[idx + 1] + 0.114 * this.imageData[idx + 2];
    }
    return gray;
  }

  getPixel(x, y) {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return 0;
    return this.grayImage[y * this.width + x];
  }

  sobelEdgeDetection() {
    const gx = new Float32Array(this.width * this.height);
    const gy = new Float32Array(this.width * this.height);
    const magnitude = new Float32Array(this.width * this.height);
    const direction = new Float32Array(this.width * this.height);

    const kx = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]];
    const ky = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]];

    for (let y = 1; y < this.height - 1; y++) {
      for (let x = 1; x < this.width - 1; x++) {
        let sx = 0, sy = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const pixel = this.getPixel(x + dx, y + dy);
            sx += kx[dy + 1][dx + 1] * pixel;
            sy += ky[dy + 1][dx + 1] * pixel;
          }
        }
        const idx = y * this.width + x;
        gx[idx] = sx;
        gy[idx] = sy;
        magnitude[idx] = Math.sqrt(sx * sx + sy * sy);
        direction[idx] = Math.atan2(sy, sx);
      }
    }

    return { gx, gy, magnitude, direction };
  }

  cannyEdgeDetection(lowThreshold = 50, highThreshold = 100) {
    const { gx, gy, magnitude, direction } = this.sobelEdgeDetection();
    
    const suppressed = this.nonMaximumSuppression(magnitude, direction);
    const edges = this.doubleThreshold(suppressed, lowThreshold, highThreshold);
    const connected = this.hysteresis(edges);

    return {
      edges: connected,
      magnitude,
      direction,
      gx,
      gy
    };
  }

  nonMaximumSuppression(magnitude, direction) {
    const result = new Float32Array(this.width * this.height);
    
    for (let y = 1; y < this.height - 1; y++) {
      for (let x = 1; x < this.width - 1; x++) {
        const idx = y * this.width + x;
        const mag = magnitude[idx];
        const angle = direction[idx];
        
        let r = 1, q = 1;
        
        if ((angle >= -Math.PI / 8 && angle < Math.PI / 8) || 
            (angle >= 7 * Math.PI / 8 && angle < -7 * Math.PI / 8)) {
          r = magnitude[idx - 1];
          q = magnitude[idx + 1];
        } else if ((angle >= Math.PI / 8 && angle < 3 * Math.PI / 8) ||
                   (angle >= -7 * Math.PI / 8 && angle < -5 * Math.PI / 8)) {
          r = magnitude[idx + this.width - 1];
          q = magnitude[idx - this.width + 1];
        } else if ((angle >= 3 * Math.PI / 8 && angle < 5 * Math.PI / 8) ||
                   (angle >= -5 * Math.PI / 8 && angle < -3 * Math.PI / 8)) {
          r = magnitude[idx - this.width];
          q = magnitude[idx + this.width];
        } else {
          r = magnitude[idx - this.width - 1];
          q = magnitude[idx + this.width + 1];
        }
        
        if (mag >= q && mag >= r) {
          result[idx] = mag;
        } else {
          result[idx] = 0;
        }
      }
    }
    
    return result;
  }

  doubleThreshold(magnitude, low, high) {
    const result = new Uint8Array(this.width * this.height);
    
    for (let i = 0; i < this.width * this.height; i++) {
      const mag = magnitude[i];
      if (mag >= high) {
        result[i] = 2;
      } else if (mag >= low) {
        result[i] = 1;
      } else {
        result[i] = 0;
      }
    }
    
    return result;
  }

  hysteresis(edges) {
    const result = new Uint8Array(this.width * this.height);
    const visited = new Set();
    
    const dfs = (x, y) => {
      const stack = [[x, y]];
      
      while (stack.length > 0) {
        const [cx, cy] = stack.pop();
        const key = `${cx},${cy}`;
        
        if (visited.has(key)) continue;
        if (cx < 1 || cx >= this.width - 1 || cy < 1 || cy >= this.height - 1) continue;
        
        visited.add(key);
        const idx = cy * this.width + cx;
        
        if (edges[idx] >= 1) {
          result[idx] = 255;
          
          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              const nx = cx + dx;
              const ny = cy + dy;
              const nidx = ny * this.width + nx;
              if (edges[nidx] >= 1 && !visited.has(`${nx},${ny}`)) {
                stack.push([nx, ny]);
              }
            }
          }
        }
      }
    };
    
    for (let y = 1; y < this.height - 1; y++) {
      for (let x = 1; x < this.width - 1; x++) {
        const idx = y * this.width + x;
        if (edges[idx] === 2 && !visited.has(`${x},${y}`)) {
          dfs(x, y);
        }
      }
    }
    
    return result;
  }

  computeEdgeTangents(edges, direction) {
    const tangents = new Float32Array(this.width * this.height * 2);
    
    for (let i = 0; i < this.width * this.height; i++) {
      if (edges[i] > 0) {
        const angle = direction[i];
        const tx = -Math.sin(angle);
        const ty = Math.cos(angle);
        tangents[i * 2] = tx;
        tangents[i * 2 + 1] = ty;
      }
    }
    
    return tangents;
  }

  findEdgeContinuity(edges, gx, gy, radius = 5) {
    const continuity = new Float32Array(this.width * this.height);
    
    for (let y = radius; y < this.height - radius; y++) {
      for (let x = radius; x < this.width - radius; x++) {
        const idx = y * this.width + x;
        if (edges[idx] === 0) continue;
        
        const edgeX = gx[idx];
        const edgeY = gy[idx];
        const edgeLen = Math.sqrt(edgeX * edgeX + edgeY * edgeY);
        
        if (edgeLen < 0.1) continue;
        
        let totalWeight = 0;
        let continuityScore = 0;
        
        for (let dy = -radius; dy <= radius; dy++) {
          for (let dx = -radius; dx <= radius; dx++) {
            if (dx === 0 && dy === 0) continue;
            
            const nx = x + dx;
            const ny = y + dy;
            const nidx = ny * this.width + nx;
            
            if (edges[nidx] === 0) continue;
            
            const dist = Math.sqrt(dx * dx + dy * dy);
            const weight = 1 / (dist + 1);
            
            const nEdgeX = gx[nidx];
            const nEdgeY = gy[nidx];
            const nEdgeLen = Math.sqrt(nEdgeX * nEdgeX + nEdgeY * nEdgeY);
            
            if (nEdgeLen < 0.1) continue;
            
            const dotProduct = (edgeX * nEdgeX + edgeY * nEdgeY) / (edgeLen * nEdgeLen);
            const angleSimilarity = Math.abs(dotProduct);
            
            const dotDir = (dx * edgeX + dy * edgeY) / (dist * edgeLen);
            const directionScore = Math.abs(dotDir);
            
            continuityScore += weight * angleSimilarity * (1 - directionScore);
            totalWeight += weight;
          }
        }
        
        if (totalWeight > 0) {
          continuity[idx] = continuityScore / totalWeight;
        }
      }
    }
    
    return continuity;
  }
}

module.exports = EdgeDetection;
