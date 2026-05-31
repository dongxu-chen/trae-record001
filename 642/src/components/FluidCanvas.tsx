import { useFluidSimulation } from '@/hooks/useFluidSimulation'
import { useSimulationStore } from '@/store/useSimulationStore'
import { useEffect, useRef } from 'react'
import type { SceneType } from '@/types'

interface FluidCanvasProps {
  onCanvasReady?: (canvas: HTMLCanvasElement | null) => void
}

export function FluidCanvas({ onCanvasReady }: FluidCanvasProps) {
  const { isPlaying, resolution, currentScene } = useSimulationStore((state) => state.simulation)
  const fluidParams = useSimulationStore((state) => state.fluidParams)
  const forceFields = useSimulationStore((state) => state.forceFields)
  const colorZones = useSimulationStore((state) => state.colorZones)
  const emitters = useSimulationStore((state) => state.emitters)

  const lastSceneRef = useRef<SceneType>(currentScene)

  const { containerRef, setPlaying, reset, getCanvas, updateSceneData } = useFluidSimulation({
    resolution,
    transparency: fluidParams.transparency,
  })

  useEffect(() => {
    setPlaying(isPlaying)
  }, [isPlaying, setPlaying])

  useEffect(() => {
    if (onCanvasReady) {
      onCanvasReady(getCanvas())
    }
  }, [getCanvas, onCanvasReady])

  useEffect(() => {
    if (currentScene !== lastSceneRef.current) {
      lastSceneRef.current = currentScene
      reset()
    }
  }, [currentScene, reset])

  useEffect(() => {
    updateSceneData({
      forceFields,
      colorZones,
      emitters,
    })
  }, [forceFields, colorZones, emitters, updateSceneData])

  useEffect(() => {
    if (!isPlaying) {
      reset()
    }
  }, [resolution, isPlaying, reset])

  return (
    <div
      ref={containerRef}
      className="w-full h-full cursor-crosshair"
      style={{ background: 'linear-gradient(135deg, #0A1628 0%, #0d1f35 100%)' }}
    />
  )
}
