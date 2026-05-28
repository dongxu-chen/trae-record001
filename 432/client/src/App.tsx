import React from 'react';
import { PdfProvider, usePdfContext } from './contexts/PdfContext';
import PdfUploader from './components/PdfUploader';
import Toolbar from './components/Toolbar';
import PdfCanvas from './components/PdfCanvas';
import Sidebar from './components/Sidebar';

const AppContent: React.FC = () => {
  const { state } = usePdfContext();
  const { document } = state;

  if (!document) {
    return <PdfUploader />;
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4">
        <h1 className="text-lg font-semibold text-gray-800">PDF标注工具</h1>
        <span className="ml-4 text-sm text-gray-500 truncate max-w-md">
          {document.name}
        </span>
      </div>
      <Toolbar />
      <div className="flex-1 flex overflow-hidden">
        <PdfCanvas />
        <Sidebar />
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <PdfProvider>
      <AppContent />
    </PdfProvider>
  );
};

export default App;
