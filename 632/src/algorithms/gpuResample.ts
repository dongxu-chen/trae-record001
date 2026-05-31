const UPSCALE_VS = `
attribute vec2 a_position;
attribute vec2 a_texCoord;
varying vec2 v_texCoord;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
  v_texCoord = a_texCoord;
}
`;

const UPSCALE_FS = `
precision highp float;
varying vec2 v_texCoord;
uniform sampler2D u_image;
uniform vec2 u_texSize;
uniform float u_scale;

vec4 textureBicubic(sampler2D tex, vec2 texCoords) {
  vec2 texSize = u_texSize;
  vec2 invTexSize = 1.0 / texSize;
  vec2 p = texCoords * texSize - 0.5;
  vec2 f = fract(p);
  vec2 c = p - f;

  float a = f.x;
  float b = f.y;

  vec2 s0 = (c + 0.5 - 1.0) * invTexSize;
  vec2 s1 = (c + 0.5) * invTexSize;
  vec2 s2 = (c + 0.5 + 1.0) * invTexSize;
  vec2 s3 = (c + 0.5 + 2.0) * invTexSize;

  float w0 = (-a*a*a + 3.0*a*a - 3.0*a + 1.0) / 6.0;
  float w1 = (3.0*a*a*a - 6.0*a*a + 4.0) / 6.0;
  float w2 = (-3.0*a*a*a + 3.0*a*a + 3.0*a + 1.0) / 6.0;
  float w3 = a*a*a / 6.0;

  float h0 = (-b*b*b + 3.0*b*b - 3.0*b + 1.0) / 6.0;
  float h1 = (3.0*b*b*b - 6.0*b*b + 4.0) / 6.0;
  float h2 = (-3.0*b*b*b + 3.0*b*b + 3.0*b + 1.0) / 6.0;
  float h3 = b*b*b / 6.0;

  vec4 result = vec4(0.0);
  result += texture2D(tex, vec2(s0.x, s0.y)) * w0 * h0;
  result += texture2D(tex, vec2(s1.x, s0.y)) * w1 * h0;
  result += texture2D(tex, vec2(s2.x, s0.y)) * w2 * h0;
  result += texture2D(tex, vec2(s3.x, s0.y)) * w3 * h0;
  result += texture2D(tex, vec2(s0.x, s1.y)) * w0 * h1;
  result += texture2D(tex, vec2(s1.x, s1.y)) * w1 * h1;
  result += texture2D(tex, vec2(s2.x, s1.y)) * w2 * h1;
  result += texture2D(tex, vec2(s3.x, s1.y)) * w3 * h1;
  result += texture2D(tex, vec2(s0.x, s2.y)) * w0 * h2;
  result += texture2D(tex, vec2(s1.x, s2.y)) * w1 * h2;
  result += texture2D(tex, vec2(s2.x, s2.y)) * w2 * h2;
  result += texture2D(tex, vec2(s3.x, s2.y)) * w3 * h2;
  result += texture2D(tex, vec2(s0.x, s3.y)) * w0 * h3;
  result += texture2D(tex, vec2(s1.x, s3.y)) * w1 * h3;
  result += texture2D(tex, vec2(s2.x, s3.y)) * w2 * h3;
  result += texture2D(tex, vec2(s3.x, s3.y)) * w3 * h3;

  return result;
}

void main() {
  gl_FragColor = textureBicubic(u_image, v_texCoord);
}
`;

const DOWNSCALE_FS = `
precision highp float;
varying vec2 v_texCoord;
uniform sampler2D u_image;
uniform vec2 u_texSize;
uniform float u_scale;

void main() {
  vec2 pixelSize = 1.0 / u_texSize;
  vec2 boxSize = pixelSize * u_scale;
  vec2 baseUV = v_texCoord - boxSize * 0.5;

  vec4 color = vec4(0.0);
  float totalWeight = 0.0;
  int samples = int(u_scale);
  if (samples < 2) samples = 2;
  if (samples > 8) samples = 8;

  for (int y = 0; y < 8; y++) {
    if (y >= samples) break;
    for (int x = 0; x < 8; x++) {
      if (x >= samples) break;
      vec2 offset = (vec2(float(x), float(y)) + 0.5) / float(samples) * boxSize;
      vec4 sampleColor = texture2D(u_image, baseUV + offset);
      color += sampleColor;
      totalWeight += 1.0;
    }
  }

  gl_FragColor = color / totalWeight;
}
`;

let glCanvas: HTMLCanvasElement | null = null;
let gl: WebGLRenderingContext | null = null;
let upscaleProgram: WebGLProgram | null = null;
let downscaleProgram: WebGLProgram | null = null;
let quadBuffer: WebGLBuffer | null = null;

function initWebGL(): boolean {
  if (gl) return true;

  glCanvas = document.createElement('canvas');
  gl = glCanvas.getContext('webgl', {
    preserveDrawingBuffer: true,
    premultipliedAlpha: false,
    antialias: false
  });

  if (!gl) {
    console.warn('WebGL不可用，回退到CPU处理');
    return false;
  }

  upscaleProgram = createProgram(gl, UPSCALE_VS, UPSCALE_FS);
  downscaleProgram = createProgram(gl, UPSCALE_VS, DOWNSCALE_FS);

  if (!upscaleProgram || !downscaleProgram) {
    gl = null;
    return false;
  }

  const vertices = new Float32Array([
    -1, -1, 0, 0,
     1, -1, 1, 0,
    -1,  1, 0, 1,
     1,  1, 1, 1,
  ]);

  quadBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

  return true;
}

function createShader(gl: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error('Shader编译错误:', gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function createProgram(gl: WebGLRenderingContext, vsSource: string, fsSource: string): WebGLProgram | null {
  const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
  if (!vs || !fs) return null;

  const program = gl.createProgram();
  if (!program) return null;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('Program链接错误:', gl.getProgramInfoLog(program));
    gl.deleteProgram(program);
    return null;
  }

  return program;
}

function uploadTexture(gl: WebGLRenderingContext, imageData: ImageData): WebGLTexture | null {
  const texture = gl.createTexture();
  if (!texture) return null;

  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, imageData.width, imageData.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, imageData.data);

  return texture;
}

function drawQuad(gl: WebGLRenderingContext, program: WebGLProgram) {
  gl.useProgram(program);

  const posLoc = gl.getAttribLocation(program, 'a_position');
  const texLoc = gl.getAttribLocation(program, 'a_texCoord');

  gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);

  gl.enableVertexAttribArray(posLoc);
  gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 16, 0);

  gl.enableVertexAttribArray(texLoc);
  gl.vertexAttribPointer(texLoc, 2, gl.FLOAT, false, 16, 8);

  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}

function readPixels(gl: WebGLRenderingContext, width: number, height: number): ImageData {
  const pixels = new Uint8ClampedArray(width * height * 4);
  gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

  const result = new ImageData(width, height);
  for (let y = 0; y < height; y++) {
    const srcRow = (height - 1 - y) * width * 4;
    const dstRow = y * width * 4;
    for (let x = 0; x < width * 4; x++) {
      result.data[dstRow + x] = pixels[srcRow + x];
    }
  }

  return result;
}

export function gpuResize(
  imageData: ImageData,
  newWidth: number,
  newHeight: number,
  mode: 'bicubic' | 'box' = 'bicubic'
): ImageData {
  if (!initWebGL() || !gl || !glCanvas) {
    return cpuFallbackResize(imageData, newWidth, newHeight);
  }

  const currentGL = gl;
  const canvas = glCanvas;

  const texture = uploadTexture(currentGL, imageData);
  if (!texture) {
    return cpuFallbackResize(imageData, newWidth, newHeight);
  }

  canvas.width = newWidth;
  canvas.height = newHeight;
  currentGL.viewport(0, 0, newWidth, newHeight);

  const program = mode === 'box' ? downscaleProgram! : upscaleProgram!;
  currentGL.useProgram(program);

  const texSizeLoc = currentGL.getUniformLocation(program, 'u_texSize');
  const scaleLoc = currentGL.getUniformLocation(program, 'u_scale');
  const imageLoc = currentGL.getUniformLocation(program, 'u_image');

  currentGL.uniform2f(texSizeLoc, imageData.width, imageData.height);
  if (mode === 'box') {
    const scaleX = newWidth > 0 ? imageData.width / newWidth : 1;
    const scaleY = newHeight > 0 ? imageData.height / newHeight : 1;
    currentGL.uniform1f(scaleLoc, Math.max(scaleX, scaleY));
  }
  currentGL.uniform1i(imageLoc, 0);

  currentGL.activeTexture(currentGL.TEXTURE0);
  currentGL.bindTexture(currentGL.TEXTURE_2D, texture);

  drawQuad(currentGL, program);

  const result = readPixels(currentGL, newWidth, newHeight);

  currentGL.deleteTexture(texture);

  return result;
}

export function gpuSSAAUpscale(
  imageData: ImageData,
  scale: number
): ImageData {
  const upW = imageData.width * scale;
  const upH = imageData.height * scale;
  const upscaled = gpuResize(imageData, upW, upH, 'bicubic');
  return gpuResize(upscaled, imageData.width, imageData.height, 'box');
}

function cpuFallbackResize(
  imageData: ImageData,
  newWidth: number,
  newHeight: number
): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = newWidth;
  canvas.height = newHeight;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new ImageData(newWidth, newHeight);

  const srcCanvas = document.createElement('canvas');
  srcCanvas.width = imageData.width;
  srcCanvas.height = imageData.height;
  const srcCtx = srcCanvas.getContext('2d');
  if (!srcCtx) return new ImageData(newWidth, newHeight);
  srcCtx.putImageData(imageData, 0, 0);

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(srcCanvas, 0, 0, newWidth, newHeight);

  return ctx.getImageData(0, 0, newWidth, newHeight);
}

export function isWebGLAvailable(): boolean {
  return initWebGL();
}

export function cleanupGPU() {
  if (gl) {
    if (upscaleProgram) gl.deleteProgram(upscaleProgram);
    if (downscaleProgram) gl.deleteProgram(downscaleProgram);
    if (quadBuffer) gl.deleteBuffer(quadBuffer);
    gl = null;
    upscaleProgram = null;
    downscaleProgram = null;
    quadBuffer = null;
    glCanvas = null;
  }
}
