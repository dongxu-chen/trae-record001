import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import Zdog from 'zdog';
import { ZoomIn, ZoomOut, RotateCcw, Eye } from 'lucide-react';
import { useEditorStore } from '@/store/editorStore';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

type ViewMode = 'front' | 'side' | 'top';

interface BonePart {
  name: string;
  color: string;
  length: number;
  parent?: string;
  position: [number, number, number];
}

const BONE_PARTS: BonePart[] = [
  { name: 'head', color: '#ff6b9d', length: 30, position: [0, 100, 0] },
  { name: 'neck', color: '#c084fc', length: 15, parent: 'head', position: [0, 70, 0] },
  { name: 'torso', color: '#60a5fa', length: 60, parent: 'neck', position: [0, 10, 0] },
  { name: 'leftShoulder', color: '#34d399', length: 20, parent: 'torso', position: [-30, 55, 0] },
  { name: 'leftArm', color: '#fbbf24', length: 40, parent: 'leftShoulder', position: [-55, 30, 0] },
  { name: 'leftForearm', color: '#f87171', length: 40, parent: 'leftArm', position: [-80, 0, 0] },
  { name: 'rightShoulder', color: '#34d399', length: 20, parent: 'torso', position: [30, 55, 0] },
  { name: 'rightArm', color: '#fbbf24', length: 40, parent: 'rightShoulder', position: [55, 30, 0] },
  { name: 'rightForearm', color: '#f87171', length: 40, parent: 'rightArm', position: [80, 0, 0] },
  { name: 'hips', color: '#a78bfa', length: 25, parent: 'torso', position: [0, -30, 0] },
  { name: 'leftThigh', color: '#2dd4bf', length: 50, parent: 'hips', position: [-20, -60, 0] },
  { name: 'leftCalf', color: '#fb923c', length: 50, parent: 'leftThigh', position: [-20, -110, 0] },
  { name: 'rightThigh', color: '#2dd4bf', length: 50, parent: 'hips', position: [20, -60, 0] },
  { name: 'rightCalf', color: '#fb923c', length: 50, parent: 'rightThigh', position: [20, -110, 0] },
];

const BONE_NAME_MAP: Record<string, string> = {
  head: 'head',
  neck: 'neck',
  spine: 'torso',
  spine1: 'torso',
  spine2: 'torso',
  leftShoulder: 'leftShoulder',
  leftArm: 'leftArm',
  leftForeArm: 'leftForearm',
  leftHand: 'leftForearm',
  rightShoulder: 'rightShoulder',
  rightArm: 'rightArm',
  rightForeArm: 'rightForearm',
  rightHand: 'rightForearm',
  hips: 'hips',
  leftUpLeg: 'leftThigh',
  leftLeg: 'leftCalf',
  leftFoot: 'leftCalf',
  rightUpLeg: 'rightThigh',
  rightLeg: 'rightCalf',
  rightFoot: 'rightCalf',
};

function quaternionToEuler(x: number, y: number, z: number, w: number): [number, number, number] {
  const sinr_cosp = 2 * (w * x + y * z);
  const cosr_cosp = 1 - 2 * (x * x + y * y);
  const roll = Math.atan2(sinr_cosp, cosr_cosp);

  const sinp = 2 * (w * y - z * x);
  const pitch = Math.abs(sinp) >= 1 ? Math.sign(sinp) * Math.PI / 2 : Math.asin(sinp);

  const siny_cosp = 2 * (w * z + x * y);
  const cosy_cosp = 1 - 2 * (y * y + z * z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp);

  return [roll, pitch, yaw];
}

export function Skeleton2DPreview() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const illoRef = useRef<Zdog.Illustration | null>(null);
  const boneAnchorsRef = useRef<Map<string, Zdog.Anchor>>(new Map());
  const boneShapesRef = useRef<Map<string, { line: Zdog.Shape; joint: Zdog.Ellipse }>>(new Map());
  const animationFrameRef = useRef<number | null>(null);

  const { skeleton, selectedBoneUuid, setSelectedBone, isPlaying, currentTime } = useEditorStore();

  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState<ViewMode>('front');

  const boneRotationMap = useMemo(() => {
    const map = new Map<string, [number, number, number]>();
    skeleton.forEach((bone) => {
      const mappedName = BONE_NAME_MAP[bone.name.toLowerCase()] || BONE_NAME_MAP[bone.name];
      if (mappedName) {
        const [x, y, z, w] = bone.rotation;
        const euler = quaternionToEuler(x, y, z, w);
        map.set(mappedName, euler);
      }
    });
    return map;
  }, [skeleton]);

  const selectedMappedBone = useMemo(() => {
    if (!selectedBoneUuid) return null;
    const bone = skeleton.find((b) => b.uuid === selectedBoneUuid);
    if (!bone) return null;
    return BONE_NAME_MAP[bone.name.toLowerCase()] || BONE_NAME_MAP[bone.name] || null;
  }, [selectedBoneUuid, skeleton]);

  const getViewRotation = useCallback((mode: ViewMode): [number, number, number] => {
    switch (mode) {
      case 'front':
        return [0, 0, 0];
      case 'side':
        return [0, Math.PI / 2, 0];
      case 'top':
        return [Math.PI / 2, 0, 0];
      default:
        return [0, 0, 0];
    }
  }, []);

  const drawGrid = useCallback((ctx: CanvasRenderingContext2D, width: number, height: number, scale: number) => {
    const gridSize = 20 * scale;
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.2)';
    ctx.lineWidth = 0.5;

    const centerX = width / 2;
    const centerY = height / 2;

    for (let x = centerX % gridSize; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    for (let y = centerY % gridSize; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(100, 116, 139, 0.5)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(centerX, 0);
    ctx.lineTo(centerX, height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
  }, []);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!illoRef.current || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    const scale = zoom * 2;
    const scaledX = x / scale;
    const scaledY = y / scale;

    let closestBone: string | null = null;
    let closestDist = Infinity;

    boneAnchorsRef.current.forEach((anchor, boneName) => {
      const bonePart = BONE_PARTS.find((p) => p.name === boneName);
      if (!bonePart) return;

      const anchorX = anchor.translate.x;
      const anchorY = anchor.translate.y;
      const dist = Math.sqrt((scaledX - anchorX) ** 2 + (scaledY - anchorY) ** 2);

      if (dist < 20 && dist < closestDist) {
        closestDist = dist;
        closestBone = boneName;
      }
    });

    if (closestBone) {
      const originalBone = skeleton.find((b) => {
        const mapped = BONE_NAME_MAP[b.name.toLowerCase()] || BONE_NAME_MAP[b.name];
        return mapped === closestBone;
      });
      if (originalBone) {
        setSelectedBone(originalBone.uuid === selectedBoneUuid ? null : originalBone.uuid);
      }
    }
  }, [zoom, skeleton, selectedBoneUuid, setSelectedBone]);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      if (!containerRef.current) return;
      const { width, height } = containerRef.current.getBoundingClientRect();
      canvas.width = width;
      canvas.height = height;
    };

    resizeCanvas();

    const illo = new Zdog.Illustration({
      element: canvas,
      zoom: 2,
      center: true,
      resize: false,
    });

    illoRef.current = illo;

    const rootAnchor = new Zdog.Anchor({
      addTo: illo,
    });

    BONE_PARTS.forEach((part) => {
      const parentAnchor = part.parent ? boneAnchorsRef.current.get(part.parent) : rootAnchor;
      
      const anchor = new Zdog.Anchor({
        addTo: parentAnchor || rootAnchor,
        translate: { x: part.position[0], y: -part.position[1], z: part.position[2] },
      });

      boneAnchorsRef.current.set(part.name, anchor);

      const joint = new Zdog.Ellipse({
        addTo: anchor,
        diameter: 8,
        stroke: 2,
        fill: true,
        color: part.color,
      });

      let line: Zdog.Shape | null = null;
      if (part.parent) {
        line = new Zdog.Shape({
          addTo: anchor,
          path: [
            { x: 0, y: 0, z: 0 },
            { x: -part.position[0] + (BONE_PARTS.find((p) => p.name === part.parent)?.position[0] || 0),
              y: part.position[1] - (BONE_PARTS.find((p) => p.name === part.parent)?.position[1] || 0),
              z: -part.position[2] + (BONE_PARTS.find((p) => p.name === part.parent)?.position[2] || 0) },
          ],
          stroke: 4,
          color: part.color,
        });
      }

      if (line) {
        boneShapesRef.current.set(part.name, { line, joint });
      }
    });

    const animate = () => {
      if (!ctx || !canvas) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawGrid(ctx, canvas.width, canvas.height, zoom * 2);

      const [viewX, viewY, viewZ] = getViewRotation(viewMode);
      rootAnchor.rotate.x = viewX;
      rootAnchor.rotate.y = viewY;
      rootAnchor.rotate.z = viewZ;

      boneAnchorsRef.current.forEach((anchor, boneName) => {
        const rotation = boneRotationMap.get(boneName);
        if (rotation) {
          anchor.rotate.x = rotation[0];
          anchor.rotate.y = viewMode === 'front' ? rotation[1] : rotation[2];
          anchor.rotate.z = viewMode === 'front' ? rotation[2] : -rotation[1];
        }

        const shapes = boneShapesRef.current.get(boneName);
        if (shapes) {
          const isSelected = selectedMappedBone === boneName;
          shapes.joint.stroke = isSelected ? 4 : 2;
          shapes.joint.color = isSelected ? '#ff00ff' : BONE_PARTS.find((p) => p.name === boneName)?.color || '#fff';
          shapes.line.stroke = isSelected ? 6 : 4;
          shapes.line.color = isSelected ? '#ff00ff' : BONE_PARTS.find((p) => p.name === boneName)?.color || '#fff';

          if (isSelected) {
            shapes.joint.stroke = 6;
            shapes.joint.color = '#ff00ff';
          }
        }
      });

      illo.zoom = zoom * 2;
      illo.updateRenderGraph();

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    const resizeObserver = new ResizeObserver(resizeCanvas);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      illo.remove();
      boneAnchorsRef.current.clear();
      boneShapesRef.current.clear();
    };
  }, [viewMode, zoom, boneRotationMap, selectedMappedBone, drawGrid, getViewRotation]);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.3));
  const handleReset = () => {
    setZoom(1);
    setViewMode('front');
  };

  return (
    <div ref={containerRef} className="relative w-full h-full bg-space-900 overflow-hidden">
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        className="cursor-pointer"
        style={{ display: 'block' }}
      />

      <div className="absolute top-4 left-4 flex items-center gap-2 bg-space-800/90 backdrop-blur-sm rounded-lg p-2 border border-space-600">
        <Button variant="ghost" size="sm" onClick={handleZoomOut}>
          <ZoomOut className="w-4 h-4" />
        </Button>
        <span className="text-xs text-space-300 min-w-[3rem] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <Button variant="ghost" size="sm" onClick={handleZoomIn}>
          <ZoomIn className="w-4 h-4" />
        </Button>
        <div className="w-px h-6 bg-space-600" />
        <Button variant="ghost" size="sm" onClick={handleReset}>
          <RotateCcw className="w-4 h-4" />
        </Button>
      </div>

      <div className="absolute top-4 right-4 flex items-center gap-2 bg-space-800/90 backdrop-blur-sm rounded-lg p-2 border border-space-600">
        <Eye className="w-4 h-4 text-space-400" />
        {(['front', 'side', 'top'] as ViewMode[]).map((mode) => (
          <Button
            key={mode}
            variant="ghost"
            size="sm"
            onClick={() => setViewMode(mode)}
            className={cn(
              'min-w-[3rem]',
              viewMode === mode && 'bg-cyber-500/20 text-cyber-400'
            )}
          >
            {mode === 'front' ? '前' : mode === 'side' ? '侧' : '顶'}
          </Button>
        ))}
      </div>

      <div className="absolute bottom-4 left-4 bg-space-800/90 backdrop-blur-sm rounded-lg p-3 border border-space-600">
        <p className="text-xs text-space-400 mb-2">骨骼图例</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {BONE_PARTS.slice(0, 8).map((part) => (
            <div key={part.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: part.color }}
              />
              <span className="text-xs text-space-300">
                {part.name.replace(/([A-Z])/g, ' $1').trim()}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-4 right-4 bg-space-800/90 backdrop-blur-sm rounded-lg p-2 border border-space-600">
        <p className="text-xs text-space-400">
          {isPlaying ? '播放中' : '已暂停'} | 时间: {currentTime.toFixed(2)}s
        </p>
      </div>
    </div>
  );
}
