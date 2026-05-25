import * as THREE from 'three'
import { Annotation, LabelType } from '@/types'

export interface PointData {
  position: THREE.Vector3
  color: THREE.Color
  normal?: THREE.Vector3
  label?: LabelType
}

export class AIPreAnnotator {
  private points: PointData[] = []
  private groundHeight: number = 0

  setPoints(points: PointData[]) {
    this.points = points
    this.estimateGroundHeight()
  }

  private estimateGroundHeight() {
    if (this.points.length === 0) return
    
    const heights = this.points.map(p => p.position.y).sort((a, b) => a - b)
    const lowerPercentile = heights[Math.floor(heights.length * 0.1)]
    this.groundHeight = lowerPercentile + 0.5
  }

  private ransacPlane(
    points: PointData[],
    threshold: number = 0.3,
    maxIterations: number = 100
  ): { inliers: PointData[]; normal: THREE.Vector3 } {
    let bestInliers: PointData[] = []
    let bestNormal = new THREE.Vector3(0, 1, 0)

    for (let i = 0; i < maxIterations && points.length >= 3; i++) {
      const indices: number[] = []
      while (indices.length < 3) {
        const idx = Math.floor(Math.random() * points.length)
        if (!indices.includes(idx)) indices.push(idx)
      }

      const p1 = points[indices[0]].position
      const p2 = points[indices[1]].position
      const p3 = points[indices[2]].position

      const v1 = new THREE.Vector3().subVectors(p2, p1)
      const v2 = new THREE.Vector3().subVectors(p3, p1)
      const normal = new THREE.Vector3().crossVectors(v1, v2).normalize()

      if (Math.abs(normal.y) < 0.7) continue

      const inliers = points.filter(p => {
        const d = Math.abs(
          normal.x * (p.position.x - p1.x) +
          normal.y * (p.position.y - p1.y) +
          normal.z * (p.position.z - p1.z)
        )
        return d < threshold
      })

      if (inliers.length > bestInliers.length) {
        bestInliers = inliers
        bestNormal = normal
      }
    }

    return { inliers: bestInliers, normal: bestNormal }
  }

  private dbscanClustering(
    points: PointData[],
    eps: number,
    minPoints: number
  ): PointData[][] {
    const clusters: PointData[][] = []
    const visited = new Set<number>()
    const noise: PointData[] = []

    const regionQuery = (pointIdx: number): number[] => {
      const neighbors: number[] = []
      const p = points[pointIdx].position

      for (let i = 0; i < points.length; i++) {
        if (i === pointIdx) continue
        const dist = p.distanceTo(points[i].position)
        if (dist < eps) {
          neighbors.push(i)
        }
      }
      return neighbors
    }

    for (let i = 0; i < points.length; i++) {
      if (visited.has(i)) continue

      visited.add(i)
      const neighbors = regionQuery(i)

      if (neighbors.length < minPoints) {
        noise.push(points[i])
      } else {
        const cluster: PointData[] = []
        const queue = [...neighbors]

        cluster.push(points[i])

        while (queue.length > 0) {
          const q = queue.shift()!
          if (!visited.has(q)) {
            visited.add(q)
            const qNeighbors = regionQuery(q)
            if (qNeighbors.length >= minPoints) {
              queue.push(...qNeighbors.filter(n => !visited.has(n)))
            }
          }
          if (!cluster.some(c => c === points[q])) {
            cluster.push(points[q])
          }
        }

        if (cluster.length >= minPoints) {
          clusters.push(cluster)
        }
      }
    }

    return clusters
  }

  private classifyCluster(cluster: PointData[]): LabelType {
    if (cluster.length === 0) return 'vehicle'

    const positions = cluster.map(p => p.position)
    const bbox = new THREE.Box3().setFromPoints(positions)
    const size = new THREE.Vector3()
    bbox.getSize(size)

    const centerY = bbox.min.y + size.y / 2
    const height = size.y

    if (centerY < this.groundHeight + 1 && height < 0.8) {
      return 'ground'
    }

    const volume = size.x * size.y * size.z
    const footprint = size.x * size.z

    if (height > 1 && height < 2.5 && footprint > 2 && footprint < 20 && volume < 30) {
      return 'vehicle'
    }

    if (height > 1.5 && height < 2.5 && footprint < 1.5 && volume < 3) {
      return 'pedestrian'
    }

    if (height < 1 && size.x > 5 && size.z > 5) {
      return 'ground'
    }

    return 'vehicle'
  }

  async preAnnotate(): Promise<Annotation[]> {
    const annotations: Annotation[] = []
    const startTime = Date.now()

    console.log('Starting AI pre-annotation...')
    console.log(`Total points: ${this.points.length}`)

    const { inliers: groundPoints } = this.ransacPlane(this.points, 0.5, 50)
    console.log(`Ground points: ${groundPoints.length}`)

    if (groundPoints.length > 1000) {
      const positions = groundPoints.map(p => p.position)
      const bbox = new THREE.Box3().setFromPoints(positions)
      const center = new THREE.Vector3()
      bbox.getCenter(center)
      const size = new THREE.Vector3()
      bbox.getSize(size)

      annotations.push({
        id: `ai_ground_${Date.now()}`,
        projectId: '',
        label: 'ground',
        type: 'box',
        geometry: {
          center: { x: center.x, y: center.y, z: center.z },
          size: { x: size.x, y: size.y, z: size.z },
          rotation: { x: 0, y: 0, z: 0 },
        },
        pointIndices: groundPoints.map((_, i) => i),
        userId: 'ai',
        userName: 'AI Assistant',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
    }

    const nonGroundPoints = this.points.filter(p => p.position.y > this.groundHeight + 0.3)
    console.log(`Non-ground points: ${nonGroundPoints.length}`)

    const clusters = this.dbscanClustering(nonGroundPoints, 1.5, 20)
    console.log(`Detected clusters: ${clusters.length}`)

    for (let i = 0; i < Math.min(clusters.length, 10); i++) {
      const cluster = clusters[i]
      const label = this.classifyCluster(cluster)

      const positions = cluster.map(p => p.position)
      const bbox = new THREE.Box3().setFromPoints(positions)
      const center = new THREE.Vector3()
      bbox.getCenter(center)
      const size = new THREE.Vector3()
      bbox.getSize(size)

      if (size.x > 0.5 && size.y > 0.5 && size.z > 0.5) {
        annotations.push({
          id: `ai_${label}_${Date.now()}_${i}`,
          projectId: '',
          label,
          type: 'box',
          geometry: {
            center: { x: center.x, y: center.y, z: center.z },
            size: { x: size.x, y: size.y, z: size.z },
            rotation: { x: 0, y: 0, z: 0 },
          },
          pointIndices: [],
          userId: 'ai',
          userName: 'AI Assistant',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        })
      }
    }

    console.log(`AI pre-annotation completed in ${Date.now() - startTime}ms`)
    console.log(`Generated ${annotations.length} annotations`)

    return annotations
  }

  async quickAnnotate(region: { min: THREE.Vector3; max: THREE.Vector3 }): Promise<Annotation | null> {
    const pointsInRegion = this.points.filter(p =>
      p.position.x >= region.min.x && p.position.x <= region.max.x &&
      p.position.y >= region.min.y && p.position.y <= region.max.y &&
      p.position.z >= region.min.z && p.position.z <= region.max.z
    )

    if (pointsInRegion.length < 10) return null

    const label = this.classifyCluster(pointsInRegion)
    const positions = pointsInRegion.map(p => p.position)
    const bbox = new THREE.Box3().setFromPoints(positions)
    const center = new THREE.Vector3()
    bbox.getCenter(center)
    const size = new THREE.Vector3()
    bbox.getSize(size)

    return {
      id: `ai_${label}_${Date.now()}`,
      projectId: '',
      label,
      type: 'box',
      geometry: {
        center: { x: center.x, y: center.y, z: center.z },
        size: { x: size.x, y: size.y, z: size.z },
        rotation: { x: 0, y: 0, z: 0 },
      },
      pointIndices: [],
      userId: 'ai',
      userName: 'AI Assistant',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
  }
}
