import { create } from 'zustand'
import type {
  AppState,
  ToolType,
  FluidParams,
  Obstacle,
  LightSource,
  Material,
  SceneType,
  ColorZone,
  ForceField,
  Emitter,
  Vector2,
} from '@/types'
import { SCENE_CONFIGS } from '@/config/scenes'

const initialFluidParams: FluidParams = {
  density: 1.0,
  viscosity: 0.1,
  velocity: 5.0,
  diffusion: 0.001,
  pressure: 1.0,
  color: { r: 0, g: 0.96, b: 1 },
  transparency: 0.7,
  vorticityScale: 0.15,
  velocityDissipation: 0.995,
  pressureIterations: 25,
}

const initialLights: LightSource[] = [
  {
    id: 'main-light',
    type: 'directional',
    position: { x: 5, y: 10, z: 5 },
    color: '#ffffff',
    intensity: 1.5,
    castShadow: true,
  },
  {
    id: 'ambient-light',
    type: 'point',
    position: { x: 0, y: 5, z: 0 },
    color: '#00F5FF',
    intensity: 0.5,
    castShadow: false,
  },
]

const initialMaterials: Material[] = [
  {
    id: 'smoke',
    name: '烟雾',
    color: '#888888',
    refractiveIndex: 1.0,
    absorption: 0.1,
    scattering: 0.5,
  },
  {
    id: 'water',
    name: '水流',
    color: '#0066FF',
    refractiveIndex: 1.33,
    absorption: 0.01,
    scattering: 0.1,
  },
  {
    id: 'fire',
    name: '火焰',
    color: '#FF6B35',
    refractiveIndex: 1.0,
    absorption: 0.2,
    scattering: 0.8,
  },
]

export const useSimulationStore = create<
  AppState & {
    setCurrentTool: (tool: ToolType) => void
    setFluidParams: (params: Partial<FluidParams>) => void
    addObstacle: (obstacle: Omit<Obstacle, 'id'>) => void
    removeObstacle: (id: string) => void
    updateObstacle: (id: string, updates: Partial<Obstacle>) => void
    addLight: (light: Omit<LightSource, 'id'>) => void
    removeLight: (id: string) => void
    updateLight: (id: string, updates: Partial<LightSource>) => void
    setSelectedObject: (id: string | null) => void
    toggleSimulation: () => void
    resetSimulation: () => void
    setFps: (fps: number) => void
    setResolution: (res: number) => void
    switchScene: (sceneType: SceneType) => void
    addColorZone: (zone: Omit<ColorZone, 'id'>) => void
    removeColorZone: (id: string) => void
    updateColorZone: (id: string, updates: Partial<ColorZone>) => void
    addForceField: (field: Omit<ForceField, 'id'>) => void
    removeForceField: (id: string) => void
    updateForceField: (id: string, updates: Partial<ForceField>) => void
    addEmitter: (emitter: Omit<Emitter, 'id'>) => void
    removeEmitter: (id: string) => void
    updateEmitter: (id: string, updates: Partial<Emitter>) => void
    updateMouseForce: (updates: Partial<AppState['mouseForce']>) => void
    setMouseForcePosition: (position: Vector2, lastPosition: Vector2) => void
  }
>((set, get) => ({
  currentTool: 'select',
  fluidParams: initialFluidParams,
  obstacles: [],
  lights: initialLights,
  materials: initialMaterials,
  simulation: {
    isPlaying: true,
    fps: 60,
    gpuMemory: 0,
    resolution: 128,
    currentScene: 'custom',
  },
  selectedObjectId: null,
  colorZones: [],
  forceFields: [],
  emitters: [],
  scenes: SCENE_CONFIGS,
  mouseForce: {
    enabled: false,
    position: { x: 0, y: 0 },
    lastPosition: { x: 0, y: 0 },
    strength: 10,
    radius: 40,
  },

  setCurrentTool: (tool) => set({ currentTool: tool }),

  setFluidParams: (params) =>
    set((state) => ({
      fluidParams: { ...state.fluidParams, ...params },
    })),

  addObstacle: (obstacle) =>
    set((state) => ({
      obstacles: [...state.obstacles, { ...obstacle, id: `obs-${Date.now()}` }],
    })),

  removeObstacle: (id) =>
    set((state) => ({
      obstacles: state.obstacles.filter((o) => o.id !== id),
    })),

  updateObstacle: (id, updates) =>
    set((state) => ({
      obstacles: state.obstacles.map((o) =>
        o.id === id ? { ...o, ...updates } : o
      ),
    })),

  addLight: (light) =>
    set((state) => ({
      lights: [...state.lights, { ...light, id: `light-${Date.now()}` }],
    })),

  removeLight: (id) =>
    set((state) => ({
      lights: state.lights.filter((l) => l.id !== id),
    })),

  updateLight: (id, updates) =>
    set((state) => ({
      lights: state.lights.map((l) =>
        l.id === id ? { ...l, ...updates } : l
      ),
    })),

  setSelectedObject: (id) => set({ selectedObjectId: id }),

  toggleSimulation: () =>
    set((state) => ({
      simulation: { ...state.simulation, isPlaying: !state.simulation.isPlaying },
    })),

  resetSimulation: () => {
    const { simulation } = get()
    const scene = SCENE_CONFIGS[simulation.currentScene]
    set({
      simulation: { ...simulation, isPlaying: true },
      colorZones: [...scene.colorZones],
      forceFields: [...scene.forceFields],
      emitters: [...scene.emitters],
      fluidParams: { ...initialFluidParams, ...scene.fluidParams },
    })
  },

  setFps: (fps) =>
    set((state) => ({
      simulation: { ...state.simulation, fps },
    })),

  setResolution: (resolution) =>
    set((state) => ({
      simulation: { ...state.simulation, resolution },
    })),

  switchScene: (sceneType) => {
    const scene = SCENE_CONFIGS[sceneType]
    set({
      simulation: {
        ...get().simulation,
        currentScene: sceneType,
      },
      fluidParams: {
        ...get().fluidParams,
        ...scene.fluidParams,
      },
      colorZones: [...scene.colorZones],
      forceFields: [...scene.forceFields],
      emitters: [...scene.emitters],
    })
  },

  addColorZone: (zone) =>
    set((state) => ({
      colorZones: [...state.colorZones, { ...zone, id: `zone-${Date.now()}` }],
    })),

  removeColorZone: (id) =>
    set((state) => ({
      colorZones: state.colorZones.filter((z) => z.id !== id),
    })),

  updateColorZone: (id, updates) =>
    set((state) => ({
      colorZones: state.colorZones.map((z) =>
        z.id === id ? { ...z, ...updates } : z
      ),
    })),

  addForceField: (field) =>
    set((state) => ({
      forceFields: [...state.forceFields, { ...field, id: `force-${Date.now()}` }],
    })),

  removeForceField: (id) =>
    set((state) => ({
      forceFields: state.forceFields.filter((f) => f.id !== id),
    })),

  updateForceField: (id, updates) =>
    set((state) => ({
      forceFields: state.forceFields.map((f) =>
        f.id === id ? { ...f, ...updates } : f
      ),
    })),

  addEmitter: (emitter) =>
    set((state) => ({
      emitters: [...state.emitters, { ...emitter, id: `emitter-${Date.now()}` }],
    })),

  removeEmitter: (id) =>
    set((state) => ({
      emitters: state.emitters.filter((e) => e.id !== id),
    })),

  updateEmitter: (id, updates) =>
    set((state) => ({
      emitters: state.emitters.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      ),
    })),

  updateMouseForce: (updates) =>
    set((state) => ({
      mouseForce: { ...state.mouseForce, ...updates },
    })),

  setMouseForcePosition: (position, lastPosition) =>
    set((state) => ({
      mouseForce: {
        ...state.mouseForce,
        position,
        lastPosition,
      },
    })),
}))
