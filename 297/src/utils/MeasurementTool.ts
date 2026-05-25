import * as THREE from 'three'

export type MeasurementType = 'distance' | 'area' | 'angle'

export interface DistanceMeasurement {
  id: string
  type: 'distance'
  start: THREE.Vector3
  end: THREE.Vector3
  value: number
  unit: string
}

export interface AreaMeasurement {
  id: string
  type: 'area'
  points: THREE.Vector3[]
  value: number
  unit: string
}

export interface AngleMeasurement {
  id: string
  type: 'angle'
  points: [THREE.Vector3, THREE.Vector3, THREE.Vector3]
  value: number
  unit: string
}

export type Measurement = DistanceMeasurement | AreaMeasurement | AngleMeasurement

export class MeasurementTool {
  private measurementPoints: THREE.Vector3[] = []
  private currentType: MeasurementType = 'distance'
  private measurements: Measurement[] = []

  setType(type: MeasurementType) {
    this.currentType = type
    this.measurementPoints = []
  }

  getType(): MeasurementType {
    return this.currentType
  }

  getPoints(): THREE.Vector3[] {
    return this.measurementPoints
  }

  addPoint(point: THREE.Vector3): Measurement | null {
    this.measurementPoints.push(point.clone())

    if (this.currentType === 'distance' && this.measurementPoints.length >= 2) {
      return this.completeDistance()
    }

    if (this.currentType === 'area' && this.measurementPoints.length >= 3) {
      return null
    }

    if (this.currentType === 'angle' && this.measurementPoints.length >= 3) {
      return this.completeAngle()
    }

    return null
  }

  completeArea(): AreaMeasurement | null {
    if (this.measurementPoints.length < 3) return null

    const area = this.calculatePolygonArea(this.measurementPoints)
    const measurement: AreaMeasurement = {
      id: `measure_area_${Date.now()}`,
      type: 'area',
      points: [...this.measurementPoints],
      value: area,
      unit: 'm²',
    }

    this.measurements.push(measurement)
    this.measurementPoints = []

    return measurement
  }

  private completeDistance(): DistanceMeasurement {
    const start = this.measurementPoints[0]
    const end = this.measurementPoints[1]
    const distance = start.distanceTo(end)

    const measurement: DistanceMeasurement = {
      id: `measure_dist_${Date.now()}`,
      type: 'distance',
      start: start.clone(),
      end: end.clone(),
      value: distance,
      unit: 'm',
    }

    this.measurements.push(measurement)
    this.measurementPoints = []

    return measurement
  }

  private completeAngle(): AngleMeasurement {
    const points = this.measurementPoints.slice(0, 3) as [THREE.Vector3, THREE.Vector3, THREE.Vector3]
    const angle = this.calculateAngle(points[0], points[1], points[2])

    const measurement: AngleMeasurement = {
      id: `measure_angle_${Date.now()}`,
      type: 'angle',
      points,
      value: angle,
      unit: '°',
    }

    this.measurements.push(measurement)
    this.measurementPoints = []

    return measurement
  }

  private calculatePolygonArea(points: THREE.Vector3[]): number {
    if (points.length < 3) return 0

    let area = 0
    const n = points.length

    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n
      const cross = new THREE.Vector3()
        .crossVectors(points[i], points[j])
        .length()
      area += cross
    }

    return area / 2
  }

  private calculateAngle(
    p1: THREE.Vector3,
    vertex: THREE.Vector3,
    p2: THREE.Vector3
  ): number {
    const v1 = new THREE.Vector3().subVectors(p1, vertex).normalize()
    const v2 = new THREE.Vector3().subVectors(p2, vertex).normalize()
    const dot = v1.dot(v2)
    const angle = Math.acos(Math.max(-1, Math.min(1, dot)))
    return (angle * 180) / Math.PI
  }

  cancel() {
    this.measurementPoints = []
  }

  removeMeasurement(id: string) {
    this.measurements = this.measurements.filter(m => m.id !== id)
  }

  clearAll() {
    this.measurements = []
    this.measurementPoints = []
  }

  getMeasurements(): Measurement[] {
    return this.measurements
  }

  getRequiredPoints(): number {
    switch (this.currentType) {
      case 'distance': return 2
      case 'area': return -1
      case 'angle': return 3
      default: return 2
    }
  }

  formatValue(value: number, type: MeasurementType): string {
    if (type === 'distance') {
      if (value < 1) {
        return `${(value * 100).toFixed(1)} cm`
      } else if (value < 1000) {
        return `${value.toFixed(2)} m`
      } else {
        return `${(value / 1000).toFixed(2)} km`
      }
    } else if (type === 'area') {
      if (value < 1) {
        return `${(value * 10000).toFixed(1)} cm²`
      } else if (value < 1000000) {
        return `${value.toFixed(2)} m²`
      } else {
        return `${(value / 1000000).toFixed(2)} km²`
      }
    } else {
      return `${value.toFixed(1)}°`
    }
  }
}

export function createMeasurementLine(start: THREE.Vector3, end: THREE.Vector3): THREE.Line {
  const points = [start.clone(), end.clone()]
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({
    color: 0xffff00,
    linewidth: 2,
    transparent: true,
    opacity: 0.9,
  })
  return new THREE.Line(geometry, material)
}

export function createMeasurementPoint(position: THREE.Vector3, index: number): THREE.Group {
  const group = new THREE.Group()

  const sphereGeo = new THREE.SphereGeometry(0.15, 8, 8)
  const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffff00 })
  const sphere = new THREE.Mesh(sphereGeo, sphereMat)
  sphere.position.copy(position)
  group.add(sphere)

  const canvas = document.createElement('canvas')
  canvas.width = 32
  canvas.height = 32
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#ffff00'
  ctx.font = 'bold 16px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(index.toString(), 16, 16)

  const texture = new THREE.CanvasTexture(canvas)
  const spriteMat = new THREE.SpriteMaterial({ map: texture })
  const sprite = new THREE.Sprite(spriteMat)
  sprite.position.copy(position)
  sprite.position.y += 0.3
  sprite.scale.set(1, 1, 1)
  group.add(sprite)

  return group
}

export function createAreaPolygon(points: THREE.Vector3[]): THREE.Group {
  const group = new THREE.Group()

  const shape = new THREE.Shape()
  if (points.length >= 2) {
    shape.moveTo(points[0].x, points[0].z)
    for (let i = 1; i < points.length; i++) {
      shape.lineTo(points[i].x, points[i].z)
    }
    shape.closePath()
  }

  const geometry = new THREE.ShapeGeometry(shape)
  geometry.rotateX(-Math.PI / 2)
  geometry.translate(0, points[0]?.y || 0, 0)

  const material = new THREE.MeshBasicMaterial({
    color: 0xffff00,
    transparent: true,
    opacity: 0.3,
    side: THREE.DoubleSide,
  })
  const mesh = new THREE.Mesh(geometry, material)
  group.add(mesh)

  const linePoints = [...points, points[0]].map(p => new THREE.Vector3(p.x, (points[0]?.y || 0) + 0.01, p.z))
  const lineGeo = new THREE.BufferGeometry().setFromPoints(linePoints)
  const lineMat = new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 2 })
  const line = new THREE.Line(lineGeo, lineMat)
  group.add(line)

  return group
}
