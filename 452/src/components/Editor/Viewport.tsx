import { useRef, useCallback } from 'react';
import { Scene } from '../Three/Scene';
import { useSceneStore } from '../../store/useSceneStore';
import type { ObjectType } from '../../types/scene';
import * as THREE from 'three';

export function Viewport() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { addObject } = useSceneStore();

  const handleSceneReady = useCallback((scene: THREE.Scene) => {
    (window as any).__threeScene = scene;
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const modelType = e.dataTransfer.getData('modelType') as ObjectType;
    if (modelType) {
      addObject(modelType);
    }
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 relative"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <Scene className="w-full h-full" onSceneReady={handleSceneReady} />

      <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-gray-900/80 backdrop-blur-sm px-3 py-2 rounded-lg">
        <div className="w-3 h-3 bg-red-500 rounded-full" title="X轴" />
        <div className="w-3 h-3 bg-green-500 rounded-full" title="Y轴" />
        <div className="w-3 h-3 bg-blue-500 rounded-full" title="Z轴" />
        <span className="text-xs text-gray-400 ml-1">坐标轴</span>
      </div>

      <div className="absolute top-4 right-4 bg-gray-900/80 backdrop-blur-sm px-3 py-2 rounded-lg">
        <div className="text-xs text-gray-400">
          左键: 选择 | 右键: 旋转 | 滚轮: 缩放 | 中键: 平移
        </div>
      </div>
    </div>
  );
}
