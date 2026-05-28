import * as THREE from 'three';
import { useHeightmapStore } from '@/store/heightmapStore';
import { heightToColor } from '@/utils/colors';

export interface ChunkData {
  positions: Float32Array;
  colors: Float32Array;
  indices: Uint32Array;
  normals: Float32Array;
}

export function generateChunkFromHeightmap(
  cx: number,
  cz: number,
  size: number,
  segments: number,
  worldSize: number,
  waterLevel: number,
  amplitude: number,
): ChunkData {
  const res = segments + 1;
  const positions = new Float32Array(res * res * 3);
  const colors = new Float32Array(res * res * 3);
  const normals = new Float32Array(res * res * 3);

  const getHeight = useHeightmapStore.getState().getInterpolatedHeight;
  const half = size / 2;
  const step = size / segments;

  let idx = 0;
  for (let z = 0; z < res; z++) {
    for (let x = 0; x < res; x++) {
      const wx = cx * size + x * step - half;
      const wz = cz * size + z * step - half;
      const h = getHeight(wx, wz, worldSize);

      positions[idx * 3] = wx;
      positions[idx * 3 + 1] = h;
      positions[idx * 3 + 2] = wz;

      const c = heightToColor(h, waterLevel, amplitude);
      colors[idx * 3] = c.r;
      colors[idx * 3 + 1] = c.g;
      colors[idx * 3 + 2] = c.b;
      idx++;
    }
  }

  for (let z = 0; z < res; z++) {
    for (let x = 0; x < res; x++) {
      const wx = cx * size + x * step - half;
      const wz = cz * size + z * step - half;

      const hL = getHeight(wx - step, wz, worldSize);
      const hR = getHeight(wx + step, wz, worldSize);
      const hU = getHeight(wx, wz - step, worldSize);
      const hD = getHeight(wx, wz + step, worldSize);

      const n = new THREE.Vector3(hL - hR, 2 * step, hU - hD).normalize();
      const i = (z * res + x) * 3;
      normals[i] = n.x;
      normals[i + 1] = n.y;
      normals[i + 2] = n.z;
    }
  }

  const indices = new Uint32Array(segments * segments * 6);
  let ii = 0;
  for (let z = 0; z < segments; z++) {
    for (let x = 0; x < segments; x++) {
      const a = z * res + x;
      const b = a + 1;
      const c = (z + 1) * res + x;
      const d = c + 1;
      indices[ii++] = a;
      indices[ii++] = c;
      indices[ii++] = b;
      indices[ii++] = b;
      indices[ii++] = c;
      indices[ii++] = d;
    }
  }

  return { positions, colors, indices, normals };
}

export function applyToGeometry(geo: THREE.PlaneGeometry, data: ChunkData) {
  geo.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(data.colors, 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geo.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geo.computeBoundingBox();
  geo.computeBoundingSphere();
  geo.rotateX(-Math.PI / 2);
}
