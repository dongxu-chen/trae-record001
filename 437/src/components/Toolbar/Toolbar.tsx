import React, { useMemo } from 'react';
import { Download, Copy, Trash2, FileCode, GitBranch, Check, Wand2, ChevronDown } from 'lucide-react';
import { useFlowStore } from '../../store/useFlowStore';
import { generateXStateCode } from '../../generators/xstate';
import { generateSpringStateMachineCode } from '../../generators/spring';
import { generatePlantUMLCode } from '../../generators/plantuml';
import { generateGraphvizCode } from '../../generators/graphviz';
import { generateTestCases, generateJestTests, generatePlainTextTests } from '../../generators/testGenerator';
import { formatTypeScript, formatJavaSimple } from '../../utils/format';
import { CodeFormat } from '../../types';

const exportConfig: Record<CodeFormat, { label: string; fileName: string }> = {
  xstate: { label: 'XState (TypeScript)', fileName: 'stateMachine.ts' },
  spring: { label: 'Spring StateMachine (Java)', fileName: 'StateMachineConfig.java' },
  plantuml: { label: 'PlantUML', fileName: 'stateMachine.puml' },
  graphviz: { label: 'Graphviz (DOT)', fileName: 'stateMachine.dot' },
  'test-jest': { label: 'Jest Tests', fileName: 'stateMachine.test.ts' },
  'test-plain': { label: 'Test Cases (Markdown)', fileName: 'testCases.md' },
};

export const Toolbar: React.FC = () => {
  const { nodes, edges, codeFormat, setCodeFormat, clearCanvas, loadExample } = useFlowStore();
  const [copied, setCopied] = React.useState(false);
  const [showExportMenu, setShowExportMenu] = React.useState(false);

  const formattedCode = useMemo(async () => {
    let rawCode: string;
    switch (codeFormat) {
      case 'xstate':
        rawCode = generateXStateCode(nodes, edges);
        return formatTypeScript(rawCode);
      case 'spring':
        rawCode = generateSpringStateMachineCode(nodes, edges);
        return formatJavaSimple(rawCode);
      case 'plantuml':
        return generatePlantUMLCode(nodes, edges);
      case 'graphviz':
        return generateGraphvizCode(nodes, edges);
      case 'test-jest': {
        const testSuite = generateTestCases(nodes, edges);
        rawCode = generateJestTests(testSuite);
        return formatTypeScript(rawCode);
      }
      case 'test-plain': {
        const testSuite = generateTestCases(nodes, edges);
        return generatePlainTextTests(testSuite);
      }
      default:
        return '';
    }
  }, [nodes, edges, codeFormat]);

  const handleCopyCode = async () => {
    const code = await formattedCode;
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    const code = await formattedCode;
    const fileName = exportConfig[codeFormat].fileName;
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportFormat = async (format: CodeFormat) => {
    setCodeFormat(format);
    setShowExportMenu(false);
    const code = await formattedCode;
    const fileName = exportConfig[format].fileName;
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-12 bg-slate-900/95 border-b border-slate-700/50 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center">
            <GitBranch size={18} className="text-white" />
          </div>
          <span className="font-semibold text-slate-100 text-sm">StateFlow</span>
          <span className="text-xs text-slate-500 hidden sm:inline">状态机生成器</span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={loadExample}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
        >
          <FileCode size={14} />
          <span className="hidden sm:inline">加载示例</span>
        </button>

        <button
          onClick={clearCanvas}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-slate-300 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
        >
          <Trash2 size={14} />
          <span className="hidden sm:inline">清空画布</span>
        </button>

        <div className="w-px h-5 bg-slate-700 mx-1" />

        <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/50 border border-slate-700/50">
          <Wand2 size={12} className="text-amber-400" />
          <span className="text-xs text-slate-400 hidden sm:inline">Prettier</span>
        </div>

        <button
          onClick={handleCopyCode}
          disabled={nodes.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-slate-300 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
          <span className="hidden sm:inline">{copied ? '已复制' : '复制代码'}</span>
        </button>

        <div className="relative">
          <button
            onClick={handleDownload}
            disabled={nodes.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-600 text-white hover:from-cyan-400 hover:to-indigo-500 transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={14} />
            <span className="hidden sm:inline">导出</span>
            <span className="hidden sm:inline">{exportConfig[codeFormat].label.split(' ')[0]}</span>
          </button>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            disabled={nodes.length === 0}
            className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium rounded-lg text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronDown size={14} />
          </button>
          {showExportMenu && (
            <div className="absolute right-0 top-full mt-1 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
              {(Object.keys(exportConfig) as CodeFormat[]).map((format) => (
                <button
                  key={format}
                  onClick={() => handleExportFormat(format)}
                  className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-700/50 hover:text-slate-100 transition-colors"
                >
                  {exportConfig[format].label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
