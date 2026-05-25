import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import {
  Play,
  Pause,
  Walking,
  Zap,
  GitMerge,
  Keyframe,
  RefreshCw,
  Activity,
  Gauge,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Slider } from '@/components/ui/Slider';
import { useEditorStore } from '@/store/editorStore';
import { useAnimationMixer } from '@/hooks/useAnimationMixer';
import { easeInOutCubic } from '@/utils/math/CurveMath';
import { cn } from '@/lib/utils';

interface ClipPreviewState {
  [clipUuid: string]: boolean;
}

interface AnimationBlenderProps {
  model: any;
}

const AnimationBlender = ({ model }: AnimationBlenderProps) => {
  const {
    blendState,
    setBlendWeight,
    setBlendWeights,
    normalizeBlendWeights,
    animationClips,
    currentTime,
    addKeyframe,
    selectedBoneUuid,
  } = useEditorStore();

  const { crossFade, setAnimationWeight } = useAnimationMixer(model);

  const [clipPreviewState, setClipPreviewState] = useState<ClipPreviewState>({});
  const [clipWeights, setClipWeights] = useState<Record<string, number>>({});
  const [autoKeyframeEnabled, setAutoKeyframeEnabled] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const curveCanvasRef = useRef<HTMLCanvasElement>(null);
  const pieCanvasRef = useRef<HTMLCanvasElement>(null);

  const { walkWeight, runWeight, transitionSpeed } = blendState;

  const mainBlendValue = useMemo(() => {
    const total = walkWeight + runWeight;
    if (total === 0) return 0.5;
    return runWeight / total;
  }, [walkWeight, runWeight]);

  const currentState = useMemo(() => {
    if (walkWeight >= 0.9) return 'walking';
    if (runWeight >= 0.9) return 'running';
    return 'blending';
  }, [walkWeight, runWeight]);

  const smoothness = useMemo(() => {
    const total = walkWeight + runWeight;
    if (total === 0) return 1;
    const normalizedWalk = walkWeight / total;
    const normalizedRun = runWeight / total;
    return 1 - Math.abs(normalizedWalk - normalizedRun);
  }, [walkWeight, runWeight]);

  const walkClips = useMemo(
    () => animationClips.filter((clip) => clip.name.toLowerCase().includes('walk')),
    [animationClips]
  );

  const runClips = useMemo(
    () => animationClips.filter((clip) => clip.name.toLowerCase().includes('run')),
    [animationClips]
  );

  const otherClips = useMemo(
    () =>
      animationClips.filter(
        (clip) =>
          !clip.name.toLowerCase().includes('walk') &&
          !clip.name.toLowerCase().includes('run')
      ),
    [animationClips]
  );

  useEffect(() => {
    const initialWeights: Record<string, number> = {};
    animationClips.forEach((clip) => {
      if (clipWeights[clip.uuid] === undefined) {
        initialWeights[clip.uuid] = clip.name.toLowerCase().includes('walk')
          ? walkWeight
          : clip.name.toLowerCase().includes('run')
          ? runWeight
          : 0;
      }
    });
    if (Object.keys(initialWeights).length > 0) {
      setClipWeights((prev) => ({ ...prev, ...initialWeights }));
    }
  }, [animationClips]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, rect.width, rect.height);

    const gradient = ctx.createLinearGradient(0, 0, rect.width, 0);
    gradient.addColorStop(0, '#22d3ee');
    gradient.addColorStop(1, '#f472b6');

    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = (rect.height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(rect.width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i <= rect.width; i++) {
      const t = i / rect.width;
      const eased = easeInOutCubic(t);
      const y = rect.height - eased * rect.height;
      if (i === 0) {
        ctx.moveTo(i, y);
      } else {
        ctx.lineTo(i, y);
      }
    }
    ctx.stroke();

    const progressX = mainBlendValue * rect.width;
    const progressY = rect.height - easeInOutCubic(mainBlendValue) * rect.height;

    ctx.fillStyle = '#22d3ee';
    ctx.beginPath();
    ctx.arc(progressX, progressY, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = '#22d3ee';
    ctx.lineWidth = 2;
    ctx.stroke();
  }, [mainBlendValue]);

  useEffect(() => {
    const canvas = curveCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = (rect.height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(rect.width, y);
      ctx.stroke();
    }

    const walkGradient = ctx.createLinearGradient(0, 0, 0, rect.height);
    walkGradient.addColorStop(0, '#22d3ee');
    walkGradient.addColorStop(1, '#0891b2');

    const runGradient = ctx.createLinearGradient(0, 0, 0, rect.height);
    runGradient.addColorStop(0, '#f472b6');
    runGradient.addColorStop(1, '#db2777');

    ctx.strokeStyle = walkGradient;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i <= rect.width; i++) {
      const t = i / rect.width;
      const eased = easeInOutCubic(t);
      const y = rect.height - (1 - mainBlendValue) * eased * rect.height;
      if (i === 0) {
        ctx.moveTo(i, y);
      } else {
        ctx.lineTo(i, y);
      }
    }
    ctx.stroke();

    ctx.strokeStyle = runGradient;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i <= rect.width; i++) {
      const t = i / rect.width;
      const eased = easeInOutCubic(t);
      const y = rect.height - mainBlendValue * eased * rect.height;
      if (i === 0) {
        ctx.moveTo(i, y);
      } else {
        ctx.lineTo(i, y);
      }
    }
    ctx.stroke();
  }, [mainBlendValue]);

  useEffect(() => {
    const canvas = pieCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, rect.width, rect.height);

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const radius = Math.min(centerX, centerY) - 10;
    const innerRadius = radius * 0.5;

    const total = walkWeight + runWeight;
    if (total === 0) {
      ctx.fillStyle = '#374151';
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2, true);
      ctx.fill();
      return;
    }

    const walkAngle = (walkWeight / total) * Math.PI * 2;
    const runAngle = (runWeight / total) * Math.PI * 2;

    const walkGradient = ctx.createRadialGradient(
      centerX,
      centerY,
      innerRadius,
      centerX,
      centerY,
      radius
    );
    walkGradient.addColorStop(0, '#22d3ee');
    walkGradient.addColorStop(1, '#0891b2');

    const runGradient = ctx.createRadialGradient(
      centerX,
      centerY,
      innerRadius,
      centerX,
      centerY,
      radius
    );
    runGradient.addColorStop(0, '#f472b6');
    runGradient.addColorStop(1, '#db2777');

    ctx.fillStyle = walkGradient;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + walkAngle);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = runGradient;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(
      centerX,
      centerY,
      radius,
      -Math.PI / 2 + walkAngle,
      -Math.PI / 2 + walkAngle + runAngle
    );
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#e2e8f0';
    ctx.font = 'bold 14px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const percentage = Math.round(mainBlendValue * 100);
    ctx.fillText(`${percentage}%`, centerX, centerY);
  }, [walkWeight, runWeight, mainBlendValue]);

  const handleMainBlendChange = useCallback(
    (value: number) => {
      const newRunWeight = value;
      const newWalkWeight = 1 - value;
      setBlendWeights({ walk: newWalkWeight, run: newRunWeight });
      setAnimationWeight('walk', newWalkWeight);
      setAnimationWeight('run', newRunWeight);

      if (autoKeyframeEnabled && selectedBoneUuid) {
        addKeyframe(
          selectedBoneUuid,
          'rotation',
          'w',
          currentTime,
          [newWalkWeight, newRunWeight, 0, 0]
        );
      }
    },
    [
      setBlendWeights,
      setAnimationWeight,
      autoKeyframeEnabled,
      selectedBoneUuid,
      currentTime,
      addKeyframe,
    ]
  );

  const handleTransitionSpeedChange = useCallback(
    (value: number) => {
      useEditorStore.setState((state: any) => ({
        blendState: { ...state.blendState, transitionSpeed: value },
      }));
    },
    []
  );

  const handleClipWeightChange = useCallback(
    (clipUuid: string, value: number) => {
      setClipWeights((prev) => ({ ...prev, [clipUuid]: value }));
    },
    []
  );

  const handlePresetClick = useCallback(
    (preset: 'walk' | 'run' | 'blend') => {
      let walkVal = 0;
      let runVal = 0;

      switch (preset) {
        case 'walk':
          walkVal = 1;
          runVal = 0;
          break;
        case 'run':
          walkVal = 0;
          runVal = 1;
          break;
        case 'blend':
          walkVal = 0.5;
          runVal = 0.5;
          break;
      }

      setBlendWeight('walk', walkVal);
      setBlendWeight('run', runVal);
      setAnimationWeight('walk', walkVal);
      setAnimationWeight('run', runVal);
      crossFade(walkVal > runVal ? 'run' : 'walk', walkVal > runVal ? 'walk' : 'run', 1 / transitionSpeed);
    },
    [setBlendWeight, setAnimationWeight, crossFade, transitionSpeed]
  );

  const toggleClipPreview = useCallback((clipUuid: string) => {
    setClipPreviewState((prev) => ({ ...prev, [clipUuid]: !prev[clipUuid] }));
  }, []);

  const handleAddKeyframe = useCallback(() => {
    if (selectedBoneUuid) {
      addKeyframe(selectedBoneUuid, 'rotation', 'x', currentTime, [walkWeight]);
      addKeyframe(selectedBoneUuid, 'rotation', 'y', currentTime, [runWeight]);
    }
  }, [selectedBoneUuid, currentTime, walkWeight, runWeight, addKeyframe]);

  const renderClipItem = (clip: any, type: 'walk' | 'run' | 'other') => {
    const isPreviewing = clipPreviewState[clip.uuid];
    const weight = clipWeights[clip.uuid] ?? 0;
    const color = type === 'walk' ? '#22d3ee' : type === 'run' ? '#f472b6' : '#a78bfa';

    return (
      <div
        key={clip.uuid}
        className="flex items-center gap-3 p-2 rounded-lg bg-space-700/50 border border-space-600 hover:border-space-500 transition-colors"
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={() => toggleClipPreview(clip.uuid)}
          className="flex-shrink-0"
          style={{ color }}
        >
          {isPreviewing ? <Pause size={14} /> : <Play size={14} />}
        </Button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-200 truncate">{clip.name}</span>
            <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
              {clip.duration.toFixed(2)}s
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Slider
              min={0}
              max={1}
              step={0.01}
              value={weight}
              onChange={(v) => handleClipWeightChange(clip.uuid, v as number)}
              color={color}
              className="flex-1"
            />
            <span className="text-xs text-gray-400 w-12 text-right flex-shrink-0">
              {Math.round(weight * 100)}%
            </span>
          </div>
        </div>
      </div>
    );
  };

  const getStateLabel = () => {
    switch (currentState) {
      case 'walking':
        return { text: '步行', color: 'text-cyan-400', bg: 'bg-cyan-500/20' };
      case 'running':
        return { text: '跑步', color: 'text-pink-400', bg: 'bg-pink-500/20' };
      case 'blending':
        return { text: '混合中', color: 'text-purple-400', bg: 'bg-purple-500/20' };
    }
  };

  const stateInfo = getStateLabel();

  return (
    <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-space-600 bg-space-800/80">
        <div className="flex items-center gap-2">
          <GitMerge className="text-cyber-400" size={18} />
          <span className="font-medium text-gray-100">动画混合器</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn('px-2 py-1 rounded text-xs font-medium', stateInfo.bg, stateInfo.color)}>
            {stateInfo.text}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Walking size={16} className="text-cyan-400" />
              <span className="text-sm font-medium text-gray-300">走跑切换</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <span className="text-xs text-cyan-400">{Math.round(walkWeight * 100)}%</span>
                <span className="text-xs text-gray-500 mx-1">/</span>
                <span className="text-xs text-pink-400">{Math.round(runWeight * 100)}%</span>
              </div>
              <div className={cn(
                'px-2 py-0.5 rounded text-[10px] font-mono',
                Math.abs(walkWeight + runWeight - 1) < 0.01
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              )}>
                Σ = {(walkWeight + runWeight).toFixed(2)}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={normalizeBlendWeights}
                disabled={Math.abs(walkWeight + runWeight - 1) < 0.01}
                className="h-6 px-2 text-xs"
                title="归一化权重"
              >
                <RefreshCw size={12} />
              </Button>
            </div>
          </div>

          <div className="relative h-12 bg-space-700 rounded-lg overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/30 to-pink-500/30"
              style={{ width: `${mainBlendValue * 100}%` }}
            />
            <div className="absolute inset-0 flex items-center px-4">
              <div className="w-full relative">
                <div
                  className="absolute w-6 h-8 -translate-x-1/2 bg-cyber-500 rounded cursor-grab active:cursor-grabbing shadow-cyber-glow-sm flex items-center justify-center"
                  style={{ left: `${mainBlendValue * 100}%` }}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    const slider = e.currentTarget.parentElement;
                    if (!slider) return;

                    const handleMove = (moveEvent: MouseEvent) => {
                      const rect = slider.getBoundingClientRect();
                      const percentage = Math.max(
                        0,
                        Math.min(1, (moveEvent.clientX - rect.left) / rect.width)
                      );
                      handleMainBlendChange(percentage);
                    };

                    const handleUp = () => {
                      document.removeEventListener('mousemove', handleMove);
                      document.removeEventListener('mouseup', handleUp);
                    };

                    document.addEventListener('mousemove', handleMove);
                    document.addEventListener('mouseup', handleUp);
                  }}
                >
                  <div className="w-1 h-4 bg-space-900 rounded-full" />
                </div>
              </div>
            </div>
            <div className="absolute bottom-1 left-0 right-0 flex justify-between px-2">
              <span className="text-[10px] text-cyan-400">走</span>
              <span className="text-[10px] text-pink-400">跑</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handlePresetClick('walk')}
            className={cn(
              'flex flex-col gap-1 h-auto py-2',
              currentState === 'walking' && 'border-cyan-500/60 bg-cyan-500/10'
            )}
          >
            <Walking size={18} className="text-cyan-400" />
            <span className="text-xs">100%走</span>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handlePresetClick('blend')}
            className={cn(
              'flex flex-col gap-1 h-auto py-2',
              currentState === 'blending' && 'border-purple-500/60 bg-purple-500/10'
            )}
          >
            <GitMerge size={18} className="text-purple-400" />
            <span className="text-xs">50%/50%</span>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handlePresetClick('run')}
            className={cn(
              'flex flex-col gap-1 h-auto py-2',
              currentState === 'running' && 'border-pink-500/60 bg-pink-500/10'
            )}
          >
            <Zap size={18} className="text-pink-400" />
            <span className="text-xs">100%跑</span>
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <Activity size={14} className="text-gray-400" />
              <span className="text-xs text-gray-400">过渡曲线</span>
            </div>
            <div className="h-20 bg-space-900/50 rounded-lg p-2">
              <canvas ref={canvasRef} className="w-full h-full" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <RefreshCw size={14} className="text-gray-400" />
              <span className="text-xs text-gray-400">权重变化</span>
            </div>
            <div className="h-20 bg-space-900/50 rounded-lg p-2">
              <canvas ref={curveCanvasRef} className="w-full h-full" />
            </div>
          </div>
        </div>

        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="h-28 w-28 bg-space-900/50 rounded-lg p-2">
              <canvas ref={pieCanvasRef} className="w-full h-full" />
            </div>
            <div className="flex items-center justify-center gap-3 mt-2">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-cyan-500" />
                <span className="text-[10px] text-gray-400">走</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-pink-500" />
                <span className="text-[10px] text-gray-400">跑</span>
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Gauge size={14} className="text-gray-400" />
                  <span className="text-xs text-gray-400">过渡速度</span>
                </div>
                <span className="text-xs text-cyber-400">{transitionSpeed.toFixed(1)}x</span>
              </div>
              <Slider
                min={0.1}
                max={5}
                step={0.1}
                value={transitionSpeed}
                onChange={(v) => handleTransitionSpeedChange(v as number)}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Activity size={14} className="text-gray-400" />
                  <span className="text-xs text-gray-400">平滑度</span>
                </div>
                <span className="text-xs text-green-400">{Math.round(smoothness * 100)}%</span>
              </div>
              <div className="h-2 bg-space-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-200"
                  style={{ width: `${smoothness * 100}%` }}
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant={autoKeyframeEnabled ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setAutoKeyframeEnabled(!autoKeyframeEnabled)}
                className="flex-1"
              >
                <Keyframe size={14} className={cn(!autoKeyframeEnabled && 'text-cyber-400')} />
                <span className="text-xs">自动关键帧</span>
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleAddKeyframe}
                className="flex-1"
              >
                <Keyframe size={14} className="text-yellow-400" />
                <span className="text-xs">添加关键帧</span>
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-cyan-400" />
            <span className="text-sm font-medium text-gray-300">步行动画</span>
            <span className="text-xs text-gray-500">({walkClips.length})</span>
          </div>
          {walkClips.length === 0 ? (
            <div className="text-center py-4 text-gray-500 text-sm bg-space-700/30 rounded-lg">
              暂无步行动画片段
            </div>
          ) : (
            <div className="space-y-2">
              {walkClips.map((clip) => renderClipItem(clip, 'walk'))}
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-pink-400" />
            <span className="text-sm font-medium text-gray-300">跑步动画</span>
            <span className="text-xs text-gray-500">({runClips.length})</span>
          </div>
          {runClips.length === 0 ? (
            <div className="text-center py-4 text-gray-500 text-sm bg-space-700/30 rounded-lg">
              暂无跑步动画片段
            </div>
          ) : (
            <div className="space-y-2">
              {runClips.map((clip) => renderClipItem(clip, 'run'))}
            </div>
          )}
        </div>

        {otherClips.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-purple-400" />
              <span className="text-sm font-medium text-gray-300">其他动画</span>
              <span className="text-xs text-gray-500">({otherClips.length})</span>
            </div>
            <div className="space-y-2">
              {otherClips.map((clip) => renderClipItem(clip, 'other'))}
            </div>
          </div>
        )}
      </div>

      <div className="px-4 py-3 border-t border-space-600 bg-space-800/80">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>当前时间: {currentTime.toFixed(2)}s</span>
            <span>
              状态: <span className={stateInfo.color}>{stateInfo.text}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span>平滑度: </span>
            <div className="w-16 h-1.5 bg-space-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                style={{ width: `${smoothness * 100}%` }}
              />
            </div>
            <span className="text-green-400">{Math.round(smoothness * 100)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

AnimationBlender.displayName = 'AnimationBlender';

export { AnimationBlender };
