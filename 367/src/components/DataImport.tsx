import { useRef } from 'react';
import { X, FileJson } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import { sampleTriples } from '@/utils/sampleData';
import type { Triple } from '@/types';

export default function DataImportDialog() {
  const importDialogOpen = useGraphStore((s) => s.importDialogOpen);
  const setImportDialogOpen = useGraphStore((s) => s.setImportDialogOpen);
  const importText = useGraphStore((s) => s.importText);
  const setImportText = useGraphStore((s) => s.setImportText);
  const loadTriples = useGraphStore((s) => s.loadTriples);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!importDialogOpen) return null;

  const handleImport = () => {
    const text = importText.trim();
    if (!text) return;
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        loadTriples(parsed as Triple[]);
      } else {
        alert('数据格式错误，应为三元组数组');
      }
    } catch {
      const lines = text.split('\n').filter((l) => l.trim());
      const triples: Triple[] = lines.map((line) => {
        const parts = line.split(/\t|,|\|/).map((p) => p.trim());
        return {
          subject: parts[0] || '',
          predicate: parts[1] || '',
          object: parts[2] || '',
        };
      });
      loadTriples(triples);
    }
    setImportDialogOpen(false);
    setImportText('');
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setImportText(evt.target?.result as string);
    };
    reader.readAsText(file);
  };

  const loadSample = () => {
    loadTriples(sampleTriples);
    setImportDialogOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-[600px] max-h-[80vh] glass-panel rounded-xl overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-200 font-medium">
            <FileJson size={18} />
            导入三元组数据
          </div>
          <button
            onClick={() => setImportDialogOpen(false)}
            className="text-slate-500 hover:text-slate-300"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          <div className="text-xs text-slate-400 mb-2">
            粘贴 JSON 三元组数组，或 TSV/CSV 格式（subject, predicate, object）
          </div>
          <textarea
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder={`[\n  {"subject": "张三", "predicate": "就职于", "object": "华为"}\n]`}
            className="w-full h-48 rounded-lg bg-slate-800/60 border border-slate-600/50 p-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 font-mono resize-none"
          />
          <div className="mt-3 flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.tsv,.csv,.txt"
              onChange={handleFile}
              className="text-xs text-slate-400 file:mr-3 file:rounded-md file:border-0 file:bg-slate-700/60 file:px-3 file:py-1 file:text-xs file:text-slate-200 hover:file:bg-slate-600/60"
            />
          </div>
          <div className="mt-4 pt-4 border-t border-slate-700/50">
            <button
              onClick={loadSample}
              className="w-full rounded-lg bg-slate-800/60 border border-slate-600/50 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700/60 transition-all"
            >
              加载示例数据
            </button>
          </div>
        </div>

        <div className="p-4 border-t border-slate-700/50 flex justify-end gap-2">
          <button
            onClick={() => setImportDialogOpen(false)}
            className="rounded-lg bg-slate-800/60 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700/60 transition-all"
          >
            取消
          </button>
          <button
            onClick={handleImport}
            className="rounded-lg bg-cyan-500/20 border border-cyan-400/30 px-4 py-2 text-sm text-cyan-300 hover:bg-cyan-500/30 transition-all"
          >
            导入
          </button>
        </div>
      </div>
    </div>
  );
}
