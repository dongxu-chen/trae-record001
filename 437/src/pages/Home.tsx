import React, { useState } from 'react';
import { Toolbar } from '../components/Toolbar/Toolbar';
import { Sidebar } from '../components/Sidebar/Sidebar';
import { FlowCanvas } from '../components/Canvas/FlowCanvas';
import { RightPanel } from '../components/RightPanel/RightPanel';

export default function Home() {
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden">
      <Toolbar />
      <div className="flex-1 flex min-h-0">
        <Sidebar isCollapsed={leftCollapsed} onToggle={() => setLeftCollapsed(!leftCollapsed)} />
        <main className="flex-1 min-w-0 bg-slate-900">
          <FlowCanvas />
        </main>
        <RightPanel isCollapsed={rightCollapsed} onToggle={() => setRightCollapsed(!rightCollapsed)} />
      </div>
    </div>
  );
}
