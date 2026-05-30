export type FilterType = 'dreamy' | 'backlight' | 'neon' | 'starburst' | 'custom';

export type ShaderUniformType = 'float' | 'vec2' | 'vec3' | 'vec4';

export interface ShaderUniformDef {
  name: string;
  type: ShaderUniformType;
  defaultValue: number | number[];
  min?: number;
  max?: number;
}

export interface FilterDefinition {
  id: FilterType;
  name: string;
  description: string;
  color: string;
  uniforms: ShaderUniformDef[];
}

export interface BrightnessAnalysis {
  center: { x: number; y: number };
  angle: number;
  maxBrightness: number;
}

export interface BatchProcessItem {
  image: HTMLImageElement;
  filterType: string;
  intensity: number;
  params: Record<string, number | number[]>;
}

export interface ShaderValidationResult {
  valid: boolean;
  error?: string;
  lineNumber?: number;
}

export const FILTER_DEFINITIONS: FilterDefinition[] = [
  {
    id: 'dreamy',
    name: '梦幻',
    description: '柔和模糊 + 色彩偏移 + 光晕叠加，营造梦幻氛围',
    color: '#B24BF3',
    uniforms: [
      { name: 'uBlurRadius', type: 'float', defaultValue: 0.5, min: 0, max: 1 },
      { name: 'uGlowColor', type: 'vec3', defaultValue: [1.0, 0.8, 0.95], min: 0, max: 1 },
    ],
  },
  {
    id: 'backlight',
    name: '逆光',
    description: '径向渐变光源 + 镜头光晕，营造温暖逆光效果',
    color: '#FFB800',
    uniforms: [
      { name: 'uLightPos', type: 'vec2', defaultValue: [0.5, 0.5], min: 0, max: 1 },
      { name: 'uFlareSize', type: 'float', defaultValue: 0.6, min: 0.1, max: 2 },
    ],
  },
  {
    id: 'neon',
    name: '霓虹',
    description: '边缘检测 + 发光描边 + 饱和增强，赛博朋克风格',
    color: '#00F5D4',
    uniforms: [
      { name: 'uGlowWidth', type: 'float', defaultValue: 2.0, min: 0.5, max: 5 },
      { name: 'uNeonColor', type: 'vec3', defaultValue: [0.0, 0.96, 0.83], min: 0, max: 1 },
    ],
  },
  {
    id: 'starburst',
    name: '星芒',
    description: '极坐标放射光线 + 十字光芒，自动检测亮区方向',
    color: '#FF2E97',
    uniforms: [
      { name: 'uRayCount', type: 'float', defaultValue: 16, min: 4, max: 32 },
      { name: 'uRayLength', type: 'float', defaultValue: 0.7, min: 0.2, max: 2 },
      { name: 'uBrightCenter', type: 'vec2', defaultValue: [0.5, 0.5], min: 0, max: 1 },
      { name: 'uBrightAngle', type: 'float', defaultValue: 0, min: -3.14159, max: 3.14159 },
    ],
  },
];

interface ProgramInfo {
  program: WebGLProgram;
  uniforms: Map<string, WebGLUniformLocation>;
  fragmentSource: string;
}

interface ProgramBackup {
  program: WebGLProgram | null;
  uniforms: Map<string, WebGLUniformLocation>;
  fragmentSource: string;
}

const FORBIDDEN_PATTERNS = [
  /\bwhile\s*\(/,
  /\bfor\s*\(\s*;;\s*\)/,
  /infinite\s*loop/i,
  /discard\s*\(/,
  /\bgl_FragDepth\b/,
];

const SANDBOX_VERTEX_SOURCE = `#version 300 es
in vec2 aPosition;
in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
  vTexCoord = aTexCoord;
  gl_Position = vec4(aPosition, 0.0, 1.0);
}
`;

export class ShaderManager {
  private gl: WebGL2RenderingContext;
  private canvas: HTMLCanvasElement;
  private programs: Map<string, ProgramInfo> = new Map();
  private activeProgram: ProgramInfo | null = null;
  private texture: WebGLTexture | null = null;
  private vao: WebGLVertexArrayObject | null = null;
  private imageSize: { width: number; height: number } | null = null;
  private customUniforms: ShaderUniformDef[] = [];
  private brightnessAnalysis: BrightnessAnalysis | null = null;
  private analysisCanvas: HTMLCanvasElement | null = null;
  private programBackup: ProgramBackup | null = null;
  private currentFilter: string = '';

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl2', {
      preserveDrawingBuffer: true,
      antialias: false,
    });
    if (!gl) {
      throw new Error('WebGL2 is not supported');
    }
    this.gl = gl;
    this.initVAO();
  }

  private initVAO() {
    const gl = this.gl;
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    this.vao = vao;

    const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const texCoords = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);

    const posBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    const texBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, texBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, texCoords, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 0, 0);

    gl.bindVertexArray(null);
  }

  validateShaderSyntax(source: string): ShaderValidationResult {
    for (const pattern of FORBIDDEN_PATTERNS) {
      const match = source.match(pattern);
      if (match) {
        const lineNumber = source.substring(0, match.index || 0).split('\n').length;
        return {
          valid: false,
          error: `不支持的语法: ${match[0]}`,
          lineNumber,
        };
      }
    }

    if (!source.includes('#version 300 es')) {
      return {
        valid: false,
        error: '缺少 #version 300 es 声明',
        lineNumber: 1,
      };
    }

    if (!source.includes('void main()')) {
      return {
        valid: false,
        error: '缺少 main() 函数',
      };
    }

    if (!source.includes('fragColor')) {
      return {
        valid: false,
        error: '缺少 fragColor 输出变量',
      };
    }

    if (!source.includes('out vec4 fragColor')) {
      return {
        valid: false,
        error: '缺少 out vec4 fragColor 声明',
      };
    }

    return { valid: true };
  }

  compileShaderInSandbox(
    fragmentSource: string
  ): { program: WebGLProgram; uniforms: Map<string, WebGLUniformLocation> } | null {
    const gl = this.gl;

    try {
      const vertShader = this.compileShader(SANDBOX_VERTEX_SOURCE, gl.VERTEX_SHADER);
      const fragShader = this.compileShader(fragmentSource, gl.FRAGMENT_SHADER);

      const program = this.createProgram(vertShader, fragShader);

      gl.deleteShader(vertShader);
      gl.deleteShader(fragShader);

      const uniforms = new Map<string, WebGLUniformLocation>();
      const uniformNames = [
        'uTexture',
        'uResolution',
        'uIntensity',
        'uBlurRadius',
        'uGlowColor',
        'uLightPos',
        'uFlareSize',
        'uGlowWidth',
        'uNeonColor',
        'uRayCount',
        'uRayLength',
        'uBrightCenter',
        'uBrightAngle',
      ];

      for (const name of uniformNames) {
        const loc = gl.getUniformLocation(program, name);
        if (loc) {
          uniforms.set(name, loc);
        }
      }

      return { program, uniforms };
    } catch (error) {
      return null;
    }
  }

  registerFilterWithRollback(
    filterName: string,
    vertexSource: string,
    fragmentSource: string
  ): { success: boolean; error?: string } {
    const syntaxCheck = this.validateShaderSyntax(fragmentSource);
    if (!syntaxCheck.valid) {
      return {
        success: false,
        error: `语法错误 (行 ${syntaxCheck.lineNumber || '?'}): ${syntaxCheck.error}`,
      };
    }

    const existing = this.programs.get(filterName);
    if (existing) {
      this.programBackup = {
        program: existing.program,
        uniforms: new Map(existing.uniforms),
        fragmentSource: existing.fragmentSource,
      };
    }

    try {
      const gl = this.gl;
      const vertShader = this.compileShader(vertexSource, gl.VERTEX_SHADER);
      const fragShader = this.compileShader(fragmentSource, gl.FRAGMENT_SHADER);
      const program = this.createProgram(vertShader, fragShader);

      gl.deleteShader(vertShader);
      gl.deleteShader(fragShader);

      const sandboxResult = this.compileShaderInSandbox(fragmentSource);
      if (!sandboxResult) {
        gl.deleteProgram(program);
        this.rollbackProgram(filterName);
        return { success: false, error: '沙箱执行验证失败' };
      }
      gl.deleteProgram(sandboxResult.program);

      const uniforms = new Map<string, WebGLUniformLocation>();
      const uniformNames = [
        'uTexture',
        'uResolution',
        'uIntensity',
        'uBlurRadius',
        'uGlowColor',
        'uLightPos',
        'uFlareSize',
        'uGlowWidth',
        'uNeonColor',
        'uRayCount',
        'uRayLength',
        'uBrightCenter',
        'uBrightAngle',
      ];

      for (const name of uniformNames) {
        const loc = gl.getUniformLocation(program, name);
        if (loc) {
          uniforms.set(name, loc);
        }
      }

      if (existing) {
        gl.deleteProgram(existing.program);
      }

      this.programs.set(filterName, { program, uniforms, fragmentSource });
      this.programBackup = null;

      return { success: true };
    } catch (error) {
      this.rollbackProgram(filterName);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误',
      };
    }
  }

  private rollbackProgram(filterName: string) {
    if (this.programBackup && this.programBackup.program) {
      this.programs.set(filterName, {
        program: this.programBackup.program,
        uniforms: this.programBackup.uniforms,
        fragmentSource: this.programBackup.fragmentSource,
      });
      this.programBackup = null;
    }
  }

  compileShader(source: string, type: number): WebGLShader {
    const gl = this.gl;
    const shader = gl.createShader(type);
    if (!shader) {
      throw new Error('Failed to create shader');
    }
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compile error: ${error}`);
    }
    return shader;
  }

  createProgram(
    vertexShader: WebGLShader,
    fragmentShader: WebGLShader
  ): WebGLProgram {
    const gl = this.gl;
    const program = gl.createProgram();
    if (!program) {
      throw new Error('Failed to create program');
    }
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.bindAttribLocation(program, 0, 'aPosition');
    gl.bindAttribLocation(program, 1, 'aTexCoord');
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`Program link error: ${error}`);
    }
    return program;
  }

  registerFilter(
    filterName: string,
    vertexSource: string,
    fragmentSource: string
  ) {
    const result = this.registerFilterWithRollback(filterName, vertexSource, fragmentSource);
    if (!result.success) {
      throw new Error(result.error);
    }
  }

  registerCustomFilter(
    fragmentSource: string,
    uniforms: ShaderUniformDef[]
  ): { success: boolean; filterName?: string; error?: string } {
    const syntaxCheck = this.validateShaderSyntax(fragmentSource);
    if (!syntaxCheck.valid) {
      return {
        success: false,
        error: `语法错误 (行 ${syntaxCheck.lineNumber || '?'}): ${syntaxCheck.error}`,
      };
    }

    const filterName = `custom_${Date.now()}`;
    const gl = this.gl;

    try {
      const sandboxResult = this.compileShaderInSandbox(fragmentSource);
      if (!sandboxResult) {
        return { success: false, error: '着色器验证失败' };
      }
      gl.deleteProgram(sandboxResult.program);

      const vertShader = this.compileShader(
        `#version 300 es
in vec2 aPosition;
in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
  vTexCoord = aTexCoord;
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`,
        gl.VERTEX_SHADER
      );
      const fragShader = this.compileShader(fragmentSource, gl.FRAGMENT_SHADER);
      const program = this.createProgram(vertShader, fragShader);

      gl.deleteShader(vertShader);
      gl.deleteShader(fragShader);

      const uniformMap = new Map<string, WebGLUniformLocation>();
      const baseUniforms = ['uTexture', 'uResolution', 'uIntensity'];
      for (const name of baseUniforms) {
        const loc = gl.getUniformLocation(program, name);
        if (loc) uniformMap.set(name, loc);
      }
      for (const uniform of uniforms) {
        const loc = gl.getUniformLocation(program, uniform.name);
        if (loc) uniformMap.set(uniform.name, loc);
      }

      this.programs.set(filterName, { program, uniforms: uniformMap, fragmentSource });
      this.customUniforms = uniforms;

      return { success: true, filterName };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '编译失败',
      };
    }
  }

  analyzeBrightness(image: HTMLImageElement | HTMLCanvasElement): BrightnessAnalysis {
    if (!this.analysisCanvas) {
      this.analysisCanvas = document.createElement('canvas');
      this.analysisCanvas.width = 64;
      this.analysisCanvas.height = 64;
    }

    const analysisCtx = this.analysisCanvas.getContext('2d');
    if (!analysisCtx) {
      return { center: { x: 0.5, y: 0.5 }, angle: 0, maxBrightness: 0 };
    }

    const canvas = this.analysisCanvas;
    analysisCtx.drawImage(image, 0, 0, canvas.width, canvas.height);

    const imageData = analysisCtx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    let totalWeight = 0;
    let weightedX = 0;
    let weightedY = 0;
    let maxBrightness = 0;

    const momentX = new Float32Array(180);
    const momentY = new Float32Array(180);

    for (let y = 0; y < canvas.height; y++) {
      for (let x = 0; x < canvas.width; x++) {
        const i = (y * canvas.width + x) * 4;
        const r = data[i] / 255;
        const g = data[i + 1] / 255;
        const b = data[i + 2] / 255;
        const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
        const weight = brightness * brightness;

        const nx = x / canvas.width;
        const ny = y / canvas.height;

        totalWeight += weight;
        weightedX += nx * weight;
        weightedY += ny * weight;

        if (brightness > maxBrightness) {
          maxBrightness = brightness;
        }

        const angle = Math.atan2(ny - 0.5, nx - 0.5);
        const angleIndex = Math.floor(((angle + Math.PI) / (2 * Math.PI)) * 180) % 180;
        const orthogonalAngle = angle + Math.PI / 2;
        const orthIndex = Math.floor(((orthogonalAngle + Math.PI) / (2 * Math.PI)) * 180) % 180;

        const dx = nx - 0.5;
        const dy = ny - 0.5;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const edgeWeight = brightness * Math.exp(-dist * 2);

        momentX[angleIndex] += Math.cos(angle * 2) * edgeWeight;
        momentY[angleIndex] += Math.sin(angle * 2) * edgeWeight;
        momentX[orthIndex] += Math.cos(orthogonalAngle * 2) * edgeWeight * 0.5;
        momentY[orthIndex] += Math.sin(orthogonalAngle * 2) * edgeWeight * 0.5;
      }
    }

    const centerX = totalWeight > 0 ? weightedX / totalWeight : 0.5;
    const centerY = totalWeight > 0 ? weightedY / totalWeight : 0.5;

    let maxMoment = 0;
    let dominantAngle = 0;
    for (let i = 0; i < 180; i++) {
      const moment = Math.sqrt(momentX[i] * momentX[i] + momentY[i] * momentY[i]);
      if (moment > maxMoment) {
        maxMoment = moment;
        dominantAngle = Math.atan2(momentY[i], momentX[i]) / 2;
      }
    }

    this.brightnessAnalysis = {
      center: { x: centerX, y: centerY },
      angle: dominantAngle,
      maxBrightness,
    };

    return this.brightnessAnalysis;
  }

  getBrightnessAnalysis(): BrightnessAnalysis | null {
    return this.brightnessAnalysis;
  }

  switchFilter(filterName: string): boolean {
    const programInfo = this.programs.get(filterName);
    if (!programInfo) {
      return false;
    }
    this.activeProgram = programInfo;
    this.currentFilter = filterName;
    return true;
  }

  setUniform(name: string, value: number | number[]) {
    if (!this.activeProgram) return;
    const loc = this.activeProgram.uniforms.get(name);
    if (!loc) return;

    const gl = this.gl;
    gl.useProgram(this.activeProgram.program);

    if (typeof value === 'number') {
      gl.uniform1f(loc, value);
    } else if (Array.isArray(value)) {
      switch (value.length) {
        case 1:
          gl.uniform1f(loc, value[0]);
          break;
        case 2:
          gl.uniform2f(loc, value[0], value[1]);
          break;
        case 3:
          gl.uniform3f(loc, value[0], value[1], value[2]);
          break;
        case 4:
          gl.uniform4f(loc, value[0], value[1], value[2], value[3]);
          break;
      }
    }
  }

  loadTexture(image: HTMLImageElement | HTMLCanvasElement) {
    const gl = this.gl;

    if (this.texture) {
      gl.deleteTexture(this.texture);
    }

    const texture = gl.createTexture();
    if (!texture) {
      throw new Error('Failed to create texture');
    }

    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

    this.texture = texture;
    this.imageSize = { width: image.width, height: image.height };

    if (this.currentFilter === 'starburst') {
      this.analyzeBrightness(image);
    }
  }

  render() {
    if (!this.activeProgram || !this.texture || !this.imageSize) {
      return;
    }

    if (this.currentFilter === 'starburst' && this.brightnessAnalysis) {
      this.setUniform('uBrightCenter', [
        this.brightnessAnalysis.center.x,
        this.brightnessAnalysis.center.y,
      ]);
      this.setUniform('uBrightAngle', this.brightnessAnalysis.angle);
    }

    const gl = this.gl;
    const { width, height } = this.canvas;

    gl.viewport(0, 0, width, height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.useProgram(this.activeProgram.program);
    gl.bindVertexArray(this.vao);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.texture);

    const textureLoc = this.activeProgram.uniforms.get('uTexture');
    if (textureLoc) {
      gl.uniform1i(textureLoc, 0);
    }

    const resolutionLoc = this.activeProgram.uniforms.get('uResolution');
    if (resolutionLoc) {
      gl.uniform2f(resolutionLoc, width, height);
    }

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.bindVertexArray(null);
  }

  async batchProcess(
    items: BatchProcessItem[],
    onProgress?: (index: number, total: number) => void
  ): Promise<Uint8ClampedArray[]> {
    const results: Uint8ClampedArray[] = [];
    const gl = this.gl;

    const savedState = {
      activeProgram: this.activeProgram,
      texture: this.texture,
      imageSize: this.imageSize,
      canvasSize: { width: this.canvas.width, height: this.canvas.height },
    };

    try {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const programInfo = this.programs.get(item.filterType);
        if (!programInfo) {
          results.push(new Uint8ClampedArray());
          continue;
        }

        this.activeProgram = programInfo;
        this.currentFilter = item.filterType;

        this.canvas.width = item.image.width;
        this.canvas.height = item.image.height;

        this.loadTexture(item.image);

        if (item.filterType === 'starburst') {
          this.analyzeBrightness(item.image);
        }

        this.setUniform('uIntensity', item.intensity);

        for (const [name, value] of Object.entries(item.params)) {
          this.setUniform(name, value);
        }

        this.render();

        const pixels = new Uint8Array(this.canvas.width * this.canvas.height * 4);
        gl.readPixels(0, 0, this.canvas.width, this.canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

        results.push(new Uint8ClampedArray(pixels));

        if (onProgress) {
          onProgress(i + 1, items.length);
        }

        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    } finally {
      this.activeProgram = savedState.activeProgram;
      this.texture = savedState.texture;
      this.imageSize = savedState.imageSize;
      this.canvas.width = savedState.canvasSize.width;
      this.canvas.height = savedState.canvasSize.height;
    }

    return results;
  }

  readPixels(): Uint8Array {
    const gl = this.gl;
    const { width, height } = this.canvas;
    const pixels = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    return pixels;
  }

  getImageSize(): { width: number; height: number } | null {
    return this.imageSize;
  }

  getGL(): WebGL2RenderingContext {
    return this.gl;
  }

  destroy() {
    const gl = this.gl;
    if (this.vao) gl.deleteVertexArray(this.vao);
    if (this.texture) gl.deleteTexture(this.texture);
    for (const info of this.programs.values()) {
      gl.deleteProgram(info.program);
    }
    this.programs.clear();
    if (this.analysisCanvas) {
      this.analysisCanvas = null;
    }
  }
}
