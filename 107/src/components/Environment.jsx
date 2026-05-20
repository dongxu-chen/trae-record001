import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Float, Grid } from '@react-three/drei'

const Environment = () => {
  const gridRef = useRef()

  useFrame((state) => {
    if (gridRef.current) {
      gridRef.current.material.opacity = 0.1 + Math.sin(state.clock.elapsedTime * 0.5) * 0.05
    }
  })

  return (
    <>
      <Float speed={1} rotationIntensity={0.1} floatIntensity={0.5}>
        <mesh position={[5, 3, -5]}>
          <icosahedronGeometry args={[0.5, 1]} />
          <meshStandardMaterial
            color="#00d2ff"
            wireframe
            transparent
            opacity={0.3}
          />
        </mesh>
      </Float>

      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.3}>
        <mesh position={[-5, 2, -3]}>
          <octahedronGeometry args={[0.4, 0]} />
          <meshStandardMaterial
            color="#3a7bd5"
            wireframe
            transparent
            opacity={0.4}
          />
        </mesh>
      </Float>

      <Float speed={0.8} rotationIntensity={0.15} floatIntensity={0.4}>
        <mesh position={[4, -1, 5]}>
          <torusGeometry args={[0.4, 0.1, 16, 48]} />
          <meshStandardMaterial
            color="#00d2ff"
            wireframe
            transparent
            opacity={0.35}
          />
        </mesh>
      </Float>

      <Grid
        ref={gridRef}
        args={[20, 20]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor="#00d2ff"
        sectionSize={2}
        sectionThickness={1}
        sectionColor="#3a7bd5"
        fadeDistance={25}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
        position={[0, -1.5, 0]}
      />
    </>
  )
}

export default Environment
