import { Canvas } from '@react-three/fiber'
import { Environment, ContactShadows, Float } from '@react-three/drei'
import Model from './components/Model'
import Controls from './components/Controls'
import ColorPicker from './components/ColorPicker'
import MaterialSwatch from './components/MaterialSwatch'
import ScreenshotButton from './components/ScreenshotButton'
import ARView from './components/ARView'
import EffectControls from './components/EffectControls'
import SnowEffect from './components/SnowEffect'
import useStore from './store/store'
import './App.css'

function Scene() {
  const snowEnabled = useStore((state) => state.snowEnabled)
  const arMode = useStore((state) => state.arMode)

  return (
    <>
      <color attach="background" args={[arMode ? 'transparent' : '#1a1a2e']} />
      {!arMode && <fog attach="fog" args={['#1a1a2e', 5, 20]} />}
      
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[5, 5, 5]}
        intensity={1.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
      />
      <directionalLight position={[-5, 3, -5]} intensity={0.5} />
      <spotLight
        position={[0, 10, 0]}
        angle={0.5}
        penumbra={1}
        intensity={1}
        castShadow
      />
      
      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
        <Model />
      </Float>
      
      {snowEnabled && <SnowEffect count={2000} enabled={snowEnabled} />}
      
      <ContactShadows
        position={[0, -1, 0]}
        opacity={0.4}
        scale={10}
        blur={2.5}
        far={4}
      />
      
      <Environment preset="city" />
      <Controls />
      <ScreenshotButton />
    </>
  )
}

function ControlPanel() {
  const reset = useStore((state) => state.reset)

  return (
    <div className="control-panel">
      <header className="panel-header">
        <h1 className="panel-title">3D 产品配置器</h1>
        <p className="panel-subtitle">自定义您的产品颜色和材质</p>
      </header>
      
      <div className="panel-sections">
        <ColorPicker />
        <MaterialSwatch />
        <EffectControls />
      </div>
      
      <footer className="panel-footer">
        <button className="reset-button" onClick={reset}>
          重置配置
        </button>
        <div className="instructions">
          <p>🖱️ 拖拽旋转 | 滚轮缩放</p>
        </div>
      </footer>
    </div>
  )
}

export default function App() {
  const arMode = useStore((state) => state.arMode)

  return (
    <div className="app-container">
      <div className="canvas-container">
        <Canvas
          shadows
          camera={{ position: [3, 2, 5], fov: 45 }}
          dpr={[1, 2]}
          gl={{ preserveDrawingBuffer: true }}
        >
          <Scene />
        </Canvas>
        <ARView />
      </div>
      <ControlPanel />
    </div>
  )
}
