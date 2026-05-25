import * as THREE from 'three'

export class GPUPicker {
  private renderer: THREE.WebGLRenderer
  private scene: THREE.Scene
  private camera: THREE.Camera
  private pickTexture: THREE.WebGLRenderTarget
  private pickScene: THREE.Scene
  private pointCloud: THREE.Points | null = null
  private idColorMap: Map<number, THREE.Color> = new Map()
  private colorIdMap: Map<string, number> = new Map()
  private pickBuffer: Uint8Array = new Uint8Array(4)

  constructor(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.Camera,
    width: number,
    height: number
  ) {
    this.renderer = renderer
    this.scene = scene
    this.camera = camera

    this.pickTexture = new THREE.WebGLRenderTarget(width, height, {
      minFilter: THREE.NearestFilter,
      magFilter: THREE.NearestFilter,
      format: THREE.RGBAFormat,
      type: THREE.UnsignedByteType,
    })

    this.pickScene = new THREE.Scene()
  }

  setPointCloud(pointCloud: THREE.Points): void {
    this.pointCloud = pointCloud.clone()
    
    const geometry = this.pointCloud.geometry
    const count = geometry.attributes.position.count
    const colors = new Float32Array(count * 3)

    this.idColorMap.clear()
    this.colorIdMap.clear()

    for (let i = 0; i < count; i++) {
      const color = this.idToColor(i)
      const i3 = i * 3
      colors[i3] = color.r
      colors[i3 + 1] = color.g
      colors[i3 + 2] = color.b

      this.idColorMap.set(i, color)
      this.colorIdMap.set(this.colorToString(color), i)
    }

    this.pointCloud.geometry.setAttribute(
      'color',
      new THREE.BufferAttribute(colors, 3)
    )
    ;(this.pointCloud.material as THREE.PointsMaterial).vertexColors = true
    ;(this.pointCloud.material as THREE.PointsMaterial).size = 2
    ;(this.pointCloud.material as THREE.PointsMaterial).sizeAttenuation = false

    this.pickScene.add(this.pointCloud)
  }

  private idToColor(id: number): THREE.Color {
    const r = ((id >> 0) & 0xff) / 255
    const g = ((id >> 8) & 0xff) / 255
    const b = ((id >> 16) & 0xff) / 255
    return new THREE.Color(r, g, b)
  }

  private colorToString(color: THREE.Color): string {
    return `${Math.floor(color.r * 255)},${Math.floor(color.g * 255)},${Math.floor(color.b * 255)}`
  }

  private pixelToId(r: number, g: number, b: number): number {
    return r | (g << 8) | (b << 16)
  }

  pickPoint(x: number, y: number): number | null {
    if (!this.pointCloud) return null

    const gl = this.renderer.getContext()
    
    this.renderer.setRenderTarget(this.pickTexture)
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.clear()
    this.renderer.render(this.pickScene, this.camera)

    const rect = this.renderer.domElement.getBoundingClientRect()
    const pixelX = Math.floor(x - rect.left)
    const pixelY = Math.floor(rect.height - (y - rect.top))

    gl.readPixels(
      pixelX,
      pixelY,
      1,
      1,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      this.pickBuffer
    )

    this.renderer.setRenderTarget(null)

    const r = this.pickBuffer[0]
    const g = this.pickBuffer[1]
    const b = this.pickBuffer[2]

    if (r === 0 && g === 0 && b === 0) {
      return null
    }

    return this.pixelToId(r, g, b)
  }

  pickPolygon(
    polygonPoints: { x: number; y: number }[],
    width: number,
    height: number
  ): number[] {
    if (!this.pointCloud || polygonPoints.length < 3) return []

    const gl = this.renderer.getContext()

    this.renderer.setRenderTarget(this.pickTexture)
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.clear()
    this.renderer.render(this.pickScene, this.camera)

    const pixels = new Uint8Array(width * height * 4)
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)

    this.renderer.setRenderTarget(null)

    const selectedIds: Set<number> = new Set()
    const pointInPolygon = (px: number, py: number): boolean => {
      let inside = false
      for (let i = 0, j = polygonPoints.length - 1; i < polygonPoints.length; j = i++) {
        const xi = polygonPoints[i].x, yi = polygonPoints[i].y
        const xj = polygonPoints[j].x, yj = polygonPoints[j].y

        const intersect = ((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
        if (intersect) inside = !inside
      }
      return inside
    }

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (pointInPolygon(x, y)) {
          const idx = (y * width + x) * 4
          const r = pixels[idx]
          const g = pixels[idx + 1]
          const b = pixels[idx + 2]

          if (r !== 0 || g !== 0 || b !== 0) {
            const id = this.pixelToId(r, g, b)
            if (id >= 0 && id < this.pointCloud.geometry.attributes.position.count) {
              selectedIds.add(id)
            }
          }
        }
      }
    }

    return Array.from(selectedIds)
  }

  pickBox(
    startX: number,
    startY: number,
    endX: number,
    endY: number
  ): number[] {
    if (!this.pointCloud) return []

    const minX = Math.min(startX, endX)
    const maxX = Math.max(startX, endX)
    const minY = Math.min(startY, endY)
    const maxY = Math.max(startY, endY)
    const width = Math.floor(maxX - minX)
    const height = Math.floor(maxY - minY)

    if (width < 2 || height < 2) return []

    const gl = this.renderer.getContext()

    this.renderer.setRenderTarget(this.pickTexture)
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.clear()
    this.renderer.render(this.pickScene, this.camera)

    const pixels = new Uint8Array(width * height * 4)
    gl.readPixels(
      Math.floor(minX),
      Math.floor(this.renderer.domElement.height - maxY),
      width,
      height,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      pixels
    )

    this.renderer.setRenderTarget(null)

    const selectedIds: Set<number> = new Set()

    for (let i = 0; i < width * height; i++) {
      const idx = i * 4
      const r = pixels[idx]
      const g = pixels[idx + 1]
      const b = pixels[idx + 2]

      if (r !== 0 || g !== 0 || b !== 0) {
        const id = this.pixelToId(r, g, b)
        if (id >= 0) {
          selectedIds.add(id)
        }
      }
    }

    return Array.from(selectedIds)
  }

  setSize(width: number, height: number): void {
    this.pickTexture.setSize(width, height)
  }

  dispose(): void {
    this.pickTexture.dispose()
    if (this.pointCloud) {
      this.pointCloud.geometry.dispose()
      ;(this.pointCloud.material as THREE.Material).dispose()
    }
  }
}
