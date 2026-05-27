import React, { useEffect, useState } from 'react';
import { Header } from '@/components/Header/Header';
import { Toolbar } from '@/components/Toolbar/Toolbar';
import { AnnotationCanvas } from '@/components/Canvas/AnnotationCanvas';
import { Sidebar } from '@/components/Sidebar/Sidebar';
import { StatusBar } from '@/components/StatusBar/StatusBar';
import { useAnnotationStore } from '@/store/useAnnotationStore';
import { getImageData } from '@/services/api';

function App() {
  const { images, currentImageId } = useAnnotationStore();
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (currentImageId) {
      const currentImage = images.find(img => img.id === currentImageId);
      if (currentImage?.url) {
        setCurrentImageUrl(currentImage.url);
      } else {
        getImageData(currentImageId).then(url => {
          setCurrentImageUrl(url);
        }).catch(() => {
          setCurrentImageUrl(null);
        });
      }
    } else {
      setCurrentImageUrl(null);
    }
  }, [currentImageId, images]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      const { setCurrentTool } = useAnnotationStore.getState();
      
      switch (e.key.toLowerCase()) {
        case 'v':
          setCurrentTool('select');
          break;
        case 'p':
          setCurrentTool('polygon');
          break;
        case 'o':
          setCurrentTool('point');
          break;
        case 'r':
          setCurrentTool('rectangle');
          break;
        case 'b':
          setCurrentTool('brush');
          break;
        case 's':
          setCurrentTool('sam');
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-white overflow-hidden">
      <Header />
      
      <div className="flex flex-1 overflow-hidden">
        <Toolbar />
        <main className="flex-1 relative overflow-hidden">
          <AnnotationCanvas imageUrl={currentImageUrl} />
        </main>
        <Sidebar />
      </div>
      
      <StatusBar />
    </div>
  );
}

export default App;
