import { useState, useMemo } from 'react';
import { Move, RotateCrop, Scaling, RotateCcw, Diamond, Bone, Globe } from 'lucide-react';
import * as THREE from 'three';
import { Button } from '@/components/ui/Button';
import { NumberInput } from '@/components/ui/NumberInput';
import { useEditorStore } from '@/store/editorStore';
import { useSkeletonData } from '@/hooks/useSkeletonData';
import { cn } from '@/lib/utils';

type RotationMode = 'euler' | 'quaternion';

const TransformPanel = () => {
  const {
    skeleton,
    selectedBoneUuid,
    transformMode,
    setTransformMode,
    updateBoneTransform,
    addKeyframe,
    currentTime,
    model,
  } = useEditorStore();

  const { resetBonePose, getBoneByUuid } = useSkeletonData(model);

  const [rotationMode, setRotationMode] = useState<RotationMode>('euler');
  const [linkScale, setLinkScale] = useState(false);

  const selectedBone = useMemo(() => {
    if (!selectedBoneUuid) return null;
    return skeleton.find((b) => b.uuid === selectedBoneUuid) || null;
  }, [selectedBoneUuid, skeleton]);

  const parentBone = useMemo(() => {
    if (!selectedBone?.parentUuid) return null;
    return skeleton.find((b) => b.uuid === selectedBone.parentUuid) || null;
  }, [selectedBone, skeleton]);

  const worldPosition = useMemo((): [number, number, number] | null => {
    if (!selectedBoneUuid) return null;
    const bone = getBoneByUuid(selectedBoneUuid);
    if (!bone) return null;
    const worldPos = new THREE.Vector3();
    bone.getWorldPosition(worldPos);
    return [worldPos.x, worldPos.y, worldPos.z];
  }, [selectedBoneUuid, getBoneByUuid]);

  const eulerAngles = useMemo((): [number, number, number] | null => {
    if (!selectedBone) return null;
    const quat = new THREE.Quaternion(...selectedBone.rotation);
    const euler = new THREE.Euler().setFromQuaternion(quat, 'XYZ');
    return [
      THREE.MathUtils.radToDeg(euler.x),
      THREE.MathUtils.radToDeg(euler.y),
      THREE.MathUtils.radToDeg(euler.z),
    ];
  }, [selectedBone]);

  const handleTransformChange = (
    property: 'position' | 'rotation' | 'scale',
    component: 'x' | 'y' | 'z' | 'w',
    value: number
  ) => {
    if (!selectedBone) return;

    const currentValues = [...selectedBone[property]] as number[];
    const index = component === 'x' ? 0 : component === 'y' ? 1 : component === 'z' ? 2 : 3;

    if (property === 'scale' && linkScale) {
      const uniformValue = value;
      updateBoneTransform(selectedBone.uuid, property, [uniformValue, uniformValue, uniformValue]);
    } else if (property === 'rotation' && rotationMode === 'euler') {
      const currentEuler = eulerAngles ? [...eulerAngles] : [0, 0, 0];
      currentEuler[index] = THREE.MathUtils.degToRad(value);
      const quat = new THREE.Quaternion().setFromEuler(
        new THREE.Euler(currentEuler[0], currentEuler[1], currentEuler[2], 'XYZ')
      );
      updateBoneTransform(selectedBone.uuid, property, [quat.x, quat.y, quat.z, quat.w]);
    } else {
      currentValues[index] = value;
      updateBoneTransform(selectedBone.uuid, property, currentValues);
    }
  };

  const handleAddKeyframe = (
    property: 'position' | 'rotation' | 'scale',
    component: 'x' | 'y' | 'z' | 'w'
  ) => {
    if (!selectedBone) return;

    let value: number[];
    if (property === 'rotation' && rotationMode === 'euler') {
      const quat = new THREE.Quaternion(...selectedBone.rotation);
      const euler = new THREE.Euler().setFromQuaternion(quat, 'XYZ');
      const index = component === 'x' ? 0 : component === 'y' ? 1 : 2;
      value = [THREE.MathUtils.radToDeg(euler[index])];
    } else {
      const values = selectedBone[property] as number[];
      const index = component === 'x' ? 0 : component === 'y' ? 1 : component === 'z' ? 2 : 3;
      value = [values[index]];
    }

    addKeyframe(selectedBone.uuid, property, component, currentTime, value);
  };

  const handleResetPose = () => {
    if (!selectedBone) return;
    resetBonePose(selectedBone.uuid);
  };

  if (!selectedBone) {
    return (
      <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-space-600 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-300">变换属性</h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <Bone size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">请选择一个骨骼</p>
            <p className="text-xs mt-1">在左侧骨骼层级中点击选择</p>
          </div>
        </div>
      </div>
    );
  }

  const TransformRow = ({
    axis,
    value,
    property,
    component,
    step = 0.01,
    precision = 3,
    min,
    max,
    unit,
  }: {
    axis: 'x' | 'y' | 'z' | 'w';
    value: number;
    property: 'position' | 'rotation' | 'scale';
    component: 'x' | 'y' | 'z' | 'w';
    step?: number;
    precision?: number;
    min?: number;
    max?: number;
    unit?: string;
  }) => (
    <div className="flex items-center gap-2">
      <div className="flex-1">
        <NumberInput
          value={value}
          onChange={(v) => handleTransformChange(property, component, v)}
          axis={axis === 'w' ? 'none' : axis}
          step={step}
          precision={precision}
          min={min}
          max={max}
        />
      </div>
      {unit && <span className="text-xs text-gray-500 w-6">{unit}</span>}
      <Button
        variant="ghost"
        size="sm"
        className="h-9 w-9 p-0"
        onClick={() => handleAddKeyframe(property, component)}
        title="添加关键帧"
      >
        <Diamond size={14} />
      </Button>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-space-600 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300">变换属性</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleResetPose}
          className="text-xs h-8"
        >
          <RotateCcw size={12} />
          重置
        </Button>
      </div>

      <div className="px-3 py-2 border-b border-space-600">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">{selectedBone.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">
              索引: #{selectedBone.boneIndex}
              {parentBone && (
                <span className="ml-2">父级: {parentBone.name}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="px-3 py-2 border-b border-space-600">
        <div className="flex gap-1 bg-space-900/50 p-1 rounded-md">
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              'flex-1 h-8 text-xs',
              transformMode === 'translate' && 'bg-cyber-500/20 text-cyber-400'
            )}
            onClick={() => setTransformMode('translate')}
          >
            <Move size={14} />
            位置
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              'flex-1 h-8 text-xs',
              transformMode === 'rotate' && 'bg-cyber-500/20 text-cyber-400'
            )}
            onClick={() => setTransformMode('rotate')}
          >
            <RotateCrop size={14} />
            旋转
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              'flex-1 h-8 text-xs',
              transformMode === 'scale' && 'bg-cyber-500/20 text-cyber-400'
            )}
            onClick={() => setTransformMode('scale')}
          >
            <Scaling size={14} />
            缩放
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {transformMode === 'translate' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400">位置</span>
              <span className="text-xs text-gray-500">米</span>
            </div>
            <div className="space-y-2">
              <TransformRow
                axis="x"
                value={selectedBone.position[0]}
                property="position"
                component="x"
                step={0.01}
                precision={3}
                unit="m"
              />
              <TransformRow
                axis="y"
                value={selectedBone.position[1]}
                property="position"
                component="y"
                step={0.01}
                precision={3}
                unit="m"
              />
              <TransformRow
                axis="z"
                value={selectedBone.position[2]}
                property="position"
                component="z"
                step={0.01}
                precision={3}
                unit="m"
              />
            </div>
          </div>
        )}

        {transformMode === 'rotate' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400">旋转</span>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    'h-6 px-2 text-xs',
                    rotationMode === 'euler' && 'bg-cyber-500/20 text-cyber-400'
                  )}
                  onClick={() => setRotationMode('euler')}
                >
                  欧拉角
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    'h-6 px-2 text-xs',
                    rotationMode === 'quaternion' && 'bg-cyber-500/20 text-cyber-400'
                  )}
                  onClick={() => setRotationMode('quaternion')}
                >
                  四元数
                </Button>
              </div>
            </div>

            {rotationMode === 'euler' && eulerAngles ? (
              <div className="space-y-2">
                <TransformRow
                  axis="x"
                  value={eulerAngles[0]}
                  property="rotation"
                  component="x"
                  step={1}
                  precision={2}
                  min={-180}
                  max={180}
                  unit="°"
                />
                <TransformRow
                  axis="y"
                  value={eulerAngles[1]}
                  property="rotation"
                  component="y"
                  step={1}
                  precision={2}
                  min={-180}
                  max={180}
                  unit="°"
                />
                <TransformRow
                  axis="z"
                  value={eulerAngles[2]}
                  property="rotation"
                  component="z"
                  step={1}
                  precision={2}
                  min={-180}
                  max={180}
                  unit="°"
                />
              </div>
            ) : (
              <div className="space-y-2">
                <TransformRow
                  axis="x"
                  value={selectedBone.rotation[0]}
                  property="rotation"
                  component="x"
                  step={0.01}
                  precision={4}
                  min={-1}
                  max={1}
                />
                <TransformRow
                  axis="y"
                  value={selectedBone.rotation[1]}
                  property="rotation"
                  component="y"
                  step={0.01}
                  precision={4}
                  min={-1}
                  max={1}
                />
                <TransformRow
                  axis="z"
                  value={selectedBone.rotation[2]}
                  property="rotation"
                  component="z"
                  step={0.01}
                  precision={4}
                  min={-1}
                  max={1}
                />
                <TransformRow
                  axis="w"
                  value={selectedBone.rotation[3]}
                  property="rotation"
                  component="w"
                  step={0.01}
                  precision={4}
                  min={-1}
                  max={1}
                />
              </div>
            )}
          </div>
        )}

        {transformMode === 'scale' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400">缩放</span>
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  'h-6 px-2 text-xs',
                  linkScale && 'bg-cyber-500/20 text-cyber-400'
                )}
                onClick={() => setLinkScale(!linkScale)}
              >
                {linkScale ? '已链接' : '未链接'}
              </Button>
            </div>
            <div className="space-y-2">
              <TransformRow
                axis="x"
                value={selectedBone.scale[0]}
                property="scale"
                component="x"
                step={0.01}
                precision={3}
                min={0.001}
              />
              <TransformRow
                axis="y"
                value={selectedBone.scale[1]}
                property="scale"
                component="y"
                step={0.01}
                precision={3}
                min={0.001}
              />
              <TransformRow
                axis="z"
                value={selectedBone.scale[2]}
                property="scale"
                component="z"
                step={0.01}
                precision={3}
                min={0.001}
              />
            </div>
          </div>
        )}
      </div>

      {worldPosition && (
        <div className="px-3 py-2 border-t border-space-600 bg-space-900/30">
          <div className="flex items-center gap-2 mb-2">
            <Globe size={12} className="text-gray-500" />
            <span className="text-xs font-medium text-gray-400">世界坐标</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="flex items-center gap-1">
              <span className="text-red-400 font-bold">X</span>
              <span className="text-gray-400 font-mono">{worldPosition[0].toFixed(3)}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-400 font-bold">Y</span>
              <span className="text-gray-400 font-mono">{worldPosition[1].toFixed(3)}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-blue-400 font-bold">Z</span>
              <span className="text-gray-400 font-mono">{worldPosition[2].toFixed(3)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

TransformPanel.displayName = 'TransformPanel';

export { TransformPanel };
