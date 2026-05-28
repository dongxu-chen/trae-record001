import { create } from 'zustand';
import type { ColorSpaces } from '@/types';
import { convertColor } from '@/utils/colorConverter';

interface ColorStore {
  currentColor: string;
  compareColor: string;
  colorSpaces: ColorSpaces;
  currentProject: string;
  setCurrentColor: (hex: string) => void;
  setCompareColor: (hex: string) => void;
  setCurrentProject: (project: string) => void;
}

export const useColorStore = create<ColorStore>((set) => ({
  currentColor: '#3b82f6',
  compareColor: '#f43f5e',
  colorSpaces: convertColor('#3b82f6'),
  currentProject: '',
  setCurrentColor: (hex: string) =>
    set({
      currentColor: hex,
      colorSpaces: convertColor(hex),
    }),
  setCompareColor: (hex: string) =>
    set({
      compareColor: hex,
    }),
  setCurrentProject: (project: string) =>
    set({
      currentProject: project,
    }),
}));