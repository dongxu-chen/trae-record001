import { useState, useEffect, useCallback } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Settings,
  Activity,
  Wifi,
  WifiOff,
  Cpu,
  Eye,
  AlertTriangle,
  Clock,
  Zap,
  BarChart3,
  ListVideo,
  Maximize2,
  Volume2,
  VolumeX,
  RefreshCw,
  Download,
  Upload,
} from "lucide-react";
import Timeline from "@/components/Timeline";
import { cn } from "@/lib/utils";

interface ActionSegment {
  id: string;
  action: string;
  startTime: number;
  endTime: number;
  confidence: number;
  color: string;
}

const mockSegments: ActionSegment[] = [
  { id: "1", action: "站立", startTime: 0, endTime: 3.2, confidence: 0.95, color: "#165DFF" },
  { id: "2", action: "行走", startTime: 3.2, endTime: 8.5, confidence: 0.92, color: "#00FFA3" },
  { id: "3", action: "挥手", startTime: 8.5, endTime: 9.8, confidence: 0.88, color: "#13C2C2" },
  { id: "4", action: "行走", startTime: 9.8, endTime: 15.3, confidence: 0.94, color: "#00FFA3" },
  { id: "5", action: "跑步", startTime: 15.3, endTime: 18.7, confidence: 0.89, color: "#FF7D00" },
  { id: "6", action: "行走", startTime: 18.7, endTime: 22.1, confidence: 0.91, color: "#00FFA3" },
  { id: "7", action: "坐下", startTime: 22.1, endTime: 28.4, confidence: 0.96, color: "#FF4D4F" },
  { id: "8", action: "站立", startTime: 28.4, endTime: 30.2, confidence: 0.93, color: "#165DFF" },
  { id: "9", action: "跳跃", startTime: 30.2, endTime: 31.5, confidence: 0.87, color: "#FAAD14" },
  { id: "10", action: "站立", startTime: 31.5, endTime: 35.8, confidence: 0.94, color: "#165DFF" },
  { id: "11", action: "行走", startTime: 35.8, endTime: 42.3, confidence: 0.92, color: "#00FFA3" },
  { id: "12", action: "挥手", startTime: 42.3, endTime: 43.6, confidence: 0.90, color: "#13C2C2" },
  { id: "13", action: "行走", startTime: 43.6, endTime: 50.0, confidence: 0.93, color: "#00FFA3" },
  { id: "14", action: "摔倒", startTime: 50.0, endTime: 51.2, confidence: 0.98, color: "#F5222D" },
  { id: "15", action: "躺下", startTime: 51.2, endTime: 60.0, confidence: 0.95, color: "#722ED1" },
];

const actionStats = [
  { action: "行走", count: 4, totalTime: 20.7, avgConfidence: 0.92 },
  { action: "站立", count: 3, totalTime: 10.9, avgConfidence: 0.94 },
  { action: "坐下", count: 1, totalTime: 6.3, avgConfidence: 0.96 },
  { action: "跑步", count: 1, totalTime: 3.4, avgConfidence: 0.89 },
  { action: "挥手", count: 2, totalTime: 2.6, avgConfidence: 0.89 },
  { action: "跳跃", count: 1, totalTime: 1.3, avgConfidence: 0.87 },
  { action: "摔倒", count: 1, totalTime: 1.2, avgConfidence: 0.98 },
  { action: "躺下", count: 1, totalTime: 8.8, avgConfidence: 0.95 },
];

const alerts = [
  { id: "1", type: "danger", message: "检测到摔倒行为", time: "00:50", confidence: 98 },
  { id: "2", type: "warning", message: "异常快速移动", time: "00:15", confidence: 89 },
  { id: "3", type: "info", message: "人员进入监控区域", time: "00:00", confidence: 95 },
];

export default function Home() {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [detectionEnabled, setDetectionEnabled] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7);
  const [fps, setFps] = useState(30);

  const duration = 60;

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTime((prev) => {
        if (prev >= duration) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 0.1 * playbackSpeed;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, duration]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${ms}`;
  }, []);

  const currentAction = mockSegments.find(
    (s) => currentTime >= s.startTime && currentTime <= s.endTime
  );

  const skipBackward = () => {
    setCurrentTime((prev) => Math.max(0, prev - 5));
  };

  const skipForward = () => {
    setCurrentTime((prev) => Math.min(duration, prev + 5));
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const currentSegment = mockSegments.find(
    (s) => currentTime >= s.startTime && currentTime <= s.endTime
  );

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(22, 93, 255, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(22, 93, 255, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: "50px 50px",
        }}
      />

      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl pointer-events-none" />

      <header className="relative z-10 h-14 border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-xl flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              行为分析智能监控系统
            </h1>
          </div>
          <div className="h-6 w-px bg-slate-700" />
          <div className="flex items-center gap-2 text-sm">
            <ListVideo className="w-4 h-4 text-slate-400" />
            <span className="text-slate-400">通道 01</span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium",
              isConnected
                ? "bg-green-500/10 text-green-400 border border-green-500/30"
                : "bg-red-500/10 text-red-400 border border-red-500/30"
            )}>
              {isConnected ? (
                <><Wifi className="w-3 h-3 animate-pulse" /> 已连接</>
              ) : (
                <><WifiOff className="w-3 h-3" /> 断开连接</>
              )}
            </div>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30">
              <Activity className="w-3 h-3" />
              <span>FPS: {fps}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">
              <Zap className="w-3 h-3" />
              <span>延迟: 45ms</span>
            </div>
          </div>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className={cn(
              "p-2 rounded-lg transition-all",
              showSettings
                ? "bg-primary/20 text-primary"
                : "text-slate-400 hover:text-white hover:bg-slate-800"
            )}
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="relative z-10 flex h-[calc(100vh-3.5rem)]">
        <div className="w-[60%] flex flex-col border-r border-slate-700/50">
          <div className="flex-1 relative p-4">
            <div className="w-full h-full rounded-xl overflow-hidden bg-black border border-slate-700/50 relative">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-900 to-black flex items-center justify-center">
                <div className="text-center">
                  <div className="w-32 h-32 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                    <Eye className="w-16 h-16 text-primary/50" />
                  </div>
                  <p className="text-slate-500 text-sm">视频预览区域</p>
                  <p className="text-slate-600 text-xs mt-1">1920 × 1080 @ 30fps</p>
                </div>
              </div>

              {currentSegment && (
                <div className="absolute top-4 left-4 right-4 flex justify-between items-start pointer-events-none">
                  <div className="glass-panel px-4 py-2 rounded-lg">
                    <div className="text-xs text-slate-400 mb-1">当前动作</div>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded animate-pulse-highlight"
                        style={{ backgroundColor: currentSegment.color }}
                      />
                      <span className="text-white font-bold">{currentSegment.action}</span>
                      <span className="text-accent font-mono text-sm">
                        {(currentSegment.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="glass-panel px-4 py-2 rounded-lg">
                    <div className="text-xs text-slate-400 mb-1">时间戳</div>
                    <div className="text-white font-mono font-bold">
                      {formatTime(currentTime)}
                    </div>
                  </div>
                </div>
              )}

              {alerts.filter(a => a.type === "danger").map((alert) => (
                <div
                  key={alert.id}
                  className="absolute top-16 left-4 right-4 glass-panel border-red-500/50 bg-red-500/10 px-4 py-2 rounded-lg flex items-center gap-3 animate-pulse-highlight"
                >
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <div className="flex-1">
                    <div className="text-red-400 font-medium text-sm">{alert.message}</div>
                    <div className="text-red-300/70 text-xs">置信度: {alert.confidence}%</div>
                  </div>
                  <span className="text-red-300/70 text-xs font-mono">{alert.time}</span>
                </div>
              ))}

              <div className="absolute bottom-4 left-4 flex gap-2">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className="p-2 glass-panel rounded-lg text-slate-300 hover:text-white transition-colors"
                >
                  {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="p-2 glass-panel rounded-lg text-slate-300 hover:text-white transition-colors"
                >
                  <Maximize2 className="w-5 h-5" />
                </button>
              </div>

              <div className="absolute bottom-4 right-4 glass-panel px-3 py-1 rounded-lg">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-xs text-slate-300 font-mono">REC</span>
                  <span className="text-xs text-slate-400 font-mono">{formatTime(currentTime)} / {formatTime(duration)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="h-24 px-4 pb-4">
            <div className="w-full h-full glass-panel rounded-xl p-3 flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={skipBackward}
                    className="p-1.5 rounded hover:bg-slate-700/50 text-slate-300 hover:text-white transition-colors"
                  >
                    <SkipBack className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="p-2 rounded-full bg-primary hover:bg-primary/90 text-white transition-colors shadow-lg shadow-primary/30"
                  >
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                  </button>
                  <button
                    onClick={skipForward}
                    className="p-1.5 rounded hover:bg-slate-700/50 text-slate-300 hover:text-white transition-colors"
                  >
                    <SkipForward className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-mono">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                  <select
                    value={playbackSpeed}
                    onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                    className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-primary"
                  >
                    <option value={0.5}>0.5x</option>
                    <option value={1}>1x</option>
                    <option value={2}>2x</option>
                    <option value={4}>4x</option>
                  </select>
                </div>
              </div>

              <div className="flex-1 relative">
                <div className="absolute inset-0 bg-slate-800/50 rounded-lg overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary/30 to-accent/30 transition-all duration-100"
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="w-[25%] flex flex-col border-r border-slate-700/50 overflow-hidden">
          <div className="p-4 border-b border-slate-700/50">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-white">检测结果</h2>
            </div>

            {currentAction && (
              <div className="glass-panel rounded-xl p-4 mb-3 border-primary/30">
                <div className="text-xs text-slate-400 mb-2">实时检测</div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{
                        backgroundColor: `${currentAction.color}30`,
                        border: `2px solid ${currentAction.color}`,
                        boxShadow: `0 0 20px ${currentAction.color}40`,
                      }}
                    >
                      <Activity className="w-5 h-5" style={{ color: currentAction.color }} />
                    </div>
                    <div>
                      <div className="text-white font-bold text-lg">{currentAction.action}</div>
                      <div className="text-xs text-slate-400">
                        {formatTime(currentAction.startTime)} - {formatTime(currentAction.endTime)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-accent font-mono">
                      {(currentAction.confidence * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-slate-500">置信度</div>
                  </div>
                </div>
              </div>
            )}

            <div className="glass-panel rounded-xl p-3">
              <div className="text-xs text-slate-400 mb-2">检测配置</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-300">行为检测</span>
                  <button
                    onClick={() => setDetectionEnabled(!detectionEnabled)}
                    className={cn(
                      "w-10 h-5 rounded-full transition-colors relative",
                      detectionEnabled ? "bg-primary" : "bg-slate-600"
                    )}
                  >
                    <div
                      className={cn(
                        "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform",
                        detectionEnabled ? "translate-x-5" : "translate-x-0.5"
                      )}
                    />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-300">置信度阈值</span>
                  <span className="text-sm text-accent font-mono">{(confidenceThreshold * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-medium text-slate-200">动作统计</h3>
              </div>
              <div className="space-y-2">
                {actionStats.map((stat, index) => (
                  <div
                    key={stat.action}
                    className="glass-panel rounded-lg p-3 hover:bg-slate-800/50 transition-colors cursor-pointer animate-slide-in"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-white font-medium">{stat.action}</span>
                      <span className="text-xs text-slate-400">{stat.count} 次</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-accent animate-progress-bar"
                          style={{
                            width: `${(stat.totalTime / duration) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 font-mono w-16 text-right">
                        {stat.totalTime.toFixed(1)}s
                      </span>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="text-slate-500">平均置信度</span>
                      <span className="text-primary font-mono">{(stat.avgConfidence * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-warning" />
                <h3 className="text-sm font-medium text-slate-200">告警记录</h3>
              </div>
              <div className="space-y-2">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={cn(
                      "glass-panel rounded-lg p-3 transition-colors",
                      alert.type === "danger" && "border-red-500/30 bg-red-500/5",
                      alert.type === "warning" && "border-yellow-500/30 bg-yellow-500/5",
                      alert.type === "info" && "border-blue-500/30 bg-blue-500/5"
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-2">
                        <AlertTriangle
                          className={cn(
                            "w-4 h-4 mt-0.5",
                            alert.type === "danger" && "text-red-400",
                            alert.type === "warning" && "text-yellow-400",
                            alert.type === "info" && "text-blue-400"
                          )}
                        />
                        <div>
                          <div className="text-sm text-white">{alert.message}</div>
                          <div className="text-xs text-slate-500">
                            置信度: {alert.confidence}%
                          </div>
                        </div>
                      </div>
                      <span className="text-xs text-slate-500 font-mono">{alert.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="w-[15%] flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-700/50">
            <div className="flex items-center gap-2 mb-3">
              <Settings className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-white">控制面板</h2>
            </div>

            <div className="space-y-2">
              <button className="w-full py-2 px-3 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg flex items-center justify-center gap-2 transition-colors border border-primary/30">
                <RefreshCw className="w-4 h-4" />
                <span className="text-sm">重新分析</span>
              </button>
              <button className="w-full py-2 px-3 bg-slate-700/50 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center gap-2 transition-colors">
                <Download className="w-4 h-4" />
                <span className="text-sm">导出报告</span>
              </button>
              <button className="w-full py-2 px-3 bg-slate-700/50 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center gap-2 transition-colors">
                <Upload className="w-4 h-4" />
                <span className="text-sm">上传视频</span>
              </button>
            </div>
          </div>

          <div className="p-4 border-b border-slate-700/50">
            <div className="text-xs text-slate-400 mb-2">视频信息</div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">分辨率</span>
                <span className="text-slate-300 font-mono">1920×1080</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">帧率</span>
                <span className="text-slate-300 font-mono">30 fps</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">时长</span>
                <span className="text-slate-300 font-mono">01:00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">文件大小</span>
                <span className="text-slate-300 font-mono">256 MB</span>
              </div>
            </div>
          </div>

          <div className="flex-1 p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-5 h-5 text-accent" />
              <h2 className="text-base font-semibold text-white">时间轴</h2>
            </div>
            <div className="flex-1 min-h-0">
              <Timeline
                segments={mockSegments}
                currentTime={currentTime}
                duration={duration}
                onTimeChange={setCurrentTime}
              />
            </div>

            <div className="mt-4">
              <div className="text-xs text-slate-400 mb-2">动作图例</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries({
                  "站立": "#165DFF",
                  "行走": "#00FFA3",
                  "跑步": "#FF7D00",
                  "坐下": "#FF4D4F",
                  "躺下": "#722ED1",
                  "挥手": "#13C2C2",
                  "跳跃": "#FAAD14",
                  "摔倒": "#F5222D",
                }).map(([action, color]) => (
                  <div key={action} className="flex items-center gap-1.5">
                    <div
                      className="w-3 h-3 rounded-sm"
                      style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}80` }}
                    />
                    <span className="text-[11px] text-slate-400">{action}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center" onClick={() => setShowSettings(false)}>
          <div className="glass-panel w-96 rounded-xl p-6 animate-slide-in" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">系统设置</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-300 block mb-2">WebSocket 地址</label>
                <input
                  type="text"
                  defaultValue="ws://localhost:8080/ws"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-2">检测模型</label>
                <select className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary">
                  <option>ST-GCN (时空图卷积)</option>
                  <option>3D ResNet</option>
                  <option>SlowFast</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-2">
                  置信度阈值: {(confidenceThreshold * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-2">
                  目标 FPS: {fps}
                </label>
                <input
                  type="range"
                  min="15"
                  max="60"
                  step="5"
                  value={fps}
                  onChange={(e) => setFps(Number(e.target.value))}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-slate-300">自动保存报告</span>
                <button className="w-10 h-5 rounded-full bg-primary relative">
                  <div className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-white" />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">显示调试信息</span>
                <button className="w-10 h-5 rounded-full bg-slate-600 relative">
                  <div className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white" />
                </button>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
              >
                保存设置
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
