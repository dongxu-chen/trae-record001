export type ElementType = 'rect' | 'circle' | 'ellipse' | 'path' | 'line' | 'polygon' | 'text' | 'image';

export type AnimationType = 'keyframes' | 'motionPath' | 'morph' | 'frameByFrame';

export type AnimationProperty = 'x' | 'y' | 'rotation' | 'scale' | 'scaleX' | 'scaleY' | 'opacity' | 'fill' | 'stroke' | 'strokeWidth' | 'path';

export interface Transform {
  x: number;
  y: number;
  rotation: number;
  scaleX: number;
  scaleY: number;
}

export interface SVGElementData {
  id: string;
  type: ElementType;
  name: string;
  visible: boolean;
  locked: boolean;
  attributes: Record<string, any>;
  transform: Transform;
}

export interface Keyframe {
  id: string;
  time: number;
  value: any;
  easing?: string;
}

export interface FrameData {
  id: string;
  index: number;
  svgContent: string;
  duration: number;
}

export interface FrameAnimation {
  id: string;
  name: string;
  frames: FrameData[];
  fps: number;
  loop: boolean;
  width: number;
  height: number;
}

export interface MotionPathConfig {
  path: string;
  align?: string;
  alignToSelf?: boolean;
  start?: number;
  end?: number;
  orient?: 'auto' | 'auto-start' | 'auto-end' | 'none';
}

export interface AnimationTrack {
  id: string;
  elementId: string;
  elementName: string;
  property: AnimationProperty;
  keyframes: Keyframe[];
  type: AnimationType;
  easing: string;
  duration: number;
  delay: number;
  repeat?: number;
  yoyo?: boolean;
  motionPath?: MotionPathConfig;
  frameAnimation?: FrameAnimation;
}

export interface Project {
  id: string;
  name: string;
  width: number;
  height: number;
  duration: number;
  fps: number;
  elements: SVGElementData[];
  tracks: AnimationTrack[];
  frameAnimations: FrameAnimation[];
  createdAt: number;
  updatedAt: number;
}

export interface EditorState {
  selectedElementId: string | null;
  selectedTrackId: string | null;
  selectedKeyframeId: string | null;
  currentTime: number;
  isPlaying: boolean;
  isLooping: boolean;
  zoom: number;
  pan: { x: number; y: number };
  showGrid: boolean;
  snapToGrid: boolean;
  gridSize: number;
  activeModal: 'none' | 'codePreview' | 'marketplace' | 'frameImport';
}

export interface AnimationTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail: string;
  author: string;
  project: Project;
  tags: string[];
  downloads: number;
  createdAt: number;
}

export const TEMPLATE_CATEGORIES = [
  'All',
  'Loading',
  'Transition',
  'Button',
  'Icon',
  'Background',
  'Text Effect',
  'Character',
  'Logo',
  'Particle',
] as const;

export interface EasingPreset {
  name: string;
  value: string;
  label: string;
}

export const EASING_PRESETS: EasingPreset[] = [
  { name: 'none', value: 'none', label: 'Linear' },
  { name: 'power1.in', value: 'power1.in', label: 'Power 1 In' },
  { name: 'power1.out', value: 'power1.out', label: 'Power 1 Out' },
  { name: 'power1.inOut', value: 'power1.inOut', label: 'Power 1 InOut' },
  { name: 'power2.in', value: 'power2.in', label: 'Power 2 In' },
  { name: 'power2.out', value: 'power2.out', label: 'Power 2 Out' },
  { name: 'power2.inOut', value: 'power2.inOut', label: 'Power 2 InOut' },
  { name: 'power3.in', value: 'power3.in', label: 'Power 3 In' },
  { name: 'power3.out', value: 'power3.out', label: 'Power 3 Out' },
  { name: 'power3.inOut', value: 'power3.inOut', label: 'Power 3 InOut' },
  { name: 'power4.in', value: 'power4.in', label: 'Power 4 In' },
  { name: 'power4.out', value: 'power4.out', label: 'Power 4 Out' },
  { name: 'power4.inOut', value: 'power4.inOut', label: 'Power 4 InOut' },
  { name: 'back.in', value: 'back.in', label: 'Back In' },
  { name: 'back.out', value: 'back.out', label: 'Back Out' },
  { name: 'back.inOut', value: 'back.inOut', label: 'Back InOut' },
  { name: 'elastic.in', value: 'elastic.in', label: 'Elastic In' },
  { name: 'elastic.out', value: 'elastic.out', label: 'Elastic Out' },
  { name: 'elastic.inOut', value: 'elastic.inOut', label: 'Elastic InOut' },
  { name: 'bounce.in', value: 'bounce.in', label: 'Bounce In' },
  { name: 'bounce.out', value: 'bounce.out', label: 'Bounce Out' },
  { name: 'bounce.inOut', value: 'bounce.inOut', label: 'Bounce InOut' },
  { name: 'circ.in', value: 'circ.in', label: 'Circ In' },
  { name: 'circ.out', value: 'circ.out', label: 'Circ Out' },
  { name: 'circ.inOut', value: 'circ.inOut', label: 'Circ InOut' },
  { name: 'expo.in', value: 'expo.in', label: 'Expo In' },
  { name: 'expo.out', value: 'expo.out', label: 'Expo Out' },
  { name: 'expo.inOut', value: 'expo.inOut', label: 'Expo InOut' },
  { name: 'sine.in', value: 'sine.in', label: 'Sine In' },
  { name: 'sine.out', value: 'sine.out', label: 'Sine Out' },
  { name: 'sine.inOut', value: 'sine.inOut', label: 'Sine InOut' },
];
