import React, { useState, useRef } from 'react';
import { FileCode, Copy, Download, Check, FileText } from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { downloadScript, copyToClipboard, downloadRequirements } from '../../utils/scriptGenerator';

interface ScriptPreviewProps {
  className?: string;
}

export const ScriptPreview: React.FC<ScriptPreviewProps> = ({ className = '' }) => {
  const { cleaningResult } = useDataStore();
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLPreElement>(null);

  const handleCopy = async () => {
    if (cleaningResult?.script) {
      await copyToClipboard(cleaningResult.script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (cleaningResult?.script) {
      downloadScript(cleaningResult.script, 'cleaning_script.py');
    }
  };

  const handleDownloadRequirements = () => {
    downloadRequirements();
  };

  if (!cleaningResult?.script) {
    return (
      <div className={`card ${className}`}>
        <div className="card-header">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <FileCode size={18} className="text-primary-400" />
            清洗脚本
          </h3>
        </div>
        <div className="card-body">
          <div className="text-center py-12 text-bg-500">
            <FileCode size={48} className="mx-auto mb-4 opacity-30" />
            <p>完成数据清洗后，此处将显示对应的Python/Pandas脚本</p>
          </div>
        </div>
      </div>
    );
  }

  const lines = cleaningResult.script.split('\n');
  const maxLineNumber = lines.length.toString().length;

  return (
    <div className={`card ${className}`}>
      <div className="card-header flex items-center justify-between">
        <h3 className="font-semibold text-bg-100 flex items-center gap-2">
          <FileCode size={18} className="text-primary-400" />
          Python/Pandas 清洗脚本
        </h3>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="btn btn-ghost text-sm"
            title="复制脚本"
          >
            {copied ? <Check size={16} className="text-success-400" /> : <Copy size={16} />}
            {copied ? '已复制' : '复制'}
          </button>
          <button
            onClick={handleDownloadRequirements}
            className="btn btn-secondary text-sm"
            title="下载 requirements.txt"
          >
            <FileText size={16} />
            requirements.txt
          </button>
          <button
            onClick={handleDownload}
            className="btn btn-success text-sm"
            title="下载脚本"
          >
            <Download size={16} />
            下载 .py
          </button>
        </div>
      </div>
      <div className="card-body p-0">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <pre
            ref={codeRef}
            className="code-block !m-0 !rounded-none !border-0"
          >
            {lines.map((line, idx) => (
              <div key={idx} className="flex">
                <span className="inline-block text-bg-600 select-none text-right pr-4 min-w-[3rem]">
                  {(idx + 1).toString().padStart(maxLineNumber, ' ')}
                </span>
                <code>{line || ' '}</code>
              </div>
            ))}
          </pre>
        </div>
      </div>
    </div>
  );
};
