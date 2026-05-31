import { useState } from 'react'
import { Play, Pause, RotateCcw, ChevronDown, ChevronUp, Download, MousePointer } from 'lucide-react'
import { useSimulationStore } from '@/store/useSimulationStore'
import { AnimationExporter } from '@/utils/exporter'
import { SceneSelector } from './SceneSelector'

interface ControlPanelProps {
  canvas: HTMLCanvasElement | null
}

export function ControlPanel({ canvas }: ControlPanelProps) {
  const { simulation, fluidParams, mouseForce, setFluidParams, toggleSimulation, resetSimulation, setResolution, updateMouseForce } =
    useSimulationStore((state) => ({
      simulation: state.simulation,
      fluidParams: state.fluidParams,
      mouseForce: state.mouseForce,
      setFluidParams: state.setFluidParams,
      toggleSimulation: state.toggleSimulation,
      resetSimulation: state.resetSimulation,
      setResolution: state.setResolution,
      updateMouseForce: state.updateMouseForce,
    }))

  const [expandedSections, setExpandedSections] = useState({
    simulation: true,
    fluid: true,
    interaction: true,
    material: true,
    export: true,
  })

  const [isRecording, setIsRecording] = useState(false)
  const [exportFps, setExportFps] = useState(30)
  const [exporter] = useState(() => new AnimationExporter(30))

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const handleRecord = () => {
    if (!canvas) return

    if (isRecording) {
      exporter.download(`fluid-sim-${Date.now()}.webm`)
      setIsRecording(false)
    } else {
      exporter.setTargetFps(exportFps)
      exporter.start(canvas)
      setIsRecording(true)
    }
  }

  const SliderControl = ({
    label,
    value,
    min,
    max,
    step,
    onChange,
    unit = '',
  }: {
    label: string
    value: number
    min: number
    max: number
    step: number
    onChange: (value: number) => void
    unit?: string
  }) => (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-400">{label}</span>
        <span className="text-sm text-cyber-cyan font-mono">
          {value.toFixed(2)}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
    </div>
  )

  const Section = ({
    title,
    sectionKey,
    children,
  }: {
    title: string
    sectionKey: keyof typeof expandedSections
    children: React.ReactNode
  }) => (
    <div className="mb-4">
      <button
        className="w-full flex items-center justify-between py-2 hover:text-cyber-cyan transition-colors"
        onClick={() => toggleSection(sectionKey)}
      >
        <span className="section-title mb-0">{title}</span>
        {expandedSections[sectionKey] ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>
      {expandedSections[sectionKey] && <div className="mt-2">{children}</div>}
    </div>
  )

  return (
    <div className="absolute right-4 top-1/2 -translate-y-1/2 z-10 w-72">
      <div className="glass-panel p-4 max-h-[80vh] overflow-y-auto">
        <SceneSelector />

        <Section title="模拟控制" sectionKey="simulation">
          <div className="flex gap-2 mb-4">
            <button
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg transition-all duration-200 bg-cyber-cyan/20 border border-cyber-cyan/50 hover:bg-cyber-cyan/30"
              onClick={toggleSimulation}
            >
              {simulation.isPlaying ? (
                <>
                  <Pause className="w-4 h-4" />
                  <span>暂停</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>播放</span>
                </>
              )}
            </button>
            <button
              className="flex items-center justify-center p-2 rounded-lg transition-all duration-200 bg-white/5 border border-white/10 hover:bg-white/10"
              onClick={resetSimulation}
              title="重置"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          <div className="mb-4">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm text-gray-400">模拟分辨率</span>
              <span className="text-sm text-cyber-cyan font-mono">{simulation.resolution}px</span>
            </div>
            <select
              value={simulation.resolution}
              onChange={(e) => setResolution(parseInt(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-cyber-cyan/50"
            >
              <option value={128}>128 x 128 (快速)</option>
              <option value={256}>256 x 256 (平衡)</option>
              <option value={512}>512 x 512 (高质量)</option>
            </select>
          </div>
        </Section>

        <Section title="流体参数" sectionKey="fluid">
          <SliderControl
            label="密度"
            value={fluidParams.density}
            min={0.1}
            max={3}
            step={0.1}
            onChange={(v) => setFluidParams({ density: v })}
          />
          <SliderControl
            label="粘度"
            value={fluidParams.viscosity}
            min={0.01}
            max={1}
            step={0.01}
            onChange={(v) => setFluidParams({ viscosity: v })}
          />
          <SliderControl
            label="速度"
            value={fluidParams.velocity}
            min={0.5}
            max={20}
            step={0.5}
            onChange={(v) => setFluidParams({ velocity: v })}
          />
          <SliderControl
            label="扩散"
            value={fluidParams.diffusion}
            min={0.0001}
            max={0.01}
            step={0.0001}
            onChange={(v) => setFluidParams({ diffusion: v })}
          />
          <SliderControl
            label="透明度"
            value={fluidParams.transparency}
            min={0.1}
            max={1}
            step={0.05}
            onChange={(v) => setFluidParams({ transparency: v })}
          />
          <SliderControl
            label="涡量强度"
            value={fluidParams.vorticityScale}
            min={0}
            max={0.5}
            step={0.01}
            onChange={(v) => setFluidParams({ vorticityScale: v })}
          />
          <SliderControl
            label="速度耗散"
            value={fluidParams.velocityDissipation}
            min={0.9}
            max={1}
            step={0.001}
            onChange={(v) => setFluidParams({ velocityDissipation: v })}
          />
          <SliderControl
            label="压力迭代"
            value={fluidParams.pressureIterations}
            min={10}
            max={50}
            step={1}
            onChange={(v) => setFluidParams({ pressureIterations: v })}
            unit="次"
          />
        </Section>

        <Section title="交互力场" sectionKey="interaction">
          <div className="flex items-center gap-2 mb-4">
            <MousePointer className="w-4 h-4 text-cyber-cyan" />
            <span className="text-sm text-gray-400">鼠标拖拽力场</span>
          </div>
          <SliderControl
            label="力场强度"
            value={mouseForce.strength}
            min={1}
            max={30}
            step={1}
            onChange={(v) => updateMouseForce({ strength: v })}
          />
          <SliderControl
            label="作用半径"
            value={mouseForce.radius}
            min={10}
            max={100}
            step={5}
            onChange={(v) => updateMouseForce({ radius: v })}
            unit="px"
          />
          <p className="text-xs text-gray-500 mt-2">
            按住鼠标并拖拽可施加力场影响流体走向
          </p>
        </Section>

        <Section title="颜色材质" sectionKey="material">
          <div className="mb-4">
            <span className="text-sm text-gray-400 block mb-2">流体颜色</span>
            <div className="flex gap-2">
              {['#00F5FF', '#7B2FFD', '#FF6B35', '#00FF88', '#FFD700'].map((color) => (
                <button
                  key={color}
                  className="w-8 h-8 rounded-full border-2 transition-all hover:scale-110"
                  style={{
                    backgroundColor: color,
                    borderColor:
                      fluidParams.color.r === parseInt(color.slice(1, 3), 16) / 255 &&
                      fluidParams.color.g === parseInt(color.slice(3, 5), 16) / 255 &&
                      fluidParams.color.b === parseInt(color.slice(5, 7), 16) / 255
                        ? '#ffffff'
                        : 'transparent',
                  }}
                  onClick={() =>
                    setFluidParams({
                      color: {
                        r: parseInt(color.slice(1, 3), 16) / 255,
                        g: parseInt(color.slice(3, 5), 16) / 255,
                        b: parseInt(color.slice(5, 7), 16) / 255,
                      },
                    })
                  }
                />
              ))}
            </div>
          </div>
        </Section>

        <Section title="动画导出" sectionKey="export">
          {!isRecording && (
            <div className="mb-4">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-gray-400">导出帧率</span>
                <span className="text-sm text-neon-purple font-mono">{exportFps} FPS</span>
              </div>
              <select
                value={exportFps}
                onChange={(e) => setExportFps(parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neon-purple/50"
              >
                <option value={24}>24 FPS (电影级)</option>
                <option value={30}>30 FPS (标准)</option>
                <option value={60}>60 FPS (高流畅)</option>
              </select>
            </div>
          )}
          <button
            className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg transition-all duration-200 ${
              isRecording
                ? 'bg-warning-orange/30 border border-warning-orange animate-pulse'
                : 'bg-neon-purple/20 border border-neon-purple/50 hover:bg-neon-purple/30'
            }`}
            onClick={handleRecord}
            disabled={!canvas}
          >
            <Download className="w-4 h-4" />
            <span>{isRecording ? '停止录制' : '录制动画'}</span>
          </button>
          {isRecording && (
            <p className="text-xs text-warning-orange mt-2 text-center">
              正在录制中 ({exportFps} FPS)... 点击停止并下载
            </p>
          )}
        </Section>
      </div>
    </div>
  )
}
