import { OrbitControls } from '@react-three/drei'
import { useRef, useEffect } from 'react'
import * as THREE from 'three'

export default function Controls() {
  const controlsRef = useRef()

  useEffect(() => {
    if (controlsRef.current) {
      const controls = controlsRef.current
      const initialTarget = new THREE.Vector3(0, 0.25, 0)
      controls.target.copy(initialTarget)
      controls.enablePan = false
      controls.enableZoom = true
      controls.enableRotate = true
      controls.minDistance = 2.5
      controls.maxDistance = 10
      controls.minPolarAngle = Math.PI / 6
      controls.maxPolarAngle = Math.PI / 2
      controls.enableDamping = true
      controls.dampingFactor = 0.05
      controls.update()
    }
  }, [])

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enablePan={false}
      minDistance={2.5}
      maxDistance={10}
      minPolarAngle={Math.PI / 6}
      maxPolarAngle={Math.PI / 2}
      enableDamping
      dampingFactor={0.05}
    />
  )
}
