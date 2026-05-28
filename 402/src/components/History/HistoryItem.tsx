import { useState } from 'react';
import { Copy, Check, Trash2, Edit3, Save } from 'lucide-react';
import type { ScanRecord } from '../../types';

interface HistoryItemProps {
  record: ScanRecord;
  selected: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onUpdateNote: (id: string, note: string) => void;
}

export function HistoryItem({
  record,
  selected,
  onSelect,
  onDelete,
  onUpdateNote,
}: HistoryItemProps) {
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState(record.note || '');

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const typeLabels: Record<string, string> = {
    qrcode: '二维码',
    barcode: '条形码',
    manual: '手动输入',
  };

  const typeColors: Record<string, string> = {
    qrcode: 'bg-blue-500/20 text-blue-400',
    barcode: 'bg-green-500/20 text-green-400',
    manual: 'bg-purple-500/20 text-purple-400',
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(record.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleSaveNote = () => {
    onUpdateNote(record.id, note);
    setEditing(false);
  };

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-200 ${
        selected
          ? 'border-blue-500 bg-blue-500/10'
          : 'border-gray-700/50 bg-[#161b22] hover:border-gray-600'
      }`}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onSelect(record.id)}
          className="mt-1 w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 bg-gray-700"
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded ${
                typeColors[record.type] || 'bg-gray-500/20 text-gray-400'
              }`}
            >
              {typeLabels[record.type] || record.type}
            </span>
            <span className="text-xs text-gray-500">{formatTime(record.timestamp)}</span>
          </div>

          <p className="text-white text-sm font-mono break-all line-clamp-2 mb-2">
            {record.content}
          </p>

          {editing ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="添加备注..."
                className="flex-1 px-3 py-1.5 text-sm bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                autoFocus
              />
              <button
                onClick={handleSaveNote}
                className="p-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors"
              >
                <Save className="w-4 h-4" />
              </button>
            </div>
          ) : (
            record.note && (
              <p className="text-gray-400 text-sm">
                <span className="text-gray-500">备注:</span> {record.note}
              </p>
            )
          )}
        </div>

        <div className="flex items-center gap-1">
          {!editing && (
            <>
              <button
                onClick={handleCopy}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
                title="复制"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => setEditing(true)}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
                title="编辑备注"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDelete(record.id)}
                className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
