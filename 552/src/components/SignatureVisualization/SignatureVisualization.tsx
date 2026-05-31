import { useMemo } from 'react';
import { MapPin, FileText, Layers } from 'lucide-react';
import type { SignatureVisualization as SignatureVisualizationType } from '../../../shared';
import { cn } from '@/lib/utils';

interface SignatureVisualizationProps {
  visualization?: SignatureVisualizationType;
}

export default function SignatureVisualization({ visualization }: SignatureVisualizationProps) {
  if (!visualization || !visualization.hasVisualRepresentation) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
          <MapPin className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">无可视化签名位置</h3>
        <p className="text-gray-500 text-sm">该文档中的签名没有可见的位置标注，或者签名不可视</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-gray-600 bg-blue-50 p-3 rounded-lg">
        <Layers className="w-4 h-4 text-blue-600" />
        <span>文档共 <strong>{visualization.pageCount}</strong> 页，发现 <strong>{visualization.positions.length}</strong> 个签名位置</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visualization.positions.map((pos, idx) => (
          <SignaturePositionCard key={idx} position={pos} index={idx} />
        ))}
      </div>

      <PagePreview positions={visualization.positions} pageCount={visualization.pageCount} />
    </div>
  );
}

function SignaturePositionCard({ position, index }: { position: any; index: number }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          <MapPin className="w-4 h-4 text-blue-600" />
        </div>
        <div>
          <div className="font-medium text-gray-900 text-sm">签名 {index + 1}</div>
          <div className="text-xs text-gray-500">{position.fieldName}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-gray-50 rounded p-2">
          <span className="text-gray-500">页面</span>
          <div className="font-medium text-gray-900">第 {position.pageIndex + 1} 页</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <span className="text-gray-500">尺寸</span>
          <div className="font-medium text-gray-900">{position.width.toFixed(0)} × {position.height.toFixed(0)} pt</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <span className="text-gray-500">位置</span>
          <div className="font-medium text-gray-900">X:{position.left.toFixed(0)} Y:{position.top.toFixed(0)}</div>
        </div>
        {position.signerName && (
          <div className="bg-gray-50 rounded p-2">
            <span className="text-gray-500">签名者</span>
            <div className="font-medium text-gray-900 truncate">{position.signerName}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function PagePreview({ positions, pageCount }: { positions: any[]; pageCount: number }) {
  const pagesWithSigs = useMemo(() => {
    const map = new Map<number, any[]>();
    for (const pos of positions) {
      const list = map.get(pos.pageIndex) || [];
      list.push(pos);
      map.set(pos.pageIndex, list);
    }
    return map;
  }, [positions]);

  const PREVIEW_SCALE = 0.35;
  const PAGE_WIDTH = 595;
  const PAGE_HEIGHT = 842;

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900 flex items-center gap-2">
        <FileText className="w-4 h-4" />
        签名位置预览
      </h4>
      <div className="flex flex-wrap gap-4 justify-center">
        {Array.from(pagesWithSigs.entries()).map(([pageIndex, sigs]) => {
          const firstSig = sigs[0];
          const pageW = firstSig?.pageWidth || PAGE_WIDTH;
          const pageH = firstSig?.pageHeight || PAGE_HEIGHT;
          const displayW = pageW * PREVIEW_SCALE;
          const displayH = pageH * PREVIEW_SCALE;

          return (
            <div key={pageIndex} className="flex flex-col items-center gap-2">
              <div
                className="relative border border-gray-300 bg-white shadow-sm rounded"
                style={{ width: displayW, height: displayH }}
              >
                {sigs.map((sig, idx) => {
                  const sigLeft = (sig.left / pageW) * displayW;
                  const sigTop = (sig.top / pageH) * displayH;
                  const sigWidth = (sig.width / pageW) * displayW;
                  const sigHeight = (sig.height / pageH) * displayH;

                  return (
                    <div
                      key={idx}
                      className={cn(
                        'absolute border-2 border-blue-500 bg-blue-100/40 rounded-sm',
                        'flex items-center justify-center cursor-pointer',
                        'hover:bg-blue-200/60 hover:border-blue-600 transition-colors',
                        'group'
                      )}
                      style={{
                        left: Math.max(0, sigLeft),
                        top: Math.max(0, sigTop),
                        width: Math.max(8, sigWidth),
                        height: Math.max(8, sigHeight),
                      }}
                    >
                      <MapPin className="w-3 h-3 text-blue-600 opacity-60 group-hover:opacity-100" />
                    </div>
                  );
                })}
              </div>
              <span className="text-xs text-gray-500">第 {pageIndex + 1} 页</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
