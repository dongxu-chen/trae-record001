import { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useTerrainStore } from '@/store/terrainStore';
import { useHeightmapStore } from '@/store/heightmapStore';
import { generateChunkFromHeightmap, applyToGeometry, type ChunkData } from './chunkGen';

const LOD_LEVELS = [128, 64, 32, 16];
const TRANSITION_DURATION = 0.8;

interface ChunkMeshProps {
  data: ChunkData;
  wireframe: boolean;
  showShadows: boolean;
  opacity: number;
}

function ChunkMesh({ data, wireframe, showShadows, opacity }: ChunkMeshProps) {
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);

  const geometry = useMemo(() => {
    const g = new THREE.PlaneGeometry(1, 1, 1, 1);
    applyToGeometry(g, data);
    return g;
  }, [data]);

  useEffect(() => {
    if (materialRef.current) {
      materialRef.current.opacity = opacity;
      materialRef.current.transparent = opacity < 1;
    }
  }, [opacity]);

  useEffect(() => {
    return () => {
      geometry.dispose();
    };
  }, [geometry]);

  return (
    <mesh
      geometry={geometry}
      castShadow={showShadows}
      receiveShadow={showShadows}
    >
      <meshStandardMaterial
        ref={materialRef}
        vertexColors
        wireframe={wireframe}
        flatShading
        roughness={0.9}
        metalness={0.05}
        transparent={opacity < 1}
        opacity={opacity}
      />
    </mesh>
  );
}

interface ActiveChunk {
  key: string;
  cx: number;
  cz: number;
  segments: number;
  data: ChunkData;
  fadeStart: number;
  fadeIn: boolean;
}

export function TerrainLOD() {
  const noiseType = useTerrainStore((s) => s.noiseType);
  const amplitude = useTerrainStore((s) => s.amplitude);
  const frequency = useTerrainStore((s) => s.frequency);
  const octaves = useTerrainStore((s) => s.octaves);
  const persistence = useTerrainStore((s) => s.persistence);
  const lacunarity = useTerrainStore((s) => s.lacunarity);
  const seed = useTerrainStore((s) => s.seed);
  const waterLevel = useTerrainStore((s) => s.waterLevel);
  const chunkSize = useTerrainStore((s) => s.chunkSize);
  const chunks = useTerrainStore((s) => s.chunks);
  const lodBias = useTerrainStore((s) => s.lodBias);
  const wireframe = useTerrainStore((s) => s.wireframe);
  const showShadows = useTerrainStore((s) => s.showShadows);

  const modified = useHeightmapStore((s) => s.modified);
  const brushSize = useHeightmapStore((s) => s.brushSize);
  const tools = useHeightmapStore((s) => s.tools);
  const applyBrush = useHeightmapStore((s) => s.applyBrush);
  const getInterpolatedHeight = useHeightmapStore((s) => s.getInterpolatedHeight);
  const generateFromNoise = useHeightmapStore((s) => s.generateFromNoise);

  const { camera, clock, gl } = useThree();
  const [activeChunks, setActiveChunks] = useState<ActiveChunk[]>([]);
  const activeChunksRef = useRef<ActiveChunk[]>([]);
  activeChunksRef.current = activeChunks;

  const [brushPosition, setBrushPosition] = useState<THREE.Vector3 | null>(null);
  const brushMeshRef = useRef<THREE.Mesh>(null);
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const mouse = useMemo(() => new THREE.Vector2(), []);
  const isDragging = useRef(false);

  const generating = useRef<Set<string>>(new Set());
  const prevSeed = useRef(seed);
  const fadeTimers = useRef<Map<string, number>>(new Map());
  const heightmapModified = useRef(modified);
  const worldSize = chunkSize * chunks;

  useEffect(() => {
    const opts = {
      type: noiseType,
      amplitude,
      frequency,
      octaves,
      persistence,
      lacunarity,
      seed,
    };
    generateFromNoise(opts, waterLevel);
  }, [seed, amplitude, frequency, octaves, persistence, lacunarity, noiseType, waterLevel, generateFromNoise]);

  const seedRef = useRef(seed);
  seedRef.current = seed;
  const paramsRef = useRef({ chunkSize, lodBias, waterLevel, amplitude });
  paramsRef.current = { chunkSize, lodBias, waterLevel, amplitude };

  const chunkKeys = useMemo(() => {
    const keys: string[] = [];
    const half = Math.floor(chunks / 2);
    for (let cz = -half; cz <= half; cz++) {
      for (let cx = -half; cx <= half; cx++) {
        keys.push(`${cx},${cz}`);
      }
    }
    return keys;
  }, [chunks]);

  const regenerateAllChunks = useCallback(() => {
    const now = clock.elapsedTime;
    for (const key of chunkKeys) {
      const [cx, cz] = key.split(',').map(Number);
      const centerX = cx * paramsRef.current.chunkSize;
      const centerZ = cz * paramsRef.current.chunkSize;
      const dist = Math.hypot(camera.position.x - centerX, camera.position.z - centerZ);
      let lodIndex = Math.floor(dist / (paramsRef.current.chunkSize * paramsRef.current.lodBias));
      lodIndex = Math.min(Math.max(lodIndex, 0), LOD_LEVELS.length - 1);
      const segments = LOD_LEVELS[lodIndex];

      const genKey = `${key}-${segments}`;
      if (generating.current.has(genKey)) continue;
      generating.current.add(genKey);

      const data = generateChunkFromHeightmap(
        cx, cz, paramsRef.current.chunkSize, segments,
        worldSize, paramsRef.current.waterLevel, paramsRef.current.amplitude
      );

      setActiveChunks((prev) => {
        const existing = prev.find((c) => c.key === key);
        const newChunk: ActiveChunk = {
          key, cx, cz, segments, data,
          fadeStart: now, fadeIn: true,
        };
        if (!existing) return [...prev, newChunk];
        return prev.map((c) => (c.key === key ? newChunk : c));
      });
      fadeTimers.current.set(key, now);
      generating.current.delete(genKey);
    }
  }, [chunkKeys, worldSize, clock, camera]);

  useEffect(() => {
    if (modified !== heightmapModified.current) {
      heightmapModified.current = modified;
      regenerateAllChunks();
    }
  }, [modified, regenerateAllChunks]);

  useEffect(() => {
    regenerateAllChunks();
    prevSeed.current = seed;
  }, [seed, regenerateAllChunks]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const rect = gl.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (!tools.sculpting) return;

      raycaster.setFromCamera(mouse, camera);
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
      const intersect = new THREE.Vector3();
      raycaster.ray.intersectPlane(plane, intersect);

      if (intersect) {
        const h = getInterpolatedHeight(intersect.x, intersect.z, worldSize);
        intersect.y = h;
        setBrushPosition(intersect.clone());
      }
    };

    const handleMouseDown = (e: MouseEvent) => {
      if (!tools.sculpting) return;
      if (e.button === 0) isDragging.current = true;
    };

    const handleMouseUp = () => {
      isDragging.current = false;
    };

    const handleDrag = () => {
      if (!isDragging.current || !tools.sculpting || !brushPosition) return;
      applyBrush(brushPosition.x, brushPosition.z, worldSize);
    };

    const canvas = gl.domElement;
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    const interval = setInterval(handleDrag, 16);

    return () => {
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      clearInterval(interval);
    };
  }, [gl, camera, mouse, raycaster, tools, worldSize, brushPosition, getInterpolatedHeight, applyBrush]);

  useFrame(() => {
    if (brushMeshRef.current && brushPosition && tools.sculpting) {
      brushMeshRef.current.position.copy(brushPosition);
      brushMeshRef.current.scale.setScalar(brushSize * 2);
    }
  });

  return (
    <group>
      {activeChunks.map((chunk) => {
        const now = clock.elapsedTime;
        const opacity = chunk.fadeIn
          ? Math.min(1, (now - chunk.fadeStart) / TRANSITION_DURATION)
          : 1;

        return (
          <ChunkMesh
            key={`${chunk.key}-${chunk.segments}`}
            data={chunk.data}
            wireframe={wireframe}
            showShadows={showShadows}
            opacity={opacity}
          />
        );
      })}

      {tools.sculpting && brushPosition && (
        <mesh ref={brushMeshRef} position={brushPosition} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.9, 1, 32]} />
          <meshBasicMaterial color="#ff6b35" transparent opacity={0.8} side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
}
