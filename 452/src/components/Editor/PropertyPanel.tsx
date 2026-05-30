import { useControls, button, folder } from 'leva';
import { useSceneStore } from '../../store/useSceneStore';
import { Settings, Sun, Palette } from 'lucide-react';

export function PropertyPanel() {
  const {
    selectedObjectId,
    objects,
    updateObject,
    updateObjectMaterial,
    updateObjectPhysics,
    updateObjectAnimation,
    addAnimationClip,
    removeObject,
    lights,
    updateLight,
    addLight,
    removeLight,
    backgroundColor,
    setBackgroundColor,
    fog,
    setFog,
    showNormalMaps,
    setShowNormalMaps,
    physicsEnabled,
    setPhysicsEnabled,
    gravity,
    setGravity,
  } = useSceneStore();

  const selectedObject = objects.find((obj) => obj.id === selectedObjectId);

  useControls(
    '场景设置',
    () => ({
      背景颜色: {
        value: backgroundColor,
        onChange: (v) => setBackgroundColor(v),
      },
      法线贴图显示: {
        value: showNormalMaps,
        onChange: (v) => setShowNormalMaps(v),
      },
      雾效: folder({
        启用: {
          value: fog.enabled,
          onChange: (v) => setFog({ enabled: v }),
        },
        颜色: {
          value: fog.color,
          onChange: (v) => setFog({ color: v }),
        },
        近距: {
          value: fog.near,
          min: 0,
          max: 100,
          onChange: (v) => setFog({ near: v }),
        },
        远距: {
          value: fog.far,
          min: 0,
          max: 200,
          onChange: (v) => setFog({ far: v }),
        },
      }),
    }),
    [backgroundColor, fog, showNormalMaps]
  );

  useControls(
    '物理引擎',
    () => ({
      启用物理: {
        value: physicsEnabled,
        onChange: (v) => setPhysicsEnabled(v),
      },
      重力X: {
        value: gravity[0],
        min: -50,
        max: 50,
        step: 0.1,
        onChange: (v) => setGravity([v, gravity[1], gravity[2]]),
      },
      重力Y: {
        value: gravity[1],
        min: -50,
        max: 50,
        step: 0.1,
        onChange: (v) => setGravity([gravity[0], v, gravity[2]]),
      },
      重力Z: {
        value: gravity[2],
        min: -50,
        max: 50,
        step: 0.1,
        onChange: (v) => setGravity([gravity[0], gravity[1], v]),
      },
    }),
    [physicsEnabled, gravity]
  );

  useControls(
    '光源',
    () => ({
      添加光源: folder({
        环境光: button(() => addLight('ambient')),
        平行光: button(() => addLight('directional')),
        点光源: button(() => addLight('point')),
      }),
      ...Object.fromEntries(
        lights.map((light, index) => [
          `光源 ${index + 1} (${light.type})`,
          folder({
            颜色: {
              value: light.color,
              onChange: (v) => updateLight(light.id, { color: v }),
            },
            强度: {
              value: light.intensity,
              min: 0,
              max: 5,
              step: 0.1,
              onChange: (v) => updateLight(light.id, { intensity: v }),
            },
            ...(light.position && {
              位置X: {
                value: light.position[0],
                min: -20,
                max: 20,
                step: 0.1,
                onChange: (v) =>
                  updateLight(light.id, {
                    position: [v, light.position![1], light.position![2]],
                  }),
              },
              位置Y: {
                value: light.position[1],
                min: -20,
                max: 20,
                step: 0.1,
                onChange: (v) =>
                  updateLight(light.id, {
                    position: [light.position![0], v, light.position![2]],
                  }),
              },
              位置Z: {
                value: light.position[2],
                min: -20,
                max: 20,
                step: 0.1,
                onChange: (v) =>
                  updateLight(light.id, {
                    position: [light.position![0], light.position![1], v],
                  }),
              },
            }),
            删除: button(() => removeLight(light.id)),
          }),
        ])
      ),
    }),
    [lights]
  );

  if (selectedObject) {
    useControls(
      selectedObject.name,
      () => ({
        名称: {
          value: selectedObject.name,
          onChange: (v) => updateObject(selectedObject.id, { name: v }),
        },
        变换: folder({
          位置X: {
            value: selectedObject.position[0],
            min: -50,
            max: 50,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                position: [v, selectedObject.position[1], selectedObject.position[2]],
              }),
          },
          位置Y: {
            value: selectedObject.position[1],
            min: -50,
            max: 50,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                position: [selectedObject.position[0], v, selectedObject.position[2]],
              }),
          },
          位置Z: {
            value: selectedObject.position[2],
            min: -50,
            max: 50,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                position: [selectedObject.position[0], selectedObject.position[1], v],
              }),
          },
          旋转X: {
            value: selectedObject.rotation[0],
            min: -Math.PI,
            max: Math.PI,
            step: 0.01,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                rotation: [v, selectedObject.rotation[1], selectedObject.rotation[2]],
              }),
          },
          旋转Y: {
            value: selectedObject.rotation[1],
            min: -Math.PI,
            max: Math.PI,
            step: 0.01,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                rotation: [selectedObject.rotation[0], v, selectedObject.rotation[2]],
              }),
          },
          旋转Z: {
            value: selectedObject.rotation[2],
            min: -Math.PI,
            max: Math.PI,
            step: 0.01,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                rotation: [selectedObject.rotation[0], selectedObject.rotation[1], v],
              }),
          },
          缩放X: {
            value: selectedObject.scale[0],
            min: 0.1,
            max: 10,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                scale: [v, selectedObject.scale[1], selectedObject.scale[2]],
              }),
          },
          缩放Y: {
            value: selectedObject.scale[1],
            min: 0.1,
            max: 10,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                scale: [selectedObject.scale[0], v, selectedObject.scale[2]],
              }),
          },
          缩放Z: {
            value: selectedObject.scale[2],
            min: 0.1,
            max: 10,
            step: 0.1,
            onChange: (v) =>
              updateObject(selectedObject.id, {
                scale: [selectedObject.scale[0], selectedObject.scale[1], v],
              }),
          },
        }),
        材质: folder({
          颜色: {
            value: selectedObject.material.color,
            onChange: (v) => updateObjectMaterial(selectedObject.id, { color: v }),
          },
          金属度: {
            value: selectedObject.material.metalness,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) => updateObjectMaterial(selectedObject.id, { metalness: v }),
          },
          粗糙度: {
            value: selectedObject.material.roughness,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) => updateObjectMaterial(selectedObject.id, { roughness: v }),
          },
          自发光颜色: {
            value: selectedObject.material.emissive,
            onChange: (v) => updateObjectMaterial(selectedObject.id, { emissive: v }),
          },
          自发光强度: {
            value: selectedObject.material.emissiveIntensity,
            min: 0,
            max: 5,
            step: 0.1,
            onChange: (v) =>
              updateObjectMaterial(selectedObject.id, { emissiveIntensity: v }),
          },
          法线贴图URL: {
            value: selectedObject.material.normalMapUrl,
            onChange: (v) =>
              updateObjectMaterial(selectedObject.id, { normalMapUrl: v }),
          },
          法线强度: {
            value: selectedObject.material.normalScale,
            min: 0,
            max: 5,
            step: 0.1,
            onChange: (v) =>
              updateObjectMaterial(selectedObject.id, { normalScale: v }),
          },
        }),
        物理: folder({
          启用刚体: {
            value: selectedObject.physics.enabled,
            onChange: (v) => updateObjectPhysics(selectedObject.id, { enabled: v }),
          },
          刚体类型: {
            value: selectedObject.physics.bodyType,
            options: ['dynamic', 'fixed', 'kinematic'] as const,
            onChange: (v) => updateObjectPhysics(selectedObject.id, { bodyType: v }),
          },
          质量: {
            value: selectedObject.physics.mass,
            min: 0.01,
            max: 100,
            step: 0.1,
            onChange: (v) => updateObjectPhysics(selectedObject.id, { mass: v }),
          },
          弹性: {
            value: selectedObject.physics.restitution,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) => updateObjectPhysics(selectedObject.id, { restitution: v }),
          },
          摩擦力: {
            value: selectedObject.physics.friction,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) => updateObjectPhysics(selectedObject.id, { friction: v }),
          },
          线性阻尼: {
            value: selectedObject.physics.linearDamping,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) =>
              updateObjectPhysics(selectedObject.id, { linearDamping: v }),
          },
          角阻尼: {
            value: selectedObject.physics.angularDamping,
            min: 0,
            max: 1,
            step: 0.01,
            onChange: (v) =>
              updateObjectPhysics(selectedObject.id, { angularDamping: v }),
          },
        }),
        动画: folder({
          启用动画: {
            value: selectedObject.animation.enabled,
            onChange: (v) =>
              updateObjectAnimation(selectedObject.id, { enabled: v }),
          },
          播放: {
            value: selectedObject.animation.isPlaying,
            onChange: (v) =>
              updateObjectAnimation(selectedObject.id, { isPlaying: v }),
          },
          当前片段: {
            value: selectedObject.animation.currentClip,
            options: [
              '',
              ...selectedObject.animation.clips.map((c) => c.name),
            ],
            onChange: (v) =>
              updateObjectAnimation(selectedObject.id, { currentClip: v }),
          },
          播放速度: {
            value: selectedObject.animation.timeScale,
            min: 0.01,
            max: 5,
            step: 0.1,
            onChange: (v) =>
              updateObjectAnimation(selectedObject.id, { timeScale: v }),
          },
          添加片段: button(() => {
            const clipNum = selectedObject.animation.clips.length + 1;
            addAnimationClip(selectedObject.id, {
              name: `clip-${clipNum}`,
              start: 0,
              end: 1,
              loop: true,
              speed: 1,
            });
          }),
        }),
        删除: button(() => removeObject(selectedObject.id)),
      }),
      [selectedObject]
    );
  }

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Settings size={20} className="text-cyan-400" />
          属性面板
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {!selectedObject && (
          <div className="p-4 text-center">
            <div className="text-gray-500 text-sm">
              选择场景中的物体以编辑属性
            </div>
          </div>
        )}

        <div id="leva__root" />
      </div>

      <div className="p-4 border-t border-gray-700 space-y-2">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Sun size={14} />
          <span>光源数量: {lights.length}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Palette size={14} />
          <span>物体数量: {objects.length}</span>
        </div>
      </div>
    </div>
  );
}
