import { create } from 'zustand';
import type { FunctionItem, ViewState, MouseState, DrawConfig } from '../types';
import { getNextColor } from '../utils/colors';
import { parseAndCompile, computeDerivative } from '../utils/expressionParser';

interface GraphState {
  functions: FunctionItem[];
  viewState: ViewState;
  drawConfig: DrawConfig;
  mouseState: MouseState;
  addFunction: (expression: string, color?: string) => { success: boolean; error?: string };
  removeFunction: (id: string) => void;
  toggleFunctionVisibility: (id: string) => void;
  toggleDerivative: (id: string) => void;
  updateFunctionColor: (id: string, color: string) => void;
  setViewState: (state: Partial<ViewState>) => void;
  resetView: () => void;
  setMouseState: (state: Partial<MouseState>) => void;
  setDrawConfig: (config: Partial<DrawConfig>) => void;
  loadFromLocalStorage: () => void;
  saveToLocalStorage: () => void;
}

const defaultViewState: ViewState = {
  xMin: -10,
  xMax: 10,
  yMin: -10,
  yMax: 10,
  gridVisible: true,
  axisVisible: true,
};

const defaultDrawConfig: DrawConfig = {
  lineWidth: 2,
  gridColor: 'rgba(255, 255, 255, 0.1)',
  axisColor: 'rgba(255, 255, 255, 0.6)',
  backgroundColor: '#0f172a',
};

const defaultMouseState: MouseState = {
  x: 0,
  y: 0,
  mathX: 0,
  mathY: 0,
  isDragging: false,
};

export const useGraphStore = create<GraphState>((set, get) => ({
  functions: [],
  viewState: defaultViewState,
  drawConfig: defaultDrawConfig,
  mouseState: defaultMouseState,

  addFunction: (expression: string, color?: string) => {
    const result = parseAndCompile(expression);
    if (!result.success || !result.compiled) {
      return { success: false, error: result.error };
    }

    const functions = get().functions;
    const newFunction: FunctionItem = {
      id: Date.now().toString(),
      expression,
      compiledFunction: result.compiled,
      color: color || getNextColor(functions.length),
      visible: true,
      showDerivative: false,
    };

    set((state) => ({
      functions: [...state.functions, newFunction],
    }));

    get().saveToLocalStorage();
    return { success: true };
  },

  removeFunction: (id: string) => {
    set((state) => ({
      functions: state.functions.filter((f) => f.id !== id),
    }));
    get().saveToLocalStorage();
  },

  toggleFunctionVisibility: (id: string) => {
    set((state) => ({
      functions: state.functions.map((f) =>
        f.id === id ? { ...f, visible: !f.visible } : f
      ),
    }));
    get().saveToLocalStorage();
  },

  toggleDerivative: (id: string) => {
    set((state) => {
      const func = state.functions.find((f) => f.id === id);
      if (!func) return state;

      const updatedFunctions = state.functions.map((f) => {
        if (f.id !== id) return f;

        if (!f.showDerivative) {
          const derivResult = computeDerivative(f.expression);
          if (derivResult.success && derivResult.derivative && derivResult.compiled) {
            return {
              ...f,
              showDerivative: true,
              derivativeExpression: derivResult.derivative,
              derivativeCompiled: derivResult.compiled,
            };
          }
          return f;
        } else {
          return {
            ...f,
            showDerivative: false,
          };
        }
      });

      return { functions: updatedFunctions };
    });
    get().saveToLocalStorage();
  },

  updateFunctionColor: (id: string, color: string) => {
    set((state) => ({
      functions: state.functions.map((f) =>
        f.id === id ? { ...f, color } : f
      ),
    }));
    get().saveToLocalStorage();
  },

  setViewState: (newState) => {
    set((state) => ({
      viewState: { ...state.viewState, ...newState },
    }));
  },

  resetView: () => {
    set({ viewState: defaultViewState });
  },

  setMouseState: (newState) => {
    set((state) => ({
      mouseState: { ...state.mouseState, ...newState },
    }));
  },

  setDrawConfig: (config) => {
    set((state) => ({
      drawConfig: { ...state.drawConfig, ...config },
    }));
  },

  loadFromLocalStorage: () => {
    try {
      const saved = localStorage.getItem('graphTool_functions');
      if (saved) {
        const savedFunctions = JSON.parse(saved) as FunctionItem[];
        const compiledFunctions: FunctionItem[] = [];

        for (const f of savedFunctions) {
          const compileResult = parseAndCompile(f.expression);
          if (compileResult.success && compileResult.compiled) {
            const func: FunctionItem = {
              ...f,
              compiledFunction: compileResult.compiled,
            };

            if (f.showDerivative && f.derivativeExpression) {
              const derivResult = computeDerivative(f.expression);
              if (derivResult.success && derivResult.compiled) {
                func.derivativeCompiled = derivResult.compiled;
                func.derivativeExpression = derivResult.derivative;
              }
            }

            compiledFunctions.push(func);
          }
        }

        set({ functions: compiledFunctions });
      }

      const savedView = localStorage.getItem('graphTool_viewState');
      if (savedView) {
        set({ viewState: JSON.parse(savedView) });
      }
    } catch {
      console.error('Failed to load from localStorage');
    }
  },

  saveToLocalStorage: () => {
    try {
      const functionsToSave = get().functions.map((f) => ({
        id: f.id,
        expression: f.expression,
        color: f.color,
        visible: f.visible,
        showDerivative: f.showDerivative,
        derivativeExpression: f.derivativeExpression,
      }));
      localStorage.setItem('graphTool_functions', JSON.stringify(functionsToSave));
      localStorage.setItem('graphTool_viewState', JSON.stringify(get().viewState));
    } catch {
      console.error('Failed to save to localStorage');
    }
  },
}));
