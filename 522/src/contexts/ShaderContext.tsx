import { createContext, useContext, useRef, useEffect, useState, ReactNode } from 'react';
import { ShaderManager, BatchProcessItem, ShaderValidationResult } from '@/utils/shaderManager';
import {
  vertexShaderSource,
  dreamyFragmentSource,
  backlightFragmentSource,
  neonFragmentSource,
  starburstFragmentSource,
} from '@/shaders';

interface ShaderContextType {
  shaderManager: ShaderManager | null;
  isInitialized: boolean;
  init: (canvas: HTMLCanvasElement) => void;
  batchProcess: (
    items: BatchProcessItem[],
    onProgress?: (index: number, total: number) => void
  ) => Promise<Uint8ClampedArray[]>;
  validateShader: (source: string) => ShaderValidationResult;
  registerCustomFilter: (
    source: string,
    uniforms: { name: string; type: string; defaultValue: number | number[] }[]
  ) => { success: boolean; filterName?: string; error?: string };
}

const ShaderContext = createContext<ShaderContextType | null>(null);

export function ShaderProvider({ children }: { children: ReactNode }) {
  const shaderManagerRef = useRef<ShaderManager | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const init = (canvas: HTMLCanvasElement) => {
    if (shaderManagerRef.current) return;

    try {
      const manager = new ShaderManager(canvas);
      manager.registerFilter('dreamy', vertexShaderSource, dreamyFragmentSource);
      manager.registerFilter(
        'backlight',
        vertexShaderSource,
        backlightFragmentSource
      );
      manager.registerFilter('neon', vertexShaderSource, neonFragmentSource);
      manager.registerFilter(
        'starburst',
        vertexShaderSource,
        starburstFragmentSource
      );
      shaderManagerRef.current = manager;
      setIsInitialized(true);
    } catch (error) {
      console.error('Failed to initialize ShaderManager:', error);
    }
  };

  const batchProcess = async (
    items: BatchProcessItem[],
    onProgress?: (index: number, total: number) => void
  ) => {
    if (!shaderManagerRef.current) {
      throw new Error('ShaderManager not initialized');
    }
    return shaderManagerRef.current.batchProcess(items, onProgress);
  };

  const validateShader = (source: string) => {
    if (!shaderManagerRef.current) {
      return { valid: false, error: 'ShaderManager not initialized' };
    }
    return shaderManagerRef.current.validateShaderSyntax(source);
  };

  const registerCustomFilter = (
    source: string,
    uniforms: { name: string; type: string; defaultValue: number | number[] }[]
  ) => {
    if (!shaderManagerRef.current) {
      return { success: false, error: 'ShaderManager not initialized' };
    }
    return shaderManagerRef.current.registerCustomFilter(source, uniforms);
  };

  useEffect(() => {
    return () => {
      if (shaderManagerRef.current) {
        shaderManagerRef.current.destroy();
        shaderManagerRef.current = null;
      }
    };
  }, []);

  return (
    <ShaderContext.Provider
      value={{
        shaderManager: shaderManagerRef.current,
        isInitialized,
        init,
        batchProcess,
        validateShader,
        registerCustomFilter,
      }}
    >
      {children}
    </ShaderContext.Provider>
  );
}

export function useShader() {
  const context = useContext(ShaderContext);
  if (!context) {
    throw new Error('useShader must be used within a ShaderProvider');
  }
  return context;
}

export default ShaderContext;
