import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import type { SceneData } from '../types/scene';
import * as THREE from 'three';

export function exportSceneAsGLTF(
  threeScene: THREE.Scene,
  fileName?: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const exporter = new GLTFExporter();

    exporter.parse(
      threeScene,
      (result) => {
        let blob: Blob;

        if (result instanceof ArrayBuffer) {
          blob = new Blob([result], { type: 'application/octet-stream' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = fileName || `scene-${Date.now()}.glb`;
          a.click();
          URL.revokeObjectURL(url);
        } else {
          const json = JSON.stringify(result, null, 2);
          blob = new Blob([json], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = fileName || `scene-${Date.now()}.gltf`;
          a.click();
          URL.revokeObjectURL(url);
        }

        resolve();
      },
      (error) => {
        reject(error);
      },
      {
        binary: true,
        embedImages: true,
        includeCustomExtensions: true,
      }
    );
  });
}

export function exportSceneAsJSON(data: SceneData, fileName?: string): void {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName || `scene-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
