import { useRef, useState, useCallback, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import {
  OrbitControls,
  Grid,
  TransformControls,
  Html,
} from '@react-three/drei';
import { EffectComposer, Bloom, FXAA } from '@react-three/postprocessing';
import * as THREE from 'three';
import { Upload, Eye, EyeOff, Box, Grid3x3, Ghost, Move, RotateCw, Maximize2 } from 'lucide-react';
import { useEditorStore } from '@/store/editorStore';
import { useAnimationMixer } from '@/hooks/useAnimationMixer';
import { useSkeletonData } from '@/hooks/useSkeletonData';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

function SceneLighting() {
  return (
    <>
      <ambientLight intensity={0.4} color="#ffffff" />
      <directionalLight
        position={[5, 10, 7]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={50}
        shadow-camera-left={-20}
        shadow-camera-right={20}
        shadow-camera-top={20}
        shadow-camera-bottom={-20}
      />
      <pointLight position={[-10, 5, -10]} intensity={0.5} color="#4da6ff" />
      <pointLight position={[10, 5, 10]} intensity={0.5} color="#ff6b6b" />
    </>
  );
}

function SceneHelpers() {
  return (
    <>
      <Grid
        args={[20, 20]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#2a2a3e"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#4a4a6e"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />
      <axesHelper args={[5]} />
    </>
  );
}

function PostProcessing() {
  return (
    <EffectComposer multisampling={0} disableNormalPass>
      <FXAA />
      <Bloom
        intensity={0.3}
        luminanceThreshold={0.2}
        luminanceSmoothing={0.9}
        mipmapBlur
      />
    </EffectComposer>
  );
}

function SkinnedMeshRenderer({
  mesh,
  displayMode,
  visible,
}: {
  mesh: THREE.SkinnedMesh;
  displayMode: 'solid' | 'wireframe' | 'transparent';
  visible: boolean;
}) {
  const meshRef = useRef<THREE.SkinnedMesh>(null);

  useEffect(() => {
    if (meshRef.current) {
      const material = meshRef.current.material as THREE.MeshStandardMaterial;
      if (material) {
        material.wireframe = displayMode === 'wireframe';
        material.transparent = displayMode === 'transparent';
        material.opacity = displayMode === 'transparent' ? 0.3 : 1;
        material.needsUpdate = true;
      }
    }
  }, [displayMode]);

  useFrame(() => {
    if (meshRef.current && meshRef.current.skeleton) {
      meshRef.current.skeleton.update();
      meshRef.current.skeleton.pose();
    }
  });

  return (
    <primitive
      ref={meshRef}
      object={mesh}
      visible={visible}
      castShadow
      receiveShadow
    />
  );
}

function SkeletonRenderer({
  skeleton,
  showSkeleton,
  selectedBoneUuid,
  onBoneClick,
}: {
  skeleton: THREE.Skeleton;
  showSkeleton: boolean;
  selectedBoneUuid: string | null;
  onBoneClick: (uuid: string) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const skeletonHelperRef = useRef<THREE.SkeletonHelper | null>(null);

  useFrame(() => {
    if (skeletonHelperRef.current) {
      skeletonHelperRef.current.update();
    }
  });

  useEffect(() => {
    if (!groupRef.current) return;

    if (skeletonHelperRef.current) {
      groupRef.current.remove(skeletonHelperRef.current);
      skeletonHelperRef.current.dispose();
    }

    const helper = new THREE.SkeletonHelper(skeleton.bones[0].parent as THREE.Object3D);
    helper.material = new THREE.LineBasicMaterial({
      color: 0x00ff88,
      linewidth: 2,
      transparent: true,
      opacity: 0.8,
    });
    skeletonHelperRef.current = helper;
    groupRef.current.add(helper);

    return () => {
      if (skeletonHelperRef.current) {
        skeletonHelperRef.current.dispose();
      }
    };
  }, [skeleton]);

  const handleBoneClick = useCallback(
    (e: any) => {
      e.stopPropagation();
      const bone = e.object;
      if (bone instanceof THREE.Bone) {
        onBoneClick(bone.uuid);
      }
    },
    [onBoneClick]
  );

  return (
    <group ref={groupRef} visible={showSkeleton}>
      {skeleton.bones.map((bone) => {
        const isSelected = bone.uuid === selectedBoneUuid;
        const sphereGeometry = new THREE.SphereGeometry(isSelected ? 0.08 : 0.05, 8, 8);
        const sphereMaterial = new THREE.MeshBasicMaterial({
          color: isSelected ? 0xffcc00 : 0x00ff88,
        });

        return (
          <mesh
            key={bone.uuid}
            geometry={sphereGeometry}
            material={sphereMaterial}
            position={bone.position}
            onClick={handleBoneClick}
            userData={{ boneUuid: bone.uuid }}
          />
        );
      })}
    </group>
  );
}

function BoneTransformControls({
  bone,
  mode,
}: {
  bone: THREE.Bone | null;
  mode: 'translate' | 'rotate' | 'scale';
}) {
  const { scene } = useThree();
  const transformControlsRef = useRef<any>(null);
  const [isDragging, setIsDragging] = useState(false);

  useFrame(() => {
    if (bone && isDragging) {
      bone.updateMatrixWorld(true);
      const root = bone.parent;
      if (root) {
        root.traverse((child) => {
          if (child instanceof THREE.SkinnedMesh && child.skeleton) {
            child.skeleton.update();
            child.skeleton.pose();
          }
        });
      }
    }
  });

  const handleObjectChange = useCallback(() => {
    if (bone) {
      bone.updateMatrixWorld(true);
      const root = bone.parent;
      if (root) {
        root.traverse((child) => {
          if (child instanceof THREE.SkinnedMesh && child.skeleton) {
            child.skeleton.update();
            child.skeleton.pose();
          }
        });
      }
    }
  }, [bone]);

  if (!bone) return null;

  return (
    <TransformControls
      ref={transformControlsRef}
      object={bone}
      mode={mode}
      onMouseDown={() => setIsDragging(true)}
      onMouseUp={() => setIsDragging(false)}
      onChange={handleObjectChange}
    >
      <object3D object={bone} />
    </TransformControls>
  );
}

function ModelScene() {
  const {
    model,
    selectedBoneUuid,
    transformMode,
    showSkeleton,
    showMesh,
    meshDisplayMode,
    setSelectedBone,
  } = useEditorStore();

  useAnimationMixer(model);
  useSkeletonData(model);

  const selectedBoneRef = useRef<THREE.Bone | null>(null);

  useEffect(() => {
    if (model && selectedBoneUuid) {
      const bone = model.getObjectByProperty('uuid', selectedBoneUuid);
      selectedBoneRef.current = bone instanceof THREE.Bone ? bone : null;
    } else {
      selectedBoneRef.current = null;
    }
  }, [model, selectedBoneUuid]);

  const skinnedMeshes: THREE.SkinnedMesh[] = [];
  let skeleton: THREE.Skeleton | null = null;

  if (model) {
    model.traverse((obj) => {
      if (obj instanceof THREE.SkinnedMesh) {
        skinnedMeshes.push(obj);
        if (!skeleton && obj.skeleton) {
          skeleton = obj.skeleton;
        }
      }
    });
  }

  const handleBoneClick = useCallback(
    (uuid: string) => {
      setSelectedBone(uuid === selectedBoneUuid ? null : uuid);
    },
    [selectedBoneUuid, setSelectedBone]
  );

  if (!model) {
    return null;
  }

  return (
    <>
      <primitive object={model} />
      {skinnedMeshes.map((mesh, index) => (
        <SkinnedMeshRenderer
          key={`${mesh.uuid}-${index}`}
          mesh={mesh}
          displayMode={meshDisplayMode}
          visible={showMesh}
        />
      ))}
      {skeleton && showSkeleton && (
        <SkeletonRenderer
          skeleton={skeleton}
          showSkeleton={showSkeleton}
          selectedBoneUuid={selectedBoneUuid}
          onBoneClick={handleBoneClick}
        />
      )}
      <BoneTransformControls
        bone={selectedBoneRef.current}
        mode={transformMode}
      />
    </>
  );
}

function CameraController({ isDragging }: { isDragging: boolean }) {
  const controlsRef = useRef<any>(null);

  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.enabled = !isDragging;
    }
  }, [isDragging]);

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.05}
      minDistance={0.5}
      maxDistance={50}
      enablePan
      enableRotate
      enableZoom
    />
  );
}

function DropZone({
  onFileDrop,
  onButtonClick,
  isDragOver,
  setIsDragOver,
}: {
  onFileDrop: (file: File) => void;
  onButtonClick: () => void;
  isDragOver: boolean;
  setIsDragOver: (value: boolean) => void;
}) {
  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(true);
    },
    [setIsDragOver]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
    },
    [setIsDragOver]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        const ext = file.name.split('.').pop()?.toLowerCase();
        if (ext === 'glb' || ext === 'gltf' || ext === 'fbx') {
          onFileDrop(file);
        }
      }
    },
    [onFileDrop, setIsDragOver]
  );

  return (
    <div
      className={cn(
        'absolute inset-0 flex items-center justify-center pointer-events-none z-10',
        isDragOver && 'pointer-events-auto'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div
        className={cn(
          'border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300',
          isDragOver
            ? 'border-cyber-400 bg-cyber-500/20 scale-105'
            : 'border-space-600 bg-space-800/80'
        )}
      >
        <Upload
          className={cn(
            'w-12 h-12 mx-auto mb-4 transition-colors',
            isDragOver ? 'text-cyber-400' : 'text-space-400'
          )}
        />
        <p
          className={cn(
            'text-lg font-medium mb-2',
            isDragOver ? 'text-cyber-300' : 'text-space-200'
          )}
        >
          {isDragOver ? '释放以导入模型' : '拖放模型文件到此处'}
        </p>
        <p className="text-sm text-space-400 mb-4">支持 .glb, .gltf, .fbx 格式</p>
        <Button
          onClick={(e) => {
            e.stopPropagation();
            onButtonClick();
          }}
          className="pointer-events-auto"
        >
          或点击选择文件
        </Button>
      </div>
    </div>
  );
}

function Toolbar() {
  const {
    showSkeleton,
    showMesh,
    meshDisplayMode,
    transformMode,
    toggleSkeleton,
    toggleMesh,
    setMeshDisplayMode,
    setTransformMode,
    clearModel,
    model,
  } = useEditorStore();

  return (
    <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-20">
      <div className="flex items-center gap-2 bg-space-800/90 backdrop-blur-sm rounded-lg p-2 border border-space-600">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSkeleton}
          className={cn(showSkeleton && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Grid3x3 className="w-4 h-4" />
          骨骼
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleMesh}
          className={cn(showMesh && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Eye className="w-4 h-4" />
          网格
        </Button>
        <div className="w-px h-6 bg-space-600" />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMeshDisplayMode('solid')}
          className={cn(meshDisplayMode === 'solid' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Box className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMeshDisplayMode('wireframe')}
          className={cn(meshDisplayMode === 'wireframe' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Grid3x3 className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMeshDisplayMode('transparent')}
          className={cn(meshDisplayMode === 'transparent' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Ghost className="w-4 h-4" />
        </Button>
        <div className="w-px h-6 bg-space-600" />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setTransformMode('translate')}
          className={cn(transformMode === 'translate' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Move className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setTransformMode('rotate')}
          className={cn(transformMode === 'rotate' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <RotateCw className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setTransformMode('scale')}
          className={cn(transformMode === 'scale' && 'bg-cyber-500/20 text-cyber-400')}
        >
          <Maximize2 className="w-4 h-4" />
        </Button>
      </div>
      {model && (
        <Button variant="secondary" size="sm" onClick={clearModel}>
          清除模型
        </Button>
      )}
    </div>
  );
}

export function Viewport3D() {
  const { model, loadModel } = useEditorStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isTransformDragging, setIsTransformDragging] = useState(false);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        loadModel(file);
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [loadModel]
  );

  const handleButtonClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileDrop = useCallback(
    (file: File) => {
      loadModel(file);
    },
    [loadModel]
  );

  return (
    <div className="relative w-full h-full bg-space-900 overflow-hidden">
      <input
        ref={fileInputRef}
        type="file"
        accept=".glb,.gltf,.fbx"
        onChange={handleFileSelect}
        className="hidden"
      />

      <Canvas
        shadows
        camera={{ position: [3, 3, 3], fov: 50 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
        }}
        style={{ background: '#0a0a12' }}
      >
        <color attach="background" args={['#0a0a12']} />
        <fog attach="fog" args={['#0a0a12', 10, 50]} />

        <SceneLighting />
        <SceneHelpers />
        <ModelScene />
        <CameraController isDragging={isTransformDragging} />
        <PostProcessing />
      </Canvas>

      <Toolbar />

      {!model && (
        <DropZone
          onFileDrop={handleFileDrop}
          onButtonClick={handleButtonClick}
          isDragOver={isDragOver}
          setIsDragOver={setIsDragOver}
        />
      )}
    </div>
  );
}
