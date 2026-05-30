import { Header } from '@/components/Header';
import { SearchPanel } from '@/components/SearchPanel';
import { LineageGraph } from '@/components/LineageGraph';
import { DetailPanel } from '@/components/DetailPanel';
import { DataSourceModal } from '@/components/DataSourceModal';
import { useLineageStore } from '@/stores/useLineageStore';
import { exportReport } from '@/utils/export';

function App() {
  const { analysisResult, riskAssessment, fieldDictionary } = useLineageStore();

  const handleExport = (format: 'json' | 'excel') => {
    if (analysisResult) {
      exportReport(analysisResult, format, riskAssessment || undefined, fieldDictionary || undefined);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-white">
      <Header onExport={handleExport} />
      <div className="flex-1 flex overflow-hidden">
        <SearchPanel />
        <LineageGraph />
        <DetailPanel />
      </div>
      <DataSourceModal />
    </div>
  );
}

export default App;
