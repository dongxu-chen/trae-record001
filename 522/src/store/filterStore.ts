import { create } from 'zustand';

export interface ImageItem {
  id: string;
  name: string;
  src: string;
  file: File;
  width: number;
  height: number;
}

export interface FilterConfig {
  filterType: string;
  intensity: number;
  customParams: Record<string, number | number[]>;
}

export interface PresetItem {
  id: string;
  name: string;
  config: FilterConfig;
  createdAt: string;
}

export interface BatchItem {
  imageId: string;
  config: FilterConfig;
  status: 'pending' | 'processing' | 'done' | 'error';
}

export interface CustomFilterDef {
  id: string;
  name: string;
  fragmentShader: string;
  uniforms: { name: string; type: string; defaultValue: number | number[]; min?: number; max?: number }[];
  compiled: boolean;
  error?: string;
}

interface FilterState {
  images: ImageItem[];
  selectedImageId: string | null;
  activeFilter: string;
  filterIntensity: number;
  filterParams: Record<string, number | number[]>;
  presets: PresetItem[];
  customFilters: CustomFilterDef[];
  batchQueue: BatchItem[];
  showExportModal: boolean;
  showBatchPanel: boolean;
  compareMode: boolean;
  zoomLevel: number;
}

interface FilterActions {
  addImage: (file: File) => void;
  removeImage: (id: string) => void;
  selectImage: (id: string) => void;
  setActiveFilter: (type: string) => void;
  setFilterIntensity: (value: number) => void;
  setFilterParam: (name: string, value: number | number[]) => void;
  savePreset: (name: string) => void;
  loadPreset: (id: string) => void;
  deletePreset: (id: string) => void;
  addCustomFilter: (name: string, fragmentShader: string, uniforms: CustomFilterDef['uniforms']) => void;
  removeCustomFilter: (id: string) => void;
  addToBatch: (imageId: string) => void;
  removeFromBatch: (imageId: string) => void;
  updateBatchItemStatus: (imageId: string, status: BatchItem['status']) => void;
  toggleExportModal: () => void;
  toggleBatchPanel: () => void;
  toggleCompareMode: () => void;
  setZoomLevel: (level: number) => void;
}

type FilterStore = FilterState & FilterActions;

let nextId = 1;
function generateId(): string {
  return `img_${Date.now()}_${nextId++}`;
}

export const useFilterStore = create<FilterStore>((set, get) => ({
  images: [],
  selectedImageId: null,
  activeFilter: 'dreamy',
  filterIntensity: 0.5,
  filterParams: {},
  presets: [],
  customFilters: [],
  batchQueue: [],
  showExportModal: false,
  showBatchPanel: false,
  compareMode: false,
  zoomLevel: 1,

  addImage: (file: File) => {
    const id = generateId();
    const src = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const imageItem: ImageItem = {
        id,
        name: file.name,
        src,
        file,
        width: img.naturalWidth,
        height: img.naturalHeight,
      };
      set((state) => ({
        images: [...state.images, imageItem],
        selectedImageId: state.selectedImageId ?? id,
      }));
    };
    img.src = src;
  },

  removeImage: (id: string) => {
    set((state) => {
      const image = state.images.find((i) => i.id === id);
      if (image) {
        URL.revokeObjectURL(image.src);
      }
      return {
        images: state.images.filter((i) => i.id !== id),
        selectedImageId: state.selectedImageId === id
          ? state.images.find((i) => i.id !== id)?.id ?? null
          : state.selectedImageId,
        batchQueue: state.batchQueue.filter((b) => b.imageId !== id),
      };
    });
  },

  selectImage: (id: string) => {
    set({ selectedImageId: id });
  },

  setActiveFilter: (type: string) => {
    set({ activeFilter: type });
  },

  setFilterIntensity: (value: number) => {
    set({ filterIntensity: value });
  },

  setFilterParam: (name: string, value: number | number[]) => {
    set((state) => ({
      filterParams: { ...state.filterParams, [name]: value },
    }));
  },

  savePreset: (name: string) => {
    const { activeFilter, filterIntensity, filterParams } = get();
    const preset: PresetItem = {
      id: `preset_${Date.now()}`,
      name,
      config: {
        filterType: activeFilter,
        intensity: filterIntensity,
        customParams: { ...filterParams },
      },
      createdAt: new Date().toISOString(),
    };
    set((state) => ({
      presets: [...state.presets, preset],
    }));
  },

  loadPreset: (id: string) => {
    const preset = get().presets.find((p) => p.id === id);
    if (preset) {
      set({
        activeFilter: preset.config.filterType,
        filterIntensity: preset.config.intensity,
        filterParams: { ...preset.config.customParams },
      });
    }
  },

  deletePreset: (id: string) => {
    set((state) => ({
      presets: state.presets.filter((p) => p.id !== id),
    }));
  },

  addCustomFilter: (name: string, fragmentShader: string, uniforms: CustomFilterDef['uniforms']) => {
    const filter: CustomFilterDef = {
      id: `custom_${Date.now()}`,
      name,
      fragmentShader,
      uniforms,
      compiled: false,
    };
    set((state) => ({
      customFilters: [...state.customFilters, filter],
    }));
  },

  removeCustomFilter: (id: string) => {
    set((state) => ({
      customFilters: state.customFilters.filter((f) => f.id !== id),
    }));
  },

  addToBatch: (imageId: string) => {
    const { activeFilter, filterIntensity, filterParams } = get();
    const exists = get().batchQueue.some((b) => b.imageId === imageId);
    if (exists) return;
    const item: BatchItem = {
      imageId,
      config: {
        filterType: activeFilter,
        intensity: filterIntensity,
        customParams: { ...filterParams },
      },
      status: 'pending',
    };
    set((state) => ({
      batchQueue: [...state.batchQueue, item],
    }));
  },

  removeFromBatch: (imageId: string) => {
    set((state) => ({
      batchQueue: state.batchQueue.filter((b) => b.imageId !== imageId),
    }));
  },

  updateBatchItemStatus: (imageId: string, status: BatchItem['status']) => {
    set((state) => ({
      batchQueue: state.batchQueue.map((b) =>
        b.imageId === imageId ? { ...b, status } : b
      ),
    }));
  },

  toggleExportModal: () => {
    set((state) => ({ showExportModal: !state.showExportModal }));
  },

  toggleBatchPanel: () => {
    set((state) => ({ showBatchPanel: !state.showBatchPanel }));
  },

  toggleCompareMode: () => {
    set((state) => ({ compareMode: !state.compareMode }));
  },

  setZoomLevel: (level: number) => {
    set({ zoomLevel: level });
  },
}));

export default useFilterStore;
