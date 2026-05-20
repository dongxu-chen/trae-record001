import { useRef, useEffect, useState } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const animationConfigs = {
  rotate360: {
    duration: 8000,
    easing: 'easeInOut',
    animate: (progress, camera, data) => {
      const angle = progress * Math.PI * 2
      camera.position.x = Math.cos(angle) * data.radius
      camera.position.z = Math.sin(angle) * data.radius
      camera.position.y = 3
      camera.lookAt(0, 0, 0)
    },
    setup: (camera) => ({
      radius: camera.position.length()
    })
  },
  zoomIn: {
    duration: 2000,
    easing: 'easeOut',
    animate: (progress, camera, data) => {
      camera.position.lerpVectors(data.startPos, data.targetPos, progress)
      camera.lookAt(0, 0, 0)
    },
    setup: (camera) => ({
      startPos: camera.position.clone(),
      targetPos: new THREE.Vector3(1.5, 1.5, 1.5)
    })
  },
  orbit: {
    duration: 5000,
    easing: 'easeInOut',
    animate: (progress, camera, data) => {
      const angle = data.startAngle + progress * Math.PI
      const height = 3 + Math.sin(progress * Math.PI * 2) * 1
      camera.position.x = Math.cos(angle) * data.startRadius
      camera.position.z = Math.sin(angle) * data.startRadius
      camera.position.y = height
      camera.lookAt(0, 0, 0)
    },
    setup: (camera) => ({
      startAngle: Math.atan2(camera.position.z, camera.position.x),
      startRadius: new THREE.Vector2(camera.position.x, camera.position.z).length()
    })
  },
  flyAround: {
    duration: 6000,
    easing: 'easeInOut',
    animate: (progress, camera) => {
      const angle = progress * Math.PI * 1.5
      const radius = 5 + Math.sin(progress * Math.PI * 3) * 1
      const height = 2 + Math.sin(progress * Math.PI * 2) * 2
      camera.position.x = Math.cos(angle) * radius
      camera.position.z = Math.sin(angle) * radius
      camera.position.y = height
      camera.lookAt(0, 0, 0)
    },
    setup: () => ({})
  },
  topDown: {
    duration: 3000,
    easing: 'easeOut',
    animate: (progress, camera, data) => {
      camera.position.lerpVectors(data.startPos, data.targetPos, progress)
      camera.lookAt(0, 0, 0)
    },
    setup: (camera) => ({
      startPos: camera.position.clone(),
      targetPos: new THREE.Vector3(0, 8, 0.01)
    })
  },
  closeUp: {
    duration: 2500,
    easing: 'easeOut',
    animate: (progress, camera, data) => {
      camera.position.lerpVectors(data.startPos, data.targetPos, progress)
      camera.lookAt(0, 0.5, 0)
    },
    setup: (camera) => ({
      startPos: camera.position.clone(),
      targetPos: new THREE.Vector3(0.8, 1, 2)
    })
  }
}

const easingFunctions = {
  linear: (t) => t,
  easeIn: (t) => t * t,
  easeOut: (t) => 1 - (1 - t) * (1 - t),
  easeInOut: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)
}

const CameraAnimation = ({ animation, isPlaying, onComplete, controlsRef }) => {
  const { camera } = useThree()
  const animationRef = useRef({
    startTime: null,
    data: null,
    isPlaying: false
  })

  useEffect(() => {
    if (isPlaying && animation && animationConfigs[animation]) {
      animationRef.current.startTime = performance.now()
      animationRef.current.data = animationConfigs[animation].setup(camera)
      animationRef.current.isPlaying = true

      if (controlsRef.current) {
        controlsRef.current.enabled = false
      }
    }
  }, [isPlaying, animation, camera, controlsRef])

  useFrame(() => {
    if (!animationRef.current.isPlaying) return

    const config = animationConfigs[animation]
    if (!config) return

    const elapsed = performance.now() - animationRef.current.startTime
    const rawProgress = Math.min(elapsed / config.duration, 1)
    const easedProgress = easingFunctions[config.easing](rawProgress)

    config.animate(easedProgress, camera, animationRef.current.data)

    if (controlsRef.current) {
      controlsRef.current.update()
    }

    if (rawProgress >= 1) {
      animationRef.current.isPlaying = false
      if (controlsRef.current) {
        controlsRef.current.enabled = true
      }
      onComplete?.()
    }
  })

  return null
}

export default CameraAnimation
