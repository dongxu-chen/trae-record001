import { useState, useRef, useEffect, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'
import * as dat from 'dat.gui'

const HDRI_PRESETS = [
  { name: '工作室', color: 0x1a1a2e, type: 'color' },
  { name: '室外日光', color: 0x87ceeb, type: 'color' },
  { name: '夜景', color: 0x0a0a1a, type: 'color' },
  { name: '温暖室内', color: 0xffeedd, type: 'color' },
  { name: '冷色调', color: 0x4488ff, type: 'color' },
]

function App() {
  const containerRef = useRef(null)
  const sceneRef = useRef(null)
  const cameraRef = useRef(null)
  const rendererRef = useRef(null)
  const controlsRef = useRef(null)
  const modelRef = useRef(null)
  const model2Ref = useRef(null)
  const mixerRef = useRef(null)
  const mixer2Ref = useRef(null)
  const guiRef = useRef(null)
  const animationIdRef = useRef(null)
  const clockRef = useRef(new THREE.Clock())
  const raycasterRef = useRef(new THREE.Raycaster())
  const mouseRef = useRef(new THREE.Vector2())

  const [loading, setLoading] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [modelInfo, setModelInfo] = useState({
    vertices: 0,
    faces: 0,
    meshCount: 0,
    materialCount: 0,
    name: '',
    format: '',
    metadata: {}
  })
  const [model2Info, setModel2Info] = useState({
    vertices: 0,
    faces: 0,
    meshCount: 0,
    materialCount: 0,
    name: '',
    format: '',
    metadata: {}
  })
  const [animations, setAnimations] = useState([])
  const [animations2, setAnimations2] = useState([])
  const [currentAnimation, setCurrentAnimation] = useState(null)
  const [currentAnimation2, setCurrentAnimation2] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPlaying2, setIsPlaying2] = useState(false)

  const [measureMode, setMeasureMode] = useState(false)
  const [measurePoints, setMeasurePoints] = useState([])
  const [measureDistance, setMeasureDistance] = useState(null)
  const measureLineRef = useRef(null)
  const measureMarkersRef = useRef([])

  const [currentEnv, setCurrentEnv] = useState('工作室')
  const envMapRef = useRef(null)

  useEffect(() => {
    initScene()
    return () => {
      cleanup()
    }
  }, [])

  const initScene = () => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a2e)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    )
    camera.position.set(5, 5, 5)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.screenSpacePanning = true
    controls.minDistance = 0.5
    controls.maxDistance = 100
    controlsRef.current = controls

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1)
    directionalLight.position.set(5, 10, 7.5)
    directionalLight.castShadow = true
    directionalLight.shadow.mapSize.width = 2048
    directionalLight.shadow.mapSize.height = 2048
    scene.add(directionalLight)

    const pointLight = new THREE.PointLight(0x00d4ff, 0.5)
    pointLight.position.set(-5, 5, -5)
    scene.add(pointLight)

    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222)
    gridHelper.name = 'gridHelper'
    scene.add(gridHelper)

    initGUI(scene, ambientLight, directionalLight, pointLight)

    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)
      const delta = clockRef.current.getDelta()
      
      if (mixerRef.current) {
        mixerRef.current.update(delta)
      }
      if (mixer2Ref.current) {
        mixer2Ref.current.update(delta)
      }
      
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    const handleClick = (event) => {
      if (!measureMode) return

      const rect = renderer.domElement.getBoundingClientRect()
      mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

      raycasterRef.current.setFromCamera(mouseRef.current, camera)
      const meshes = []
      
      if (modelRef.current) {
        modelRef.current.traverse((child) => {
          if (child.isMesh) meshes.push(child)
        })
      }
      if (model2Ref.current) {
        model2Ref.current.traverse((child) => {
          if (child.isMesh) meshes.push(child)
        })
      }

      const intersects = raycasterRef.current.intersectObjects(meshes)
      
      if (intersects.length > 0) {
        const point = intersects[0].point
        addMeasurePoint(point)
      }
    }

    renderer.domElement.addEventListener('click', handleClick)

    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('click', handleClick)
    }
  }

  const initGUI = (scene, ambientLight, directionalLight, pointLight) => {
    if (guiRef.current) {
      guiRef.current.destroy()
    }

    const gui = new dat.GUI({ width: 300 })
    guiRef.current = gui

    const lightFolder = gui.addFolder('光照设置')
    lightFolder.add(ambientLight, 'intensity', 0, 2).name('环境光强度')
    lightFolder.add(directionalLight, 'intensity', 0, 3).name('主光强度')
    lightFolder.add(directionalLight.position, 'x', -20, 20).name('主光X')
    lightFolder.add(directionalLight.position, 'y', -20, 20).name('主光Y')
    lightFolder.add(directionalLight.position, 'z', -20, 20).name('主光Z')
    lightFolder.add(pointLight, 'intensity', 0, 2).name('点光强度')
    lightFolder.addColor({ color: '#00d4ff' }, 'color').name('点光颜色').onChange((color) => {
      pointLight.color.set(color)
    })

    const materialFolder = gui.addFolder('材质设置')
    const materialParams = {
      wireframe: false,
      flatShading: false,
      metalness: 0.5,
      roughness: 0.5
    }
    
    const updateAllMaterials = (callback) => {
      if (modelRef.current) {
        modelRef.current.traverse((child) => {
          if (child.isMesh && child.material) {
            callback(child.material)
          }
        })
      }
      if (model2Ref.current) {
        model2Ref.current.traverse((child) => {
          if (child.isMesh && child.material) {
            callback(child.material)
          }
        })
      }
    }

    materialFolder.add(materialParams, 'wireframe').name('线框模式').onChange((value) => {
      updateAllMaterials((mat) => {
        if (Array.isArray(mat)) {
          mat.forEach(m => m.wireframe = value)
        } else {
          mat.wireframe = value
        }
      })
    })

    materialFolder.add(materialParams, 'flatShading').name('平面着色').onChange((value) => {
      updateAllMaterials((mat) => {
        if (Array.isArray(mat)) {
          mat.forEach(m => {
            m.flatShading = value
            m.needsUpdate = true
          })
        } else {
          mat.flatShading = value
          mat.needsUpdate = true
        }
      })
    })

    materialFolder.add(materialParams, 'metalness', 0, 1).name('金属度').onChange((value) => {
      updateAllMaterials((mat) => {
        if (Array.isArray(mat)) {
          mat.forEach(m => {
            if (m.metalness !== undefined) m.metalness = value
          })
        } else {
          if (mat.metalness !== undefined) mat.metalness = value
        }
      })
    })

    materialFolder.add(materialParams, 'roughness', 0, 1).name('粗糙度').onChange((value) => {
      updateAllMaterials((mat) => {
        if (Array.isArray(mat)) {
          mat.forEach(m => {
            if (m.roughness !== undefined) m.roughness = value
          })
        } else {
          if (mat.roughness !== undefined) mat.roughness = value
        }
      })
    })

    const sceneFolder = gui.addFolder('场景设置')
    sceneFolder.addColor({ color: '#1a1a2e' }, 'color').name('背景颜色').onChange((color) => {
      scene.background = new THREE.Color(color)
    })

    const envFolder = gui.addFolder('环境设置')
    const envParams = { environment: '工作室' }
    envFolder.add(envParams, 'environment', HDRI_PRESETS.map(e => e.name)).name('环境预设').onChange((name) => {
      setEnvironment(name)
    })
  }

  const setEnvironment = (name) => {
    if (!sceneRef.current) return
    const preset = HDRI_PRESETS.find(p => p.name === name)
    if (preset) {
      sceneRef.current.background = new THREE.Color(preset.color)
      setCurrentEnv(name)
    }
  }

  const convertFBXMaterial = (material) => {
    if (!material) return material

    const params = {
      color: material.color ? material.color.clone() : new THREE.Color(0xffffff),
      map: material.map || null,
      normalMap: material.normalMap || null,
      roughnessMap: material.roughnessMap || null,
      metalnessMap: material.metalnessMap || null,
      emissive: material.emissive ? material.emissive.clone() : new THREE.Color(0x000000),
      emissiveMap: material.emissiveMap || null,
      aoMap: material.aoMap || null,
      alphaMap: material.alphaMap || null,
      transparent: material.transparent || false,
      opacity: material.opacity !== undefined ? material.opacity : 1,
      side: material.side || THREE.FrontSide,
    }

    if (material.isMeshPhongMaterial || material.isMeshLambertMaterial) {
      params.roughness = material.shininess ? 1 - (material.shininess / 100) : 0.5
      params.metalness = material.reflectivity || 0
    } else if (material.isMeshStandardMaterial) {
      params.roughness = material.roughness !== undefined ? material.roughness : 0.5
      params.metalness = material.metalness !== undefined ? material.metalness : 0
    } else {
      params.roughness = 0.5
      params.metalness = 0
    }

    return new THREE.MeshStandardMaterial(params)
  }

  const processFBXModel = (model) => {
    model.traverse((child) => {
      if (child.isMesh && child.material) {
        if (Array.isArray(child.material)) {
          child.material = child.material.map(mat => convertFBXMaterial(mat))
        } else {
          child.material = convertFBXMaterial(child.material)
        }
      }
    })
    return model
  }

  const calculateModelStats = (model) => {
    let vertices = 0
    let faces = 0
    let meshCount = 0
    let materialCount = 0

    model.traverse((child) => {
      if (child.isMesh) {
        meshCount++
        child.castShadow = true
        child.receiveShadow = true
        
        if (child.material) {
          if (Array.isArray(child.material)) {
            materialCount += child.material.length
          } else {
            materialCount++
          }
        }
        
        if (child.geometry) {
          const positionAttr = child.geometry.getAttribute('position')
          const indexAttr = child.geometry.getIndex()
          
          if (positionAttr) {
            vertices += positionAttr.count
          }
          
          if (indexAttr) {
            faces += indexAttr.count / 3
          } else if (positionAttr) {
            faces += positionAttr.count / 3
          }
        }
      }
    })

    return {
      vertices: Math.round(vertices),
      faces: Math.round(faces),
      meshCount,
      materialCount
    }
  }

  const loadModel = (file, modelIndex = 1) => {
    if (!sceneRef.current) return

    setLoading(true)
    const fileName = file.name.toLowerCase()
    let loader

    if (fileName.endsWith('.glb') || fileName.endsWith('.gltf')) {
      loader = new GLTFLoader()
    } else if (fileName.endsWith('.obj')) {
      loader = new OBJLoader()
    } else if (fileName.endsWith('.fbx')) {
      loader = new FBXLoader()
    } else {
      alert('不支持的文件格式！请上传 glTF、OBJ 或 FBX 格式的模型。')
      setLoading(false)
      return
    }

    const url = URL.createObjectURL(file)
    const onLoad = (loadedData, format) => {
      let model
      let animations = []

      if (format === 'glTF/GLB' && loadedData.scene) {
        model = loadedData.scene
        animations = loadedData.animations || []
        model.userData = { ...model.userData, metadata: loadedData.asset || {} }
      } else {
        model = loadedData
        model.userData = { ...model.userData, metadata: { format } }
      }

      if (format === 'FBX') {
        model = processFBXModel(model)
        animations = loadedData.animations || []
      }

      handleLoadedModel(model, file.name, format, animations, modelIndex)
    }

    const onError = (error) => {
      console.error('加载模型失败:', error)
      alert('模型加载失败！')
      setLoading(false)
    }

    if (fileName.endsWith('.glb') || fileName.endsWith('.gltf')) {
      loader.load(url, (gltf) => onLoad(gltf, 'glTF/GLB'), undefined, onError)
    } else if (fileName.endsWith('.obj')) {
      loader.load(url, (obj) => onLoad(obj, 'OBJ'), undefined, onError)
    } else if (fileName.endsWith('.fbx')) {
      loader.load(url, (fbx) => onLoad(fbx, 'FBX'), undefined, onError)
    }
  }

  const handleLoadedModel = (model, name, format, animations, modelIndex) => {
    const scene = sceneRef.current
    const currentModelRef = modelIndex === 1 ? modelRef : model2Ref
    const currentMixerRef = modelIndex === 1 ? mixerRef : mixer2Ref
    const setCurrentModelInfo = modelIndex === 1 ? setModelInfo : setModel2Info
    const setCurrentAnimations = modelIndex === 1 ? setAnimations : setAnimations2

    if (currentModelRef.current && scene) {
      scene.remove(currentModelRef.current)
    }

    const stats = calculateModelStats(model)

    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    const scale = 5 / maxDim

    model.position.sub(center)
    model.scale.multiplyScalar(scale)

    if (compareMode) {
      const offsetX = modelIndex === 1 ? -4 : 4
      model.position.x += offsetX
    }

    if (currentMixerRef.current) {
      currentMixerRef.current.stopAllAction()
    }

    if (animations && animations.length > 0) {
      const mixer = new THREE.AnimationMixer(model)
      if (modelIndex === 1) {
        mixerRef.current = mixer
      } else {
        mixer2Ref.current = mixer
      }

      const animationNames = animations.map((clip, index) => ({
        name: clip.name || `动画 ${index + 1}`,
        clip: clip
      }))
      setCurrentAnimations(animationNames)
    } else {
      setCurrentAnimations([])
    }

    if (modelIndex === 1) {
      modelRef.current = model
    } else {
      model2Ref.current = model
    }

    if (scene) {
      scene.add(model)
    }

    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(10, 10, 10)
      cameraRef.current.lookAt(0, 0, 0)
      controlsRef.current.target.set(0, 0, 0)
      controlsRef.current.update()
    }

    const metadata = model.userData?.metadata || {}

    setCurrentModelInfo({
      vertices: stats.vertices,
      faces: stats.faces,
      meshCount: stats.meshCount,
      materialCount: stats.materialCount,
      name: name,
      format: format,
      metadata: metadata
    })

    setLoading(false)
  }

  const playAnimation = (animationData, modelIndex = 1) => {
    const currentMixerRef = modelIndex === 1 ? mixerRef : mixer2Ref
    const setCurrentAnim = modelIndex === 1 ? setCurrentAnimation : setCurrentAnimation2
    const setPlaying = modelIndex === 1 ? setIsPlaying : setIsPlaying2

    if (!currentMixerRef.current || !animationData) return

    currentMixerRef.current.stopAllAction()
    const action = currentMixerRef.current.clipAction(animationData.clip)
    action.play()
    setCurrentAnim(animationData)
    setPlaying(true)
  }

  const toggleAnimation = (modelIndex = 1) => {
    const currentMixerRef = modelIndex === 1 ? mixerRef : mixer2Ref
    const playing = modelIndex === 1 ? isPlaying : isPlaying2
    const setPlaying = modelIndex === 1 ? setIsPlaying : setIsPlaying2

    if (!currentMixerRef.current) return

    if (playing) {
      currentMixerRef.current.timeScale = 0
      setPlaying(false)
    } else {
      currentMixerRef.current.timeScale = 1
      setPlaying(true)
    }
  }

  const addMeasurePoint = (point) => {
    if (!sceneRef.current) return

    const newPoints = [...measurePoints, point.clone()]
    
    if (newPoints.length > 2) {
      newPoints.shift()
    }

    setMeasurePoints(newPoints)

    if (measureMarkersRef.current.length > 0) {
      measureMarkersRef.current.forEach(marker => {
        sceneRef.current.remove(marker)
      })
      measureMarkersRef.current = []
    }

    if (measureLineRef.current) {
      sceneRef.current.remove(measureLineRef.current)
      measureLineRef.current = null
    }

    const markerGeometry = new THREE.SphereGeometry(0.05, 16, 16)
    const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 })
    
    newPoints.forEach(p => {
      const marker = new THREE.Mesh(markerGeometry, markerMaterial)
      marker.position.copy(p)
      sceneRef.current.add(marker)
      measureMarkersRef.current.push(marker)
    })

    if (newPoints.length === 2) {
      const lineGeometry = new THREE.BufferGeometry().setFromPoints(newPoints)
      const lineMaterial = new THREE.LineBasicMaterial({ color: 0xff0000, linewidth: 2 })
      const line = new THREE.Line(lineGeometry, lineMaterial)
      sceneRef.current.add(line)
      measureLineRef.current = line

      const distance = newPoints[0].distanceTo(newPoints[1])
      setMeasureDistance(distance)
    } else {
      setMeasureDistance(null)
    }
  }

  const clearMeasurements = () => {
    if (!sceneRef.current) return

    setMeasurePoints([])
    setMeasureDistance(null)

    if (measureMarkersRef.current.length > 0) {
      measureMarkersRef.current.forEach(marker => {
        sceneRef.current.remove(marker)
      })
      measureMarkersRef.current = []
    }

    if (measureLineRef.current) {
      sceneRef.current.remove(measureLineRef.current)
      measureLineRef.current = null
    }
  }

  const toggleCompareMode = () => {
    const newCompareMode = !compareMode
    setCompareMode(newCompareMode)

    if (modelRef.current) {
      modelRef.current.position.x = newCompareMode ? -4 : 0
    }
    if (model2Ref.current) {
      model2Ref.current.position.x = newCompareMode ? 4 : 0
    }
  }

  const takeScreenshot = (transparent = true) => {
    if (!rendererRef.current || !sceneRef.current || !cameraRef.current) return

    const renderer = rendererRef.current
    const scene = sceneRef.current
    const camera = cameraRef.current

    const originalBackground = scene.background
    const originalClearAlpha = renderer.getClearAlpha()

    if (transparent) {
      scene.background = null
      renderer.setClearAlpha(0)
    }

    renderer.render(scene, camera)

    const dataURL = renderer.domElement.toDataURL('image/png')

    if (transparent) {
      scene.background = originalBackground
      renderer.setClearAlpha(originalClearAlpha)
      renderer.render(scene, camera)
    }

    const link = document.createElement('a')
    link.download = `model-screenshot-${Date.now()}.png`
    link.href = dataURL
    link.click()
  }

  const handleFileChange = (e, modelIndex = 1) => {
    const file = e.target.files[0]
    if (file) {
      loadModel(file, modelIndex)
    }
    e.target.value = ''
  }

  const cleanup = () => {
    if (animationIdRef.current) {
      cancelAnimationFrame(animationIdRef.current)
    }
    if (guiRef.current) {
      guiRef.current.destroy()
    }
    if (rendererRef.current && containerRef.current) {
      containerRef.current.removeChild(rendererRef.current.domElement)
      rendererRef.current.dispose()
    }
  }

  return (
    <div className="app">
      <div ref={containerRef} className="canvas-container" />
      
      <div className="toolbar">
        <label className="toolbar-button">
          <input
            type="file"
            className="file-input"
            accept=".glb,.gltf,.obj,.fbx"
            onChange={(e) => handleFileChange(e, 1)}
          />
          <button>📁 加载模型1</button>
        </label>
        {compareMode && (
          <label className="toolbar-button">
            <input
              type="file"
              className="file-input"
              accept=".glb,.gltf,.obj,.fbx"
              onChange={(e) => handleFileChange(e, 2)}
            />
            <button>📁 加载模型2</button>
          </label>
        )}
        <button onClick={toggleCompareMode} className={compareMode ? 'active' : ''}>
          🔀 {compareMode ? '关闭对比' : '对比模式'}
        </button>
        <button onClick={() => setMeasureMode(!measureMode)} className={measureMode ? 'active' : ''}>
          📏 {measureMode ? '关闭测量' : '测量工具'}
        </button>
        <button onClick={() => takeScreenshot(true)}>📷 透明截图</button>
        <button onClick={() => takeScreenshot(false)}>🖼️ 带背景截图</button>
      </div>

      <div className="controls-hint">
        <h4>操作提示</h4>
        <p>🖱️ 左键拖拽：旋转</p>
        <p>🖱️ 右键拖拽：平移</p>
        <p>🖱️ 滚轮：缩放</p>
        {measureMode && <p style={{ color: '#ff6b6b' }}>📍 点击模型表面测量</p>}
      </div>

      <div className="info-panel">
        <h3>模型1信息</h3>
        <div className="info-row">
          <span className="info-label">名称：</span>
          <span className="info-value">{modelInfo.name || '未加载'}</span>
        </div>
        <div className="info-row">
          <span className="info-label">格式：</span>
          <span className="info-value">{modelInfo.format || '-'}</span>
        </div>
        <div className="info-row">
          <span className="info-label">顶点数：</span>
          <span className="info-value">{modelInfo.vertices.toLocaleString()}</span>
        </div>
        <div className="info-row">
          <span className="info-label">面数：</span>
          <span className="info-value">{modelInfo.faces.toLocaleString()}</span>
        </div>
        <div className="info-row">
          <span className="info-label">网格数量：</span>
          <span className="info-value">{modelInfo.meshCount || 0}</span>
        </div>
        <div className="info-row">
          <span className="info-label">材质数量：</span>
          <span className="info-value">{modelInfo.materialCount || 0}</span>
        </div>
        {modelInfo.metadata && Object.keys(modelInfo.metadata).length > 0 && (
          <>
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', margin: '10px 0', paddingTop: '10px' }}>
              <strong style={{ color: '#00d4ff', fontSize: '13px' }}>元数据</strong>
            </div>
            {Object.entries(modelInfo.metadata).map(([key, value]) => (
              <div key={key} className="info-row" style={{ fontSize: '12px' }}>
                <span className="info-label">{key}：</span>
                <span className="info-value">{String(value)}</span>
              </div>
            ))}
          </>
        )}
      </div>

      {compareMode && (
        <div className="info-panel" style={{ left: 'auto', right: '20px' }}>
          <h3>模型2信息</h3>
          <div className="info-row">
            <span className="info-label">名称：</span>
            <span className="info-value">{model2Info.name || '未加载'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">格式：</span>
            <span className="info-value">{model2Info.format || '-'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">顶点数：</span>
            <span className="info-value">{model2Info.vertices.toLocaleString()}</span>
          </div>
          <div className="info-row">
            <span className="info-label">面数：</span>
            <span className="info-value">{model2Info.faces.toLocaleString()}</span>
          </div>
          <div className="info-row">
            <span className="info-label">网格数量：</span>
            <span className="info-value">{model2Info.meshCount || 0}</span>
          </div>
          <div className="info-row">
            <span className="info-label">材质数量：</span>
            <span className="info-value">{model2Info.materialCount || 0}</span>
          </div>
        </div>
      )}

      {measureMode && (
        <div className="measure-panel">
          <h4>📏 测量工具</h4>
          <div className="info-row">
            <span className="info-label">已选点：</span>
            <span className="info-value">{measurePoints.length}/2</span>
          </div>
          {measureDistance !== null && (
            <div className="info-row">
              <span className="info-label">距离：</span>
              <span className="info-value" style={{ color: '#00ff88' }}>
                {measureDistance.toFixed(4)} 单位
              </span>
            </div>
          )}
          <button onClick={clearMeasurements} style={{ 
            marginTop: '10px', 
            width: '100%',
            padding: '8px',
            background: 'rgba(255,100,100,0.3)',
            border: '1px solid rgba(255,100,100,0.5)',
            borderRadius: '6px',
            color: 'white',
            cursor: 'pointer'
          }}>
            清除测量
          </button>
        </div>
      )}

      {animations.length > 0 && (
        <div className="animation-controls" style={{ bottom: compareMode ? '140px' : '20px' }}>
          <strong style={{ color: '#00d4ff', marginBottom: '5px' }}>模型1动画</strong>
          <select
            value={currentAnimation?.name || ''}
            onChange={(e) => {
              const anim = animations.find(a => a.name === e.target.value)
              if (anim) playAnimation(anim, 1)
            }}
          >
            <option value="">选择动画</option>
            {animations.map((anim, index) => (
              <option key={index} value={anim.name}>{anim.name}</option>
            ))}
          </select>
          <div className="animation-buttons">
            <button
              className={isPlaying ? 'active' : ''}
              onClick={() => toggleAnimation(1)}
              disabled={!currentAnimation}
            >
              {isPlaying ? '⏸️ 暂停' : '▶️ 播放'}
            </button>
          </div>
        </div>
      )}

      {compareMode && animations2.length > 0 && (
        <div className="animation-controls" style={{ right: '340px' }}>
          <strong style={{ color: '#00d4ff', marginBottom: '5px' }}>模型2动画</strong>
          <select
            value={currentAnimation2?.name || ''}
            onChange={(e) => {
              const anim = animations2.find(a => a.name === e.target.value)
              if (anim) playAnimation(anim, 2)
            }}
          >
            <option value="">选择动画</option>
            {animations2.map((anim, index) => (
              <option key={index} value={anim.name}>{anim.name}</option>
            ))}
          </select>
          <div className="animation-buttons">
            <button
              className={isPlaying2 ? 'active' : ''}
              onClick={() => toggleAnimation(2)}
              disabled={!currentAnimation2}
            >
              {isPlaying2 ? '⏸️ 暂停' : '▶️ 播放'}
            </button>
          </div>
        </div>
      )}

      <div className="env-panel">
        <h4>🌍 环境预设</h4>
        <div className="env-buttons">
          {HDRI_PRESETS.map((preset) => (
            <button
              key={preset.name}
              className={currentEnv === preset.name ? 'active' : ''}
              onClick={() => setEnvironment(preset.name)}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>加载模型中...</p>
        </div>
      )}
    </div>
  )
}

export default App
