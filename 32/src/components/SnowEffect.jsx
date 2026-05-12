import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export default function SnowEffect({ count = 2000, enabled = true }) {
  const pointsRef = useRef()
  
  const { positions, velocities } = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const velocities = new Float32Array(count)
    
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 20
      positions[i * 3 + 1] = Math.random() * 10
      positions[i * 3 + 2] = (Math.random() - 0.5) * 20
      velocities[i] = 0.02 + Math.random() * 0.03
    }
    
    return { positions, velocities }
  }, [count])
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    return geo
  }, [positions])
  
  const material = useMemo(() => {
    return new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.05,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    })
  }, [])
  
  useFrame(() => {
    if (!enabled || !pointsRef.current) return
    
    const positions = pointsRef.current.geometry.attributes.position.array
    
    for (let i = 0; i < count; i++) {
      positions[i * 3 + 1] -= velocities[i]
      positions[i * 3] += Math.sin(Date.now() * 0.001 + i) * 0.002
      positions[i * 3 + 2] += Math.cos(Date.now() * 0.0015 + i) * 0.001
      
      if (positions[i * 3 + 1] < -3) {
        positions[i * 3] = (Math.random() - 0.5) * 20
        positions[i * 3 + 1] = 10
        positions[i * 3 + 2] = (Math.random() - 0.5) * 20
      }
    }
    
    pointsRef.current.geometry.attributes.position.needsUpdate = true
  })
  
  useEffect(() => {
    if (pointsRef.current) {
      pointsRef.current.visible = enabled
    }
  }, [enabled])
  
  if (!enabled) return null
  
  return (
    <points ref={pointsRef} geometry={geometry} material={material} />
  )
}
