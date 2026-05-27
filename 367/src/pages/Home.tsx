import { useEffect } from 'react';
import GraphCanvas from '@/components/GraphCanvas';
import Toolbar from '@/components/Toolbar';
import DetailPanel from '@/components/DetailPanel';
import StatusBar from '@/components/StatusBar';
import DataImportDialog from '@/components/DataImport';
import Timeline from '@/components/Timeline';
import { useGraphStore } from '@/store/graphStore';
import { sampleTriples } from '@/utils/sampleData';

export default function Home() {
  const hoveredNode = useGraphStore((s) => s.hoveredNode);
  const pathResult = useGraphStore((s) => s.pathResult);
  const loadTriples = useGraphStore((s) => s.loadTriples);

  useEffect(() => {
    loadTriples(sampleTriples);
  }, [loadTriples]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#070b14]">
      <Toolbar />
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 relative">
          <GraphCanvas
            pathResult={pathResult}
            hoveredNodeId={hoveredNode}
          />
        </div>
        <DetailPanel />
      </div>
      <Timeline />
      <StatusBar />
      <DataImportDialog />
    </div>
  );
}
