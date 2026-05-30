import React, { useState, useRef, useEffect, useCallback } from 'react';
import { IconConfig } from '../engine/types';
import { IconGenerator } from '../engine/IconGenerator';
import {
  AnimationConfig,
  AnimationType,
  animationPresets,
  defaultAnimationConfig,
  calculateAnimationFrame,
} from '../engine/animationEngine';
import { downloadLottie } from '../utils/lottieExporter';
import {
  Play,
  Pause,
  RotateCcw,
  Download,
  Sparkles,
  Clock,
  Repeat,
  ChevronDown,
} from 'lucide-react';

interface AnimationPreviewProps {
  config: IconConfig;
}

export function AnimationPreview({ config }: AnimationPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const generatorRef = useRef<IconGenerator | null>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [showPresets, setShowPresets] = useState(false);
  const [animationConfig, setAnimationConfig] = useState<AnimationConfig>(
    defaultAnimationConfig
  );

  const selectedPreset = animationPresets.find((p) => p.id === animationConfig.type);

  useEffect(() => {
    if (!offscreenCanvasRef.current) {
      offscreenCanvasRef.current = document.createElement('canvas');
      generatorRef.current = new IconGenerator(offscreenCanvasRef.current);
    }
  }, []);

  const renderFrame = useCallback(
    (timestamp: number) => {
      if (!canvasRef.current || !generatorRef.current || !offscreenCanvasRef.current) return;

      const ctx = canvasRef.current.getContext('2d');
      if (!ctx) return;

      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const frame = calculateAnimationFrame(animationConfig, elapsed);

      const size = config.size;
      canvasRef.current.width = size;
      canvasRef.current.height = size;

      generatorRef.current.generate(config);

      ctx.clearRect(0, 0, size, size);

      ctx.save();

      const centerX = size / 2;
      const centerY = size / 2;

      ctx.translate(centerX + frame.translateX, centerY + frame.translateY);
      ctx.rotate((frame.rotation * Math.PI) / 180);
      ctx.scale(frame.scale, frame.scale);
      ctx.globalAlpha = frame.opacity;

      if (frame.colorShift > 0 && frame.colorShift < 1) {
        ctx.filter = `hue-rotate(${frame.colorShift * 360}deg)`;
      }

      ctx.drawImage(
        offscreenCanvasRef.current,
        -centerX,
        -centerY
      );

      ctx.restore();

      if (isPlaying) {
        if (!animationConfig.loop && elapsed >= animationConfig.duration + animationConfig.delay) {
          setIsPlaying(false);
          return;
        }
        animationRef.current = requestAnimationFrame(renderFrame);
      }
    },
    [config, animationConfig, isPlaying]
  );

  useEffect(() => {
    if (isPlaying) {
      startTimeRef.current = null;
      animationRef.current = requestAnimationFrame(renderFrame);
    } else if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, renderFrame]);

  const handlePlayPause = () => {
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      startTimeRef.current = null;
      setIsPlaying(true);
    }
  };

  const handleReset = () => {
    startTimeRef.current = null;
    if (!isPlaying) {
      setIsPlaying(true);
    }
  };

  const handleSelectPreset = (type: AnimationType) => {
    setAnimationConfig({
      ...animationConfig,
      type,
    });
    setShowPresets(false);
    startTimeRef.current = null;
  };

  const handleDownloadLottie = () => {
    downloadLottie(config, animationConfig);
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <div className="flex items-center gap-3 pb-4 border-b border-gray-100 mb-6">
        <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-xl">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">图标动画</h3>
          <p className="text-sm text-gray-500">选择动画效果并导出Lottie动画</p>
        </div>
      </div>

      <div className="relative flex items-center justify-center p-8 bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl mb-6 overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `
            linear-gradient(45deg, #fff 25%, transparent 25%),
            linear-gradient(-45deg, #fff 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #fff 75%),
            linear-gradient(-45deg, transparent 75%, #fff 75%)
          `,
          backgroundSize: '20px 20px',
          backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
        }} />
        <div className="relative">
          <canvas
            ref={canvasRef}
            className="max-w-full h-auto rounded-lg shadow-2xl"
            style={{ maxHeight: '280px' }}
          />
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            动画效果
          </label>
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="w-full flex items-center justify-between px-4 py-3 border-2 border-gray-200 rounded-xl hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg font-medium text-gray-800">
                {selectedPreset?.name || '选择动画'}
              </span>
              <span className="text-sm text-gray-500">
                {selectedPreset?.description}
              </span>
            </div>
            <ChevronDown
              className={`w-5 h-5 text-gray-400 transition-transform ${
                showPresets ? 'rotate-180' : ''
              }`}
            />
          </button>

          {showPresets && (
            <div className="absolute z-10 w-full mt-2 bg-white border-2 border-gray-200 rounded-xl shadow-xl overflow-hidden">
              <div className="grid grid-cols-2 gap-1 p-2">
                {animationPresets.map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => handleSelectPreset(preset.id)}
                    className={`p-3 rounded-lg text-left transition-colors ${
                      animationConfig.type === preset.id
                        ? 'bg-blue-100 text-blue-700'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <div className="font-medium text-sm">{preset.name}</div>
                    <div className="text-xs text-gray-500">{preset.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Clock className="w-4 h-4" />
              动画时长
            </label>
            <input
              type="range"
              min={500}
              max={3000}
              step={100}
              value={animationConfig.duration}
              onChange={(e) =>
                setAnimationConfig({
                  ...animationConfig,
                  duration: Number(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="text-xs text-gray-500 text-center">
              {animationConfig.duration}ms
            </div>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Repeat className="w-4 h-4" />
              循环播放
            </label>
            <button
              onClick={() =>
                setAnimationConfig({
                  ...animationConfig,
                  loop: !animationConfig.loop,
                })
              }
              className={`relative w-full h-12 rounded-xl border-2 transition-colors ${
                animationConfig.loop
                  ? 'bg-blue-50 border-blue-300'
                  : 'bg-gray-50 border-gray-200'
              }`}
            >
              <span
                className={`absolute top-1 w-9 h-9 bg-white rounded-lg shadow-md transition-transform ${
                  animationConfig.loop
                    ? 'translate-x-[calc(100%-8px)]'
                    : 'translate-x-1'
                }`}
              />
              <span
                className={`absolute left-4 text-sm font-medium ${
                  animationConfig.loop ? 'text-blue-600' : 'text-gray-400'
                }`}
              >
                循环
              </span>
              <span
                className={`absolute right-4 text-sm font-medium ${
                  animationConfig.loop ? 'text-gray-400' : 'text-gray-600'
                }`}
              >
                单次
              </span>
            </button>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handlePlayPause}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl ${
              isPlaying
                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600'
                : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4" />
                暂停
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                播放
              </>
            )}
          </button>

          <button
            onClick={handleReset}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            重置
          </button>

          <button
            onClick={handleDownloadLottie}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium hover:from-purple-600 hover:to-pink-600 transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            <Download className="w-4 h-4" />
            Lottie
          </button>
        </div>

        <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
          <p className="text-sm text-blue-700">
            <strong>Lottie动画导出：</strong> 导出的JSON文件可在Web、iOS、Android端原生渲染，保持矢量清晰度。
          </p>
        </div>
      </div>
    </div>
  );
}
