import { useState, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import Model from './components/Model'
import Environment from './components/Environment'
import ControlPanel from './components/ControlPanel'
import Hotspot from './components/Hotspot'
import ProductModal from './components/ProductModal'
import CameraAnimation from './components/CameraAnimation'
import * as THREE from 'three'

const SceneCleaner = () => {
  const { scene, gl } = useThree()

  return null
}

const App = () => {
  const [materialProps, setMaterialProps] = useState({
    color: '#ff6b6b',
    metalness: 0.5,
    roughness: 0.5,
    envMapIntensity: 1
  })

  const [backgroundColor, setBackgroundColor] = useState('#1a1a2e')
  const [animation, setAnimation] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [activeHotspot, setActiveHotspot] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [modelType, setModelType] = useState('helmet')
  const controlsRef = useRef()

  const hotspots = {
    helmet: [
      {
        id: 1,
        position: [1.5, 1, 0],
        label: '头盔前部',
        icon: '🔲',
        title: '头盔前部',
        description: '采用高强度航空级铝合金材质，经过精密CNC加工和阳极氧化处理，确保表面光滑耐磨，具有出色的抗腐蚀性能。',
        features: ['高强度铝合金', 'CNC精密加工', '阳极氧化处理', '耐磨抗腐蚀', '轻量化设计']
      },
      {
        id: 2,
        position: [-1, 0.8, 1],
        label: '接口模块',
        icon: '🔌',
        title: '通讯接口模块',
        description: '集成多种高速接口，支持USB 3.2、HDMI 2.1等，满足各种外设连接需求。接口采用镀金处理，信号传输稳定可靠。',
        features: ['USB 3.2 高速接口', 'HDMI 2.1 输出', '镀金触点设计', '智能电源管理', '即插即用']
      },
      {
        id: 3,
        position: [0, 2, 0.5],
        label: '顶部传感器',
        icon: '🌬️',
        title: '智能传感器阵列',
        description: '采用流体动力学设计的散热系统，配备静音涡轮风扇和大面积散热鳍片，有效降低运行温度，延长设备使用寿命。',
        features: ['多传感器融合', '智能环境感知', '温度自动控制', '防尘过滤网', '静音运行']
      }
    ],
    duck: [
      {
        id: 4,
        position: [0, 2.5, 0],
        label: '小黄鸭',
        icon: '🦆',
        title: '经典小黄鸭',
        description: '童年经典的小黄鸭造型，采用环保无毒的PVC材质，安全可靠。表面采用哑光喷涂工艺，手感细腻。',
        features: ['环保PVC材质', '无毒无害', '哑光喷涂工艺', '细腻手感', '经典设计']
      },
      {
        id: 5,
        position: [1, 1, 0.5],
        label: '鸭嘴',
        icon: '👄',
        title: '橙色鸭嘴',
        description: '鲜艳的橙色鸭嘴，使用食品级硅胶材质，柔软有弹性，安全无毒。',
        features: ['食品级硅胶', '柔软有弹性', '安全无毒', '鲜艳色彩', '耐黄变']
      }
    ],
    avocado: [
      {
        id: 6,
        position: [0, 0.5, 0],
        label: '牛油果',
        icon: '🥑',
        title: '仿真牛油果',
        description: '1:1比例还原真实牛油果，纹理细节逼真，颜色采用渐变喷涂技术，呈现自然的绿色渐变效果。',
        features: ['1:1真实比例', '纹理细节逼真', '渐变喷涂技术', '自然绿色渐变', '环保材料']
      },
      {
        id: 7,
        position: [0.3, 0.3, 0.3],
        label: '果核',
        icon: '🌰',
        title: '大果核',
        description: '椭圆形大果核，表面采用磨砂处理，质感出众，颜色采用天然棕色系，与果肉形成鲜明对比。',
        features: ['椭圆形设计', '磨砂表面处理', '天然棕色系', '质感出众', '与果肉对比鲜明']
      }
    ],
    torus: [
      {
        id: 8,
        position: [0, 1.5, 0],
        label: '环形结',
        icon: '🔗',
        title: '数学之美',
        description: '基于复杂数学公式生成的3D环形结结构，展示数学与艺术的完美结合，每一个角度都是新的发现。',
        features: ['数学公式生成', '复杂拓扑结构', '360度无死角', '几何美学', '参数化设计']
      },
      {
        id: 9,
        position: [1, 0.5, 0],
        label: '曲面细节',
        icon: '📐',
        title: '精密曲面',
        description: '每一个曲面都经过精密计算，使用高多边形网格，确保曲面平滑过渡，呈现完美的光影效果。',
        features: ['高多边形网格', '平滑过渡', '完美光影', '数学精确性', '无限细节']
      }
    ]
  }

  const currentHotspots = hotspots[modelType] || hotspots.helmet

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset()
    }
    setIsPlaying(false)
  }

  const updateMaterial = (key, value) => {
    setMaterialProps((prev) => ({ ...prev, [key]: value }))
  }

  const handleHotspotClick = (hotspot) => {
    setActiveHotspot(hotspot)
    setShowModal(true)
  }

  const handleAnimationComplete = () => {
    setIsPlaying(false)
  }

  const backgroundPresets = [
    '#1a1a2e',
    '#16213e',
    '#0f3460',
    '#533483',
    '#2d3436',
    '#636e72',
    '#2c3e50',
    '#34495e'
  ]

  return (
    <div className="app-container">
      <div className="canvas-container">
        <Canvas
          camera={{ position: [3, 3, 3], fov: 50 }}
          gl={{
            antialias: true,
            powerPreference: 'high-performance',
            failIfMajorPerformanceCaveat: true
          }}
          style={{ background: backgroundColor }}
          onCreated={({ gl }) => {
            gl.setPixelRatio(Math.min(window.devicePixelRatio, 2))
          }}
        >
          <SceneCleaner />

          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
          <directionalLight position={[-10, -10, -5]} intensity={0.3} />

          <Environment />
          <Model modelType={modelType} materialProps={materialProps} />

          {currentHotspots.map((hotspot) => (
            <Hotspot
              key={hotspot.id}
              position={hotspot.position}
              label={hotspot.label}
              icon={hotspot.icon}
              onClick={() => handleHotspotClick(hotspot)}
              isActive={activeHotspot?.id === hotspot.id}
            />
          ))}

          <CameraAnimation
            animation={animation}
            isPlaying={isPlaying}
            onComplete={handleAnimationComplete}
            controlsRef={controlsRef}
          />

          <OrbitControls
            ref={controlsRef}
            enableDamping
            dampingFactor={0.05}
            minDistance={1}
            maxDistance={10}
            makeDefault
            enableTouch={true}
            touchAction="none"
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            touches={{
              ONE: THREE.TOUCH.ROTATE,
              TWO: THREE.TOUCH.DOLLY_PAN
            }}
          />
        </Canvas>
      </div>

      <ControlPanel
        materialProps={materialProps}
        updateMaterial={updateMaterial}
        backgroundColor={backgroundColor}
        setBackgroundColor={setBackgroundColor}
        backgroundPresets={backgroundPresets}
        resetCamera={resetCamera}
        animation={animation}
        setAnimation={setAnimation}
        isPlaying={isPlaying}
        setIsPlaying={setIsPlaying}
        hotspots={currentHotspots}
        activeHotspot={activeHotspot}
        setActiveHotspot={setActiveHotspot}
        modelType={modelType}
        setModelType={setModelType}
      />

      <ProductModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false)
          setActiveHotspot(null)
        }}
        hotspot={activeHotspot}
      />
    </div>
  )
}

export default App
