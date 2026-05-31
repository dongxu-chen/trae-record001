import { useRef, useEffect, useCallback } from 'react'
import * as THREE from 'three'
import { GPGPU, FluidSolver } from '@/utils/gpgpu'
import { useSimulationStore } from '@/store/useSimulationStore'
import type { ForceField, ColorZone, Emitter, Vector2 } from '@/types'

import vertexShader from '@/shaders/fluidSim.vert?raw'
import semiLagrangianAdvectionShader from '@/shaders/semiLagrangianAdvection.frag?raw'
import divergenceShader from '@/shaders/divergence.frag?raw'
import pressureShader from '@/shaders/pressure.frag?raw'
import gradientShader from '@/shaders/gradient.frag?raw'
import splatShader from '@/shaders/splat.frag?raw'
import vorticityShader from '@/shaders/vorticity.frag?raw'
import vorticityConfinementShader from '@/shaders/vorticityConfinement.frag?raw'
import applyForceShader from '@/shaders/applyForce.frag?raw'
import applyColorZonesShader from '@/shaders/applyColorZones.frag?raw'
import emitParticlesShader from '@/shaders/emitParticles.frag?raw'
import volumeRenderShader from '@/shaders/volumeRender.frag?raw'

interface UseFluidSimulationOptions {
  resolution?: number
  color?: THREE.Color
  transparency?: number
  fixedTimeStep?: number
}

export function useFluidSimulation(options: UseFluidSimulationOptions = {}) {
  const {
    resolution = 256,
    color = new THREE.Color(0, 0.96, 1),
    transparency = 0.7,
    fixedTimeStep = 1 / 60,
  } = options

  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null)
  const fluidSolverRef = useRef<FluidSolver | null>(null)
  const renderMaterialRef = useRef<THREE.ShaderMaterial | null>(null)
  const animationIdRef = useRef<number>(0)
  const isPlayingRef = useRef(true)
  const mouseRef = useRef({ x: 0, y: 0, lastX: 0, lastY: 0, down: false })
  const timeRef = useRef(0)
  const accumulatorRef = useRef(0)
  const lastTimeRef = useRef(0)
  const fixedTimeStepRef = useRef(fixedTimeStep)

  const storeUnsubscribeRef = useRef<() => void | null>(null)

  const init = useCallback(() => {
    if (!containerRef.current) return

    const width = containerRef.current.clientWidth
    const height = containerRef.current.clientHeight

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
      powerPreference: 'high-performance',
    })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x0a1628, 1)
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const scene = new THREE.Scene()
    sceneRef.current = scene

    const camera = new THREE.OrthographicCamera(-0.5, 0.5, 0.5, -0.5, 0.01, 100)
    camera.position.z = 1
    cameraRef.current = camera

    const gpgpu = new GPGPU({
      width: resolution,
      height: resolution,
      renderer,
    })

    const shaders = {
      advection: semiLagrangianAdvectionShader,
      divergence: divergenceShader,
      pressure: pressureShader,
      gradient: gradientShader,
      splat: splatShader,
      vorticity: vorticityShader,
      vorticityConfinement: vorticityConfinementShader,
      applyForce: applyForceShader,
      applyColorZones: applyColorZonesShader,
      emitParticles: emitParticlesShader,
    }

    const fluidSolver = new FluidSolver(gpgpu, vertexShader, shaders)
    fluidSolverRef.current = fluidSolver

    const renderMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader: volumeRenderShader,
      uniforms: {
        uFluidData: { value: null },
        uColor: { value: color },
        uTransparency: { value: transparency },
        uLightPos: { value: new THREE.Vector3(0.5, 0.5, 0) },
        uResolution: { value: new THREE.Vector2(width, height) },
        uTime: { value: 0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    renderMaterialRef.current = renderMaterial

    const quad = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), renderMaterial)
    scene.add(quad)

    const state = useSimulationStore.getState()
    fluidSolver.setForceFields(state.forceFields)
    fluidSolver.setColorZones(state.colorZones)
    fluidSolver.setEmitters(state.emitters)
    fluidSolver.setVorticityScale(state.fluidParams.vorticityScale)
    fluidSolver.setVelocityDissipation(state.fluidParams.velocityDissipation)
    fluidSolver.setPressureIterations(state.fluidParams.pressureIterations)

    for (let i = 0; i < 8; i++) {
      const x = Math.random() * resolution
      const y = Math.random() * resolution
      const splatColor = new THREE.Color().setHSL(Math.random() * 0.2 + 0.5, 1, 0.5)
      fluidSolver.splat(new THREE.Vector2(x, y), splatColor, 1000)
    }

    storeUnsubscribeRef.current = useSimulationStore.subscribe(
      (state) => state,
      (state) => {
        if (fluidSolverRef.current) {
          fluidSolverRef.current.setForceFields(state.forceFields)
          fluidSolverRef.current.setColorZones(state.colorZones)
          fluidSolverRef.current.setEmitters(state.emitters)
          fluidSolverRef.current.setVorticityScale(state.fluidParams.vorticityScale)
          fluidSolverRef.current.setVelocityDissipation(state.fluidParams.velocityDissipation)
          fluidSolverRef.current.setPressureIterations(state.fluidParams.pressureIterations)
        }
        if (renderMaterialRef.current) {
          renderMaterialRef.current.uniforms.uTransparency.value = state.fluidParams.transparency
        }
      }
    )

    const handleResize = () => {
      if (!containerRef.current || !renderer) return
      const w = containerRef.current.clientWidth
      const h = containerRef.current.clientHeight
      renderer.setSize(w, h)
      if (renderMaterial) {
        renderMaterial.uniforms.uResolution.value.set(w, h)
      }
    }

    window.addEventListener('resize', handleResize)

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const newX = ((e.clientX - rect.left) / rect.width) * resolution
      const newY = ((1 - (e.clientY - rect.top) / rect.height)) * resolution

      mouseRef.current.lastX = mouseRef.current.x
      mouseRef.current.lastY = mouseRef.current.y
      mouseRef.current.x = newX
      mouseRef.current.y = newY

      const state = useSimulationStore.getState()
      state.setMouseForcePosition(
        { x: newX, y: newY },
        { x: mouseRef.current.lastX, y: mouseRef.current.lastY }
      )
    }

    const handleMouseDown = () => {
      mouseRef.current.down = true
      const state = useSimulationStore.getState()
      state.updateMouseForce({ enabled: true })
    }

    const handleMouseUp = () => {
      mouseRef.current.down = false
      const state = useSimulationStore.getState()
      state.updateMouseForce({ enabled: false })
    }

    const handleMouseLeave = () => {
      mouseRef.current.down = false
      const state = useSimulationStore.getState()
      state.updateMouseForce({ enabled: false })
    }

    containerRef.current.addEventListener('mousemove', handleMouseMove)
    containerRef.current.addEventListener('mousedown', handleMouseDown)
    containerRef.current.addEventListener('mouseup', handleMouseUp)
    containerRef.current.addEventListener('mouseleave', handleMouseLeave)

    lastTimeRef.current = performance.now() / 1000

    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)

      const currentTime = performance.now() / 1000
      const frameTime = currentTime - lastTimeRef.current
      lastTimeRef.current = currentTime

      if (isPlayingRef.current && fluidSolver) {
        accumulatorRef.current += frameTime

        while (accumulatorRef.current >= fixedTimeStepRef.current) {
          const state = useSimulationStore.getState()

          if (state.mouseForce.enabled) {
            const dx = state.mouseForce.position.x - state.mouseForce.lastPosition.x
            const dy = state.mouseForce.position.y - state.mouseForce.lastPosition.y
            const dist = Math.sqrt(dx * dx + dy * dy)

            if (dist > 0.1) {
              const direction: Vector2 = { x: dx / dist, y: dy / dist }
              const strength = Math.min(dist * state.mouseForce.strength, 30)

              fluidSolver.applyForce(
                state.mouseForce.position,
                direction,
                strength,
                state.mouseForce.radius,
                timeRef.current
              )

              const mouseColor = new THREE.Color().setHSL(
                0.55 + Math.sin(timeRef.current) * 0.1,
                1,
                0.6
              )
              fluidSolver.splat(
                new THREE.Vector2(state.mouseForce.position.x, state.mouseForce.position.y),
                mouseColor,
                600
              )
            }
          }

          fluidSolver.step(fixedTimeStepRef.current, timeRef.current)
          accumulatorRef.current -= fixedTimeStepRef.current
        }

        timeRef.current += frameTime

        if (renderMaterial) {
          renderMaterial.uniforms.uFluidData.value = fluidSolver.getDensityTexture()
          renderMaterial.uniforms.uTime.value = timeRef.current
        }
      }

      renderer.render(scene, camera)
    }

    animate()

    return () => {
      window.removeEventListener('resize', handleResize)
      if (containerRef.current) {
        containerRef.current.removeEventListener('mousemove', handleMouseMove)
        containerRef.current.removeEventListener('mousedown', handleMouseDown)
        containerRef.current.removeEventListener('mouseup', handleMouseUp)
        containerRef.current.removeEventListener('mouseleave', handleMouseLeave)
      }
      if (storeUnsubscribeRef.current) {
        storeUnsubscribeRef.current()
      }
      cancelAnimationFrame(animationIdRef.current)
      fluidSolver.dispose()
      renderMaterial.dispose()
      renderer.dispose()
    }
  }, [resolution, color, transparency, fixedTimeStep])

  useEffect(() => {
    const cleanup = init()
    return cleanup
  }, [init])

  const setPlaying = useCallback((playing: boolean) => {
    isPlayingRef.current = playing
    if (playing) {
      lastTimeRef.current = performance.now() / 1000
    }
  }, [])

  const reset = useCallback(() => {
    if (fluidSolverRef.current) {
      const state = useSimulationStore.getState()
      fluidSolverRef.current.setForceFields(state.forceFields)
      fluidSolverRef.current.setColorZones(state.colorZones)
      fluidSolverRef.current.setEmitters(state.emitters)

      for (let i = 0; i < 8; i++) {
        const x = Math.random() * resolution
        const y = Math.random() * resolution
        const splatColor = new THREE.Color().setHSL(Math.random() * 0.2 + 0.5, 1, 0.5)
        fluidSolverRef.current.splat(new THREE.Vector2(x, y), splatColor, 1000)
      }
    }
  }, [resolution])

  const splat = useCallback((x: number, y: number, color?: THREE.Color, radius?: number) => {
    if (fluidSolverRef.current) {
      const splatColor = color || new THREE.Color().setHSL(0.55 + Math.random() * 0.1, 1, 0.6)
      fluidSolverRef.current.splat(new THREE.Vector2(x, y), splatColor, radius || 800)
    }
  }, [])

  const getCanvas = useCallback(() => {
    return rendererRef.current?.domElement || null
  }, [])

  const setFixedTimeStep = useCallback((dt: number) => {
    fixedTimeStepRef.current = dt
  }, [])

  const applyForce = useCallback(
    (position: Vector2, direction: Vector2, strength: number, radius: number, time: number) => {
      if (fluidSolverRef.current) {
        fluidSolverRef.current.applyForce(position, direction, strength, radius, time)
      }
    },
    []
  )

  const updateSceneData = useCallback(
    (data: {
      forceFields?: ForceField[]
      colorZones?: ColorZone[]
      emitters?: Emitter[]
    }) => {
      if (fluidSolverRef.current) {
        if (data.forceFields) fluidSolverRef.current.setForceFields(data.forceFields)
        if (data.colorZones) fluidSolverRef.current.setColorZones(data.colorZones)
        if (data.emitters) fluidSolverRef.current.setEmitters(data.emitters)
      }
    },
    []
  )

  return {
    containerRef,
    setPlaying,
    reset,
    splat,
    getCanvas,
    setFixedTimeStep,
    applyForce,
    updateSceneData,
  }
}
