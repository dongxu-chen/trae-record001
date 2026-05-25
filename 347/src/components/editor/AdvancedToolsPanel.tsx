import { useState, useRef, useCallback } from 'react';
import {
  Move,
  Hand,
  Footprints,
  Target,
  Upload,
  RefreshCw,
  Copy,
  Play,
  Pause,
  ChevronDown,
  ChevronRight,
  Settings,
  Zap,
  GitMerge,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Slider } from '@/components/ui/Slider';
import { useEditorStore } from '@/store/editorStore';
import { cn } from '@/lib/utils';
import type { IKTarget } from '@/types/animation';

type TabType = 'ik' | 'bvh' | 'retarget';

const AdvancedToolsPanel = () => {
  const [activeTab, setActiveTab] = useState<TabType>('ik');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    footIK: true,
    handIK: true,
    bvhImport: true,
    retarget: true,
  });

  const {
    ikState,
    addIKTarget,
    removeIKTarget,
    updateIKTarget,
    setIKTargetEnabled,
    setActiveIKTarget,
    setIKSolverType,
    toggleShowIKTargets,
    importBVH,
    bvhImportState,
    setBVHImportScale,
    retargetState,
    setRetargetScale,
    setRetargetMirror,
    setRetargetPreservePosition,
    setAutoBoneMapping,
    performRetarget,
    animationClips,
    importedAnimations,
  } = useEditorStore();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const handleAddFootIK = useCallback(() => {
    const newTarget: IKTarget = {
      id: `foot_ik_${Date.now()}`,
      name: `Foot IK ${ikState.targets.filter((t) => t.type === 'foot').length + 1}`,
      type: 'foot',
      bonePath: '',
      position: [0, 0, 0],
      enabled: true,
      poleVector: [0, 1, 0],
      weight: 1,
    };
    addIKTarget(newTarget);
  }, [ikState.targets, addIKTarget]);

  const handleAddHandIK = useCallback(() => {
    const newTarget: IKTarget = {
      id: `hand_ik_${Date.now()}`,
      name: `Hand IK ${ikState.targets.filter((t) => t.type === 'hand').length + 1}`,
      type: 'hand',
      bonePath: '',
      position: [0, 0, 0],
      enabled: true,
      poleVector: [0, 1, 0],
      weight: 1,
    };
    addIKTarget(newTarget);
  }, [ikState.targets, addIKTarget]);

  const handleBVHFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.bvh')) {
      await importBVH(file);
    }
  }, [importBVH]);

  const tabs: { id: TabType; label: string; icon: typeof Move }[] = [
    { id: 'ik', label: 'IK', icon: Target },
    { id: 'bvh', label: 'BVH', icon: Upload },
    { id: 'retarget', label: '重定向', icon: GitMerge },
  ];

  return (
    <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="flex items-center gap-1 px-2 py-2 border-b border-space-600 bg-space-800/80">
        {tabs.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={activeTab === id ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(id)}
            className="flex items-center gap-1"
          >
            <Icon size={14} />
            <span className="text-xs">{label}</span>
          </Button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {activeTab === 'ik' && (
          <>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Settings size={14} className="text-cyber-400" />
                <span className="text-sm font-medium text-gray-300">IK求解器设置</span>
              </div>
            </div>

            <div className="space-y-2 p-3 bg-space-700/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">求解器类型</span>
                <select
                  value={ikState.solverType}
                  onChange={(e) => setIKSolverType(e.target.value as 'FABRIK' | 'CCD')}
                  className="bg-space-800 border border-space-600 rounded px-2 py-1 text-xs text-gray-300"
                >
                  <option value="FABRIK">FABRIK</option>
                  <option value="CCD">CCD</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">显示目标</span>
                <Button
                  variant={ikState.showTargets ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={toggleShowIKTargets}
                >
                  <Layers size={14} />
                </Button>
              </div>
            </div>

            <div
              className="border border-space-600 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleSection('footIK')}
                className="w-full flex items-center justify-between p-3 bg-space-700/50 hover:bg-space-600/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Footprints size={16} className="text-cyan-400" />
                  <span className="text-sm font-medium text-gray-300">脚部IK</span>
                  <span className="text-xs text-gray-500">
                    ({ikState.targets.filter((t) => t.type === 'foot').length}个目标)
                  </span>
                </div>
                {expandedSections.footIK ? (
                  <ChevronDown size={16} className="text-gray-400" />
                ) : (
                  <ChevronRight size={16} className="text-gray-400" />
                )}
              </button>

              {expandedSections.footIK && (
                <div className="p-3 space-y-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleAddFootIK}
                    className="w-full"
                  >
                    <Move size={14} />
                    <span>添加脚部目标</span>
                  </Button>

                  {ikState.targets
                    .filter((t) => t.type === 'foot')
                    .map((target) => (
                      <IKTargetItem
                        key={target.id}
                        target={target}
                        isActive={ikState.activeTargetId === target.id}
                        onSelect={() => setActiveIKTarget(target.id)}
                        onToggle={() => setIKTargetEnabled(target.id, !target.enabled)}
                        onRemove={() => removeIKTarget(target.id)}
                        onUpdate={(updates) => updateIKTarget(target.id, updates)}
                      />
                    ))}
                </div>
              )}
            </div>

            <div
              className="border border-space-600 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleSection('handIK')}
                className="w-full flex items-center justify-between p-3 bg-space-700/50 hover:bg-space-600/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Hand size={16} className="text-pink-400" />
                  <span className="text-sm font-medium text-gray-300">手部IK</span>
                  <span className="text-xs text-gray-500">
                    ({ikState.targets.filter((t) => t.type === 'hand').length}个目标)
                  </span>
                </div>
                {expandedSections.handIK ? (
                  <ChevronDown size={16} className="text-gray-400" />
                ) : (
                  <ChevronRight size={16} className="text-gray-400" />
                )}
              </button>

              {expandedSections.handIK && (
                <div className="p-3 space-y-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleAddHandIK}
                    className="w-full"
                  >
                    <Move size={14} />
                    <span>添加手部目标</span>
                  </Button>

                  {ikState.targets
                    .filter((t) => t.type === 'hand')
                    .map((target) => (
                      <IKTargetItem
                        key={target.id}
                        target={target}
                        isActive={ikState.activeTargetId === target.id}
                        onSelect={() => setActiveIKTarget(target.id)}
                        onToggle={() => setIKTargetEnabled(target.id, !target.enabled)}
                        onRemove={() => removeIKTarget(target.id)}
                        onUpdate={(updates) => updateIKTarget(target.id, updates)}
                      />
                    ))}
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'bvh' && (
          <>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Upload size={14} className="text-cyber-400" />
                <span className="text-sm font-medium text-gray-300">BVH动作捕捉导入</span>
              </div>
            </div>

            <div className="space-y-3 p-3 bg-space-700/50 rounded-lg">
              <input
                ref={fileInputRef}
                type="file"
                accept=".bvh"
                onChange={handleBVHFileSelect}
                className="hidden"
              />

              <Button
                variant="primary"
                className="w-full"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={16} />
                <span>选择BVH文件</span>
              </Button>

              {bvhImportState && (
                <div className="space-y-2 pt-2 border-t border-space-600">
                  <div className="text-xs text-gray-400">
                    <div className="flex justify-between">
                      <span>文件名:</span>
                      <span className="text-gray-300">{bvhImportState.fileName}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>关节数:</span>
                      <span className="text-gray-300">{bvhImportState.jointCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>帧数:</span>
                      <span className="text-gray-300">{bvhImportState.frameCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>时长:</span>
                      <span className="text-gray-300">{bvhImportState.duration.toFixed(2)}s</span>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">缩放比例</label>
                    <Slider
                      min={0.001}
                      max={0.1}
                      step={0.001}
                      value={bvhImportState.scale}
                      onChange={(v) => setBVHImportScale(v as number)}
                      className="w-full"
                    />
                    <span className="text-xs text-gray-500">{bvhImportState.scale.toFixed(3)}</span>
                  </div>
                </div>
              )}
            </div>

            {importedAnimations.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Zap size={14} className="text-cyber-400" />
                  <span className="text-sm font-medium text-gray-300">已导入动画</span>
                </div>

                <div className="space-y-1">
                  {importedAnimations.map((anim) => (
                    <div
                      key={anim.uuid}
                      className="flex items-center justify-between p-2 bg-space-700/50 rounded"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-gray-300 truncate">{anim.name}</div>
                        <div className="text-[10px] text-gray-500">
                          {anim.source} | {anim.duration.toFixed(2)}s | {anim.boneCount}骨骼
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <Play size={12} />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'retarget' && (
          <>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <GitMerge size={14} className="text-cyber-400" />
                <span className="text-sm font-medium text-gray-300">动作重定向</span>
              </div>
            </div>

            <div className="space-y-3 p-3 bg-space-700/50 rounded-lg">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">目标缩放因子</label>
                <Slider
                  min={0.1}
                  max={2}
                  step={0.1}
                  value={retargetState.scaleFactor}
                  onChange={(v) => setRetargetScale(v as number)}
                  className="w-full"
                />
                <span className="text-xs text-gray-500">
                  {retargetState.scaleFactor.toFixed(2)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">镜像动作</span>
                <Button
                  variant={retargetState.mirror ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setRetargetMirror(!retargetState.mirror)}
                >
                  {retargetState.mirror ? '开启' : '关闭'}
                </Button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">保留位置</span>
                <Button
                  variant={retargetState.preservePosition ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setRetargetPreservePosition(!retargetState.preservePosition)}
                >
                  {retargetState.preservePosition ? '开启' : '关闭'}
                </Button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">自动骨骼映射</span>
                <Button
                  variant={retargetState.autoMapping ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setAutoBoneMapping(!retargetState.autoMapping)}
                >
                  {retargetState.autoMapping ? '开启' : '关闭'}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Copy size={14} className="text-cyber-400" />
                <span className="text-sm font-medium text-gray-300">选择源动画</span>
              </div>

              <div className="space-y-1 max-h-48 overflow-y-auto">
                {animationClips.map((clip) => (
                  <div
                    key={clip.uuid}
                    className="flex items-center justify-between p-2 bg-space-700/50 rounded hover:bg-space-600/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-300 truncate">{clip.name}</div>
                      <div className="text-[10px] text-gray-500">
                        {clip.duration.toFixed(2)}s | {clip.tracks.length}轨道
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => performRetarget(clip.uuid)}
                    >
                      <RefreshCw size={12} />
                      <span>重定向</span>
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

interface IKTargetItemProps {
  target: IKTarget;
  isActive: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onRemove: () => void;
  onUpdate: (updates: Partial<IKTarget>) => void;
}

const IKTargetItem = ({
  target,
  isActive,
  onSelect,
  onToggle,
  onRemove,
  onUpdate,
}: IKTargetItemProps) => {
  return (
    <div
      className={cn(
        'p-2 rounded border transition-colors',
        isActive
          ? 'border-cyber-400 bg-cyber-500/10'
          : 'border-space-600 bg-space-800/50 hover:border-space-500'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <input
          type="text"
          value={target.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
          className="bg-transparent text-xs text-gray-300 border-b border-space-600 focus:border-cyber-400 outline-none w-24"
          onClick={onSelect}
        />
        <div className="flex items-center gap-1">
          <Button
            variant={target.enabled ? 'primary' : 'ghost'}
            size="sm"
            onClick={onToggle}
            className="h-6 w-6 p-0"
          >
            {target.enabled ? <Play size={10} /> : <Pause size={10} />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
          >
            ×
          </Button>
        </div>
      </div>

      <div className="space-y-1 text-[10px]">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">权重</span>
          <Slider
            min={0}
            max={1}
            step={0.01}
            value={target.weight}
            onChange={(v) => onUpdate({ weight: v as number })}
            className="flex-1"
          />
        </div>

        <div className="grid grid-cols-3 gap-1">
          {['X', 'Y', 'Z'].map((axis, idx) => (
            <div key={axis} className="flex items-center gap-1">
              <span className="text-gray-500">{axis}</span>
              <input
                type="number"
                value={target.position[idx].toFixed(3)}
                onChange={(e) => {
                  const newPos = [...target.position] as [number, number, number];
                  newPos[idx] = parseFloat(e.target.value);
                  onUpdate({ position: newPos });
                }}
                className="w-full bg-space-900 border border-space-600 rounded px-1 text-gray-300 text-[10px]"
                step={0.01}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdvancedToolsPanel;
