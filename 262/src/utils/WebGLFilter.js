const vertexShaderSource = `
  attribute vec2 a_position;
  attribute vec2 a_texCoord;
  varying vec2 v_texCoord;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_texCoord = a_texCoord;
  }
`

const fragmentShaderSource = `
  precision highp float;
  uniform sampler2D u_image;
  uniform float u_brightness;
  uniform float u_contrast;
  uniform float u_saturation;
  varying vec2 v_texCoord;

  void main() {
    vec4 color = texture2D(u_image, v_texCoord);
    
    vec3 brightness = color.rgb + u_brightness;
    
    float contrastFactor = (1.0 + u_contrast) / (1.0 - u_contrast + 0.001);
    vec3 contrast = (brightness - 0.5) * contrastFactor + 0.5;
    
    float average = (contrast.r + contrast.g + contrast.b) / 3.0;
    vec3 saturation = mix(vec3(average), contrast, 1.0 + u_saturation);
    
    gl_FragColor = vec4(clamp(saturation, 0.0, 1.0), color.a);
  }
`

class WebGLFilter {
  constructor() {
    this.gl = null
    this.program = null
    this.texture = null
    this.offscreenCanvas = null
    this.uniforms = {}
    this.currentFilters = {
      brightness: 0,
      contrast: 0,
      saturation: 0
    }
    this.initialized = false
  }

  init() {
    if (this.initialized) return

    this.offscreenCanvas = document.createElement('canvas')
    this.gl = this.offscreenCanvas.getContext('webgl', {
      preserveDrawingBuffer: true,
      antialias: false
    })

    if (!this.gl) {
      console.warn('WebGL not supported, falling back to Canvas 2D')
      return false
    }

    this.createShaderProgram()
    this.createBuffers()
    this.initialized = true
    return true
  }

  createShader(type, source) {
    const shader = this.gl.createShader(type)
    this.gl.shaderSource(shader, source)
    this.gl.compileShader(shader)

    if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
      console.error('Shader compile error:', this.gl.getShaderInfoLog(shader))
      this.gl.deleteShader(shader)
      return null
    }
    return shader
  }

  createShaderProgram() {
    const vertexShader = this.createShader(this.gl.VERTEX_SHADER, vertexShaderSource)
    const fragmentShader = this.createShader(this.gl.FRAGMENT_SHADER, fragmentShaderSource)

    this.program = this.gl.createProgram()
    this.gl.attachShader(this.program, vertexShader)
    this.gl.attachShader(this.program, fragmentShader)
    this.gl.linkProgram(this.program)

    if (!this.gl.getProgramParameter(this.program, this.gl.LINK_STATUS)) {
      console.error('Program link error:', this.gl.getProgramInfoLog(this.program))
      return
    }

    this.gl.useProgram(this.program)

    this.uniforms = {
      image: this.gl.getUniformLocation(this.program, 'u_image'),
      brightness: this.gl.getUniformLocation(this.program, 'u_brightness'),
      contrast: this.gl.getUniformLocation(this.program, 'u_contrast'),
      saturation: this.gl.getUniformLocation(this.program, 'u_saturation')
    }
  }

  createBuffers() {
    const positions = new Float32Array([
      -1, -1,  1, -1,  -1, 1,
      -1,  1,  1, -1,   1, 1
    ])
    const positionBuffer = this.gl.createBuffer()
    this.gl.bindBuffer(this.gl.ARRAY_BUFFER, positionBuffer)
    this.gl.bufferData(this.gl.ARRAY_BUFFER, positions, this.gl.STATIC_DRAW)

    const positionLocation = this.gl.getAttribLocation(this.program, 'a_position')
    this.gl.enableVertexAttribArray(positionLocation)
    this.gl.vertexAttribPointer(positionLocation, 2, this.gl.FLOAT, false, 0, 0)

    const texCoords = new Float32Array([
      0, 1,  1, 1,  0, 0,
      0, 0,  1, 1,  1, 0
    ])
    const texCoordBuffer = this.gl.createBuffer()
    this.gl.bindBuffer(this.gl.ARRAY_BUFFER, texCoordBuffer)
    this.gl.bufferData(this.gl.ARRAY_BUFFER, texCoords, this.gl.STATIC_DRAW)

    const texCoordLocation = this.gl.getAttribLocation(this.program, 'a_texCoord')
    this.gl.enableVertexAttribArray(texCoordLocation)
    this.gl.vertexAttribPointer(texCoordLocation, 2, this.gl.FLOAT, false, 0, 0)
  }

  createTexture(image) {
    if (this.texture) {
      this.gl.deleteTexture(this.texture)
    }

    this.texture = this.gl.createTexture()
    this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture)
    
    this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE)
    this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE)
    this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR)
    this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR)

    this.gl.texImage2D(
      this.gl.TEXTURE_2D,
      0,
      this.gl.RGBA,
      this.gl.RGBA,
      this.gl.UNSIGNED_BYTE,
      image
    )
  }

  applyFilter(imageElement, filters = {}) {
    if (!this.initialized && !this.init()) {
      return this.fallbackFilter(imageElement, filters)
    }

    const width = imageElement.naturalWidth || imageElement.width
    const height = imageElement.naturalHeight || imageElement.height

    this.offscreenCanvas.width = width
    this.offscreenCanvas.height = height
    this.gl.viewport(0, 0, width, height)

    this.createTexture(imageElement)

    this.currentFilters = { ...this.currentFilters, ...filters }
    
    this.gl.uniform1i(this.uniforms.image, 0)
    this.gl.uniform1f(this.uniforms.brightness, this.currentFilters.brightness)
    this.gl.uniform1f(this.uniforms.contrast, this.currentFilters.contrast)
    this.gl.uniform1f(this.uniforms.saturation, this.currentFilters.saturation)

    this.gl.drawArrays(this.gl.TRIANGLES, 0, 6)

    return this.offscreenCanvas
  }

  fallbackFilter(imageElement, filters) {
    const width = imageElement.naturalWidth || imageElement.width
    const height = imageElement.naturalHeight || imageElement.height

    this.offscreenCanvas = this.offscreenCanvas || document.createElement('canvas')
    this.offscreenCanvas.width = width
    this.offscreenCanvas.height = height

    const ctx = this.offscreenCanvas.getContext('2d')
    ctx.drawImage(imageElement, 0, 0)

    const imageData = ctx.getImageData(0, 0, width, height)
    const data = imageData.data

    const brightness = (filters.brightness || 0) * 255
    const contrastFactor = (1 + (filters.contrast || 0)) / (1 - (filters.contrast || 0) + 0.001)
    const saturation = 1 + (filters.saturation || 0)

    for (let i = 0; i < data.length; i += 4) {
      let r = data[i]
      let g = data[i + 1]
      let b = data[i + 2]

      r = Math.max(0, Math.min(255, r + brightness))
      g = Math.max(0, Math.min(255, g + brightness))
      b = Math.max(0, Math.min(255, b + brightness))

      r = (r - 128) * contrastFactor + 128
      g = (g - 128) * contrastFactor + 128
      b = (b - 128) * contrastFactor + 128

      const gray = 0.299 * r + 0.587 * g + 0.114 * b
      r = gray + (r - gray) * saturation
      g = gray + (g - gray) * saturation
      b = gray + (b - gray) * saturation

      data[i] = Math.max(0, Math.min(255, r))
      data[i + 1] = Math.max(0, Math.min(255, g))
      data[i + 2] = Math.max(0, Math.min(255, b))
    }

    ctx.putImageData(imageData, 0, 0)
    return this.offscreenCanvas
  }

  getCurrentFilters() {
    return { ...this.currentFilters }
  }

  resetFilters() {
    this.currentFilters = {
      brightness: 0,
      contrast: 0,
      saturation: 0
    }
  }

  dispose() {
    if (this.texture) {
      this.gl?.deleteTexture(this.texture)
      this.texture = null
    }
    if (this.program) {
      this.gl?.deleteProgram(this.program)
      this.program = null
    }
    if (this.offscreenCanvas) {
      this.offscreenCanvas.width = 1
      this.offscreenCanvas.height = 1
      this.offscreenCanvas = null
    }
    this.gl = null
    this.initialized = false
  }
}

export const webGLFilter = new WebGLFilter()
export default WebGLFilter
