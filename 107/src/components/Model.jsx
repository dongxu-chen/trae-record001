import { useRef, useEffect, Suspense } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { useGLTF, Center, useProgress } from '@react-three/drei'

export const modelConfigs = {
  helmet: {
    url: 'https://threejs.org/examples/models/gltf/DamagedHelmet/glTF/DamagedHelmet.gltf',
    scale: 2,
    name: '头盔模型'
  },
  duck: {
    url: 'https://threejs.org/examples/models/gltf/Duck/glTF/Duck.gltf',
    scale: 3,
    name: '小黄鸭'
  },
  avocado: {
    url: 'https://threejs.org/examples/models/gltf/Avocado/glTF/Avocado.gltf',
    scale: 0.5,
    name: '牛油果'
  },
  torus: {
    url: null,
    scale: 1,
    name: '环形结'
  }
}

const HelmetModel = ({ materialProps, meshesRef }) => {
  const { scene } = useGLTF(modelConfigs.helmet.url)

  useEffect(() => {
    const meshes = []
    scene.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
        meshes.push(child)
      }
    })
    meshesRef.current = meshes
  }, [scene, meshesRef])

  return (
    <Center>
      <primitive object={scene} scale={modelConfigs.helmet.scale} />
    </Center>
  )
}

const DuckModel = ({ materialProps, meshesRef }) => {
  const { scene } = useGLTF(modelConfigs.duck.url)

  useEffect(() => {
    const meshes = []
    scene.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
        meshes.push(child)
      }
    })
    meshesRef.current = meshes
  }, [scene, meshesRef])

  return (
    <Center>
      <primitive object={scene} scale={modelConfigs.duck.scale} />
    </Center>
  )
}

const AvocadoModel = ({ materialProps, meshesRef }) => {
  const { scene } = useGLTF(modelConfigs.avocado.url)

  useEffect(() => {
    const meshes = []
    scene.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
        meshes.push(child)
      }
    })
    meshesRef.current = meshes
  }, [scene, meshesRef])

  return (
    <Center>
      <primitive object={scene} scale={modelConfigs.avocado.scale} />
    </Center>
  )
}

const TorusModel = ({ materialProps, meshesRef }) => {
  const meshRef = useRef()

  useEffect(() => {
    if (meshRef.current) {
      meshesRef.current = [meshRef.current]
    }
  }, [meshesRef])

  return (
    <mesh ref={meshRef} castShadow receiveShadow>
      <torusKnotGeometry args={[1, 0.3, 128, 32]} />
      <meshStandardMaterial
        color={materialProps.color}
        metalness={materialProps.metalness}
        roughness={materialProps.roughness}
        envMapIntensity={materialProps.envMapIntensity}
      />
    </mesh>
  )
}

const LoadingIndicator = () => {
  const { progress } = useProgress()

  return (
    <group position={[0, -2, 0]}>
      <mesh>
        <boxGeometry args={[2, 0.1, 0.1]} />
        <meshBasicMaterial color="#333" />
      </mesh>
      <mesh position={[-(1 - progress / 100), 0, 0]}>
        <boxGeometry args={[(progress / 100) * 2, 0.15, 0.15]} />
        <meshBasicMaterial color="#00d2ff" />
      </mesh>
    </group>
  )
}

const ModelContent = ({ modelType, materialProps, meshesRef }) => {
  const groupRef = useRef()

  useEffect(() => {
    meshesRef.current.forEach((mesh) => {
      if (mesh.material) {
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        materials.forEach((mat) => {
          if (mat.color) mat.color.set(materialProps.color)
          if (typeof mat.metalness === 'number') mat.metalness = materialProps.metalness
          if (typeof mat.roughness === 'number') mat.roughness = materialProps.roughness
          if (typeof mat.envMapIntensity === 'number')
            mat.envMapIntensity = materialProps.envMapIntensity
          mat.needsUpdate = true
        })
      }
    })
  }, [materialProps, meshesRef])

  useFrame((state, delta) => {
    if (groupRef.current) {
    }
  })

  const ModelComponent = {
    helmet: HelmetModel,
    duck: DuckModel,
    avocado: AvocadoModel,
    torus: TorusModel
  }[modelType] || HelmetModel

  return (
    <group ref={groupRef}>
      <ModelComponent materialProps={materialProps} meshesRef={meshesRef} />
    </group>
  )
}

const Model = ({ modelType, materialProps, onLoadComplete }) => {
  const meshesRef = useRef([])

  return (
    <Suspense fallback={<LoadingIndicator />}>
      <ModelContent
        modelType={modelType}
        materialProps={materialProps}
        meshesRef={meshesRef}
      />
    </Suspense>
  )
}

export default Model
