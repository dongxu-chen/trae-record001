import { useState, useRef, useEffect } from 'react';
import { Layers, Wand2, Github, Download, Brain, Activity, Store } from 'lucide-react';
import FilterPanel from '@/components/FilterPanel';
import PreviewCanvas from '@/components/PreviewCanvas';
import ParamsPanel from '@/components/ParamsPanel';
import ImageUploader from '@/components/ImageUploader';
import CustomFilterModal from '@/components/CustomFilterModal';
import ExportModal from '@/components/ExportModal';
import BatchPanel from '@/components/BatchPanel';
import AIRecommendPanel from '@/components/AIRecommendPanel';
import AnimationPanel from '@/components/AnimationPanel';
import MarketplaceModal from '@/components/MarketplaceModal';
import useFilterStore from '@/store/filterStore';
import { cn } from '@/lib/utils';

export default function Home() {
  const [showCustomFilterModal, setShowCustomFilterModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showBatchPanel, setShowBatchPanel] = useState(false);
  const [showMarketplaceModal, setShowMarketplaceModal] = useState(false);
  const [selectedImageElement, setSelectedImageElement] = useState<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { images, selectedImageId, toggleExportModal, showExportModal: storeShowExportModal } =
    useFilterStore();

  useEffect(() => {
    if (storeShowExportModal) {
      setShowExportModal(true);
    }
  }, [storeShowExportModal]);

  useEffect(() => {
    if (selectedImageId) {
      const selectedImage = images.find((img) => img.id === selectedImageId);
      if (selectedImage) {
        const img = new Image();
        img.onload = () => {
          setSelectedImageElement(img);
        };
        img.src = selectedImage.src;
      }
    } else {
      setSelectedImageElement(null);
    }
  }, [selectedImageId, images]);

  const handleExport = async (format: string, quality: number) => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;

    const mimeType =
      format === 'png'
        ? 'image/png'
        : format === 'webp'
        ? 'image/webp'
        : 'image/jpeg';

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const selectedImage = images.find((img) => img.id === selectedImageId);
        const baseName = selectedImage?.name.replace(/\.[^/.]+$/, '') || 'filtered';
        a.download = `${baseName}_lumifx.${format}`;
        a.click();
        URL.revokeObjectURL(url);
      },
      mimeType,
      quality
    );

    setShowExportModal(false);
  };

  const handleBatchProcess = async () => {
    console.log('Batch processing...');
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-surface-dark grid-bg overflow-hidden">
      <header className="h-14 border-b border-surface-border glass-panel flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center neon-glow">
            <Wand2 size={18} className="text-white" />
          </div>
          <h1 className="font-display font-bold text-xl tracking-tight">
            <span className="neon-text">Lumi</span>
            <span className="text-white">FX</span>
          </h1>
          <span className="text-xs text-gray-500 ml-2 px-2 py-0.5 bg-surface-card rounded-full">
            v1.0
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMarketplaceModal(true)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2',
              'bg-surface-card hover:bg-surface-hover border border-transparent hover:border-neon-cyan/30'
            )}
          >
            <Store size={16} />
            滤镜市场
          </button>
          <button
            onClick={() => setShowBatchPanel(!showBatchPanel)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2',
              showBatchPanel
                ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
                : 'bg-surface-card hover:bg-surface-hover border border-transparent'
            )}
          >
            <Layers size={16} />
            批量处理
          </button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg bg-surface-card hover:bg-surface-hover transition-colors"
          >
            <Github size={18} />
          </a>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-72 flex-shrink-0 p-4 overflow-y-auto space-y-4">
          <FilterPanel onUploadCustom={() => setShowCustomFilterModal(true)} />
          <AIRecommendPanel imageElement={selectedImageElement} />
          <AnimationPanel />
        </aside>

        <main className="flex-1 flex flex-col min-w-0 p-4">
          <div className="mb-4 flex-shrink-0">
            <ImageUploader />
          </div>
          <div className="flex-1 min-h-0 glass-panel rounded-xl overflow-hidden">
            <PreviewCanvas />
          </div>
        </main>

        <aside className="w-80 flex-shrink-0 p-4 overflow-y-auto">
          <ParamsPanel onExport={() => setShowExportModal(true)} />
        </aside>
      </div>

      <CustomFilterModal
        isOpen={showCustomFilterModal}
        onClose={() => setShowCustomFilterModal(false)}
      />

      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        onExport={handleExport}
      />

      <BatchPanel
        isOpen={showBatchPanel}
        onClose={() => setShowBatchPanel(false)}
        onProcess={handleBatchProcess}
      />

      <MarketplaceModal
        isOpen={showMarketplaceModal}
        onClose={() => setShowMarketplaceModal(false)}
      />
    </div>
  );
}
