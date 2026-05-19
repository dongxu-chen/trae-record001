import { useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'

const Hotspot = ({ position, label, icon, onClick, isActive }) => {
  const groupRef = useRef()
  const [hovered, setHovered] = useState(false)

  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.lookAt(state.camera.position)
    }
  })

  return (
    <group ref={groupRef} position={position}>
      <Html transform zIndexRange={[100, 0]} distanceFactor={10}>
        <div
          onClick={onClick}
          onPointerEnter={() => setHovered(true)}
          onPointerLeave={() => setHovered(false)}
          style={{
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: isActive
              ? 'linear-gradient(135deg, #00d2ff, #3a7bd5)'
              : hovered
                ? 'rgba(0, 210, 255, 0.3)'
                : 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(10px)',
            padding: '8px 16px',
            borderRadius: '20px',
            border: `2px solid ${isActive ? '#00d2ff' : hovered ? '#00d2ff' : 'rgba(255, 255, 255, 0.2)'}`,
            color: 'white',
            fontSize: '14px',
            fontWeight: 600,
            whiteSpace: 'nowrap',
            boxShadow: isActive
              ? '0 0 20px rgba(0, 210, 255, 0.5)'
              : hovered
                ? '0 4px 15px rgba(0, 210, 255, 0.3)'
                : '0 2px 10px rgba(0, 0, 0, 0.3)',
            transform: hovered ? 'scale(1.1)' : 'scale(1)',
            transition: 'all 0.3s ease',
            userSelect: 'none',
            touchAction: 'none',
            pointerEvents: 'auto'
          }}
        >
          <span style={{ fontSize: '18px' }}>{icon || '📍'}</span>
          <span>{label}</span>
        </div>
      </Html>

      <mesh position={[0, 0, -0.1]}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshBasicMaterial
          color={isActive ? '#00d2ff' : hovered ? '#3a7bd5' : '#ffffff'}
          transparent
          opacity={0.8}
        />
      </mesh>

      <mesh position={[0, 0, -0.05]}>
        <ringGeometry args={[0.08, 0.12, 32]} />
        <meshBasicMaterial
          color={isActive ? '#00d2ff' : '#ffffff'}
          transparent
          opacity={0.5}
          side={2}
        />
      </mesh>
    </group>
  )
}

export default Hotspot
