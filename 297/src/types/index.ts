export interface User {
  id: string
  username: string
  role: 'annotator' | 'admin'
}

export interface Project {
  id: string
  name: string
  description: string
  pointCloudPath: string | null
  createdAt: string
  createdBy: string
}

export type LabelType = 'ground' | 'vehicle' | 'pedestrian'
export type AnnotationType = 'box' | 'polygon'
export type ToolType = 'select' | 'box' | 'polygon' | 'none'

export interface Point3D {
  x: number
  y: number
  z: number
}

export interface BoxGeometry {
  center: Point3D
  size: Point3D
  rotation: Point3D
}

export interface PolygonGeometry {
  points: Point3D[]
  height: number
}

export interface Annotation {
  id: string
  projectId: string
  label: LabelType
  type: AnnotationType
  geometry: BoxGeometry | PolygonGeometry
  pointIndices: number[]
  userId: string
  userName?: string
  createdAt: string
  updatedAt: string
}

export interface OnlineUser {
  id: string
  username: string
  color: string
  position?: Point3D
}

export interface RegionLock {
  id: string
  userId: string
  userName: string
  projectId: string
  boundingBox: {
    min: Point3D
    max: Point3D
  }
  center: Point3D
  createdAt: string
  expiresAt: string
}

export interface Statistics {
  totalAnnotations: number
  totalPoints: number
  labelDistribution: Record<LabelType, number>
  userContributions: Array<{
    userId: string
    username: string
    count: number
  }>
  progress: number
}

export const LABEL_COLORS: Record<LabelType, string> = {
  ground: '#00B42A',
  vehicle: '#F53F3F',
  pedestrian: '#FF7D00',
}

export const LABEL_NAMES: Record<LabelType, string> = {
  ground: '地面',
  vehicle: '车辆',
  pedestrian: '行人',
}
