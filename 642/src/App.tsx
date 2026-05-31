import { useState } from 'react'
import { Navbar } from '@/components/Navbar'
import { Toolbar } from '@/components/Toolbar'
import { ControlPanel } from '@/components/ControlPanel'
import { StatusBar } from '@/components/StatusBar'
import { FluidCanvas } from '@/components/FluidCanvas'

function App() {
  const [canvas, setCanvas] = useState<HTMLCanvasElement | null>(null)

  return (
    <div className="w-full h-full relative overflow-hidden bg-space-blue">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyber-cyan/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-neon-purple/5 rounded-full blur-3xl" />
      </div>

      <Navbar />
      <Toolbar />
      <ControlPanel canvas={canvas} />
      <StatusBar />

      <div className="absolute inset-0 pt-20 pb-16 px-20">
        <div className="w-full h-full rounded-xl overflow-hidden border border-cyber-cyan/20 shadow-2xl">
          <FluidCanvas onCanvasReady={setCanvas} />
        </div>
      </div>

      <div className="absolute bottom-24 left-1/2 -translate-x-1/2 text-center pointer-events-none">
        <p className="text-xs text-gray-500">
          点击并拖动鼠标与流体交互
        </p>
      </div>
    </div>
  )
}

export default App
