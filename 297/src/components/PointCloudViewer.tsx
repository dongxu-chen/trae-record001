import { useRef, useEffect, useCallback, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useAnnotationStore } from '@/store/annotationStore'
import { useCollaborationStore } from '@/store/collaborationStore'
import { useAuthStore } from '@/store/authStore'
import { useToolsStore } from '@/store/toolsStore'
import { Annotation, LABEL_COLORS, BoxGeometry, Point3D, RegionLock } from '@/types'
import { OctreeLOD, OctreePoint } from '@/utils/Octree'
import { GPUPicker } from '@/utils/GPUPicker'
import { MeasurementTool } from '@/utils/MeasurementTool'
import { wsService } from '@/services/websocket'

interface PointCloudViewerProps {
  projectId: string
  onPointSelect?: (points: number[]) => void
}

export default function PointCloudViewer({ projectId }: PointCloudViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const pointCloudRef = useRef<THREE.Points | null>(null)
  const annotationMeshesRef = useRef<Map<string, THREE.Group>>(new Map())
  const regionLockMeshesRef = useRef<Map<string, THREE.Mesh>>(new Map())
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster())
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2())
  const isDraggingRef = useRef(false)
  const dragStartRef = useRef<THREE.Vector2 | null>(null)
  const boxHelperRef = useRef<THREE.Mesh | null>(null)
  const polygonPointsRef = useRef<{ x: number; y: number; z: number }[]>([])
  const polygonLineRef = useRef<THREE.Line | null>(null)
  const octreeRef = useRef<OctreeLOD | null>(null)
  const gpuPickerRef = useRef<GPUPicker | null>(null)
  const lastCameraPosRef = useRef<THREE.Vector3>(new THREE.Vector3())
  const animationFrameRef = useRef<number>(0)
  const currentLockIdRef = useRef<string | null>(null)
  const measurementToolRef = useRef<MeasurementTool | null>(null)
  const measurementPointsRef = useRef<THREE.Vector3[]>([])
  const measurementLinesRef = useRef<THREE.Line[]>([])
  const measurementMarkersRef = useRef<THREE.Mesh[]>([])
  const measurementAreaRef = useRef<THREE.Mesh | null>(null)

  const user = useAuthStore((state) => state.user)
  const {
    currentTool,
    currentLabel,
    annotations,
    addAnnotation,
    deleteAnnotation,
    selectedAnnotationId,
    setSelectedAnnotationId,
    isDrawing,
    setIsDrawing,
    addDrawingPoint,
    clearDrawingPoints,
  } = useAnnotationStore()

  const { regionLocks, addRegionLock, removeRegionLock, isRegionLocked } = useCollaborationStore()
  const {
    activeTool,
    measurementType,
    addMeasurement,
    clearMeasurements,
  } = useToolsStore()

  const [pointCount, setPointCount] = useState(0)
  const [displayedPoints, setDisplayedPoints] = useState(0)
  const [mousePosition, setMousePosition] = useState<Point3D>({ x: 0, y: 0, z: 0 })
  const [loadingProgress, setLoadingProgress] = useState(100)
  const [lockWarning, setLockWarning] = useState<string | null>(null)

  const generateSamplePointCloud = useCallback(() => {
    const count = 100000
    const points: OctreePoint[] = []

    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 100
      const z = (Math.random() - 0.5) * 100
      const y = Math.random() * 5 - Math.abs(x) * 0.05 - Math.abs(z) * 0.05

      const heightRatio = (Math.max(y, -2) + 2) / 7
      const color = new THREE.Color(
        0.5 + heightRatio * 0.3,
        0.5 + heightRatio * 0.2,
        0.5 + heightRatio * 0.1
      )

      points.push({
        position: new THREE.Vector3(x, Math.max(y, -2), z),
        color,
        originalIndex: i,
      })
    }

    return points
  }, [])

  const createAnnotationMesh = useCallback((annotation: Annotation) => {
    const group = new THREE.Group()
    const color = new THREE.Color(LABEL_COLORS[annotation.label])

    if (annotation.type === 'box') {
      const geo = annotation.geometry as BoxGeometry
      const boxGeometry = new THREE.BoxGeometry(geo.size.x, geo.size.y, geo.size.z)
      const edges = new THREE.EdgesGeometry(boxGeometry)
      const lineMaterial = new THREE.LineBasicMaterial({ color, linewidth: 2 })
      const lineSegments = new THREE.LineSegments(edges, lineMaterial)
      
      const fillMaterial = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.15,
        side: THREE.DoubleSide,
      })
      const fillMesh = new THREE.Mesh(boxGeometry, fillMaterial)
      
      group.add(lineSegments)
      group.add(fillMesh)
      group.position.set(geo.center.x, geo.center.y, geo.center.z)
      group.rotation.set(geo.rotation.x, geo.rotation.y, geo.rotation.z)
    } else if (annotation.type === 'polygon') {
      const polyGeo = annotation.geometry as any
      if (polyGeo.points && polyGeo.points.length >= 3) {
        const shape = new THREE.Shape()
        shape.moveTo(polyGeo.points[0].x, polyGeo.points[0].z)
        for (let i = 1; i < polyGeo.points.length; i++) {
          shape.lineTo(polyGeo.points[i].x, polyGeo.points[i].z)
        }
        shape.closePath()

        const extrudeSettings = { depth: polyGeo.height || 2, bevelEnabled: false }
        const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings)
        geometry.rotateX(-Math.PI / 2)
        
        const edges = new THREE.EdgesGeometry(geometry)
        const lineMaterial = new THREE.LineBasicMaterial({ color, linewidth: 2 })
        const lineSegments = new THREE.LineSegments(edges, lineMaterial)
        
        const fillMaterial = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.15,
          side: THREE.DoubleSide,
        })
        const fillMesh = new THREE.Mesh(geometry, fillMaterial)
        
        const minY = Math.min(...polyGeo.points.map((p: any) => p.y))
        lineSegments.position.y = minY
        fillMesh.position.y = minY
        
        group.add(lineSegments)
        group.add(fillMesh)
      }
    }

    group.userData = { annotationId: annotation.id }
    return group
  }, [])

  const createRegionLockMesh = useCallback((lock: RegionLock) => {
    const isOwnLock = lock.userId === user?.id
    const color = new THREE.Color(isOwnLock ? '#165DFF' : '#F53F3F')
    
    const size = {
      x: lock.boundingBox.max.x - lock.boundingBox.min.x,
      y: lock.boundingBox.max.y - lock.boundingBox.min.y,
      z: lock.boundingBox.max.z - lock.boundingBox.min.z,
    }
    
    const geometry = new THREE.BoxGeometry(size.x, size.y, size.z)
    const edges = new THREE.EdgesGeometry(geometry)
    const lineMaterial = new THREE.LineBasicMaterial({ 
      color, 
      linewidth: 2,
      transparent: true,
      opacity: 0.8,
    })
    const lineSegments = new THREE.LineSegments(edges, lineMaterial)
    
    const fillMaterial = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: isOwnLock ? 0.1 : 0.05,
      side: THREE.DoubleSide,
    })
    const fillMesh = new THREE.Mesh(geometry, fillMaterial)
    
    const group = new THREE.Group()
    group.add(lineSegments)
    group.add(fillMesh)
    group.position.set(lock.center.x, lock.center.y, lock.center.z)
    
    return group
  }, [user?.id])

  const updatePointCloudWithLOD = useCallback(() => {
    if (!cameraRef.current || !octreeRef.current || !sceneRef.current) return

    const visibleData = octreeRef.current.getVisiblePoints(cameraRef.current, 5)
    
    if (pointCloudRef.current) {
      const geometry = pointCloudRef.current.geometry
      geometry.dispose()
      
      const newGeometry = new THREE.BufferGeometry()
      newGeometry.setAttribute('position', new THREE.BufferAttribute(visibleData.positions, 3))
      newGeometry.setAttribute('color', new THREE.BufferAttribute(visibleData.colors, 3))
      
      pointCloudRef.current.geometry = newGeometry
      setDisplayedPoints(visibleData.positions.length / 3)

      if (gpuPickerRef.current) {
        gpuPickerRef.current.setPointCloud(pointCloudRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!containerRef.current) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0a0f)
    scene.fog = new THREE.Fog(0x0a0a0f, 50, 200)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      60,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000,
    )
    camera.position.set(30, 30, 30)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = 5
    controls.maxDistance = 150
    controlsRef.current = controls

    const gridHelper = new THREE.GridHelper(100, 20, 0x333333, 0x1a1a1a)
    scene.add(gridHelper)

    const axesHelper = new THREE.AxesHelper(10)
    scene.add(axesHelper)

    const ambientLight = new THREE.AmbientLight(0x404040, 0.5)
    scene.add(ambientLight)

    const octree = new OctreeLOD(2000, 6)
    const samplePoints = generateSamplePointCloud()
    octree.build(samplePoints)
    octreeRef.current = octree
    setPointCount(samplePoints.length)

    const initialData = octree.getVisiblePoints(camera, 3)
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(initialData.positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(initialData.colors, 3))

    const material = new THREE.PointsMaterial({
      size: 0.3,
      vertexColors: true,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.9,
    })

    const pointCloud = new THREE.Points(geometry, material)
    scene.add(pointCloud)
    pointCloudRef.current = pointCloud
    setDisplayedPoints(initialData.positions.length / 3)

    const gpuPicker = new GPUPicker(
      renderer,
      scene,
      camera,
      containerRef.current.clientWidth,
      containerRef.current.clientHeight
    )
    gpuPicker.setPointCloud(pointCloud)
    gpuPickerRef.current = gpuPicker

    const measurementTool = new MeasurementTool()
    measurementToolRef.current = measurementTool

    lastCameraPosRef.current.copy(camera.position)

    let frameCount = 0
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate)
      controls.update()

      frameCount++
      if (frameCount % 10 === 0 && octreeRef.current) {
        const distance = camera.position.distanceTo(lastCameraPosRef.current)
        if (distance > 2 || !controls.getState()) {
          updatePointCloudWithLOD()
          lastCameraPosRef.current.copy(camera.position)
        }
      }

      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      if (!containerRef.current) return
      camera.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
      gpuPicker.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameRef.current)
      gpuPicker.dispose()
      renderer.dispose()
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [generateSamplePointCloud, updatePointCloudWithLOD])

  useEffect(() => {
    if (!sceneRef.current) return

    annotationMeshesRef.current.forEach((mesh) => {
      sceneRef.current?.remove(mesh)
    })
    annotationMeshesRef.current.clear()

    annotations.forEach((annotation) => {
      const mesh = createAnnotationMesh(annotation)
      sceneRef.current?.add(mesh)
      annotationMeshesRef.current.set(annotation.id, mesh)
    })
  }, [annotations, createAnnotationMesh])

  useEffect(() => {
    if (!sceneRef.current) return

    regionLockMeshesRef.current.forEach((mesh) => {
      sceneRef.current?.remove(mesh)
    })
    regionLockMeshesRef.current.clear()

    regionLocks.forEach((lock) => {
      const mesh = createRegionLockMesh(lock)
      sceneRef.current?.add(mesh)
      regionLockMeshesRef.current.set(lock.id, mesh)
    })
  }, [regionLocks, createRegionLockMesh])

  useEffect(() => {
    if (!sceneRef.current) return

    annotationMeshesRef.current.forEach((mesh, id) => {
      const isSelected = id === selectedAnnotationId
      mesh.traverse((child) => {
        if (child instanceof THREE.LineSegments) {
          const material = child.material as THREE.LineBasicMaterial
          const annotation = annotations.find(a => a.id === id)
          if (annotation) {
            const baseColor = new THREE.Color(LABEL_COLORS[annotation.label])
            material.color.copy(isSelected ? new THREE.Color(0xffffff) : baseColor)
          }
        }
      })
    })
  }, [selectedAnnotationId, annotations])

  const acquireLockForRegion = useCallback((center: Point3D, boundingBox: { min: Point3D; max: Point3D }): boolean => {
    const radius = Math.max(
      (boundingBox.max.x - boundingBox.min.x) / 2,
      (boundingBox.max.y - boundingBox.min.y) / 2,
      (boundingBox.max.z - boundingBox.min.z) / 2
    )

    const existingLock = isRegionLocked(center, radius)
    if (existingLock && existingLock.userId !== user?.id) {
      setLockWarning(`区域已被 ${existingLock.userName} 锁定，请选择其他区域`)
      setTimeout(() => setLockWarning(null), 3000)
      return false
    }

    if (user && projectId) {
      wsService.acquireRegionLock(projectId, center, radius, boundingBox)
    }

    return true
  }, [isRegionLocked, user, projectId])

  const handleMouseDown = useCallback((e: MouseEvent) => {
    if (e.button !== 0) return
    if (!containerRef.current || !cameraRef.current || !pointCloudRef.current) return

    const rect = containerRef.current.getBoundingClientRect()
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

    if (activeTool === 'measure' && measurementToolRef.current && sceneRef.current) {
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
      const intersectPoint = new THREE.Vector3()
      raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current)
      raycasterRef.current.ray.intersectPlane(plane, intersectPoint)

      measurementToolRef.current.setType(measurementType)
      const result = measurementToolRef.current.addPoint(intersectPoint.clone())

      const markerGeo = new THREE.SphereGeometry(0.3, 16, 16)
      const markerMat = new THREE.MeshBasicMaterial({ color: 0xFBBF24 })
      const marker = new THREE.Mesh(markerGeo, markerMat)
      marker.position.copy(intersectPoint)
      sceneRef.current.add(marker)
      measurementMarkersRef.current.push(marker)

      measurementPointsRef.current.push(intersectPoint.clone())

      if (measurementPointsRef.current.length >= 2) {
        const lastTwoPoints = measurementPointsRef.current.slice(-2)
        const lineGeo = new THREE.BufferGeometry().setFromPoints(lastTwoPoints)
        const lineMat = new THREE.LineBasicMaterial({ color: 0xFBBF24, linewidth: 2 })
        const line = new THREE.Line(lineGeo, lineMat)
        sceneRef.current.add(line)
        measurementLinesRef.current.push(line)
      }

      if (result && 'distance' in result) {
        addMeasurement({
          id: `meas_${Date.now()}`,
          type: 'distance',
          points: measurementPointsRef.current.map(p => ({ x: p.x, y: p.y, z: p.z })),
          value: result.distance,
          unit: 'm',
        })
        measurementPointsRef.current = []
        measurementToolRef.current.reset()
      } else if (result && 'area' in result) {
        const shape = new THREE.Shape()
        const firstPoint = measurementPointsRef.current[0]
        shape.moveTo(firstPoint.x, firstPoint.z)
        for (let i = 1; i < measurementPointsRef.current.length; i++) {
          shape.lineTo(measurementPointsRef.current[i].x, measurementPointsRef.current[i].z)
        }
        shape.closePath()

        const shapeGeo = new THREE.ShapeGeometry(shape)
        shapeGeo.rotateX(-Math.PI / 2)
        const shapeMat = new THREE.MeshBasicMaterial({
          color: 0xFBBF24,
          transparent: true,
          opacity: 0.2,
          side: THREE.DoubleSide,
        })
        const areaMesh = new THREE.Mesh(shapeGeo, shapeMat)
        sceneRef.current.add(areaMesh)
        measurementAreaRef.current = areaMesh

        addMeasurement({
          id: `meas_${Date.now()}`,
          type: 'area',
          points: measurementPointsRef.current.map(p => ({ x: p.x, y: p.y, z: p.z })),
          value: result.area,
          unit: 'm²',
        })
        measurementPointsRef.current = []
        measurementToolRef.current.reset()
      }

      return
    }

    if (currentTool === 'select') {
      raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current)
      const intersects = raycasterRef.current.intersectObjects(
        Array.from(annotationMeshesRef.current.values()),
        true,
      )

      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object
        while (obj && !obj.userData.annotationId) {
          obj = obj.parent
        }
        if (obj?.userData.annotationId) {
          setSelectedAnnotationId(obj.userData.annotationId)
          return
        }
      }
      setSelectedAnnotationId(null)
    } else if (currentTool === 'box') {
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
      const intersectPoint = new THREE.Vector3()
      raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current)
      raycasterRef.current.ray.intersectPlane(plane, intersectPoint)

      const testCenter = { x: intersectPoint.x, y: 1, z: intersectPoint.z }
      const testBox = {
        min: { x: intersectPoint.x - 1, y: 0, z: intersectPoint.z - 1 },
        max: { x: intersectPoint.x + 1, y: 2, z: intersectPoint.z + 1 },
      }

      if (!acquireLockForRegion(testCenter, testBox)) {
        return
      }

      isDraggingRef.current = true
      dragStartRef.current = new THREE.Vector2(e.clientX, e.clientY)
      
      if (boxHelperRef.current) {
        sceneRef.current?.remove(boxHelperRef.current)
      }
      
      const boxGeo = new THREE.PlaneGeometry(1, 1)
      const boxMat = new THREE.MeshBasicMaterial({
        color: 0x165DFF,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
      })
      boxHelperRef.current = new THREE.Mesh(boxGeo, boxMat)
      sceneRef.current?.add(boxHelperRef.current)
    } else if (currentTool === 'polygon') {
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
      const intersectPoint = new THREE.Vector3()
      raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current)
      raycasterRef.current.ray.intersectPlane(plane, intersectPoint)

      if (!isDrawing) {
        const testCenter = { x: intersectPoint.x, y: 1, z: intersectPoint.z }
        const testBox = {
          min: { x: intersectPoint.x - 5, y: 0, z: intersectPoint.z - 5 },
          max: { x: intersectPoint.x + 5, y: 2, z: intersectPoint.z + 5 },
        }

        if (!acquireLockForRegion(testCenter, testBox)) {
          return
        }

        setIsDrawing(true)
        polygonPointsRef.current = []
      }

      polygonPointsRef.current.push({
        x: intersectPoint.x,
        y: intersectPoint.y,
        z: intersectPoint.z,
      })
      addDrawingPoint({ x: intersectPoint.x, y: intersectPoint.y, z: intersectPoint.z })

      if (polygonLineRef.current) {
        sceneRef.current?.remove(polygonLineRef.current)
      }

      if (polygonPointsRef.current.length >= 2) {
        const points = polygonPointsRef.current.map(p => new THREE.Vector3(p.x, 0.1, p.z))
        const geometry = new THREE.BufferGeometry().setFromPoints(points)
        const material = new THREE.LineBasicMaterial({ color: 0x165DFF, linewidth: 2 })
        polygonLineRef.current = new THREE.Line(geometry, material)
        sceneRef.current?.add(polygonLineRef.current)
      }
    }
  }, [activeTool, measurementType, currentTool, isDrawing, setSelectedAnnotationId, setIsDrawing, addDrawingPoint, acquireLockForRegion, addMeasurement])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current || !cameraRef.current || !pointCloudRef.current) return

    const rect = containerRef.current.getBoundingClientRect()
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

    raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current)
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const intersectPoint = new THREE.Vector3()
    raycasterRef.current.ray.intersectPlane(plane, intersectPoint)
    
    if (intersectPoint) {
      setMousePosition({
        x: intersectPoint.x,
        y: intersectPoint.y,
        z: intersectPoint.z,
      })
    }

    if (isDraggingRef.current && dragStartRef.current && boxHelperRef.current && cameraRef.current) {
      const startNdc = new THREE.Vector2(
        ((dragStartRef.current.x - rect.left) / rect.width) * 2 - 1,
        -((dragStartRef.current.y - rect.top) / rect.height) * 2 + 1
      )
      
      const startRay = new THREE.Raycaster()
      startRay.setFromCamera(startNdc, cameraRef.current)
      const startPoint = new THREE.Vector3()
      startRay.ray.intersectPlane(plane, startPoint)
      
      const width = Math.abs(intersectPoint.x - startPoint.x)
      const depth = Math.abs(intersectPoint.z - startPoint.z)
      
      boxHelperRef.current.position.set(
        (startPoint.x + intersectPoint.x) / 2,
        0.01,
        (startPoint.z + intersectPoint.z) / 2
      )
      boxHelperRef.current.scale.set(Math.max(width, 0.1), Math.max(depth, 0.1), 1)
      boxHelperRef.current.lookAt(boxHelperRef.current.position.x, 1, boxHelperRef.current.position.z)
    }
  }, [])

  const handleMouseUp = useCallback((e: MouseEvent) => {
    if (e.button !== 0) return
    if (!containerRef.current || !cameraRef.current || !gpuPickerRef.current) return

    if (currentTool === 'box' && isDraggingRef.current && dragStartRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      
      const startX = dragStartRef.current.x - rect.left
      const startY = dragStartRef.current.y - rect.top
      const endX = e.clientX - rect.left
      const endY = e.clientY - rect.top

      const selectedPointIndices = gpuPickerRef.current.pickBox(startX, startY, endX, endY)

      if (selectedPointIndices.length > 0) {
        const startNdc = new THREE.Vector2(
          ((dragStartRef.current.x - rect.left) / rect.width) * 2 - 1,
          -((dragStartRef.current.y - rect.top) / rect.height) * 2 + 1
        )
        const endNdc = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        )

        const startRay = new THREE.Raycaster()
        const endRay = new THREE.Raycaster()
        startRay.setFromCamera(startNdc, cameraRef.current)
        endRay.setFromCamera(endNdc, cameraRef.current)

        const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
        const startPoint = new THREE.Vector3()
        const endPoint = new THREE.Vector3()
        startRay.ray.intersectPlane(plane, startPoint)
        endRay.ray.intersectPlane(plane, endPoint)

        const centerX = (startPoint.x + endPoint.x) / 2
        const centerZ = (startPoint.z + endPoint.z) / 2
        const sizeX = Math.abs(endPoint.x - startPoint.x)
        const sizeZ = Math.abs(endPoint.z - startPoint.z)

        if (sizeX > 0.5 && sizeZ > 0.5) {
          const newAnnotation: Annotation = {
            id: `ann_${Date.now()}`,
            projectId,
            label: currentLabel,
            type: 'box',
            geometry: {
              center: { x: centerX, y: 1, z: centerZ },
              size: { x: sizeX, y: 2, z: sizeZ },
              rotation: { x: 0, y: 0, z: 0 },
            },
            pointIndices: selectedPointIndices,
            userId: user?.id || '1',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }
          addAnnotation(newAnnotation)

          if (user && projectId) {
            wsService.sendAnnotationCreated(projectId, newAnnotation)
          }
        }
      }

      if (boxHelperRef.current) {
        sceneRef.current?.remove(boxHelperRef.current)
        boxHelperRef.current = null
      }
    }

    isDraggingRef.current = false
    dragStartRef.current = null
  }, [currentTool, currentLabel, projectId, user, addAnnotation])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Delete' && selectedAnnotationId) {
      deleteAnnotation(selectedAnnotationId)
      if (user && projectId) {
        wsService.sendAnnotationDeleted(projectId, selectedAnnotationId)
      }
    }
    if (e.key === 'Escape') {
      clearDrawingPoints()
      polygonPointsRef.current = []
      if (polygonLineRef.current) {
        sceneRef.current?.remove(polygonLineRef.current)
        polygonLineRef.current = null
      }
      if (boxHelperRef.current) {
        sceneRef.current?.remove(boxHelperRef.current)
        boxHelperRef.current = null
      }
      isDraggingRef.current = false
      setIsDrawing(false)

      measurementPointsRef.current = []
      measurementToolRef.current?.reset()
      measurementMarkersRef.current.forEach(m => sceneRef.current?.remove(m))
      measurementMarkersRef.current = []
      measurementLinesRef.current.forEach(l => sceneRef.current?.remove(l))
      measurementLinesRef.current = []
      if (measurementAreaRef.current) {
        sceneRef.current?.remove(measurementAreaRef.current)
        measurementAreaRef.current = null
      }
    }
    if (e.key === 'Enter' && isDrawing && polygonPointsRef.current.length >= 3) {
      if (gpuPickerRef.current && containerRef.current) {
        const width = containerRef.current.clientWidth
        const height = containerRef.current.clientHeight
        const screenPoints = polygonPointsRef.current.map(p => {
          const vector = new THREE.Vector3(p.x, p.y, p.z)
          vector.project(cameraRef.current!)
          return {
            x: (vector.x + 1) * width / 2,
            y: (-vector.y + 1) * height / 2,
          }
        })

        const selectedPointIndices = gpuPickerRef.current.pickPolygon(screenPoints, width, height)

        if (selectedPointIndices.length > 0) {
          const newAnnotation: Annotation = {
            id: `ann_${Date.now()}`,
            projectId,
            label: currentLabel,
            type: 'polygon',
            geometry: {
              points: polygonPointsRef.current,
              height: 2,
            } as any,
            pointIndices: selectedPointIndices,
            userId: user?.id || '1',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }
          addAnnotation(newAnnotation)

          if (user && projectId) {
            wsService.sendAnnotationCreated(projectId, newAnnotation)
          }
        }
      }

      clearDrawingPoints()
      polygonPointsRef.current = []
      if (polygonLineRef.current) {
        sceneRef.current?.remove(polygonLineRef.current)
        polygonLineRef.current = null
      }
      setIsDrawing(false)
    }
    if (e.key === 'v' || e.key === 'V') {
      useAnnotationStore.getState().setCurrentTool('select')
      useToolsStore.getState().setActiveTool('annotate')
    }
    if (e.key === 'b' || e.key === 'B') {
      useAnnotationStore.getState().setCurrentTool('box')
      useToolsStore.getState().setActiveTool('annotate')
    }
    if (e.key === 'p' || e.key === 'P') {
      useAnnotationStore.getState().setCurrentTool('polygon')
      useToolsStore.getState().setActiveTool('annotate')
    }
    if (e.key === 'd' || e.key === 'D') {
      useToolsStore.getState().setActiveTool('measure')
      useToolsStore.getState().setMeasurementType('distance')
    }
    if (e.key === 'a' || e.key === 'A') {
      useToolsStore.getState().setActiveTool('measure')
      useToolsStore.getState().setMeasurementType('area')
    }
    if (e.key === 'g' || e.key === 'G') {
      useToolsStore.getState().setActiveTool('measure')
      useToolsStore.getState().setMeasurementType('angle')
    }
  }, [selectedAnnotationId, deleteAnnotation, clearDrawingPoints, isDrawing, currentLabel, projectId, user, addAnnotation, setIsDrawing])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    container.addEventListener('mousedown', handleMouseDown)
    container.addEventListener('mousemove', handleMouseMove)
    container.addEventListener('mouseup', handleMouseUp)
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      container.removeEventListener('mousedown', handleMouseDown)
      container.removeEventListener('mousemove', handleMouseMove)
      container.removeEventListener('mouseup', handleMouseUp)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleMouseDown, handleMouseMove, handleMouseUp, handleKeyDown])

  const resetView = () => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(30, 30, 30)
      controlsRef.current.target.set(0, 0, 0)
      controlsRef.current.update()
    }
  }

  return (
    <div ref={containerRef} className="w-full h-full relative">
      <div className="absolute top-4 left-4 glass-panel rounded-lg px-3 py-2 text-xs text-zinc-400 space-y-1">
        <div>总点数: {pointCount.toLocaleString()}</div>
        <div>显示点数: {displayedPoints.toLocaleString()}</div>
        <div>LOD等级: {loadingProgress}%</div>
        <div>X: {mousePosition.x.toFixed(2)} Y: {mousePosition.y.toFixed(2)} Z: {mousePosition.z.toFixed(2)}</div>
        <div>标注: {annotations.length}</div>
      </div>
      
      {lockWarning && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500/90 text-white px-4 py-2 rounded-lg text-sm font-medium animate-pulse z-20">
          {lockWarning}
        </div>
      )}

      {isDrawing && polygonPointsRef.current.length > 0 && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 glass-panel rounded-lg px-4 py-2 text-sm text-white z-10">
          多边形绘制中 ({polygonPointsRef.current.length}个点) - 按 Enter 完成，按 Escape 取消
        </div>
      )}

      {activeTool === 'measure' && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 glass-panel rounded-lg px-4 py-2 text-sm text-white z-10">
          {measurementType === 'distance' && `距离测量 - 已选择 ${measurementPointsRef.current.length}/2 个点 - 按 Escape 取消`}
          {measurementType === 'area' && `面积测量 - 已选择 ${measurementPointsRef.current.length}/3 个点 - 点击起点闭合 - 按 Escape 取消`}
          {measurementType === 'angle' && `角度测量 - 已选择 ${measurementPointsRef.current.length}/3 个点 - 按 Escape 取消`}
        </div>
      )}

      {regionLocks.length > 0 && (
        <div className="absolute bottom-4 right-4 glass-panel rounded-lg px-3 py-2 text-xs">
          <div className="text-zinc-400 mb-1">区域锁: {regionLocks.length}</div>
          {regionLocks.map(lock => (
            <div key={lock.id} className="flex items-center gap-2 text-zinc-300">
              <div 
                className="w-2 h-2 rounded-full" 
                style={{ backgroundColor: lock.userId === user?.id ? '#165DFF' : '#F53F3F' }}
              />
              <span>{lock.userName} - {lock.userId === user?.id ? '我的' : '他人'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
