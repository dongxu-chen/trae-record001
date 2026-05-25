const vertexShaderSource = `
  attribute vec2 a_position;
  attribute vec2 a_texCoord;
  varying vec2 v_texCoord;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_texCoord = a_texCoord;
  }
`;

const fragmentShaderSource = `
  precision highp float;
  varying vec2 v_texCoord;
  uniform sampler2D u_videoTexture;
  uniform sampler2D u_bgTexture;
  uniform int u_bgType;
  uniform vec3 u_bgColor;
  uniform vec3 u_bgGradientStart;
  uniform vec3 u_bgGradientEnd;
  uniform float u_blurRadius;
  uniform float u_width;
  uniform float u_height;
  
  uniform int u_beautyEnabled;
  uniform float u_smoothLevel;
  uniform float u_whitenLevel;
  uniform float u_slimLevel;
  
  vec3 tex2D(sampler2D sampler, vec2 coord) {
    return texture2D(sampler, coord).rgb;
  }
  
  vec3 blur(sampler2D sampler, vec2 coord, float radius) {
    vec3 color = vec3(0.0);
    float total = 0.0;
    float step = 1.0 / u_width * radius;
    
    for (float x = -4.0; x <= 4.0; x += 1.0) {
      for (float y = -4.0; y <= 4.0; y += 1.0) {
        float weight = exp(-(x * x + y * y) / (2.0 * radius * radius));
        color += tex2D(sampler, coord + vec2(x * step, y * step * u_width / u_height)) * weight;
        total += weight;
      }
    }
    
    return color / total;
  }
  
  vec3 bilateralFilter(sampler2D sampler, vec2 coord, float sigma_s, float sigma_r) {
    vec3 centerColor = tex2D(sampler, coord);
    vec3 result = vec3(0.0);
    float weightSum = 0.0;
    
    float step = 1.0 / u_width * sigma_s * 2.0;
    float sigma_r2 = sigma_r * sigma_r;
    
    for (float x = -3.0; x <= 3.0; x += 1.0) {
      for (float y = -3.0; y <= 3.0; y += 1.0) {
        vec2 offset = vec2(x * step, y * step * u_width / u_height);
        vec3 sampleColor = tex2D(sampler, coord + offset);
        
        float spaceDist = x * x + y * y;
        float colorDist = distance(centerColor, sampleColor);
        colorDist = colorDist * colorDist;
        
        float weight = exp(-spaceDist / (2.0 * sigma_s * sigma_s) - colorDist / (2.0 * sigma_r2));
        
        result += sampleColor * weight;
        weightSum += weight;
      }
    }
    
    return result / weightSum;
  }
  
  bool isSkinColor(vec3 color) {
    float r = color.r;
    float g = color.g;
    float b = color.b;
    
    bool cond1 = r > 0.6 && g > 0.4 && b > 0.2;
    bool cond2 = r > g && g > b;
    bool cond3 = max(r, max(g, b)) - min(r, min(g, b)) > 0.1;
    bool cond4 = abs(r - g) > 0.05;
    
    float y = 0.299 * r + 0.587 * g + 0.114 * b;
    float cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 0.5;
    float cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 0.5;
    
    bool cond5 = y > 0.3 && y < 0.95;
    bool cond6 = cb > 0.35 && cb < 0.55;
    bool cond7 = cr > 0.5 && cr < 0.7;
    
    return (cond1 && cond2 && cond3 && cond4) || (cond5 && cond6 && cond7);
  }
  
  vec3 applyWhitening(vec3 color, float level) {
    float brightness = dot(color, vec3(0.299, 0.587, 0.114));
    float factor = 1.0 + level * 0.3;
    vec3 whitened = color * factor;
    
    vec3 desat = mix(color, vec3(brightness), 0.15 * level);
    whitened = mix(whitened, desat, 0.3);
    
    whitened = clamp(whitened, 0.0, 1.0);
    return whitened;
  }
  
  vec2 applySlimFace(vec2 coord, float level) {
    vec2 center = vec2(0.5, 0.55);
    vec2 toCenter = coord - center;
    float dist = length(toCenter);
    
    float yFactor = 1.0 - abs(coord.y - 0.55) * 1.5;
    yFactor = clamp(yFactor, 0.0, 1.0);
    
    float maxDist = 0.35;
    if (dist < maxDist) {
      float factor = (1.0 - dist / maxDist) * level * 0.15 * yFactor;
      vec2 direction = normalize(toCenter);
      coord += direction * factor;
    }
    
    return coord;
  }
  
  vec3 getBackgroundColor(vec2 coord) {
    if (u_bgType == 1) {
      return blur(u_videoTexture, coord, u_blurRadius);
    } else if (u_bgType == 2) {
      return u_bgColor;
    } else if (u_bgType == 3) {
      return mix(u_bgGradientStart, u_bgGradientEnd, coord.x + coord.y);
    }
    return tex2D(u_videoTexture, coord);
  }
  
  void main() {
    vec2 texCoord = vec2(v_texCoord.x, 1.0 - v_texCoord.y);
    
    if (u_beautyEnabled == 1 && u_slimLevel > 0.0) {
      texCoord = applySlimFace(texCoord, u_slimLevel);
    }
    
    vec3 videoColor = tex2D(u_videoTexture, texCoord);
    vec3 bgColor = getBackgroundColor(texCoord);
    
    if (u_beautyEnabled == 1) {
      bool isSkin = isSkinColor(videoColor);
      
      if (isSkin) {
        vec3 smoothed = bilateralFilter(u_videoTexture, texCoord, u_smoothLevel * 2.0 + 1.0, 0.1 + u_smoothLevel * 0.1);
        videoColor = mix(videoColor, smoothed, u_smoothLevel * 0.8);
        
        if (u_whitenLevel > 0.0) {
          vec3 whitened = applyWhitening(videoColor, u_whitenLevel);
          videoColor = mix(videoColor, whitened, u_whitenLevel);
        }
      }
    }
    
    float gray = dot(videoColor, vec3(0.299, 0.587, 0.114));
    float y = texCoord.y;
    float centerDist = length(texCoord - vec2(0.5, 0.5));
    
    float edge = smoothstep(0.2, 0.4, centerDist);
    float alpha = 0.85 + edge * 0.15;
    
    vec3 finalColor = mix(bgColor, videoColor, alpha);
    
    gl_FragColor = vec4(finalColor, 1.0);
  }
`;

class WebGLVirtualBackground {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl', { 
      preserveDrawingBuffer: false,
      alpha: false,
      antialias: false
    });

    if (!this.gl) {
      throw new Error('WebGL not supported');
    }

    this.program = null;
    this.videoTexture = null;
    this.bgTexture = null;
    this.videoElement = null;
    this.frameId = null;
    this.isRunning = false;
    this.bgType = 0;
    this.bgColor = [0.15, 0.39, 0.92];
    this.bgGradientStart = [0.13, 0.77, 0.37];
    this.bgGradientEnd = [0.08, 0.5, 0.24];
    this.blurRadius = 15;

    this.beautyEnabled = false;
    this.smoothLevel = 0.5;
    this.whitenLevel = 0.3;
    this.slimLevel = 0.2;

    this._initGL();
  }

  _initGL() {
    const gl = this.gl;

    const vertexShader = this._createShader(gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = this._createShader(gl.FRAGMENT_SHADER, fragmentShaderSource);

    this.program = gl.createProgram();
    gl.attachShader(this.program, vertexShader);
    gl.attachShader(this.program, fragmentShader);
    gl.linkProgram(this.program);

    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      throw new Error('Shader program link failed');
    }

    gl.useProgram(this.program);

    const positions = new Float32Array([
      -1, -1,  0, 0,
       1, -1,  1, 0,
      -1,  1,  0, 1,
       1,  1,  1, 1
    ]);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

    const positionLoc = gl.getAttribLocation(this.program, 'a_position');
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 16, 0);

    const texCoordLoc = gl.getAttribLocation(this.program, 'a_texCoord');
    gl.enableVertexAttribArray(texCoordLoc);
    gl.vertexAttribPointer(texCoordLoc, 2, gl.FLOAT, false, 16, 8);

    this.videoTexture = this._createTexture();
    this.bgTexture = this._createTexture();

    gl.uniform1i(gl.getUniformLocation(this.program, 'u_videoTexture'), 0);
    gl.uniform1i(gl.getUniformLocation(this.program, 'u_bgTexture'), 1);

    this._updateUniforms();
  }

  _createShader(type, source) {
    const gl = this.gl;
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error('Shader compile failed: ' + gl.getShaderInfoLog(shader));
    }

    return shader;
  }

  _createTexture() {
    const gl = this.gl;
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    return texture;
  }

  _updateUniforms() {
    const gl = this.gl;
    gl.useProgram(this.program);

    gl.uniform1i(gl.getUniformLocation(this.program, 'u_bgType'), this.bgType);
    gl.uniform3fv(gl.getUniformLocation(this.program, 'u_bgColor'), this.bgColor);
    gl.uniform3fv(gl.getUniformLocation(this.program, 'u_bgGradientStart'), this.bgGradientStart);
    gl.uniform3fv(gl.getUniformLocation(this.program, 'u_bgGradientEnd'), this.bgGradientEnd);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_blurRadius'), this.blurRadius);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_width'), this.canvas.width);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_height'), this.canvas.height);

    gl.uniform1i(gl.getUniformLocation(this.program, 'u_beautyEnabled'), this.beautyEnabled ? 1 : 0);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_smoothLevel'), this.smoothLevel);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_whitenLevel'), this.whitenLevel);
    gl.uniform1f(gl.getUniformLocation(this.program, 'u_slimLevel'), this.slimLevel);
  }

  setBackground(config) {
    if (!config || config.type === 'none') {
      this.bgType = 0;
      this.stop();
      return;
    }

    if (config.type === 'blur') {
      this.bgType = 1;
      this.blurRadius = config.radius || 15;
    } else if (config.type === 'color') {
      this.bgType = 2;
      this.bgColor = this._hexToRgb(config.color);
    } else if (config.type === 'gradient') {
      this.bgType = 3;
      this.bgGradientStart = this._hexToRgb(config.colors[0]);
      this.bgGradientEnd = this._hexToRgb(config.colors[1]);
    }

    this._updateUniforms();

    if (this.videoElement && !this.isRunning) {
      this.start(this.videoElement);
    }
  }

  setBeauty(config) {
    if (!config) {
      this.beautyEnabled = false;
    } else {
      this.beautyEnabled = config.enabled !== false;
      if (typeof config.smoothLevel === 'number') this.smoothLevel = Math.max(0, Math.min(1, config.smoothLevel));
      if (typeof config.whitenLevel === 'number') this.whitenLevel = Math.max(0, Math.min(1, config.whitenLevel));
      if (typeof config.slimLevel === 'number') this.slimLevel = Math.max(0, Math.min(1, config.slimLevel));
    }

    this._updateUniforms();

    if (this.videoElement && !this.isRunning) {
      this.start(this.videoElement);
    }
  }

  setBeautyEnabled(enabled) {
    this.beautyEnabled = enabled;
    this._updateUniforms();
    
    if (enabled && this.videoElement && !this.isRunning) {
      this.start(this.videoElement);
    }
  }

  setSmoothLevel(level) {
    this.smoothLevel = Math.max(0, Math.min(1, level));
    this._updateUniforms();
  }

  setWhitenLevel(level) {
    this.whitenLevel = Math.max(0, Math.min(1, level));
    this._updateUniforms();
  }

  setSlimLevel(level) {
    this.slimLevel = Math.max(0, Math.min(1, level));
    this._updateUniforms();
  }

  _hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
      parseInt(result[1], 16) / 255,
      parseInt(result[2], 16) / 255,
      parseInt(result[3], 16) / 255
    ] : [0, 0, 0];
  }

  start(videoElement) {
    if (!videoElement) return;
    
    this.videoElement = videoElement;
    this.isRunning = true;

    if (this.bgType === 0 && !this.beautyEnabled) {
      return;
    }

    this._renderLoop();
  }

  stop() {
    this.isRunning = false;
    if (this.frameId) {
      cancelAnimationFrame(this.frameId);
      this.frameId = null;
    }
  }

  _renderLoop = () => {
    if (!this.isRunning || !this.videoElement || (this.bgType === 0 && !this.beautyEnabled)) {
      return;
    }

    const gl = this.gl;

    if (this.videoElement.readyState === this.videoElement.HAVE_ENOUGH_DATA) {
      if (this.canvas.width !== this.videoElement.videoWidth ||
          this.canvas.height !== this.videoElement.videoHeight) {
        this.canvas.width = this.videoElement.videoWidth;
        this.canvas.height = this.videoElement.videoHeight;
        gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        this._updateUniforms();
      }

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.videoTexture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, this.videoElement);

      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    this.frameId = requestAnimationFrame(this._renderLoop);
  };

  getCanvasStream() {
    return this.canvas.captureStream(30);
  }

  destroy() {
    this.stop();
    
    const gl = this.gl;
    if (this.program) {
      gl.deleteProgram(this.program);
    }
    if (this.videoTexture) {
      gl.deleteTexture(this.videoTexture);
    }
    if (this.bgTexture) {
      gl.deleteTexture(this.bgTexture);
    }
  }
}

export default WebGLVirtualBackground;
