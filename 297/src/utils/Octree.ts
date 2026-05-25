import * as THREE from 'three'

export interface OctreePoint {
  position: THREE.Vector3
  color: THREE.Color
  originalIndex: number
}

export class OctreeNode {
  bounds: THREE.Box3
  center: THREE.Vector3
  halfSize: number
  points: OctreePoint[] = []
  children: OctreeNode[] = []
  level: number
  isLeaf: boolean = true
  pointCount: number = 0

  constructor(center: THREE.Vector3, halfSize: number, level: number = 0) {
    this.center = center.clone()
    this.halfSize = halfSize
    this.level = level
    this.bounds = new THREE.Box3(
      new THREE.Vector3(
        center.x - halfSize,
        center.y - halfSize,
        center.z - halfSize
      ),
      new THREE.Vector3(
        center.x + halfSize,
        center.y + halfSize,
        center.z + halfSize
      )
    )
  }

  containsPoint(point: OctreePoint): boolean {
    return this.bounds.containsPoint(point.position)
  }

  subdivide(maxPointsPerNode: number, maxLevel: number): void {
    if (this.level >= maxLevel || this.points.length <= maxPointsPerNode) {
      this.isLeaf = true
      return
    }

    this.isLeaf = false
    const newHalfSize = this.halfSize / 2
    const offset = newHalfSize

    const offsets = [
      [-offset, -offset, -offset],
      [offset, -offset, -offset],
      [-offset, offset, -offset],
      [offset, offset, -offset],
      [-offset, -offset, offset],
      [offset, -offset, offset],
      [-offset, offset, offset],
      [offset, offset, offset],
    ]

    for (const [ox, oy, oz] of offsets) {
      const childCenter = new THREE.Vector3(
        this.center.x + ox,
        this.center.y + oy,
        this.center.z + oz
      )
      const child = new OctreeNode(childCenter, newHalfSize, this.level + 1)
      this.children.push(child)
    }

    for (const point of this.points) {
      for (const child of this.children) {
        if (child.containsPoint(point)) {
          child.points.push(point)
          child.pointCount++
          break
        }
      }
    }

    this.points = []

    for (const child of this.children) {
      child.subdivide(maxPointsPerNode, maxLevel)
      this.pointCount += child.pointCount
    }
  }

  getVisibleNodes(
    camera: THREE.Camera,
    frustum: THREE.Frustum,
    targetLevel: number,
    result: OctreeNode[] = []
  ): OctreeNode[] {
    const distance = this.center.distanceTo(camera.position)
    const screenSize = (this.halfSize * 2) / distance
    const lodThreshold = 0.02 * (1 + this.level * 0.5)

    if (!frustum.intersectsBox(this.bounds)) {
      return result
    }

    if (this.isLeaf || screenSize < lodThreshold || this.level >= targetLevel) {
      if (this.points.length > 0 || this.pointCount > 0) {
        result.push(this)
      }
      return result
    }

    for (const child of this.children) {
      child.getVisibleNodes(camera, frustum, targetLevel, result)
    }

    return result
  }
}

export class OctreeLOD {
  root: OctreeNode | null = null
  maxPointsPerNode: number
  maxLevel: number
  allPoints: OctreePoint[] = []

  constructor(maxPointsPerNode: number = 1000, maxLevel: number = 6) {
    this.maxPointsPerNode = maxPointsPerNode
    this.maxLevel = maxLevel
  }

  build(points: OctreePoint[]): void {
    this.allPoints = points

    if (points.length === 0) {
      return
    }

    const box = new THREE.Box3()
    for (const point of points) {
      box.expandByPoint(point.position)
    }

    const center = new THREE.Vector3()
    box.getCenter(center)
    const size = new THREE.Vector3()
    box.getSize(size)
    const halfSize = Math.max(size.x, size.y, size.z) / 2 * 1.1

    this.root = new OctreeNode(center, halfSize, 0)
    this.root.points = [...points]
    this.root.pointCount = points.length
    this.root.subdivide(this.maxPointsPerNode, this.maxLevel)
  }

  getVisiblePoints(
    camera: THREE.Camera,
    targetLevel: number = 4
  ): { positions: Float32Array; colors: Float32Array; indices: number[] } {
    if (!this.root) {
      return { positions: new Float32Array(), colors: new Float32Array(), indices: [] }
    }

    const frustum = new THREE.Frustum()
    const matrix = new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
    frustum.setFromProjectionMatrix(matrix)

    const visibleNodes = this.root.getVisibleNodes(camera, frustum, targetLevel)
    
    let totalPoints = 0
    for (const node of visibleNodes) {
      totalPoints += node.points.length
    }

    const positions = new Float32Array(totalPoints * 3)
    const colors = new Float32Array(totalPoints * 3)
    const indices: number[] = []
    let offset = 0

    for (const node of visibleNodes) {
      for (const point of node.points) {
        const i3 = offset * 3
        positions[i3] = point.position.x
        positions[i3 + 1] = point.position.y
        positions[i3 + 2] = point.position.z
        colors[i3] = point.color.r
        colors[i3 + 1] = point.color.g
        colors[i3 + 2] = point.color.b
        indices.push(point.originalIndex)
        offset++
      }
    }

    return { positions, colors, indices }
  }

  rebuildIfNeeded(camera: THREE.Camera, lastCameraPos: THREE.Vector3): boolean {
    const distance = camera.position.distanceTo(lastCameraPos)
    return distance > this.root!.halfSize * 0.1
  }
}
