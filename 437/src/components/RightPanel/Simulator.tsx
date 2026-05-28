import React, { useMemo, useCallback, useState, useEffect } from 'react';
import { createMachine, interpret, ActorLogicFrom } from 'xstate';
import { Play, RotateCcw, Zap, History, CircleDot, ArrowRight, Clock, Activity, SkipBack, SkipForward, Pause } from 'lucide-react';
import { useFlowStore } from '../../store/useFlowStore';
import { EdgeData, StateNodeData, EventRecord } from '../../types';
import { Node, Edge } from 'reactflow';
import { cn } from '../../lib/utils';

interface EventOption {
  name: string;
  target: string;
}

export const Simulator: React.FC = () => {
  const { nodes, edges, simulator, setSimulatorState, resetSimulator } = useFlowStore();
  const [animatingEvent, setAnimatingEvent] = useState<string | null>(null);
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(-1);
  const [replaySpeed, setReplaySpeed] = useState(1000);

  const initialNode = useMemo(() => {
    return nodes.find((n) => n.data.nodeType === 'initial' || n.data.isInitial) || nodes[0];
  }, [nodes]);

  const machine = useMemo(() => {
    if (nodes.length === 0) return null;

    const states: Record<string, any> = {};
    nodes.forEach((node: Node<StateNodeData>) => {
      const stateName = node.data.label;
      const nodeEdges = edges.filter((e: Edge<EdgeData>) => e.source === node.id);

      const on: Record<string, any> = {};
      nodeEdges.forEach((edge: Edge<EdgeData>) => {
        const targetNode = nodes.find((n) => n.id === edge.target);
        if (targetNode) {
          const event = String(edge.data?.event || edge.label || 'TRANSITION');
          on[event] = { target: targetNode.data.label };
        }
      });

      states[stateName] = {
        type: node.data.nodeType === 'final' ? 'final' : undefined,
        on: Object.keys(on).length > 0 ? on : undefined,
      };
    });

    try {
      return createMachine({
        id: 'simulator',
        initial: initialNode?.data.label || '',
        states,
      });
    } catch {
      return null;
    }
  }, [nodes, edges, initialNode]);

  const service = useMemo(() => {
    if (!machine) return null;
    return interpret(machine as unknown as ActorLogicFrom<any>);
  }, [machine]);

  const availableEvents = useMemo((): EventOption[] => {
    if (!simulator.currentState) return [];
    const currentNode = nodes.find((n) => n.data.label === simulator.currentState);
    if (!currentNode) return [];

    return edges
      .filter((e) => e.source === currentNode.id)
      .map((edge) => {
        const targetNode = nodes.find((n) => n.id === edge.target);
        return {
          name: String(edge.data?.event || edge.label || 'TRANSITION'),
          target: targetNode?.data.label || '',
        };
      });
  }, [nodes, edges, simulator.currentState]);

  const handleStart = useCallback(() => {
    if (service && initialNode) {
      service.stop();
      service.start();
      setSimulatorState({
        currentState: initialNode.data.label,
        history: [initialNode.data.label],
        eventHistory: [],
        isRunning: true,
        lastEvent: null,
      });
    }
  }, [service, initialNode, setSimulatorState]);

  const handleReset = useCallback(() => {
    if (service) {
      service.stop();
    }
    setIsReplaying(false);
    setReplayIndex(-1);
    resetSimulator();
  }, [service, resetSimulator]);

  const handleStartReplay = useCallback(() => {
    if (simulator.eventHistory.length === 0) return;
    setIsReplaying(true);
    setReplayIndex(-1);
    if (service && initialNode) {
      service.stop();
      service.start();
    }
    setSimulatorState({
      currentState: initialNode?.data.label || null,
      history: initialNode ? [initialNode.data.label] : [],
      eventHistory: [],
      isRunning: true,
      lastEvent: null,
    });
  }, [simulator.eventHistory, service, initialNode, setSimulatorState]);

  const handleStopReplay = useCallback(() => {
    setIsReplaying(false);
  }, []);

  const handleStepBack = useCallback(() => {
    if (replayIndex > 0) {
      const newIndex = replayIndex - 1;
      setReplayIndex(newIndex);
      const state = newIndex >= 0 ? simulator.eventHistory[newIndex].to : initialNode?.data.label;
      setSimulatorState({
        currentState: state || null,
        lastEvent: newIndex >= 0 ? simulator.eventHistory[newIndex].event : null,
      });
    } else if (replayIndex === 0) {
      setReplayIndex(-1);
      setSimulatorState({
        currentState: initialNode?.data.label || null,
        lastEvent: null,
      });
    }
  }, [replayIndex, simulator.eventHistory, initialNode, setSimulatorState]);

  const handleStepForward = useCallback(() => {
    if (replayIndex < simulator.eventHistory.length - 1) {
      const newIndex = replayIndex + 1;
      setReplayIndex(newIndex);
      setSimulatorState({
        currentState: simulator.eventHistory[newIndex].to,
        lastEvent: simulator.eventHistory[newIndex].event,
      });
    }
  }, [replayIndex, simulator.eventHistory, setSimulatorState]);

  useEffect(() => {
    if (!isReplaying) return;
    if (replayIndex >= simulator.eventHistory.length - 1) {
      setIsReplaying(false);
      return;
    }

    const timer = setTimeout(() => {
      const newIndex = replayIndex + 1;
      setReplayIndex(newIndex);
      setSimulatorState({
        currentState: simulator.eventHistory[newIndex].to,
        lastEvent: simulator.eventHistory[newIndex].event,
      });
    }, replaySpeed);

    return () => clearTimeout(timer);
  }, [isReplaying, replayIndex, simulator.eventHistory, replaySpeed, setSimulatorState]);

  const handleSendEvent = useCallback(
    (eventName: string, targetState: string) => {
      if (!service || !simulator.currentState) return;

      try {
        setAnimatingEvent(eventName);
        service.send({ type: eventName });
        const nextState = service.getSnapshot().value as string;
        if (nextState) {
          const eventRecord: EventRecord = {
            event: eventName,
            from: simulator.currentState,
            to: nextState,
            timestamp: Date.now(),
          };
          setSimulatorState({
            currentState: nextState,
            history: [...simulator.history, nextState],
            eventHistory: [...simulator.eventHistory, eventRecord],
            lastEvent: eventName,
          });
        }
        setTimeout(() => setAnimatingEvent(null), 300);
      } catch (error) {
        console.error('State transition error:', error);
        setAnimatingEvent(null);
      }
    },
    [service, simulator.currentState, simulator.history, simulator.eventHistory, setSimulatorState]
  );

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 p-6">
        <CircleDot size={48} className="mb-4 opacity-50" />
        <p className="text-sm text-center">请先添加状态节点</p>
        <p className="text-xs mt-2 text-center">以进行状态机模拟</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-2">
          <Activity size={16} className={cn('text-amber-400', simulator.isRunning && 'animate-pulse')} />
          <span className="text-xs font-medium text-slate-300">状态机模拟</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleStart}
            disabled={!machine}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play size={12} />
            开始
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors"
          >
            <RotateCcw size={12} />
            重置
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-2">当前状态</label>
          <div
            className={cn(
              'px-4 py-3 rounded-lg border text-sm font-semibold transition-all duration-300',
              (simulator.isRunning || isReplaying) && simulator.currentState
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400 shadow-lg shadow-emerald-500/20'
                : 'bg-slate-800 border-slate-700 text-slate-500'
            )}
          >
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  'w-3 h-3 rounded-full',
                  simulator.isRunning || isReplaying ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                )}
              />
              <span>{simulator.currentState || '未启动'}</span>
              {isReplaying && (
                <span className="ml-auto text-xs text-amber-400">
                  回放 {replayIndex + 1}/{simulator.eventHistory.length}
                </span>
              )}
            </div>
          </div>
        </div>

        {simulator.lastEvent && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
            <Zap size={14} className="text-cyan-400" />
            <span className="text-xs text-cyan-400 font-mono">触发: {simulator.lastEvent}</span>
          </div>
        )}

        {simulator.isRunning && availableEvents.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">可触发事件</label>
            <div className="space-y-2">
              {availableEvents.map((event, index) => (
                <button
                  key={index}
                  onClick={() => handleSendEvent(event.name, event.target)}
                  disabled={animatingEvent === event.name}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2.5 rounded-lg border transition-all duration-200 group',
                    animatingEvent === event.name
                      ? 'bg-cyan-500/20 border-cyan-500 scale-95'
                      : 'bg-slate-800 border-slate-700 hover:border-cyan-500 hover:bg-slate-700/50'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-md bg-slate-700 group-hover:bg-cyan-500/20 flex items-center justify-center transition-colors">
                      <Zap size={12} className="text-slate-400 group-hover:text-cyan-400" />
                    </div>
                    <span className="text-sm text-slate-200 font-mono">{event.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <ArrowRight size={12} className="text-slate-500 group-hover:text-cyan-400" />
                    <span className="text-xs text-slate-500 group-hover:text-cyan-400">{event.target}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {simulator.eventHistory.length > 0 && !isReplaying && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">
              <History size={12} className="inline mr-1" />
              事件历史 ({simulator.eventHistory.length})
            </label>
            <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-3 max-h-48 overflow-y-auto">
              <div className="space-y-2">
                {[...simulator.eventHistory].reverse().map((record, index) => (
                  <div
                    key={index}
                    className={cn(
                      'flex items-center gap-2 text-xs p-2 rounded transition-colors',
                      index === 0 ? 'bg-cyan-500/10' : 'hover:bg-slate-700/30'
                    )}
                  >
                    <div className="w-6 h-6 rounded-md bg-slate-700 flex items-center justify-center flex-shrink-0">
                      <Clock size={10} className="text-slate-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 font-mono">
                        <span className="text-slate-400 truncate">{record.from}</span>
                        <span className="text-cyan-400">→</span>
                        <span className="text-emerald-400 truncate">{record.to}</span>
                      </div>
                      <div className="text-slate-500 mt-0.5">
                        <span className="text-amber-400/70">{record.event}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {simulator.eventHistory.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">
              <History size={12} className="inline mr-1" />
              历史回放
            </label>
            <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleStepBack}
                    disabled={replayIndex < 0}
                    className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <SkipBack size={16} />
                  </button>
                  <button
                    onClick={isReplaying ? handleStopReplay : handleStartReplay}
                    disabled={!simulator.eventHistory.length}
                    className="p-2 rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    {isReplaying ? <Pause size={16} /> : <Play size={16} />}
                  </button>
                  <button
                    onClick={handleStepForward}
                    disabled={replayIndex >= simulator.eventHistory.length - 1}
                    className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <SkipForward size={16} />
                  </button>
                </div>
                <select
                  value={replaySpeed}
                  onChange={(e) => setReplaySpeed(Number(e.target.value))}
                  className="text-xs bg-slate-700 text-slate-300 rounded px-2 py-1 border border-slate-600"
                >
                  <option value={2000}>0.5x</option>
                  <option value={1000}>1x</option>
                  <option value={500}>2x</option>
                  <option value={250}>4x</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 transition-all duration-300"
                    style={{ width: `${((replayIndex + 1) / simulator.eventHistory.length) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-slate-500 w-12 text-right">
                  {replayIndex + 1}/{simulator.eventHistory.length}
                </span>
              </div>
            </div>
          </div>
        )}

        {simulator.isRunning && availableEvents.length === 0 && (
          <div className="text-center py-6 text-slate-500">
            <p className="text-sm">状态机已到达终止状态</p>
            <p className="text-xs mt-1">点击重置按钮重新开始</p>
          </div>
        )}
      </div>
    </div>
  );
};
