import { create } from 'zustand'

export const materialPresets = [
  {
    id: 'matte',
    name: '哑光',
    metalness: 0,
    roughness: 0.8,
  },
  {
    id: 'glossy',
    name: '高光',
    metalness: 0.2,
    roughness: 0.2,
  },
  {
    id: 'metallic',
    name: '金属',
    metalness: 1,
    roughness: 0.3,
  },
  {
    id: 'plastic',
    name: '塑料',
    metalness: 0,
    roughness: 0.5,
  },
]

export const colorPresets = [
  { id: 'red', name: '红色', color: '#ef4444' },
  { id: 'orange', name: '橙色', color: '#f97316' },
  { id: 'yellow', name: '黄色', color: '#eab308' },
  { id: 'green', name: '绿色', color: '#22c55e' },
  { id: 'blue', name: '蓝色', color: '#3b82f6' },
  { id: 'indigo', name: '靛蓝', color: '#6366f1' },
  { id: 'purple', name: '紫色', color: '#a855f7' },
  { id: 'pink', name: '粉色', color: '#ec4899' },
  { id: 'white', name: '白色', color: '#ffffff' },
  { id: 'gray', name: '灰色', color: '#6b7280' },
  { id: 'black', name: '黑色', color: '#1f2937' },
]

export const metalnessMapPresets = [
  { id: 'none', name: '无贴图' },
  { id: 'brushed', name: '拉丝金属' },
  { id: 'scratched', name: '划痕金属' },
  { id: 'hammers', name: '锤纹' },
]

const useStore = create((set) => ({
  color: '#3b82f6',
  materialType: 'glossy',
  rotation: [0, 0, 0],
  scale: 1,
  snowEnabled: false,
  metalnessMapType: 'none',
  arMode: false,

  setColor: (color) => set({ color }),
  setMaterialType: (materialType) => set({ materialType }),
  setRotation: (rotation) => set({ rotation }),
  setScale: (scale) => set({ scale }),
  setSnowEnabled: (snowEnabled) => set({ snowEnabled }),
  setMetalnessMapType: (metalnessMapType) => set({ metalnessMapType }),
  setArMode: (arMode) => set({ arMode }),
  toggleSnow: () => set((state) => ({ snowEnabled: !state.snowEnabled })),
  toggleArMode: () => set((state) => ({ arMode: !state.arMode })),
  
  reset: () => set({
    color: '#3b82f6',
    materialType: 'glossy',
    rotation: [0, 0, 0],
    scale: 1,
    snowEnabled: false,
    metalnessMapType: 'none',
    arMode: false,
  }),
}))

export default useStore
