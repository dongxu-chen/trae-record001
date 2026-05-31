import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { Project, SVGElementData, AnimationTrack, Keyframe, ElementType, AnimationProperty, AnimationType, FrameAnimation, FrameData } from '@/types';

interface ProjectState {
  project: Project;
  setProject: (project: Project) => void;
  updateProject: (updates: Partial<Project>) => void;
  
  addElement: (type: ElementType, attributes?: Record<string, any>) => void;
  updateElement: (id: string, updates: Partial<SVGElementData>) => void;
  deleteElement: (id: string) => void;
  duplicateElement: (id: string) => void;
  reorderElements: (elementIds: string[]) => void;
  
  addTrack: (elementId: string, property: AnimationProperty, type?: AnimationType) => void;
  updateTrack: (id: string, updates: Partial<AnimationTrack>) => void;
  deleteTrack: (id: string) => void;
  
  addKeyframe: (trackId: string, time: number, value: any) => void;
  updateKeyframe: (trackId: string, keyframeId: string, updates: Partial<Keyframe>) => void;
  deleteKeyframe: (trackId: string, keyframeId: string) => void;
  
  addFrameAnimation: (name: string, width: number, height: number, fps?: number) => FrameAnimation;
  updateFrameAnimation: (id: string, updates: Partial<FrameAnimation>) => void;
  deleteFrameAnimation: (id: string) => void;
  addFrame: (animationId: string, svgContent: string, duration?: number) => void;
  updateFrame: (animationId: string, frameId: string, updates: Partial<FrameData>) => void;
  deleteFrame: (animationId: string, frameId: string) => void;
  importFrameSequence: (animationId: string, files: File[]) => Promise<void>;
  
  resetProject: () => void;
  loadProject: (project: Project) => void;
}

const createDefaultProject = (): Project => ({
  id: uuidv4(),
  name: 'Untitled Project',
  width: 800,
  height: 600,
  duration: 5,
  fps: 60,
  elements: [],
  tracks: [],
  frameAnimations: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
});

const getDefaultAttributes = (type: ElementType): Record<string, any> => {
  switch (type) {
    case 'rect':
      return { width: 100, height: 80, fill: '#3b82f6', rx: 0, ry: 0 };
    case 'circle':
      return { r: 50, fill: '#10b981' };
    case 'ellipse':
      return { rx: 60, ry: 40, fill: '#8b5cf6' };
    case 'line':
      return { x2: 100, y2: 50, stroke: '#f59e0b', strokeWidth: 3 };
    case 'path':
      return { d: 'M0,0 C50,-50 100,50 150,0', fill: 'none', stroke: '#ef4444', strokeWidth: 3 };
    case 'polygon':
      return { points: '50,0 100,86.6 0,86.6', fill: '#06b6d4' };
    case 'text':
      return { text: 'Text', fontSize: 24, fill: '#1f2937', fontFamily: 'Arial' };
    default:
      return {};
  }
};

const getElementName = (type: ElementType, index: number): string => {
  const names: Record<ElementType, string> = {
    rect: 'Rectangle',
    circle: 'Circle',
    ellipse: 'Ellipse',
    line: 'Line',
    path: 'Path',
    polygon: 'Polygon',
    text: 'Text',
    image: 'Image',
  };
  return `${names[type]} ${index}`;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  project: createDefaultProject(),
  
  setProject: (project) => set({ project: { ...project, updatedAt: Date.now() } }),
  
  updateProject: (updates) => set((state) => ({
    project: { ...state.project, ...updates, updatedAt: Date.now() },
  })),
  
  addElement: (type, attributes = {}) => set((state) => {
    const elementIndex = state.project.elements.filter(e => e.type === type).length + 1;
    const newElement: SVGElementData = {
      id: uuidv4(),
      type,
      name: getElementName(type, elementIndex),
      visible: true,
      locked: false,
      attributes: { ...getDefaultAttributes(type), ...attributes },
      transform: {
        x: 100 + Math.random() * 200,
        y: 100 + Math.random() * 200,
        rotation: 0,
        scaleX: 1,
        scaleY: 1,
      },
    };
    return {
      project: {
        ...state.project,
        elements: [...state.project.elements, newElement],
        updatedAt: Date.now(),
      },
    };
  }),
  
  updateElement: (id, updates) => set((state) => ({
    project: {
      ...state.project,
      elements: state.project.elements.map(e =>
        e.id === id ? { ...e, ...updates } : e
      ),
      updatedAt: Date.now(),
    },
  })),
  
  deleteElement: (id) => set((state) => ({
    project: {
      ...state.project,
      elements: state.project.elements.filter(e => e.id !== id),
      tracks: state.project.tracks.filter(t => t.elementId !== id),
      updatedAt: Date.now(),
    },
  })),
  
  duplicateElement: (id) => set((state) => {
    const element = state.project.elements.find(e => e.id === id);
    if (!element) return state;
    
    const elementIndex = state.project.elements.filter(e => e.type === element.type).length + 1;
    const newElement: SVGElementData = {
      ...element,
      id: uuidv4(),
      name: getElementName(element.type, elementIndex),
      transform: {
        ...element.transform,
        x: element.transform.x + 30,
        y: element.transform.y + 30,
      },
    };
    
    const relatedTracks = state.project.tracks
      .filter(t => t.elementId === id)
      .map(t => ({
        ...t,
        id: uuidv4(),
        elementId: newElement.id,
        elementName: newElement.name,
        keyframes: t.keyframes.map(k => ({ ...k, id: uuidv4() })),
      }));
    
    return {
      project: {
        ...state.project,
        elements: [...state.project.elements, newElement],
        tracks: [...state.project.tracks, ...relatedTracks],
        updatedAt: Date.now(),
      },
    };
  }),
  
  reorderElements: (elementIds) => set((state) => {
    const orderedElements = elementIds
      .map(id => state.project.elements.find(e => e.id === id))
      .filter(Boolean) as SVGElementData[];
    return {
      project: {
        ...state.project,
        elements: orderedElements,
        updatedAt: Date.now(),
      },
    };
  }),
  
  addTrack: (elementId, property, type = 'keyframes') => set((state) => {
    const element = state.project.elements.find(e => e.id === elementId);
    if (!element) return state;
    
    const newTrack: AnimationTrack = {
      id: uuidv4(),
      elementId,
      elementName: element.name,
      property,
      keyframes: [],
      type,
      easing: 'power2.out',
      duration: 2,
      delay: 0,
    };
    
    return {
      project: {
        ...state.project,
        tracks: [...state.project.tracks, newTrack],
        updatedAt: Date.now(),
      },
    };
  }),
  
  updateTrack: (id, updates) => set((state) => ({
    project: {
      ...state.project,
      tracks: state.project.tracks.map(t =>
        t.id === id ? { ...t, ...updates } : t
      ),
      updatedAt: Date.now(),
    },
  })),
  
  deleteTrack: (id) => set((state) => ({
    project: {
      ...state.project,
      tracks: state.project.tracks.filter(t => t.id !== id),
      updatedAt: Date.now(),
    },
  })),
  
  addKeyframe: (trackId, time, value) => set((state) => {
    const newKeyframe: Keyframe = {
      id: uuidv4(),
      time,
      value,
    };
    
    return {
      project: {
        ...state.project,
        tracks: state.project.tracks.map(t => {
          if (t.id !== trackId) return t;
          const keyframes = [...t.keyframes, newKeyframe].sort((a, b) => a.time - b.time);
          return { ...t, keyframes };
        }),
        updatedAt: Date.now(),
      },
    };
  }),
  
  updateKeyframe: (trackId, keyframeId, updates) => set((state) => ({
    project: {
      ...state.project,
      tracks: state.project.tracks.map(t => {
        if (t.id !== trackId) return t;
        return {
          ...t,
          keyframes: t.keyframes.map(k =>
            k.id === keyframeId ? { ...k, ...updates } : k
          ).sort((a, b) => a.time - b.time),
        };
      }),
      updatedAt: Date.now(),
    },
  })),
  
  deleteKeyframe: (trackId, keyframeId) => set((state) => ({
    project: {
      ...state.project,
      tracks: state.project.tracks.map(t => {
        if (t.id !== trackId) return t;
        return {
          ...t,
          keyframes: t.keyframes.filter(k => k.id !== keyframeId),
        };
      }),
      updatedAt: Date.now(),
    },
  })),
  
  addFrameAnimation: (name, width, height, fps = 24) => {
    const newAnimation: FrameAnimation = {
      id: uuidv4(),
      name,
      frames: [],
      fps,
      loop: true,
      width,
      height,
    };
    set((state) => ({
      project: {
        ...state.project,
        frameAnimations: [...state.project.frameAnimations, newAnimation],
        updatedAt: Date.now(),
      },
    }));
    return newAnimation;
  },
  
  updateFrameAnimation: (id, updates) => set((state) => ({
    project: {
      ...state.project,
      frameAnimations: state.project.frameAnimations.map(fa =>
        fa.id === id ? { ...fa, ...updates } : fa
      ),
      updatedAt: Date.now(),
    },
  })),
  
  deleteFrameAnimation: (id) => set((state) => ({
    project: {
      ...state.project,
      frameAnimations: state.project.frameAnimations.filter(fa => fa.id !== id),
      updatedAt: Date.now(),
    },
  })),
  
  addFrame: (animationId, svgContent, duration = 1) => set((state) => ({
    project: {
      ...state.project,
      frameAnimations: state.project.frameAnimations.map(fa => {
        if (fa.id !== animationId) return fa;
        const newFrame: FrameData = {
          id: uuidv4(),
          index: fa.frames.length,
          svgContent,
          duration,
        };
        return { ...fa, frames: [...fa.frames, newFrame] };
      }),
      updatedAt: Date.now(),
    },
  })),
  
  updateFrame: (animationId, frameId, updates) => set((state) => ({
    project: {
      ...state.project,
      frameAnimations: state.project.frameAnimations.map(fa => {
        if (fa.id !== animationId) return fa;
        return {
          ...fa,
          frames: fa.frames.map(f => f.id === frameId ? { ...f, ...updates } : f),
        };
      }),
      updatedAt: Date.now(),
    },
  })),
  
  deleteFrame: (animationId, frameId) => set((state) => ({
    project: {
      ...state.project,
      frameAnimations: state.project.frameAnimations.map(fa => {
        if (fa.id !== animationId) return fa;
        return {
          ...fa,
          frames: fa.frames.filter(f => f.id !== frameId).map((f, i) => ({ ...f, index: i })),
        };
      }),
      updatedAt: Date.now(),
    },
  })),
  
  importFrameSequence: async (animationId, files) => {
    const readFiles = files.map(file => {
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsText(file);
      });
    });
    
    const contents = await Promise.all(readFiles);
    
    set((state) => ({
      project: {
        ...state.project,
        frameAnimations: state.project.frameAnimations.map(fa => {
          if (fa.id !== animationId) return fa;
          const newFrames: FrameData[] = contents.map((content, i) => ({
            id: uuidv4(),
            index: fa.frames.length + i,
            svgContent: content,
            duration: 1,
          }));
          return { ...fa, frames: [...fa.frames, ...newFrames] };
        }),
        updatedAt: Date.now(),
      },
    }));
  },
  
  resetProject: () => set({ project: createDefaultProject() }),
  
  loadProject: (project) => set({ project: { ...project, updatedAt: Date.now() } }),
}));
