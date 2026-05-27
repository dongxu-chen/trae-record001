import React from 'react';
import Toolbar from '@/components/Toolbar';
import ConfigPanel from '@/components/ConfigPanel';
import ChartPreview from '@/components/ChartPreview';
import '@/styles/global.less';

const App: React.FC = () => {
  return (
    <div className="app-container">
      <Toolbar />
      <div className="main-content">
        <ConfigPanel />
        <ChartPreview />
      </div>
    </div>
  );
};

export default App;
