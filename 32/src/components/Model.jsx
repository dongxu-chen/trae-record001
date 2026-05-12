import { useGLTF, Center, useProgress } from '@react-three/drei'
import { useEffect, useMemo, useRef } from 'react'
import useStore, { materialPresets } from '../store/store'
import { getMetalnessMap } from '../utils/textureGenerators'
import * as THREE from 'three'

function applyMaterialToScene(scene, color, materialPreset, metalnessMapType) {
  const metalnessMap = getMetalnessMap(metalnessMapType)
  
  scene.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true
      child.receiveShadow = true
      
      if (child.geometry) {
        child.geometry.computeVertexNormals()
        if (child.geometry.attributes.normal) {
          child.geometry.normalizeNormals()
        }
      }
      
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((mat, index) => {
            if (!mat.isMeshStandardMaterial) {
              const newMat = new THREE.MeshStandardMaterial({
                color: color,
                metalness: materialPreset.metalness,
                roughness: materialPreset.roughness,
                metalnessMap: metalnessMap,
              })
              child.material[index] = newMat
            } else {
              mat.color.set(color)
              mat.metalness = materialPreset.metalness
              mat.roughness = materialPreset.roughness
              mat.metalnessMap = metalnessMap
            }
            child.material[index].needsUpdate = true
          })
        } else {
          const mat = child.material
          if (!mat.isMeshStandardMaterial) {
            child.material = new THREE.MeshStandardMaterial({
              color: color,
              metalness: materialPreset.metalness,
              roughness: materialPreset.roughness,
              metalnessMap: metalnessMap,
            })
          } else {
            mat.color.set(color)
            mat.metalness = materialPreset.metalness
            mat.roughness = materialPreset.roughness
            mat.metalnessMap = metalnessMap
          }
          child.material.needsUpdate = true
        }
      }
    }
  })
}

function GltfModel({ url }) {
  const color = useStore((state) => state.color)
  const materialType = useStore((state) => state.materialType)
  const metalnessMapType = useStore((state) => state.metalnessMapType)
  const gltf = useGLTF(url)

  const materialPreset = useMemo(
    () => materialPresets.find((m) => m.id === materialType) || materialPresets[1],
    [materialType]
  )

  useEffect(() => {
    if (gltf && gltf.scene) {
      applyMaterialToScene(gltf.scene, color, materialPreset, metalnessMapType)
    }
  }, [gltf, color, materialPreset, metalnessMapType])

  return (
    <Center>
      <primitive object={gltf.scene} />
    </Center>
  )
}

function FallbackModel() {
  const color = useStore((state) => state.color)
  const materialType = useStore((state) => state.materialType)
  const metalnessMapType = useStore((state) => state.metalnessMapType)

  const materialPreset = useMemo(
    () => materialPresets.find((m) => m.id === materialType) || materialPresets[1],
    [materialType]
  )
  
  const metalnessMap = useMemo(
    () => getMetalnessMap(metalnessMapType),
    [metalnessMapType]
  )

  return (
    <group>
      <mesh castShadow receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[1.5, 0.8, 1.5]} />
        <meshStandardMaterial
          color={color}
          metalness={materialPreset.metalness}
          roughness={materialPreset.roughness}
          metalnessMap={metalnessMap}
        />
      </mesh>
      <mesh castShadow receiveShadow position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.3, 0.3, 0.6, 32]} />
        <meshStandardMaterial
          color={color}
          metalness={materialPreset.metalness}
          roughness={materialPreset.roughness}
          metalnessMap={metalnessMap}
        />
      </mesh>
      <mesh castShadow receiveShadow position={[0.75, 0, 0]}>
        <sphereGeometry args={[0.2, 32, 32]} />
        <meshStandardMaterial
          color={color}
          metalness={materialPreset.metalness}
          roughness={materialPreset.roughness}
          metalnessMap={metalnessMap}
        />
      </mesh>
      <mesh castShadow receiveShadow position={[-0.75, 0, 0]}>
        <sphereGeometry args={[0.2, 32, 32]} />
        <meshStandardMaterial
          color={color}
          metalness={materialPreset.metalness}
          roughness={materialPreset.roughness}
          metalnessMap={metalnessMap}
        />
      </mesh>
    </group>
  )
}

export default function Model({ modelUrl }) {
  if (modelUrl) {
    return <GltfModel url={modelUrl} />
  }
  return <FallbackModel />
}
