import { useState, useCallback } from 'react'
import ParticleCanvas from './components/ParticleCanvas'
import ControlPanel from './components/ControlPanel'
import './App.css'

function App() {
  const [config, setConfig] = useState({
    text: 'Hello',
    animationType: 'gather',
    speed: 1,
    particleSize: 2,
    particleColor: '#00d4ff',
    trailLength: 10,
    showTrail: false,
    backgroundColor: '#0a0a1a',
    backgroundEffect: 'none',
    particleSpacing: 4,
    physicsEnabled: false,
    gravity: 0.15,
    bounce: false,
    collision: false,
    mouseRadius: 120,
    mouseForce: 0.8
  })

  const [particleCount, setParticleCount] = useState(0)

  const handleParticleCount = useCallback((count) => {
    setParticleCount(count)
  }, [])

  return (
    <div className="app">
      <div className="canvas-container">
        <ParticleCanvas config={config} onParticleCount={handleParticleCount} />
        <div className="hint">点击画布重置粒子</div>
      </div>
      <ControlPanel config={config} setConfig={setConfig} particleCount={particleCount} />
    </div>
  )
}

export default App
