import { useState } from 'react';
import { Sidebar } from '@/components/Layout/Sidebar';
import { SearchPage } from '@/pages/SearchPage';
import { NetworkPage } from '@/pages/NetworkPage';
import { InfluencePage } from '@/pages/InfluencePage';
import { TrendsPage } from '@/pages/TrendsPage';
import RecommendationPage from '@/pages/RecommendationPage';
import CollaborationPage from '@/pages/CollaborationPage';
import PredictionPage from '@/pages/PredictionPage';
import { useAppStore } from '@/store';

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { currentPage } = useAppStore();

  const renderPage = () => {
    switch (currentPage) {
      case 'search':
        return <SearchPage />;
      case 'network':
        return <NetworkPage />;
      case 'influence':
        return <InfluencePage />;
      case 'trends':
        return <TrendsPage />;
      case 'recommendations':
        return <RecommendationPage />;
      case 'collaboration':
        return <CollaborationPage />;
      case 'prediction':
        return <PredictionPage />;
      default:
        return <SearchPage />;
    }
  };

  return (
    <div className="min-h-screen bg-dark-900">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      
      <main
        className={`transition-all duration-300 min-h-screen ${
          sidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        {renderPage()}
      </main>
    </div>
  );
}
