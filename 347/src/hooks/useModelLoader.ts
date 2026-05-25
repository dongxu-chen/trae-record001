import { useState, useCallback, useRef } from 'react';
import { useEditorStore } from '../store/editorStore';
import { ModelLoader, type LoadedModel } from '../utils/three/ModelLoader';

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface LoadingProgress {
  loaded: number;
  total: number;
  percentage: number;
}

interface LoadError {
  message: string;
  code?: string;
  details?: unknown;
}

export function useModelLoader() {
  const loaderRef = useRef<ModelLoader | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [progress, setProgress] = useState<LoadingProgress>({
    loaded: 0,
    total: 0,
    percentage: 0,
  });
  const [error, setError] = useState<LoadError | null>(null);
  const [loadedModel, setLoadedModel] = useState<LoadedModel | null>(null);

  const { loadModel, clearModel } = useEditorStore();

  const getLoader = useCallback((): ModelLoader => {
    if (!loaderRef.current) {
      loaderRef.current = new ModelLoader();
    }
    return loaderRef.current;
  }, []);

  const simulateProgress = useCallback((
    onProgress: (progress: LoadingProgress) => void
  ): () => void => {
    let currentProgress = 0;
    let cancelled = false;

    const interval = setInterval(() => {
      if (cancelled) return;

      const increment = Math.random() * 15;
      currentProgress = Math.min(currentProgress + increment, 95);

      onProgress({
        loaded: currentProgress,
        total: 100,
        percentage: currentProgress,
      });
    }, 100);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const loadFromFile = useCallback(async (file: File): Promise<LoadedModel | null> => {
    setLoadingState('loading');
    setError(null);
    setProgress({ loaded: 0, total: 0, percentage: 0 });

    const cancelProgress = simulateProgress(setProgress);

    try {
      const loader = getLoader();
      const model = await loader.loadFromFile(file);

      setProgress({ loaded: 100, total: 100, percentage: 100 });

      await loadModel(file);

      setLoadedModel(model);
      setLoadingState('success');

      return model;
    } catch (err) {
      const loadError: LoadError = {
        message: err instanceof Error ? err.message : 'Unknown error occurred',
        code: err instanceof Error && 'code' in err ? String((err as { code: unknown }).code) : 'LOAD_ERROR',
        details: err,
      };

      setError(loadError);
      setLoadingState('error');

      console.error('Model loading failed:', loadError);
      return null;
    } finally {
      cancelProgress();
    }
  }, [getLoader, loadModel, simulateProgress]);

  const loadFromUrl = useCallback(async (
    url: string,
    fileType: 'fbx' | 'gltf' | 'glb'
  ): Promise<LoadedModel | null> => {
    setLoadingState('loading');
    setError(null);
    setProgress({ loaded: 0, total: 0, percentage: 0 });

    const cancelProgress = simulateProgress(setProgress);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const blob = await response.blob();
      const fileName = url.split('/').pop() || `model.${fileType}`;
      const file = new File([blob], fileName, { type: blob.type });

      return await loadFromFile(file);
    } catch (err) {
      const loadError: LoadError = {
        message: err instanceof Error ? err.message : 'Unknown error occurred',
        code: 'URL_LOAD_ERROR',
        details: err,
      };

      setError(loadError);
      setLoadingState('error');

      console.error('URL model loading failed:', loadError);
      return null;
    } finally {
      cancelProgress();
    }
  }, [loadFromFile, simulateProgress]);

  const unloadModel = useCallback(() => {
    clearModel();
    setLoadedModel(null);
    setLoadingState('idle');
    setError(null);
    setProgress({ loaded: 0, total: 0, percentage: 0 });

    if (loaderRef.current) {
      loaderRef.current.dispose();
      loaderRef.current = null;
    }
  }, [clearModel]);

  const resetError = useCallback(() => {
    setError(null);
    if (loadingState === 'error') {
      setLoadingState('idle');
    }
  }, [loadingState]);

  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    const allowedExtensions = ['fbx', 'gltf', 'glb'];
    const extension = file.name.split('.').pop()?.toLowerCase();

    if (!extension || !allowedExtensions.includes(extension)) {
      return {
        valid: false,
        error: `Unsupported file format. Allowed formats: ${allowedExtensions.join(', ')}`,
      };
    }

    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `File too large. Maximum size: ${maxSize / 1024 / 1024}MB`,
      };
    }

    return { valid: true };
  }, []);

  const handleFileDrop = useCallback(async (
    event: React.DragEvent<HTMLElement>
  ): Promise<LoadedModel | null> => {
    event.preventDefault();
    event.stopPropagation();

    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) {
      setError({ message: 'No files dropped', code: 'NO_FILES' });
      return null;
    }

    const file = files[0];
    const validation = validateFile(file);

    if (!validation.valid) {
      setError({ message: validation.error || 'Invalid file', code: 'INVALID_FILE' });
      setLoadingState('error');
      return null;
    }

    return await loadFromFile(file);
  }, [validateFile, loadFromFile]);

  const handleFileInput = useCallback(async (
    event: React.ChangeEvent<HTMLInputElement>
  ): Promise<LoadedModel | null> => {
    const files = event.target.files;
    if (!files || files.length === 0) {
      return null;
    }

    const file = files[0];
    const validation = validateFile(file);

    if (!validation.valid) {
      setError({ message: validation.error || 'Invalid file', code: 'INVALID_FILE' });
      setLoadingState('error');
      return null;
    }

    return await loadFromFile(file);
  }, [validateFile, loadFromFile]);

  const getModelInfo = useCallback(() => {
    if (!loadedModel) return null;

    return {
      type: loadedModel.type,
      animationCount: loadedModel.animations.length,
      boneCount: loadedModel.bones.length,
      animations: loadedModel.animations.map((clip) => ({
        name: clip.name,
        duration: clip.duration,
        trackCount: clip.tracks.length,
      })),
    };
  }, [loadedModel]);

  const dispose = useCallback(() => {
    if (loaderRef.current) {
      loaderRef.current.dispose();
      loaderRef.current = null;
    }
  }, []);

  return {
    loadingState,
    progress,
    error,
    loadedModel,
    loadFromFile,
    loadFromUrl,
    unloadModel,
    resetError,
    validateFile,
    handleFileDrop,
    handleFileInput,
    getModelInfo,
    dispose,
    isLoading: loadingState === 'loading',
    isSuccess: loadingState === 'success',
    isError: loadingState === 'error',
    isIdle: loadingState === 'idle',
  };
}
