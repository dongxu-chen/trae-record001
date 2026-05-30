import React from 'react';
import { Canvas } from '../components/Canvas';
import { PropertyPanel } from '../components/PropertyPanel';

const Home: React.FC = () => {
  return (
    <div className="h-screen w-screen flex flex-col bg-slate-900 overflow-hidden">
      <header className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-xl flex items-center justify-center text-white text-xl shadow-lg shadow-cyan-500/30">
            ◇
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              ShapeRecognizer
            </h1>
            <p className="text-xs text-slate-400">
              智能几何形状识别与编辑工具
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 text-sm text-slate-400">
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-slate-800 rounded-full">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              后端服务运行中
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <a
              href="#"
              className="px-3 py-2 text-slate-400 hover:text-white transition-colors text-sm"
            >
              帮助
            </a>
            <a
              href="#"
              className="px-3 py-2 text-slate-400 hover:text-white transition-colors text-sm"
            >
              快捷键
            </a>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 overflow-hidden">
          <Canvas />
        </main>
        <aside className="flex-shrink-0">
          <PropertyPanel />
        </aside>
      </div>
    </div>
  );
};

export default Home;
