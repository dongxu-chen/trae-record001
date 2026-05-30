import React, { useState, useRef, useEffect, useMemo } from 'react';
import { IconConfig, normalizeConfig, createBatchConfig } from '../engine/types';
import { IconGenerator } from '../engine/IconGenerator';
import { Layers, Plus, Trash2, Download, Play } from 'lucide-react';

interface BatchItem {
  id: string;
  text: string;
}

interface BatchGeneratorProps {
  baseConfig: IconConfig;
  onGenerateAll?: () => void;
}

export function BatchGenerator({ baseConfig }: BatchGeneratorProps) {
  const [items, setItems] = useState<BatchItem[]>([
    { id: '1', text: 'A' },
    { id: '2', text: 'B' },
    { id: '3', text: 'C' },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedIcons, setGeneratedIcons] = useState<{ id: string; dataUrl: string }[]>([]);
  const previewCanvasRefs = useRef<Map<string, HTMLCanvasElement>>(new Map());

  const normalizedBase = useMemo(() => normalizeConfig(baseConfig), [baseConfig]);

  const addItem = () => {
    const newId = Date.now().toString();
    setItems([...items, { id: newId, text: '' }]);
  };

  const removeItem = (id: string) => {
    setItems(items.filter((item) => item.id !== id));
    setGeneratedIcons(generatedIcons.filter((icon) => icon.id !== id));
  };

  const updateItemText = (id: string, text: string) => {
    setItems(
      items.map((item) =>
        item.id === id ? { ...item, text } : item
      )
    );
  };

  const generateBatch = async () => {
    setIsGenerating(true);
    const newGeneratedIcons: { id: string; dataUrl: string }[] = [];

    items.forEach((item) => {
      if (item.text) {
        const config = createBatchConfig(normalizedBase, { text: item.text || 'A' });
        const dataUrl = IconGenerator.generateFromConfig(config);
        newGeneratedIcons.push({ id: item.id, dataUrl });
      }
    });

    setGeneratedIcons(newGeneratedIcons);
    setIsGenerating(false);
  };

  const downloadAll = () => {
    generatedIcons.forEach((icon, index) => {
      const item = items.find((i) => i.id === icon.id);
      if (item) {
        const link = document.createElement('a');
        link.download = `icon-${item.text || index + 1}.png`;
        link.href = icon.dataUrl;
        link.click();
      }
    });
  };

  useEffect(() => {
    items.forEach((item) => {
      const canvas = previewCanvasRefs.current.get(item.id);
      if (canvas && item.text) {
        const generator = new IconGenerator(canvas);
        const config = createBatchConfig(normalizedBase, { text: item.text || 'A' });
        generator.generate(config);
      }
    });
  }, [items, normalizedBase]);

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-xl">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">批量生成</h3>
            <p className="text-sm text-gray-500">同时生成多个图标</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={addItem}
            className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-emerald-600 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加
          </button>
        </div>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
        {items.map((item, index) => (
          <div
            key={item.id}
            className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl"
          >
            <div className="flex-shrink-0 w-16 h-16 bg-white rounded-lg overflow-hidden shadow-md">
              <canvas
                ref={(el) => {
                  if (el) previewCanvasRefs.current.set(item.id, el);
                }}
                width={64}
                height={64}
                className="w-full h-full"
              />
            </div>

            <div className="flex-grow">
              <input
                type="text"
                value={item.text}
                onChange={(e) => updateItemText(item.id, e.target.value)}
                maxLength={2}
                placeholder="输入文字"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100 text-center font-semibold uppercase"
              />
            </div>

            <span className="text-sm text-gray-500 font-mono">
              #{index + 1}
            </span>

            <button
              onClick={() => removeItem(item.id)}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              disabled={items.length <= 1}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mt-6 pt-4 border-t border-gray-100">
        <button
          onClick={generateBatch}
          disabled={isGenerating || items.length === 0}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-medium hover:from-emerald-600 hover:to-teal-600 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="w-4 h-4" />
          {isGenerating ? '生成中...' : '生成全部'}
        </button>

        <button
          onClick={downloadAll}
          disabled={generatedIcons.length === 0}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="w-4 h-4" />
          下载全部
        </button>
      </div>

      {generatedIcons.length > 0 && (
        <div className="mt-4 p-4 bg-emerald-50 rounded-xl">
          <p className="text-sm text-emerald-700">
            已生成 <span className="font-semibold">{generatedIcons.length}</span> 个图标，点击"下载全部"按钮下载
          </p>
        </div>
      )}
    </div>
  );
}
