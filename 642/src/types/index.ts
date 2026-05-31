export interface Vector3 {
  x: number
  y: number
  z: number
}

export interface Vector2 {
  x: number
  y: number
}

export interface FluidParams {
  density: number
  viscosity: number
  velocity: number
  diffusion: number
  pressure: number
  color: { r: number; g: number; b: number }
  transparency: number
  vorticityScale: number
  velocityDissipation: number
  pressureIterations: number
}

export interface Obstacle {
  id: string
  type: 'box' | 'sphere' | 'cylinder'
  position: Vector3
  size: Vector3
  rotation: Vector3
}

export interface LightSource {
  id: string
  type: 'point' | 'spot' | 'directional'
  position: Vector3
  color: string
  intensity: number
  castShadow: boolean
}

export interface Material {
  id: string
  name: string
  color: string
  refractiveIndex: number
  absorption: number
  scattering: number
}

export type ToolType = 'select' | 'obstacle' | 'light' | 'emitter' | 'material' | 'force'

export type SceneType = 'windTunnel' | 'river' | 'smoke' | 'custom'

export interface ColorZone {
  id: string
  position: Vector2
  radius: number
  color: { r: number; g: number; b: number }
  enabled: boolean
}

export interface ForceField {
  id: string
  position: Vector2
  direction: Vector2
  strength: number
  radius: number
  enabled: boolean
}

export interface Emitter {
  id: string
  position: Vector2
  direction: Vector2
  rate: number
  color: { r: number; g: number; b: number }
  enabled: boolean
}

export interface SceneConfig {
  type: SceneType
  name: string
  description: string
  icon: string
  fluidParams: Partial<FluidParams>
  colorZones: ColorZone[]
  forceFields: ForceField[]
  emitters: Emitter[]
  backgroundColor: string
}

export interface SimulationState {
  isPlaying: boolean
  fps: number
  gpuMemory: number
  resolution: number
  currentScene: SceneType
}

export interface AppState {
  currentTool: ToolType
  fluidParams: FluidParams
  obstacles: Obstacle[]
  lights: LightSource[]
  materials: Material[]
  simulation: SimulationState
  selectedObjectId: string | null
  colorZones: ColorZone[]
  forceFields: ForceField[]
  emitters: Emitter[]
  scenes: Record<SceneType, SceneConfig>
  mouseForce: {
    enabled: boolean
    position: Vector2
    lastPosition: Vector2
    strength: number
    radius: number
  }
}
