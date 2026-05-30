import { useState, useCallback, useRef, useEffect } from 'react';
import { IconConfig, defaultConfig, IconStyle, normalizeConfig } from '../engine/types';
import { IconGenerator } from '../engine/IconGenerator';

export function useIconGenerator(initialConfig?: Partial<IconConfig>) {
  const [config, setConfig] = useState<IconConfig>(() =>
    normalizeConfig({ ...defaultConfig, ...initialConfig })
  );

  const [dataUrl, setDataUrl] = useState<string>('');
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const generatorRef = useRef<IconGenerator | null>(null);

  useEffect(() => {
    const offscreen = document.createElement('canvas');
    offscreenCanvasRef.current = offscreen;
    generatorRef.current = new IconGenerator(offscreen);
  }, []);

  const generate = useCallback(() => {
    if (generatorRef.current) {
      generatorRef.current.generate(config);
      setDataUrl(generatorRef.current.toDataUrl());
    }
  }, [config]);

  useEffect(() => {
    generate();
  }, [generate]);

  const updateConfig = useCallback((updates: Partial<IconConfig>) => {
    setConfig((prev) => normalizeConfig({ ...prev, ...updates }));
  }, []);

  const setStyle = useCallback((style: IconStyle) => {
    updateConfig({ style });
  }, [updateConfig]);

  const setText = useCallback((text: string) => {
    updateConfig({ text: text || 'A' });
  }, [updateConfig]);

  const setSize = useCallback((size: number) => {
    updateConfig({ size });
  }, [updateConfig]);

  const setPrimaryColor = useCallback((color: string) => {
    updateConfig({ primaryColor: color });
  }, [updateConfig]);

  const setSecondaryColor = useCallback((color: string) => {
    updateConfig({ secondaryColor: color });
  }, [updateConfig]);

  const downloadPng = useCallback((filename?: string) => {
    if (!generatorRef.current) return;
    const name = filename || `icon-${config.text}-${config.style}`;
    const link = document.createElement('a');
    link.download = `${name}.png`;
    link.href = generatorRef.current.toDataUrl();
    link.click();
  }, [config]);

  const downloadSvg = useCallback((filename?: string) => {
    if (!generatorRef.current) return;
    const name = filename || `icon-${config.text}-${config.style}`;
    const svgString = generatorRef.current.toSvg(config);
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${name}.svg`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [config]);

  return {
    config,
    dataUrl,
    offscreenCanvasRef,
    updateConfig,
    setStyle,
    setText,
    setSize,
    setPrimaryColor,
    setSecondaryColor,
    generate,
    downloadPng,
    downloadSvg,
  };
}
