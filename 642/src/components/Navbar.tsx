import { Droplets, HelpCircle, Settings, FileDown } from 'lucide-react'

export function Navbar() {
  return (
    <nav className="absolute top-0 left-0 right-0 z-20">
      <div className="glass-panel mx-4 mt-4 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyber-cyan to-neon-purple flex items-center justify-center">
            <Droplets className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold neon-text font-orbitron tracking-wider">
              FLUID SIM
            </h1>
            <p className="text-xs text-gray-400">GPU 流体仿真可视化工具</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="tool-button" title="导出">
            <FileDown className="w-5 h-5" />
          </button>
          <button className="tool-button" title="设置">
            <Settings className="w-5 h-5" />
          </button>
          <button className="tool-button" title="帮助">
            <HelpCircle className="w-5 h-5" />
          </button>
        </div>
      </div>
    </nav>
  )
}
