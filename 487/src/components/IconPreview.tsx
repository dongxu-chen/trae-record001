import React, { useEffect, useRef, useCallback, useState } from 'react';
import { IconConfig } from '../engine/types';
import { IconGenerator } from '../engine/IconGenerator';
import { WebGLRenderer } from '../engine/renderers/WebGLRenderer';
import { useDebounce } from '../hooks/useDebounce';
import { Download, Image as ImageIcon, Maximize2, Cpu } from 'lucide-react';

interface IconPreviewProps {
  config: IconConfig;
  onDownloadPng: () => void;
  onDownloadSvg: () => void;
}

export function IconPreview({ config, onDownloadPng, onDownloadSvg }: IconPreviewProps) {
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement>(null);
  const generatorRef = useRef<IconGenerator | null>(null);
  const webglRef = useRef<WebGLRenderer | null>(null);
  const [webglAvailable, setWebglAvailable] = useState(false);

  useEffect(() => {
    const offscreen = document.createElement('canvas');
    offscreenCanvasRef.current = offscreen;
    generatorRef.current = new IconGenerator(offscreen);

    if (displayCanvasRef.current) {
      const renderer = new WebGLRenderer();
      const ok = renderer.init(displayCanvasRef.current);
      if (ok) {
        webglRef.current = renderer;
        setWebglAvailable(true);
      }
    }

    return () => {
      if (webglRef.current) {
        webglRef.current.destroy();
      }
    };
  }, []);

  const renderIcon = useCallback(() => {
    if (!generatorRef.current || !offscreenCanvasRef.current) return;

    generatorRef.current.generate(config);

    if (webglRef.current && displayCanvasRef.current) {
      webglRef.current.renderFromCanvas(offscreenCanvasRef.current);
    } else if (displayCanvasRef.current) {
      const ctx = displayCanvasRef.current.getContext('2d');
      if (ctx) {
        displayCanvasRef.current.width = config.size;
        displayCanvasRef.current.height = config.size;
        ctx.clearRect(0, 0, config.size, config.size);
        ctx.drawImage(offscreenCanvasRef.current, 0, 0);
      }
    }
  }, [config]);

  const debouncedRender = useDebounce(renderIcon, 16);

  useEffect(() => {
    debouncedRender();
  }, [debouncedRender]);

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">图标预览</h3>
        <div className="flex items-center gap-2">
          {webglAvailable && (
            <span className="flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
              <Cpu className="w-3 h-3" />
              GPU加速
            </span>
          )}
          <span className="text-sm text-gray-500">
            {config.size} × {config.size}px
          </span>
        </div>
      </div>

      <div className="relative flex items-center justify-center p-8 bg-gradient-to-br from-gray-100 to-gray-200 rounded-xl mb-6">
        <div className="absolute inset-0 opacity-30" style={{
          backgroundImage: `
            linear-gradient(45deg, #e5e7eb 25%, transparent 25%),
            linear-gradient(-45deg, #e5e7eb 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #e5e7eb 75%),
            linear-gradient(-45deg, transparent 75%, #e5e7eb 75%)
          `,
          backgroundSize: '20px 20px',
          backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
        }} />
        <div className="relative">
          <canvas
            ref={displayCanvasRef}
            className="max-w-full h-auto rounded-lg shadow-2xl transition-all duration-300 hover:scale-105"
            style={{ maxHeight: '300px' }}
          />
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={onDownloadPng}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            <ImageIcon className="w-4 h-4" />
            PNG 下载
          </button>
          <button
            onClick={onDownloadSvg}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium hover:from-purple-600 hover:to-purple-700 transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            <Download className="w-4 h-4" />
            SVG 下载
          </button>
        </div>

        <div className="p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Maximize2 className="w-4 h-4" />
            <span>当前文字: </span>
            <code className="px-2 py-1 bg-white rounded font-mono text-gray-800">
              {config.text.toUpperCase().substring(0, 2)}
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}
